#!/bin/bash

# Add a /health endpoint to your Flask app (disaster_backend/app.py or routes)
# For now, this is a helper script to test health checks manually

echo "Testing backend health..."
curl -f http://localhost:5000/health && echo "✓ Backend healthy" || echo "✗ Backend unhealthy"

echo ""
echo "Testing frontend health..."
curl -s http://localhost:3000/ | head -20 && echo "✓ Frontend healthy" || echo "✗ Frontend unhealthy"

echo ""
echo "Testing database connection..."
docker compose exec db pg_isready -U disastersas && echo "✓ Database healthy" || echo "✗ Database unhealthy"
