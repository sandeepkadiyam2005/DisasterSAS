# Railway.app - Deploy Using Existing Docker Image

This is the FASTEST deployment method if you have a Docker image URL!

## Step 1: Get Your Docker Image URL

You have two options:

### Option A: Use Your Local Image
Push your local image to Docker Hub first:

```bash
# Login to Docker Hub
docker login

# Tag your image
docker tag disaster-app:latest YOUR_DOCKERHUB_USERNAME/disaster-app:latest

# Push to Docker Hub
docker push YOUR_DOCKERHUB_USERNAME/disaster-app:latest

# Your image URL is:
YOUR_DOCKERHUB_USERNAME/disaster-app:latest
```

### Option B: Use Public Images (If Available)
Or use pre-built images:
- Backend: `python:3.11-slim` (then add your code)
- Frontend: `nginx:alpine`
- Database: `postgres:16-alpine`

---

## Step 2: Deploy to Railway.app

### 2.1 Create Railway Account
1. Go to https://railway.app
2. Sign up with GitHub
3. Create new project

### 2.2 Add Service from Existing Image
1. Click "Add Service"
2. Select **"Existing Image"** tab
3. Enter Image URL:
   ```
   YOUR_DOCKERHUB_USERNAME/disaster-app:latest
   ```

### 2.3 Configure Service

**Port:**
- Set to `5000` (or whatever your Flask app uses)

**Environment Variables:**
- `FLASK_ENV=production`
- `SECRET_KEY=<generate-with: openssl rand -hex 32>`
- `JWT_SECRET_KEY=<generate-with: openssl rand -hex 64>`
- `POSTGRES_PASSWORD=<strong-password>`
- `DATABASE_URI=postgresql+psycopg2://disastersas:PASSWORD@HOST:5432/disastersas`

### 2.4 Add PostgreSQL Database
1. Click "Add Service"
2. Select "Database"
3. Choose "PostgreSQL"
4. Railway auto-configures it

### 2.5 Connect Services
Database URL will be auto-injected as environment variable.

---

## Step 3: Deploy

1. Click "Deploy"
2. Railway pulls the image from Docker Hub
3. Starts the container
4. Services come online in 1-2 minutes

---

## Pre-Built Image Option

If you want the ABSOLUTE FASTEST deploy without Docker Hub:

### Build and Push in One Step:

```bash
# Build for production
docker build -t disaster-app:prod .

# Tag for Docker Hub
docker tag disaster-app:prod YOUR_USERNAME/disaster-app:prod

# Push
docker push YOUR_USERNAME/disaster-app:prod

# Then in Railway, use:
# YOUR_USERNAME/disaster-app:prod
```

---

## Multi-Service Deployment from Images

Deploy all three services from existing images:

### Backend Service
- Image: `YOUR_USERNAME/disaster-app:latest`
- Port: `5000`
- Env: (set all variables)

### Frontend Service (Optional)
- Image: `nginx:alpine`
- Port: `80`
- Volume: Mount your `disaster_frontend/` files
  OR use a custom Nginx image with frontend baked in

### Database Service
- Image: `postgres:16-alpine`
- Port: `5432`
- Env: `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_USER`

---

## Benefits of Using Existing Image

✓ **Faster deployment** (no build required on Railway)
✓ **Tested locally** (you know it works)
✓ **Reusable** (deploy to multiple platforms)
✓ **Version control** (tag different versions)
✓ **Smaller deployments** (image pulled from registry)

---

## Troubleshooting

### Image Not Found
- Verify image is public on Docker Hub
- Check image name spelling
- Make sure you pushed with `docker push`

### Container Starts Then Crashes
- Check environment variables are set correctly
- View logs in Railway: Service → Logs tab
- Verify `DATABASE_URI` format is correct

### Port Not Responding
- Make sure port matches app config (5000 for Flask)
- Check service settings in Railway
- Verify app is listening on `0.0.0.0` not `localhost`

---

## Docker Hub Account Setup (If Needed)

1. Go to https://hub.docker.com
2. Create free account
3. Login locally: `docker login`
4. Push images: `docker push USERNAME/image:tag`
5. Share publicly or keep private

---

## Simplest Path: Docker Compose to Railway

If you want to deploy your entire `docker-compose.yml`:

Railway doesn't directly support docker-compose files, BUT you can:

1. Build each service image locally
2. Push images to Docker Hub
3. Add each as "Existing Image" in Railway
4. Set environment variables
5. Connect services via environment variables

OR use `docker compose push` to push all at once:

```bash
# Tag and push all services
docker compose build
docker compose push
```

---

## Pre-Built vs Build on Railway

| Method | Speed | Cost | Best For |
|--------|-------|------|----------|
| Existing Image | Fastest | Cheaper | Tested, stable |
| Git Repo | Medium | Cheaper | Development |
| Docker Hub | Fast | Free | Production |

---

## Your Next Steps

1. **Push to Docker Hub:**
   ```bash
   docker login
   docker tag disaster-app:latest YOU/disaster-app:latest
   docker push YOU/disaster-app:latest
   ```

2. **Go to Railway.app**

3. **Add Existing Image:**
   - Select "Existing Image" tab
   - URL: `YOU/disaster-app:latest`

4. **Set Environment Variables**

5. **Add PostgreSQL Database**

6. **Deploy!**

Total time: **5-10 minutes**

Your app is LIVE! 🚀
