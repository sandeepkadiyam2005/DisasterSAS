# Docker Deployment Guide

## Quick Start

### 1. Production Deployment
```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

### 2. Development with Hot Reload
```bash
# Start with file watchers for live code changes
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Changes to disaster_backend/ and disaster_frontend/ sync automatically
```

### 3. Health Checks
```bash
# Check service status
docker compose ps

# View logs from specific service
docker compose logs backend
docker compose logs frontend
docker compose logs db

# Manual health check
./health-check.sh
```

## Environment Variables

Copy `.env.example` to `.env` and update with your values:
```bash
cp .env.example .env
```

**Critical secrets to change in production:**
- `SECRET_KEY` — Flask session secret
- `JWT_SECRET_KEY` — JWT token signing key
- `POSTGRES_PASSWORD` — Database password

## Service Details

### Backend (Flask)
- **Port:** 5000
- **Health:** `GET http://localhost:5000/api/health`
- **API:** `http://localhost:5000/api/*`

### Frontend (Nginx)
- **Port:** 3000
- **Health:** `GET http://localhost:3000/`
- **Proxies:** `/api/*` → backend

### Database (PostgreSQL)
- **Port:** 5432
- **User:** disastersas (from .env)
- **Data:** `/var/lib/postgresql/data` (postgres_data volume)

## Troubleshooting

### Container won't start
```bash
docker compose logs <service_name>
```

### Database connection errors
```bash
docker compose exec db psql -U disastersas -d disastersas -c "\dt"
```

### Port already in use
Update `.env`:
```bash
BACKEND_PORT=5001
FRONTEND_PORT=3001
POSTGRES_PORT=5433
```

### Rebuild without cache
```bash
docker compose build --no-cache
docker compose up
```

## Production Checklist

- [ ] Update `.env` with strong secret keys
- [ ] Use environment-specific configs (no hardcoded secrets)
- [ ] Enable HTTPS/TLS at reverse proxy level
- [ ] Set `FLASK_ENV=production`
- [ ] Backup PostgreSQL volumes regularly
- [ ] Monitor container health with `docker stats`
- [ ] Use `restart: unless-stopped` for auto-recovery (already set)
