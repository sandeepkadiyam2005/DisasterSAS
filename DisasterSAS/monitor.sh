#!/bin/bash

# Monitoring Script - Check system and app health
# Run: ./monitor.sh or add to crontab: */5 * * * * /opt/disaster-app/monitor.sh

APP_DIR="/opt/disaster-app"
LOG_FILE="/var/log/disaster-app-monitor.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

echo "════════════════════════════════════════════════════════"
echo "System & Application Health Check"
echo "════════════════════════════════════════════════════════"
log "Health check started"

cd "$APP_DIR" || exit 1

# 1. Check Docker services
echo ""
echo "✓ Docker Services Status:"
SERVICES=$(docker compose ps --services)
for service in $SERVICES; do
    if docker compose ps "$service" | grep -q "Up"; then
        echo -e "  ${GREEN}✓${NC} $service is running"
        log "$service is running"
    else
        echo -e "  ${RED}✗${NC} $service is NOT running"
        log "ALERT: $service is NOT running"
    fi
done

# 2. Check API health endpoint
echo ""
echo "✓ Backend API Health:"
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/api/health)
if [ "$HEALTH" = "200" ]; then
    echo -e "  ${GREEN}✓${NC} API responding (HTTP $HEALTH)"
    log "API is healthy (HTTP $HEALTH)"
else
    echo -e "  ${RED}✗${NC} API not responding correctly (HTTP $HEALTH)"
    log "ALERT: API returned HTTP $HEALTH"
fi

# 3. Check database connectivity
echo ""
echo "✓ Database Connectivity:"
DB_CHECK=$(docker compose exec -T db pg_isready -U disastersas -d disastersas 2>&1)
if echo "$DB_CHECK" | grep -q "accepting connections"; then
    echo -e "  ${GREEN}✓${NC} Database is healthy"
    log "Database is healthy"
else
    echo -e "  ${RED}✗${NC} Database connection failed"
    log "ALERT: Database connection failed - $DB_CHECK"
fi

# 4. Check disk space
echo ""
echo "✓ Disk Space:"
DISK=$(df / | awk 'NR==2 {print int($5)}')
if [ "$DISK" -lt 90 ]; then
    echo -e "  ${GREEN}✓${NC} Disk usage: $DISK%"
    log "Disk usage: $DISK%"
else
    echo -e "  ${RED}✗${NC} Disk usage: $DISK% (LOW SPACE WARNING)"
    log "ALERT: Disk usage is $DISK% - LOW SPACE"
fi

# 5. Check memory usage
echo ""
echo "✓ Memory Usage:"
MEMORY=$(free | awk 'NR==2 {printf("%.0f", $3/$2 * 100.0)}')
if [ "$MEMORY" -lt 90 ]; then
    echo -e "  ${GREEN}✓${NC} Memory usage: $MEMORY%"
    log "Memory usage: $MEMORY%"
else
    echo -e "  ${YELLOW}⚠${NC} Memory usage: $MEMORY% (HIGH)"
    log "WARNING: Memory usage is high ($MEMORY%)"
fi

# 6. Check CPU load
echo ""
echo "✓ CPU Load Average:"
LOAD=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}')
echo "  Load average: $LOAD"
log "Load average: $LOAD"

# 7. Check container logs for errors
echo ""
echo "✓ Recent Errors (last 5 minutes):"
ERROR_COUNT=$(docker compose logs --since 5m backend 2>&1 | grep -i "error\|exception\|warning" | wc -l)
if [ "$ERROR_COUNT" -eq 0 ]; then
    echo -e "  ${GREEN}✓${NC} No errors detected"
    log "No recent errors"
else
    echo -e "  ${YELLOW}⚠${NC} Found $ERROR_COUNT error/warning entries"
    log "WARNING: Found $ERROR_COUNT error entries in logs"
    echo "  Sample errors:"
    docker compose logs --since 5m backend 2>&1 | grep -i "error\|exception" | head -3 | sed 's/^/    /'
fi

# 8. Check certificate expiry (if using SSL)
echo ""
echo "✓ SSL Certificate (if applicable):"
CERT_FILE="/etc/letsencrypt/live/*/cert.pem"
if ls $CERT_FILE 1> /dev/null 2>&1; then
    EXPIRY=$(openssl x509 -enddate -noout -in $CERT_FILE | cut -d= -f2 2>/dev/null)
    echo "  Certificate expires: $EXPIRY"
    log "Certificate expires: $EXPIRY"
else
    echo "  No SSL certificate found (OK if using Caddy auto-renewal)"
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo "Health check completed: $(date)"
echo "════════════════════════════════════════════════════════"
log "Health check completed"

# Exit with error if any critical service is down
if ! docker compose ps | grep -q "Up.*backend"; then
    log "CRITICAL: Backend service is down"
    exit 1
fi

if ! docker compose ps | grep -q "Up.*db"; then
    log "CRITICAL: Database service is down"
    exit 1
fi

exit 0
