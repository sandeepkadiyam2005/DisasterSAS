# GitHub Setup for Railway Deployment

## Step 1: Create GitHub Repository

### Option A: Via Web Browser (Easiest)
1. Go to https://github.com/new
2. Fill in:
   - **Repository name:** `DisasterSAS` (or your preferred name)
   - **Description:** "Disaster Safety Application - Real-time Crisis Management"
   - **Visibility:** Public (for Railway access)
3. Click "Create repository"
4. Copy the repository URL (looks like: `https://github.com/YOUR_USERNAME/DisasterSAS.git`)

### Option B: Via GitHub CLI
```bash
# Install GitHub CLI from: https://cli.github.com

gh repo create DisasterSAS --public --source=. --remote=origin --push
```

---

## Step 2: Push Your Code to GitHub

### From Your Project Directory:

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: Disaster Safety App containerized for production"

# Set main branch
git branch -M main

# Add remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/DisasterSAS.git

# Push to GitHub
git push -u origin main
```

### Verify Push Success
Visit: `https://github.com/YOUR_USERNAME/DisasterSAS`

You should see:
- ✓ Dockerfile
- ✓ docker-compose.yml
- ✓ nginx.conf
- ✓ disaster_backend/ (with app.py, requirements.txt, etc.)
- ✓ disaster_frontend/ (HTML files)
- ✓ .env.example
- ✓ .dockerignore

---

## Step 3: Important Files to Commit

Make sure these files are in your GitHub repository:

### Required for Docker Build
- `Dockerfile` — Main application build
- `docker-compose.yml` — Service configuration
- `.dockerignore` — Build context optimization
- `disaster_backend/requirements.txt` — Python dependencies
- `disaster_backend/app.py` — Flask application
- `disaster_backend/run.py` — Entry point

### Recommended (For Documentation)
- `.env.example` — Environment variable template
- `DEPLOYMENT_GUIDE.md` — Deployment instructions
- `README.md` — Project description

### Do NOT Commit
- `.env` — Contains secrets! (Never push this)
- `__pycache__/` — Python cache
- `.pyc` files
- `node_modules/` — Node packages
- `.git/` — Git metadata

Your `.gitignore` should already exclude these (check `.gitignore` file).

---

## Step 4: Configure .gitignore

Make sure `.gitignore` contains:

```
# Environment variables - CRITICAL!
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/

# Node
node_modules/
npm-debug.log

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Database
*.sqlite3
*.db
```

---

## Step 5: Test Locally Before Pushing

```bash
# Make sure everything works locally
docker compose up -d

# Check services
docker compose ps

# View logs
docker compose logs -f

# Test health endpoint
curl http://localhost:5000/api/health

# Stop services
docker compose down
```

Only push to GitHub after testing locally!

---

## Step 6: Verify GitHub Repository

Visit your repository: `https://github.com/YOUR_USERNAME/DisasterSAS`

Check:
- [ ] All files present
- [ ] `.env` is NOT committed (check in .gitignore)
- [ ] No sensitive data visible
- [ ] Dockerfile is readable
- [ ] README shows your project description

---

## Step 7: Generate SSH Key (Optional, for Faster Pulls)

If you want Railway to pull faster without entering credentials:

```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "your_email@example.com"

# Add to GitHub
# Go to Settings → SSH and GPG keys → Add New SSH Key
# Paste contents of ~/.ssh/id_ed25519.pub

# Test connection
ssh -T git@github.com
```

---

## Common GitHub Issues

### "fatal: not a git repository"
```bash
# Initialize git
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/DisasterSAS.git
git push -u origin main
```

### "remote origin already exists"
```bash
# Remove old remote
git remote remove origin

# Add new remote
git remote add origin https://github.com/YOUR_USERNAME/DisasterSAS.git
git push -u origin main
```

### "fatal: The remote end hung up unexpectedly"
```bash
# Increase git buffer
git config --global http.postBuffer 524288000

# Try push again
git push -u origin main
```

### "Please make sure you have the correct access rights"
```bash
# Check if SSH key is added to GitHub
ssh -T git@github.com

# Or use HTTPS with personal access token instead of password
# (GitHub removed password authentication)

# Create token: https://github.com/settings/tokens
# Use token as password when pushing
```

---

## Step 8: Make Your Repository Ready for Railway

### Add a README.md
Create `README.md` in your project root:

```markdown
# Disaster Safety Application

Real-time disaster management platform for coordinating emergency response.

## Features
- Real-time alerts and notifications
- Disaster mapping and tracking
- Volunteer management
- Emergency resource coordination
- Survivor tracking

## Tech Stack
- Backend: Flask + PostgreSQL
- Frontend: HTML/CSS/JavaScript + Nginx
- Deployment: Docker + Railway

## Local Setup
```bash
docker compose up -d
# Visit http://localhost:3000
```

## Production Deployment
Deploy on Railway.app - see DEPLOYMENT_GUIDE.md

## Environment Variables
See `.env.example` for required variables.
```

### Add .env.example (Already Created)
Ensure `.env.example` is committed with all required variables.

---

## Step 9: Connect GitHub to Railway

1. Go to https://railway.app
2. Create/Login to account
3. Create new project
4. Select "Deploy from GitHub repo"
5. Search for "DisasterSAS"
6. Click "Deploy"
7. Railway auto-detects Dockerfile
8. Add environment variables
9. Deploy!

---

## Updating Your Code After Deployment

```bash
# Make changes locally
nano disaster_backend/app.py

# Commit changes
git add .
git commit -m "Fix: API endpoint response"

# Push to GitHub
git push origin main

# Railway auto-deploys! Watch the Deployments tab
```

---

## GitHub Best Practices

### Commit Messages
```bash
# Good
git commit -m "feat: Add health check endpoint"
git commit -m "fix: Fix database connection timeout"
git commit -m "docs: Update deployment guide"

# Avoid
git commit -m "fix stuff"
git commit -m "asdf"
```

### Branching Strategy (Optional)
```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes and commit
git commit -m "feat: Add new feature"

# Push feature branch
git push origin feature/new-feature

# Create Pull Request on GitHub
# Merge after review
# Delete branch

# Back on main
git checkout main
git pull origin main
```

---

## Helpful Commands

```bash
# Check status
git status

# View commit history
git log --oneline

# See what changed
git diff

# Undo last commit (keep changes)
git reset --soft HEAD~1

# View all branches
git branch -a

# Clone your repo to another computer
git clone https://github.com/YOUR_USERNAME/DisasterSAS.git
```

---

## Security Checklist

- [ ] `.env` file is in `.gitignore` (CRITICAL!)
- [ ] No secrets hardcoded in code
- [ ] `.env.example` shows structure without real values
- [ ] Repository visibility is appropriate (public for Railway)
- [ ] No API keys in code comments
- [ ] No passwords in commit messages

---

## Your Repository is Ready!

Once your repository is on GitHub with:
- ✓ Dockerfile
- ✓ docker-compose.yml
- ✓ All application code
- ✓ .env.example (no .env)
- ✓ .dockerignore
- ✓ README.md

**You can proceed to Railway.app deployment!**

See `RAILWAY_DEPLOYMENT_STEPS.md` for step-by-step Railway setup.
