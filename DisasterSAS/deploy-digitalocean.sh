#!/bin/bash

# DigitalOcean Droplet Setup Script
# Run this on your droplet after initial SSH

set -e

echo "═══════════════════════════════════════════════════════"
echo "  Disaster Safety App - DigitalOcean Setup"
echo "═══════════════════════════════════════════════════════"
echo ""

# Variables
DOMAIN="${1:-localhost}"
EMAIL="${2:-admin@example.com}"

if [ "$DOMAIN" = "localhost" ]; then
    echo "⚠ No domain provided. Usage: ./deploy-digitalocean.sh your-domain.com admin@email.com"
    echo "  Proceeding with localhost setup..."
fi

echo "✓ Updating system packages..."
apt-get update
apt-get upgrade -y

echo ""
echo "✓ Installing Docker..."
apt-get install -y curl
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker root

echo ""
echo "✓ Installing Docker Compose..."
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

echo ""
echo "✓ Installing Git..."
apt-get install -y git

echo ""
echo "✓ Installing Caddy (reverse proxy)..."
apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.caddy.community/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-archive-keyring.gpg
curl -1sLf 'https://dl.caddy.community/deb/caddy.repo' | tee /etc/apt/sources.list.d/caddy-caddy.list
apt-get update
apt-get install -y caddy

echo ""
echo "✓ Setting up firewall..."
apt-get install -y ufw
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
echo "y" | ufw enable

echo ""
echo "✓ Creating app directory..."
mkdir -p /opt/disaster-app
cd /opt/disaster-app

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Setup Complete!"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo ""
echo "1. Clone your repository:"
echo "   git clone <your-repo-url> ."
echo ""
echo "2. Setup environment:"
echo "   cp .env.example .env"
echo "   # Edit .env with production secrets"
echo "   nano .env"
echo ""
echo "3. Start services:"
echo "   docker compose up -d"
echo ""
echo "4. Setup HTTPS (if using domain):"
echo "   Edit /etc/caddy/Caddyfile:"
echo "   cat > /etc/caddy/Caddyfile << 'EOF'"
echo "   $DOMAIN {"
echo "       reverse_proxy localhost:3000 {"
echo "           header_up X-Forwarded-Proto https"
echo "       }"
echo "   }"
echo "   EOF"
echo ""
echo "   systemctl restart caddy"
echo ""
echo "5. Verify services:"
echo "   docker compose ps"
echo "   curl http://localhost:5000/api/health"
echo ""
echo "6. Setup automatic backups (crontab):"
echo "   crontab -e"
echo "   # Add: 0 2 * * * /opt/disaster-app/backup.sh"
echo ""
