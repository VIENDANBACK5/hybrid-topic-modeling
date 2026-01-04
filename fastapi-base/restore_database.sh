#!/bin/bash
# ==================================================================
# RESTORE DATABASE FROM BACKUP
# ==================================================================

BACKUP_DIR="/home/ai_team/lab/pipeline_mxh/backups"
DB_CONTAINER="fastapi-base-db-1"
DB_NAME="DBHuYe"
DB_USER="postgres"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  ♻️  DATABASE RESTORE                                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# List available backups
echo "📂 Available backups:"
ls -lht "$BACKUP_DIR"/DBHuYe_*.sql.gz | head -10

echo ""
read -p "Enter backup filename (or 'latest' for most recent): " BACKUP_CHOICE

if [ "$BACKUP_CHOICE" == "latest" ]; then
    BACKUP_FILE=$(ls -t "$BACKUP_DIR"/DBHuYe_*.sql.gz | head -1)
else
    BACKUP_FILE="$BACKUP_DIR/$BACKUP_CHOICE"
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo ""
echo "📦 Restoring from: $BACKUP_FILE"
echo ""
read -p "⚠️  This will DROP and recreate the database. Continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "❌ Restore cancelled"
    exit 0
fi

echo ""
echo "🔄 Restoring database..."

# Decompress and restore
zcat "$BACKUP_FILE" | docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Database restored successfully!"
    echo ""
    echo "📊 Verifying restore:"
    docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
        SELECT 
            'articles' as table_name, COUNT(*) as rows FROM articles
        UNION ALL
        SELECT 'sentiment_analysis', COUNT(*) FROM sentiment_analysis;
    "
else
    echo "❌ Restore failed!"
    exit 1
fi
