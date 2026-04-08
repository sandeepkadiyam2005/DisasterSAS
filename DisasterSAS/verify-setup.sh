#!/bin/bash
set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Docker Setup Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "✓ Checking required files..."
files=(
  "Dockerfile"
  "docker-compose.yml"
  ".dockerignore"
  ".env"
  ".env.example"
  "nginx.conf"
)

for file in "${files[@]}"; do
  if [ -f "$file" ]; then
    echo "  ✓ $file"
  else
    echo "  ✗ MISSING: $file"
    exit 1
  fi
done

echo ""
echo "✓ Checking Docker installation..."
docker --version
docker compose version

echo ""
echo "✓ Checking image status..."
docker images disaster-app:latest --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}"

echo ""
echo "✓ Validating docker-compose.yml..."
docker compose config --quiet && echo "  ✓ Configuration valid"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  All checks passed! Ready to deploy."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next steps:"
echo "  1. Review .env and update secrets for production"
echo "  2. Run: docker compose up -d"
echo "  3. Monitor: docker compose logs -f"
echo ""
