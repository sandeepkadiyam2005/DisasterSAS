# Push Docker Image to Docker Hub & Deploy to Railway

## Step 1: Create Docker Hub Account (2 minutes)

1. Go to https://hub.docker.com/signup
2. Create account (free)
3. Verify email
4. Create username (remember this!)

---

## Step 2: Login to Docker Hub (1 minute)

```bash
docker login
```

When prompted:
- Username: Your Docker Hub username
- Password: Your Docker Hub password

Success message:
```
Login Succeeded
```

---

## Step 3: Tag Your Image (1 minute)

Current image: `disaster-app:latest`

Tag it for Docker Hub:
```bash
docker tag disaster-app:latest YOUR_DOCKERHUB_USERNAME/disaster-app:latest
```

Replace `YOUR_DOCKERHUB_USERNAME` with your actual Docker Hub username.

Verify:
```bash
docker images | grep disaster-app
```

You should see:
```
disaster-app                          latest    <image-id>
YOUR_DOCKERHUB_USERNAME/disaster-app  latest    <image-id>
```

---

## Step 4: Push Image to Docker Hub (3-5 minutes)

```bash
docker push YOUR_DOCKERHUB_USERNAME/disaster-app:latest
```

Watch the upload progress. When done:
```
latest: digest: sha256:abcdef... size: 12345
```

---

## Step 5: Verify on Docker Hub

1. Go to https://hub.docker.com
2. Login with your account
3. Find your repository: `disaster-app`
4. Verify image is there with tag `latest`

Your image URL is:
```
YOUR_DOCKERHUB_USERNAME/disaster-app:latest
```

---

## Step 6: Deploy to Railway

### 6.1 Go to Railway.app

1. https://railway.app
2. Create/login to account
3. Create new project

### 6.2 Add Service from Existing Image

1. Click "Add Service"
2. Select **"Existing Image"** tab
3. Image URL field: Enter your image
   ```
   YOUR_DOCKERHUB_USERNAME/disaster-app:latest
   ```
4. Click "Connect"

### 6.3 Configure Service

1. Go to "Settings" tab
2. Set Port: `5000`

### 6.4 Add Environment Variables

Go to "Variables" tab, add:

```
FLASK_ENV=production
SECRET_KEY=generate-with-openssl-rand-hex-32
JWT_SECRET_KEY=generate-with-openssl-rand-hex-64
BACKEND_PORT=5000
POSTGRES_DB=disastersas
POSTGRES_USER=disastersas
POSTGRES_PASSWORD=strong-password
UPLOAD_FOLDER=/app/uploads
MAX_UPLOAD_BYTES=5242880
```

To generate secrets quickly:
```bash
# On your computer
openssl rand -hex 32    # For SECRET_KEY
openssl rand -hex 64    # For JWT_SECRET_KEY
```

### 6.5 Add PostgreSQL Database

1. Click "Add Service"
2. Select "Database"
3. Choose "PostgreSQL"
4. Railway creates it automatically

### 6.6 Deploy

1. Click "Deploy"
2. Railway pulls your image from Docker Hub
3. Container starts (1-2 minutes)
4. App is LIVE!

---

## Step 7: Test Deployment

Get your Railway URL from the dashboard:

```bash
curl https://YOUR_RAILWAY_URL/api/health
```

Expected response:
```json
{"status": "ok", "message": "Disaster Safety Backend Running Successfully 🚀"}
```

---

## Complete Timeline

| Step | Action | Time |
|------|--------|------|
| 1 | Create Docker Hub account | 2 min |
| 2 | Login locally | 1 min |
| 3 | Tag image | 1 min |
| 4 | Push to Docker Hub | 3-5 min |
| 5 | Verify on Docker Hub | 1 min |
| 6a | Create Railway project | 2 min |
| 6b-6f | Configure & deploy | 10 min |
| 7 | Test | 2 min |
| **TOTAL** | | **~25 min** |

---

## Helpful Commands

```bash
# List your local images
docker images | grep disaster-app

# Check image size before pushing
docker images disaster-app --format "{{.Size}}"

# View push progress
docker push YOUR_USERNAME/disaster-app:latest

# Login again (if needed)
docker login

# Logout when done
docker logout

# Test image locally before pushing
docker run -p 5000:5000 YOUR_USERNAME/disaster-app:latest
```

---

## Docker Hub Tips

### Make Image Public/Private
1. Go to https://hub.docker.com/repository/docker/YOUR_USERNAME/disaster-app
2. Settings → Repository Visibility → Public/Private
3. Save

### Tag Multiple Versions
```bash
# Version tagging
docker tag disaster-app:latest YOUR_USERNAME/disaster-app:v1.0
docker tag disaster-app:latest YOUR_USERNAME/disaster-app:latest

# Push all versions
docker push YOUR_USERNAME/disaster-app:v1.0
docker push YOUR_USERNAME/disaster-app:latest
```

### Check Image Details
```bash
# View image info before pushing
docker inspect disaster-app:latest

# View image layers
docker history disaster-app:latest
```

---

## Troubleshooting

### "denied: requested access to the resource is denied"
```bash
# You're not logged in
docker login
# Enter credentials
```

### "Error response from daemon: manifest unknown"
```bash
# Image not found in Docker Hub
# Verify you tagged it correctly:
docker images | grep disaster-app

# Make sure you pushed:
docker push YOUR_USERNAME/disaster-app:latest
```

### "no basic auth credentials"
```bash
# Not authenticated
docker logout
docker login
# Re-enter credentials
```

### Push is very slow
- Normal for first push (326MB image)
- Subsequent pushes are faster (only changes uploaded)
- Can take 5-15 minutes depending on internet

---

## Advanced: Automated Pushes

### Option 1: GitHub Actions (Auto-push on git commit)

Create `.github/workflows/docker-push.yml`:

```yaml
name: Push to Docker Hub

on:
  push:
    branches: [ main ]

jobs:
  push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: docker/build-push-action@v2
        with:
          context: .
          push: true
          tags: ${{ secrets.DOCKER_USERNAME }}/disaster-app:latest
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
```

Then in GitHub:
1. Settings → Secrets → Add `DOCKER_USERNAME` and `DOCKER_PASSWORD`
2. Push code
3. Image auto-pushes to Docker Hub

### Option 2: Docker Hub Auto-Build

Connect GitHub to Docker Hub:
1. Docker Hub → Repository → Builds
2. Connect GitHub
3. Auto-build on push

---

## After Deployment

### Update Your Image

Make changes locally:
```bash
# Edit code
nano disaster_backend/app.py

# Rebuild
docker build -t disaster-app:latest .

# Tag and push
docker tag disaster-app:latest YOUR_USERNAME/disaster-app:v2.0
docker push YOUR_USERNAME/disaster-app:v2.0

# In Railway: Update to new image tag
```

### Deploy Multiple Versions

```bash
docker tag disaster-app:latest YOU/disaster-app:v1.0
docker tag disaster-app:latest YOU/disaster-app:v2.0
docker tag disaster-app:latest YOU/disaster-app:latest

docker push YOU/disaster-app:v1.0
docker push YOU/disaster-app:v2.0
docker push YOU/disaster-app:latest
```

Then in Railway you can:
- Run `v1.0` in production
- Run `v2.0` in staging
- Test before switching

---

## Summary

You now have:
✓ Docker image built locally
✓ Image pushed to Docker Hub
✓ Ready to deploy to any platform
✓ Easy to update and version
✓ Shareable with team members

Next: Deploy to Railway.app or any Docker-compatible platform!

Your app is production-ready! 🚀
