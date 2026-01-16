#!/bin/bash
# Setup cron job to fetch AQI data periodically

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Setting up AQI data fetch cron job..."
echo "Project root: $PROJECT_ROOT"

# Add cron job to fetch every 6 hours
CRON_CMD="0 */6 * * * cd $PROJECT_ROOT && docker compose exec -T app python scripts/schedule_aqi_fetch.py >> /tmp/aqi_fetch.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "schedule_aqi_fetch.py"; then
    echo "❌ Cron job already exists. Remove it first with:"
    echo "   crontab -e"
    exit 1
fi

# Add to crontab
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo "✅ Cron job added successfully!"
echo ""
echo "Schedule: Every 6 hours"
echo "Log file: /tmp/aqi_fetch.log"
echo ""
echo "To check cron jobs:"
echo "  crontab -l"
echo ""
echo "To remove this cron job:"
echo "  crontab -e"
echo "  # Then delete the line with 'schedule_aqi_fetch.py'"
