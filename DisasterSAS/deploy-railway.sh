#!/bin/bash

# Railway.app Deployment Script
# Requires: git, railway CLI

set -e

echo "═══════════════════════════════════════════════════════"
echo "  Disaster Safety App - Railway.app Deployment Setup"
echo "═══════════════════════════════════════════════════════"
echo ""

# Check dependencies
echo "✓ Checking dependencies..."
command -v git >/dev/null 2>&1 || { echo "git not found. Install: https://git-scm.com"; exit 1; }
echo "  ✓ git found"

command -v railway >/dev/null 2>&1 || {
    echo "  ⚠ railway CLI not found"
    echo "  Install from: https://railway.app/install"
    echo "  Then run: railway login"
    exit 1
}
echo "  ✓ railway CLI found"

echo ""
echo "✓ Initializing Git repository..."
if [ ! -d .git ]; then
    git init
    git add .
    git commit -m "Initial commit - Disaster Safety App containerized"
    echo "  ✓ Git repo created"
else
    echo "  ✓ Git repo already exists"
fi

echo ""
echo "✓ Environment Setup"
if [ ! -f .env ]; then
    cp .env.example .env
    echo "  ✓ .env created from .env.example"
    echo "  ⚠ IMPORTANT: Update .env with production secrets before deploying"
else
    echo "  ✓ .env already exists"
fi

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Next Steps for Railway.app Deployment"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "1. Update .env with production secrets:"
echo "   nano .env"
echo ""
echo "2. Push to GitHub (if not already there):"
echo "   git remote add origin <your-github-repo-url>"
echo "   git push -u origin main"
echo ""
echo "3. Go to https://railway.app and:"
echo "   a) Create new project"
echo "   b) Connect GitHub repository"
echo "   c) Add services:"
echo "      - Backend (Dockerfile)"
echo "      - PostgreSQL (plugin)"
echo "      - Frontend (optional, Nginx)"
echo "   d) Set environment variables"
echo "   e) Deploy"
echo ""
echo "4. Configure domain:"
echo "   - Point DNS A record to Railway domain"
echo "   - Enable Railway's auto-HTTPS"
echo ""
echo "═══════════════════════════════════════════════════════"
echo ""
