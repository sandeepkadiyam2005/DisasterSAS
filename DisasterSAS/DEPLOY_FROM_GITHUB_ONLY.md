# Deploy to Railway.app from GitHub - Git Method Only

## Step 1: Push Code to GitHub

```bash
git init
git add .
git commit -m "Disaster Safety App - Production Ready"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/DisasterSAS.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your actual GitHub username.

---

## Step 2: Verify on GitHub

Go to: `https://github.com/YOUR_USERNAME/DisasterSAS`

Check these files exist:
- Dockerfile ✓
- docker-compose.yml ✓
- disaster_backend/ ✓
- disaster_frontend/ ✓
- .env.example ✓

---

## Step 3: Create Railway Project

1. Go to https://railway.app
2. Sign in with GitHub
3. Click "New Project"

---

## Step 4: Deploy from Git Repository

1. Click "Add Service"
2. Select "Public Git Repository" tab
3. Paste your GitHub repository URL:
   ```
   https://github.com/YOUR_USERNAME/DisasterSAS.git
   ```
4. Click "Connect"

Railway auto-detects your Dockerfile.

---

## Step 5: Configure Environment Variables

1. Click on the service
2. Go to "Variables" tab
3. Add these:

```
FLASK_ENV=production
SECRET_KEY=your_secret_key_here
JWT_SECRET_KEY=your_jwt_secret_here
BACKEND_PORT=5000
POSTGRES_DB=disastersas
POSTGRES_USER=disastersas
POSTGRES_PASSWORD=your_postgres_password
UPLOAD_FOLDER=/app/uploads
MAX_UPLOAD_BYTES=5242880
DATABASE_URI=postgresql+psycopg2://disastersas:your_postgres_password@db:5432/disastersas
```

Generate secrets:
```bash
openssl rand -hex 32    # For SECRET_KEY
openssl rand -hex 64    # For JWT_SECRET_KEY
```

---

## Step 6: Add PostgreSQL Database

1. Click "Add Service"
2. Select "Database"
3. Choose "PostgreSQL"

Railway auto-configures it.

---

## Step 7: Deploy

1. Click "Deploy" button
2. Watch build logs
3. Wait for "Container started"

---

## Step 8: Test

Get your Railway URL from dashboard.

Test:
```bash
curl https://YOUR_RAILWAY_URL/api/health
```

Expected:
```json
{"status": "ok", "message": "Disaster Safety Backend Running Successfully 🚀"}
```

---

## Done

Your app is live on Railway.app
