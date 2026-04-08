#!/bin/bash

# Generate Production Secrets for Railway.app Deployment
# Run: bash generate-secrets.sh

echo "════════════════════════════════════════════════════════════"
echo "  Production Secrets Generator"
echo "════════════════════════════════════════════════════════════"
echo ""

# Check if openssl is available
if ! command -v openssl &> /dev/null; then
    echo "✗ openssl not found. Install it first."
    exit 1
fi

echo "Generating production secrets for Railway.app deployment..."
echo ""

# Generate secrets
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 64)
POSTGRES_PASSWORD=$(openssl rand -hex 16)

echo "════════════════════════════════════════════════════════════"
echo "  COPY THESE INTO RAILWAY DASHBOARD"
echo "════════════════════════════════════════════════════════════"
echo ""

echo "SECRET_KEY:"
echo "$SECRET_KEY"
echo ""

echo "JWT_SECRET_KEY:"
echo "$JWT_SECRET_KEY"
echo ""

echo "POSTGRES_PASSWORD:"
echo "$POSTGRES_PASSWORD"
echo ""

echo "════════════════════════════════════════════════════════════"
echo "  Complete Environment Variables"
echo "════════════════════════════════════════════════════════════"
echo ""

cat << EOF
FLASK_ENV=production
SECRET_KEY=$SECRET_KEY
JWT_SECRET_KEY=$JWT_SECRET_KEY
BACKEND_PORT=5000
POSTGRES_DB=disastersas
POSTGRES_USER=disastersas
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
UPLOAD_FOLDER=/app/uploads
MAX_UPLOAD_BYTES=5242880
EOF

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Steps to Deploy to Railway.app"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "1. Go to https://railway.app"
echo "2. Create new project"
echo "3. Connect your GitHub repository (DisasterSAS)"
echo "4. Add Backend service from Dockerfile"
echo "5. Add PostgreSQL service"
echo "6. Set the environment variables above in Railway dashboard"
echo "7. Click Deploy"
echo "8. Wait for build to complete"
echo "9. Test at the generated Railway URL"
echo ""
echo "✓ Secrets generated successfully!"
echo ""
