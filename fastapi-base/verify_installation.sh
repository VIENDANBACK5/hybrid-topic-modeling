#!/bin/bash
# TopicGPT Integration - Verification Checklist
# ==============================================

echo "🔍 TopicGPT Integration - Verification Checklist"
echo "=================================================="
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

passed=0
failed=0

# Function to check file exists
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $2"
        ((passed++))
        return 0
    else
        echo -e "${RED}✗${NC} $2 (File not found: $1)"
        ((failed++))
        return 1
    fi
}

# Function to check directory exists
check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $2"
        ((passed++))
        return 0
    else
        echo -e "${RED}✗${NC} $2 (Directory not found: $1)"
        ((failed++))
        return 1
    fi
}

# Function to check Python syntax
check_python_syntax() {
    if python3 -m py_compile "$1" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $2 (syntax OK)"
        ((passed++))
        return 0
    else
        echo -e "${RED}✗${NC} $2 (syntax error)"
        ((failed++))
        return 1
    fi
}

echo "📦 1. Core Service Files"
echo "------------------------"
check_file "app/services/topic/topicgpt_service.py" "TopicGPTService"
check_file "app/services/crawler/smart_pipeline.py" "SmartCrawlerPipeline"
check_file "app/services/crawler/llm_content_enricher.py" "LLMContentEnricher"
check_file "app/services/etl/hybrid_dedupe.py" "HybridDeduplicator"
check_file "app/services/crawler/cost_optimizer.py" "CostOptimizer"
echo ""

echo "🌐 2. API Integration"
echo "---------------------"
check_file "app/api/routers/crawl.py" "Enhanced crawl.py"
if [ -f "app/api/routers/crawl.py" ]; then
    if grep -q "POST /api/crawl/smart" app/api/routers/crawl.py 2>/dev/null || \
       grep -q "smart_crawl" app/api/routers/crawl.py 2>/dev/null || \
       grep -q "SmartCrawlRequest" app/api/routers/crawl.py 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Smart endpoints found in crawl.py"
        ((passed++))
    else
        echo -e "${YELLOW}⚠${NC} Smart endpoints may not be in crawl.py"
    fi
fi
echo ""

echo "⚙️ 3. Configuration Files"
echo "-------------------------"
check_file "app/config/topicgpt_config.yaml" "Configuration file"
check_file ".env" "Environment variables" || echo -e "${YELLOW}⚠${NC} .env not found (create it with API keys)"
echo ""

echo "📁 4. Required Directories"
echo "--------------------------"
check_dir "data/cache/topicgpt" "Cache directory" || mkdir -p data/cache/topicgpt
check_dir "data/results/topicgpt" "Results directory" || mkdir -p data/results/topicgpt
check_dir "logs" "Logs directory" || mkdir -p logs
echo ""

echo "📚 5. Documentation Files"
echo "-------------------------"
check_file "TOPICGPT_README.md" "Quick reference"
check_file "TOPICGPT_INTEGRATION_GUIDE.md" "Integration guide"
check_file "TOPICGPT_INSTALLATION.md" "Installation guide"
check_file "FILES_SUMMARY.md" "Files summary"
check_file "IMPLEMENTATION_COMPLETE.md" "Implementation summary"
echo ""

echo "🧪 6. Testing Files"
echo "-------------------"
check_file "test_topicgpt.py" "Test suite"
check_file "topicgpt_commands.sh" "Shell commands"
if [ -f "test_topicgpt.py" ] && [ -x "test_topicgpt.py" ]; then
    echo -e "${GREEN}✓${NC} test_topicgpt.py is executable"
    ((passed++))
elif [ -f "test_topicgpt.py" ]; then
    echo -e "${YELLOW}⚠${NC} test_topicgpt.py is not executable (run: chmod +x test_topicgpt.py)"
fi
if [ -f "topicgpt_commands.sh" ] && [ -x "topicgpt_commands.sh" ]; then
    echo -e "${GREEN}✓${NC} topicgpt_commands.sh is executable"
    ((passed++))
