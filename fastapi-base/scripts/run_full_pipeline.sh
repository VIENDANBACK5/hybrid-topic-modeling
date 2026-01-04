#!/bin/bash
# run_full_pipeline.sh - Chạy toàn bộ pipeline từ command line

set -e  # Exit on error

echo "🚀 Starting Full Data Processing Pipeline"
echo "==========================================="

# Configuration
API_URL="${API_URL:-http://localhost:7777}"
LIMIT="${LIMIT:-500}"
BACKGROUND="${BACKGROUND:-false}"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if API is running
echo -e "${BLUE}Checking API health...${NC}"
if ! curl -s "${API_URL}/health" > /dev/null; then
    echo -e "${RED}❌ API is not running at ${API_URL}${NC}"
    echo "Please start the API first: uvicorn app.main:app --host 0.0.0.0 --port 7777"
    exit 1
fi
echo -e "${GREEN}✅ API is running${NC}"

# Get current status
echo -e "\n${BLUE}📊 Current system status:${NC}"
curl -s "${API_URL}/api/orchestrator/status" | python3 -m json.tool

# Run pipeline
echo -e "\n${BLUE}🚀 Starting pipeline execution...${NC}"
echo "Configuration:"
echo "  - Limit: ${LIMIT} articles"
echo "  - Background: ${BACKGROUND}"
echo ""

if [ "$BACKGROUND" = "true" ]; then
    # Run in background
    RESPONSE=$(curl -s -X POST "${API_URL}/api/orchestrator/run-full-pipeline?background=true" \
        -H "Content-Type: application/json" \
        -d "{
            \"sync_data\": false,
            \"classify_topics\": true,
            \"analyze_sentiment\": true,
            \"calculate_statistics\": true,
            \"regenerate_keywords\": true,
            \"train_bertopic\": false,
            \"limit\": ${LIMIT}
        }")
    
    echo -e "${GREEN}✅ Pipeline started in background${NC}"
    echo "$RESPONSE" | python3 -m json.tool
    echo ""
    echo "Check logs for progress: tail -f logs/app.log"
else
    # Run synchronously (wait for completion)
    echo "This may take a few minutes..."
    echo ""
    
    RESPONSE=$(curl -s -X POST "${API_URL}/api/orchestrator/run-full-pipeline" \
        -H "Content-Type: application/json" \
        -d "{
            \"sync_data\": false,
            \"classify_topics\": true,
            \"analyze_sentiment\": true,
            \"calculate_statistics\": true,
            \"regenerate_keywords\": true,
            \"train_bertopic\": false,
            \"limit\": ${LIMIT}
        }")
    
    # Parse result
    STATUS=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))")
    
    if [ "$STATUS" = "completed" ]; then
        echo -e "${GREEN}✅ Pipeline completed successfully!${NC}"
    elif [ "$STATUS" = "completed_with_errors" ]; then
        echo -e "${RED}⚠️  Pipeline completed with errors${NC}"
    else
        echo -e "${RED}❌ Pipeline failed${NC}"
    fi
    
    echo ""
    echo "Full result:"
    echo "$RESPONSE" | python3 -m json.tool
fi

# Show final status
echo -e "\n${BLUE}📊 Final system status:${NC}"
curl -s "${API_URL}/api/orchestrator/status" | python3 -m json.tool

echo ""
echo "==========================================="
echo -e "${GREEN}✅ Pipeline execution completed${NC}"
echo ""
echo "Next steps:"
echo "  - Check Superset dashboard for updated visualizations"
echo "  - Review logs: logs/app.log"
echo "  - API docs: ${API_URL}/docs"
