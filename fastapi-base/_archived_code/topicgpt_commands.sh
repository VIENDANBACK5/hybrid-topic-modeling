#!/bin/bash
# TopicGPT Smart Crawl - Quick Commands
# ======================================

BASE_URL="http://localhost:8000/api/crawl"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     TopicGPT Smart Crawl Commands         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# Function to pretty print JSON
pretty() {
    python3 -m json.tool
}

# 1. SMART CRAWL - Balanced Mode (RECOMMENDED)
smart_crawl_balanced() {
    echo -e "${GREEN}📊 Smart Crawl - Balanced Mode${NC}"
    curl -X POST "$BASE_URL/smart" \
        -H "Content-Type: application/json" \
        -d '{
            "url": "'"$1"'",
            "mode": "max",
            "enable_llm_enrichment": true,
            "enable_semantic_dedupe": true,
            "enable_auto_categorization": true,
            "priority": "balanced"
        }' | pretty
}

# 2. SMART CRAWL - High Quality
smart_crawl_high() {
    echo -e "${GREEN}🌟 Smart Crawl - High Quality${NC}"
    curl -X POST "$BASE_URL/smart" \
        -H "Content-Type: application/json" \
        -d '{
            "url": "'"$1"'",
            "mode": "max",
            "force_enrich_all": true,
            "priority": "high",
            "max_cost": 5.0
        }' | pretty
}

# 3. SMART CRAWL - Low Cost
smart_crawl_low() {
    echo -e "${GREEN}💰 Smart Crawl - Low Cost${NC}"
    curl -X POST "$BASE_URL/smart" \
        -H "Content-Type: application/json" \
        -d '{
            "url": "'"$1"'",
            "mode": "max",
            "enable_llm_enrichment": false,
            "enable_semantic_dedupe": true,
            "priority": "low"
        }' | pretty
}

# 4. COST REPORT
cost_report() {
    echo -e "${GREEN}📊 Cost Report${NC}"
    curl -s "$BASE_URL/cost/report" | pretty
}

# 5. SET BUDGET
set_budget() {
    echo -e "${GREEN}💵 Set Daily Budget: \$$1${NC}"
    curl -X POST "$BASE_URL/cost/set-budget?daily_budget=$1" | pretty
}

# 6. ESTIMATE COST
estimate_cost() {
    echo -e "${GREEN}🧮 Estimate Crawl Cost${NC}"
    curl -X POST "$BASE_URL/cost/estimate" \
        -H "Content-Type: application/json" \
        -d '{
            "url": "'"$1"'",
            "enable_llm_enrichment": true,
            "enable_semantic_dedupe": true
        }' | pretty
}

# 7. PIPELINE STATS
pipeline_stats() {
    echo -e "${GREEN}📈 Pipeline Statistics${NC}"
    curl -s "$BASE_URL/pipeline/stats" | pretty
}

# 8. CONFIGURE PIPELINE
configure_pipeline() {
    echo -e "${GREEN}⚙️ Configure Pipeline${NC}"
    curl -X POST "$BASE_URL/pipeline/configure" \
        -H "Content-Type: application/json" \
        -d '{
            "enable_llm_enrichment": true,
            "enable_semantic_dedupe": true,
            "similarity_threshold": 0.85,
            "priority": "balanced"
        }' | pretty
}

# Menu
show_menu() {
    echo -e "${YELLOW}Usage:${NC}"
    echo "  1. Smart Crawl (Balanced):  ./topicgpt_commands.sh balanced <URL>"
    echo "  2. Smart Crawl (High):      ./topicgpt_commands.sh high <URL>"
    echo "  3. Smart Crawl (Low):       ./topicgpt_commands.sh low <URL>"
    echo "  4. Cost Report:             ./topicgpt_commands.sh report"
    echo "  5. Set Budget:              ./topicgpt_commands.sh budget <amount>"
    echo "  6. Estimate Cost:           ./topicgpt_commands.sh estimate <URL>"
    echo "  7. Pipeline Stats:          ./topicgpt_commands.sh stats"
    echo "  8. Configure:               ./topicgpt_commands.sh configure"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo "  ./topicgpt_commands.sh balanced https://vnexpress.net"
    echo "  ./topicgpt_commands.sh report"
    echo "  ./topicgpt_commands.sh budget 20.0"
    echo ""
}

# Main
case "$1" in
    balanced)
        if [ -z "$2" ]; then
            echo "Error: URL required"
            show_menu
            exit 1
        fi
        smart_crawl_balanced "$2"
        ;;
    high)
        if [ -z "$2" ]; then
            echo "Error: URL required"
            show_menu
            exit 1
        fi
        smart_crawl_high "$2"
        ;;
    low)
        if [ -z "$2" ]; then
            echo "Error: URL required"
            show_menu
            exit 1
        fi
        smart_crawl_low "$2"
        ;;
    report)
        cost_report
        ;;
    budget)
        if [ -z "$2" ]; then
            echo "Error: Budget amount required"
            show_menu
            exit 1
        fi
        set_budget "$2"
        ;;
    estimate)
        if [ -z "$2" ]; then
            echo "Error: URL required"
            show_menu
            exit 1
        fi
        estimate_cost "$2"
        ;;
    stats)
        pipeline_stats
        ;;
    configure)
        configure_pipeline
        ;;
    *)
        show_menu
        ;;
esac