elif [ -f "topicgpt_commands.sh" ]; then
    echo -e "${YELLOW}⚠${NC} topicgpt_commands.sh is not executable (run: chmod +x topicgpt_commands.sh)"
fi
echo ""

echo "✅ 7. Python Syntax Check"
echo "--------------------------"
check_python_syntax "app/services/topic/topicgpt_service.py" "TopicGPTService syntax"
check_python_syntax "app/services/crawler/smart_pipeline.py" "SmartCrawlerPipeline syntax"
check_python_syntax "app/services/crawler/llm_content_enricher.py" "LLMContentEnricher syntax"
check_python_syntax "app/services/etl/hybrid_dedupe.py" "HybridDeduplicator syntax"
check_python_syntax "app/services/crawler/cost_optimizer.py" "CostOptimizer syntax"
echo ""

echo "📦 8. Python Dependencies"
echo "-------------------------"
if python3 -c "import openai" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} openai package installed"
    ((passed++))
else
    echo -e "${RED}✗${NC} openai package not found (run: pip install openai)"
    ((failed++))
fi

if python3 -c "import google.generativeai" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} google-generativeai package installed"
    ((passed++))
else
    echo -e "${YELLOW}⚠${NC} google-generativeai not found (optional, run: pip install google-generativeai)"
fi
echo ""

echo "🔑 9. API Keys"
echo "--------------"
if [ ! -z "$OPENAI_API_KEY" ]; then
    echo -e "${GREEN}✓${NC} OPENAI_API_KEY is set"
    ((passed++))
else
    echo -e "${RED}✗${NC} OPENAI_API_KEY not set (run: export OPENAI_API_KEY=sk-xxx)"
    ((failed++))
fi

if [ ! -z "$GEMINI_API_KEY" ]; then
    echo -e "${GREEN}✓${NC} GEMINI_API_KEY is set (optional)"
else
    echo -e "${YELLOW}⚠${NC} GEMINI_API_KEY not set (optional)"
fi
echo ""

echo "🔍 10. Code Statistics"
echo "----------------------"
if [ -f "app/services/topic/topicgpt_service.py" ]; then
    lines=$(wc -l < app/services/topic/topicgpt_service.py)
    echo "   TopicGPTService: $lines lines"
fi
if [ -f "app/services/crawler/smart_pipeline.py" ]; then
    lines=$(wc -l < app/services/crawler/smart_pipeline.py)
    echo "   SmartCrawlerPipeline: $lines lines"
fi
if [ -f "app/services/crawler/llm_content_enricher.py" ]; then
    lines=$(wc -l < app/services/crawler/llm_content_enricher.py)
    echo "   LLMContentEnricher: $lines lines"
fi
if [ -f "app/services/etl/hybrid_dedupe.py" ]; then
    lines=$(wc -l < app/services/etl/hybrid_dedupe.py)
    echo "   HybridDeduplicator: $lines lines"
fi
if [ -f "app/services/crawler/cost_optimizer.py" ]; then
    lines=$(wc -l < app/services/crawler/cost_optimizer.py)
    echo "   CostOptimizer: $lines lines"
fi
echo ""

echo "=================================================="
echo "📊 Summary"
echo "=================================================="
echo -e "${GREEN}Passed:${NC} $passed"
if [ $failed -gt 0 ]; then
    echo -e "${RED}Failed:${NC} $failed"
fi
echo ""

if [ $failed -eq 0 ]; then
    echo -e "${GREEN}🎉 All checks passed! Integration is complete.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Set API key: export OPENAI_API_KEY=sk-xxx"
    echo "2. Test: python3 test_topicgpt.py report"
    echo "3. Run: python3 test_topicgpt.py balanced https://vnexpress.net"
    echo ""
else
    echo -e "${RED}⚠️  Some checks failed. Please fix the issues above.${NC}"
    echo ""
fi

exit $failed
