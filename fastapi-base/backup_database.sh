#!/bin/bash
# ==================================================================
# DATABASE BACKUP STRATEGY
# Automated PostgreSQL backups with retention policy
# ==================================================================

BACKUP_DIR="/home/ai_team/lab/pipeline_mxh/backups"
DB_CONTAINER="fastapi-base-db-1"
DB_NAME="DBHuYe"
DB_USER="postgres"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/DBHuYe_$DATE.sql"
RETENTION_DAYS=7  # Keep backups for 7 days

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  💾 DATABASE BACKUP                                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Database: $DB_NAME"
echo "Backup to: $BACKUP_FILE"
echo ""

# Create backup
echo "📦 Creating backup..."
docker exec -t "$DB_CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    # Compress backup
    echo "🗜️  Compressing..."
    gzip "$BACKUP_FILE"
    BACKUP_FILE="${BACKUP_FILE}.gz"
    
    # Get file size
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    
    echo "✅ Backup created successfully!"
    echo "   File: $BACKUP_FILE"
    echo "   Size: $SIZE"
else
    echo "❌ Backup failed!"
    exit 1
fi

# Cleanup old backups
echo ""
echo "🧹 Cleaning up old backups (older than $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "DBHuYe_*.sql.gz" -mtime +$RETENTION_DAYS -delete

# Show remaining backups
echo ""
echo "📂 Available backups:"
ls -lh "$BACKUP_DIR"/ | grep "DBHuYe_"

echo ""
echo "✅ Backup complete!"
