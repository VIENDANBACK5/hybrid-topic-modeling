#!/bin/bash
# ==================================================================
# LOAD FULL DATASET - Sync all 7692 posts from external API
# ==================================================================

set -e

API_BASE="http://localhost:7777/api/v1/sync"
API_KEY="dev-key-12345"
SOURCE_API="http://192.168.30.28:8000"
TOTAL_EXPECTED=7692

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  📥 LOADING FULL DATASET FROM EXTERNAL API                   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Source: $SOURCE_API"
echo "Expected: ~$TOTAL_EXPECTED posts"
echo ""

# Function to check sync status
check_status() {
    curl -s "$API_BASE/status" | jq -r '.status'
}

# Function to get current count
get_current_count() {
    curl -s "$API_BASE/db-stats" | jq -r '.tables.articles'
}

echo "📊 Current database status:"
INITIAL_COUNT=$(get_current_count)
echo "   Articles in DB: $INITIAL_COUNT"
echo ""

# Calculate how many batches needed
# External API returns ~10 posts per request, so need many iterations
BATCH_SIZE=50
MAX_ITERATIONS=200  # Should be enough to get all 7692

echo "🚀 Starting sync process..."
echo "   Batch size: $BATCH_SIZE"
echo "   Max iterations: $MAX_ITERATIONS"
echo ""

SUCCESSFUL_SYNCS=0
FAILED_SYNCS=0

for i in $(seq 1 $MAX_ITERATIONS); do
    echo -n "[$i/$MAX_ITERATIONS] Triggering sync... "
    
    # Trigger sync
    RESPONSE=$(curl -s -X POST "$API_BASE/trigger" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d "{\"source_api_base\": \"$SOURCE_API\", \"endpoint\": \"/api/v1/posts\", \"limit\": $BATCH_SIZE, \"batch_size\": $BATCH_SIZE}")
    
    STATUS=$(echo "$RESPONSE" | jq -r '.status')
    
    if [ "$STATUS" == "running" ]; then
        echo -n "started... "
        SUCCESSFUL_SYNCS=$((SUCCESSFUL_SYNCS + 1))
    else
        echo "❌ failed"
        FAILED_SYNCS=$((FAILED_SYNCS + 1))
        echo "   Response: $RESPONSE"
        sleep 2
        continue
    fi
    
    # Wait for completion
    WAIT_COUNT=0
    MAX_WAIT=20
    while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
        sleep 1
        CURRENT_STATUS=$(check_status)
        
        if [ "$CURRENT_STATUS" == "completed" ] || [ "$CURRENT_STATUS" == "idle" ]; then
            CURRENT_COUNT=$(get_current_count)
            echo "✅ done (Total: $CURRENT_COUNT)"
            break
        elif [ "$CURRENT_STATUS" == "failed" ]; then
            echo "❌ sync failed"
            FAILED_SYNCS=$((FAILED_SYNCS + 1))
            break
        fi
        
        WAIT_COUNT=$((WAIT_COUNT + 1))
    done
    
    if [ $WAIT_COUNT -eq $MAX_WAIT ]; then
        echo "⏱️  timeout"
    fi
    
    # Check if we've reached all data
    CURRENT_COUNT=$(get_current_count)
    if [ $CURRENT_COUNT -ge $TOTAL_EXPECTED ]; then
        echo ""
        echo "🎉 All data loaded! ($CURRENT_COUNT posts)"
        break
    fi
    
    # Small delay between requests
    sleep 1
done

# Final status
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  📊 SYNC COMPLETE - FINAL STATUS                             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

FINAL_COUNT=$(get_current_count)
NEW_POSTS=$((FINAL_COUNT - INITIAL_COUNT))

echo "Initial count:    $INITIAL_COUNT posts"
echo "Final count:      $FINAL_COUNT posts"
echo "New posts added:  $NEW_POSTS posts"
echo "Successful syncs: $SUCCESSFUL_SYNCS"
echo "Failed syncs:     $FAILED_SYNCS"
echo ""

if [ $FINAL_COUNT -ge $TOTAL_EXPECTED ]; then
    echo "✅ SUCCESS: All data loaded!"
elif [ $NEW_POSTS -gt 0 ]; then
    echo "⚠️  PARTIAL: Got $NEW_POSTS new posts (expected ~$TOTAL_EXPECTED)"
else
    echo "❌ FAILED: No new posts added"
fi

echo ""
echo "📊 Final database stats:"
curl -s "$API_BASE/db-stats" | jq

echo ""
echo "🎯 Next step: Re-run fill_all_tables.py to populate statistics"
echo "   $ docker exec fastapi-base-app-1 python /app/fill_all_tables.py"
