# Railway.app Deployment - Step by Step

## Prerequisites
- GitHub account (free at https://github.com)
- Railway.app account (free at https://railway.app)
- Your code pushed to GitHub

## Step 1: Push Code to GitHub

### 1.1 Create GitHub Repository
1. Go to https://github.com/new
2. Create repository: `DisasterSAS` (or your preferred name)
3. Copy the repository URL

### 1.2 Push Your Code
```bash
# In your project directory
git init
git add .
git commit -m "Initial commit: Disaster Safety App containerized"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/DisasterSAS.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username.

---

## Step 2: Create Railway.app Account & Project

### 2.1 Sign Up
1. Go to https://railway.app
2. Click "Sign Up"
3. Sign in with GitHub (recommended)
4. Authorize Railway to access your GitHub account

### 2.2 Create New Project
1. Click "New Project" or "Create"
2. Select "Deploy from GitHub repo"
3. Search for `DisasterSAS` repository
4. Click to connect

---

## Step 3: Add Backend Service

### 3.1 Add Service from Dockerfile
1. In Railway dashboard, click "Add Service"
2. Select "GitHub Repo"
3. Choose your `DisasterSAS` repository
4. Railway auto-detects Dockerfile

### 3.2 Configure Environment Variables
1. Go to "Variables" tab in backend service
2. Add the following (copy from `.env.example`):

```
FLASK_ENV=production
SECRET_KEY=<generate-with: openssl rand -hex 32>
JWT_SECRET_KEY=<generate-with: openssl rand -hex 64>
BACKEND_PORT=5000
POSTGRES_DB=disastersas
POSTGRES_USER=disastersas
POSTGRES_PASSWORD=<generate-with: openssl rand -hex 16>
UPLOAD_FOLDER=/app/uploads
DATABASE_URI=postgresql+psycopg2://disastersas:<POSTGRES_PASSWORD>@<POSTGRES_HOST>:5432/disastersas
```

**To generate secrets (on your computer):**
```bash
# macOS/Linux
openssl rand -hex 32    # For SECRET_KEY
openssl rand -hex 64    # For JWT_SECRET_KEY
openssl rand -hex 16    # For POSTGRES_PASSWORD

# Windows PowerShell
[Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((Get-Random).ToString())) | ForEach-Object {$_ -replace '=',''} | Select-Object -First 32
```

### 3.3 Set Service Port
1. Go to "Settings" tab
2. Under "Port", set to `5000`

---

## Step 4: Add PostgreSQL Database

### 4.1 Add Database Plugin
1. Click "Add Service"
2. Select "Database"
3. Choose "PostgreSQL"
4. Railway creates managed database automatically

### 4.2 Railway Auto-Generates Database URL
1. Railway automatically creates `DATABASE_URL`
2. This will be available in your backend service
3. Update `DATABASE_URI` variable in backend service

---

## Step 5: Connect Services

### 5.1 Link Backend to Database
1. In backend service, go to "Variables"
2. Replace `DATABASE_URI` with Railway's auto-generated URL
3. Or let Railway inject it automatically with proper format

**The DATABASE_URL from PostgreSQL will automatically include:**
- Host
- Port
- Username
- Password
- Database name

---

## Step 6: Add Frontend Service (Optional)

### 6.1 Deploy Frontend (Nginx)
If you want separate frontend service:

1. Click "Add Service"
2. Select "Dockerfile" 
3. Create `Dockerfile.frontend`:

```dockerfile
FROM nginx:alpine
COPY disaster_frontend /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
```

4. Set port to `80` in Railway settings

### 6.2 Or Serve from Backend
Keep frontend static files served by Flask (already configured in your app).

---

## Step 7: Deploy

### 7.1 Manual Deploy
1. In Railway dashboard, click "Deploy" button
2. Railway builds your Dockerfile
3. Services start automatically
4. View logs in real-time

### 7.2 Auto-Deploy on Git Push
1. Go to "Settings"
2. Enable "Auto Deploy" on main branch
3. Now every git push auto-deploys

---

## Step 8: Configure Public URL

### 8.1 Get Backend URL
1. Click on backend service
2. Copy the public URL (looks like: `https://yourapp-production.up.railway.app`)
3. This is your backend API endpoint

### 8.2 Configure Frontend (if separate)
If frontend is separate, update API endpoint:
- Find API calls in `disaster_frontend/app.js`
- Update to use Railway backend URL

```javascript
// Instead of:
const API = 'http://localhost:5000';

// Use:
const API = 'https://yourapp-production.up.railway.app';
```

---

## Step 9: Verify Deployment

### 9.1 Test Backend Health
```bash
curl https://yourapp-production.up.railway.app/api/health
```

Should return:
```json
{"status": "ok", "message": "Disaster Safety Backend Running Successfully 🚀"}
```

### 9.2 Test Frontend
Visit: `https://yourapp-production.up.railway.app`

---

## Step 10: Setup Custom Domain (Optional)

### 10.1 Add Domain
1. Go to Railway project settings
2. Under "Domains", click "Add Domain"
3. Enter your domain (e.g., `disastersas.com`)
4. Follow DNS setup instructions

### 10.2 Update DNS Records
Point your domain registrar's A record to Railway's domain.

---

## Troubleshooting

### Build Fails
**Check logs:**
```
1. Click backend service
2. Go to "Build Logs"
3. Look for error messages
```

**Common issues:**
- Missing dependencies in `requirements.txt`
- Incorrect Dockerfile path
- Missing environment variables

### Database Connection Error
**Fix:**
1. Make sure PostgreSQL service is running
2. Verify `DATABASE_URI` environment variable
3. Check database credentials in variables

### Port Issues
1. Make sure port `5000` is set for backend
2. Check if `FLASK_ENV=production`

### View Live Logs
1. Click backend service
2. Go to "Logs" tab
3. See real-time application logs

---

## Cost & Billing

### Free Tier Includes
- 5GB memory
- 100GB bandwidth
- Limited CPU
- Good for testing/MVP

### When You Need Paid Plan
- More traffic
- More storage
- Better performance
- Auto-scale

### Upgrade
1. Go to account settings
2. Click "Billing"
3. Add payment method
4. Upgrade plan

---

## Post-Deployment Checklist

- [ ] Backend API responding (health endpoint works)
- [ ] Database is connected and working
- [ ] Frontend loads without errors
- [ ] Users can login/register
- [ ] File uploads work
- [ ] Database writes are persistent
- [ ] Logs show no errors

---

## Managing Your Deployment

### View Logs
```
Dashboard → Backend Service → Logs tab
```

### Restart Service
```
Dashboard → Backend Service → Settings → Restart
```

### Update Code
```bash
# On your computer
git add .
git commit -m "Update features"
git push origin main

# Railway auto-deploys
# Check Deployments tab to see progress
```

### Environment Variables
```
Dashboard → Service → Variables tab → Edit
```

### View Metrics
```
Dashboard → Analytics tab → CPU, Memory, Network
```

---

## Backup Your Database

### Automatic Backups
Railway PostgreSQL includes automatic backups.

### Manual Backup
1. Go to PostgreSQL service in Railway
2. Click "Connect"
3. Download or export data

---

## Next Steps

1. **Push code to GitHub** (if not done)
2. **Create Railway account** (https://railway.app)
3. **Connect GitHub repository**
4. **Add services** (Backend Dockerfile + PostgreSQL)
5. **Set environment variables**
6. **Deploy** (click Deploy button)
7. **Test** (verify endpoints working)
8. **Setup custom domain** (optional)
9. **Configure monitoring** (optional)

---

## Support

**Railway Docs:** https://docs.railway.app
**GitHub Issues:** If you encounter Docker issues
**Railway Support:** In-app help chat

---

## Your Railway Dashboard

Once deployed, you'll see:
- Backend service running
- PostgreSQL database connected
- Public URL for accessing your app
- Deployment history
- Real-time logs
- Performance metrics

All auto-managed by Railway! 🚀

---

## Security Checklist

Before going public:
- [ ] Change all secrets in environment variables
- [ ] Enable HTTPS (automatic on Railway)
- [ ] Set strong database password
- [ ] Review security headers (configured in nginx.conf)
- [ ] Test authentication flows
- [ ] Verify file upload security
- [ ] Check CORS settings

Your app is production-ready! 🎉
