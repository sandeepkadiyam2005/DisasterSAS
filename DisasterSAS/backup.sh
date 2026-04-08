#!/bin/bash

# Backup and Monitoring Script for Disaster Safety App
# Add to crontab: 0 2 * * * /opt/disaster-app/backup.sh

BACKUP_DIR="/opt/disaster-app/backups"
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30
APP_DIR="/opt/disaster-app"

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "════════════════════════════════════════════════════════"
echo "Backup started: $(date)"
echo "════════════════════════════════════════════════════════"

# 1. Backup PostgreSQL database
echo ""
echo "✓ Backing up PostgreSQL database..."
cd "$APP_DIR"

docker compose exec -T db pg_dump \
    -U disastersas \
    -d disastersas \
    --format=plain \
    > "$BACKUP_DIR/database_$BACKUP_DATE.sql" 2>&1 || {
    echo "✗ Database backup failed!"
    exit 1
}

echo "  ✓ Database backed up: database_$BACKUP_DATE.sql"

# 2. Compress backup
echo ""
echo "✓ Compressing backup..."
gzip "$BACKUP_DIR/database_$BACKUP_DATE.sql"
echo "  ✓ Compressed: database_$BACKUP_DATE.sql.gz"

# 3. Backup uploaded files volume
echo ""
echo "✓ Backing up uploads volume..."
docker run --rm \
    -v "${APP_DIR##*/}_uploads:/data" \
    -v "$BACKUP_DIR:/backup" \
    alpine tar czf "/backup/uploads_$BACKUP_DATE.tar.gz" -C /data . 2>&1 || {
    echo "⚠ Uploads backup skipped (volume may be empty)"
}

if [ -f "$BACKUP_DIR/uploads_$BACKUP_DATE.tar.gz" ]; then
    echo "  ✓ Uploads backed up: uploads_$BACKUP_DATE.tar.gz"
fi

# 4. Cleanup old backups (keep 30 days)
echo ""
echo "✓ Cleaning up old backups (>$RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "*.gz" -mtime +$RETENTION_DAYS -delete
echo "  ✓ Cleanup complete"

# 5. List recent backups
echo ""
echo "✓ Recent backups:"
ls -lh "$BACKUP_DIR" | tail -5

# 6. Health check
echo ""
echo "✓ Health check:"
if docker compose ps | grep -q "Up"; then
    echo "  ✓ All services running"
else
    echo "  ✗ Warning: Some services not running"
fi

# 7. Disk usage
echo ""
echo "✓ Disk usage:"
du -sh "$BACKUP_DIR" | awk '{print "  Backups: " $0}'
docker system df | grep -E "TYPE|local" | awk '{print "  Docker: " $0}'

echo ""
echo "════════════════════════════════════════════════════════"
echo "Backup completed: $(date)"
echo "════════════════════════════════════════════════════════"

# Optional: Upload to cloud storage (AWS S3, Google Cloud, etc.)
# aws s3 cp "$BACKUP_DIR/database_$BACKUP_DATE.sql.gz" s3://your-bucket/backups/
# gsutil cp "$BACKUP_DIR/database_$BACKUP_DATE.sql.gz" gs://your-bucket/backups/
