# 🎯 Streamlit Deployment - Command Reference

Quick reference for all deployment commands.

## 📦 Installation

### Install All Dependencies
```bash
pip install -r requirements.txt
```

### Install Streamlit Only
```bash
pip install streamlit pandas plotly python-dotenv
```

### Verify Installation
```bash
python test_deployment.py
```

## 🚀 Running Locally

### Standard Run
```bash
streamlit run streamlit_app.py
```

### Custom Port
```bash
streamlit run streamlit_app.py --server.port 8080
```

### With Environment Variables
```bash
# Windows PowerShell
$env:DB_HOST="localhost"; streamlit run streamlit_app.py

# Windows CMD
set DB_HOST=localhost && streamlit run streamlit_app.py
```

### Automated Setup & Run
```bash
python streamlit_setup.py
```

## 🧪 Testing

### Pre-flight Check
```bash
python test_deployment.py
```

### Check Streamlit Version
```bash
streamlit --version
```

### Check Python Version
```bash
python --version
```

## 🔧 Git Commands

### Initial Commit
```bash
git add .
git commit -m "Add Streamlit deployment"
git push origin main
```

### Update After Changes
```bash
git add .
git commit -m "Update Streamlit app"
git push origin main
```

### Check Status
```bash
git status
```

### View Remote URL
```bash
git remote -v
```

## 🌐 Streamlit Cloud Commands

### Open Streamlit Cloud Dashboard
```bash
# Open in browser
start https://share.streamlit.io
```

### View Logs (in Streamlit Cloud UI)
- Click app → "Manage app" → "Logs"

### Reboot App (in Streamlit Cloud UI)
- Click app → "⋮" → "Reboot app"

## 🔐 Environment Setup

### Create .env File
```bash
# Windows PowerShell
New-Item -Path .env -ItemType File

# Then edit with:
notepad .env
```

### Example .env Content
```env
DB_HOST=localhost
DB_USER=root
DB_PASS=your_password
DB_NAME=movies_db

USE_LOCAL_MONGO=false
MONGO_USERNAME=your_username
MONGO_PASSWORD=your_password
MONGO_CLUSTER=your_cluster.mongodb.net
MONGO_DB=movies_nosql
MONGO_COLL=tmdb_movies
```

## 📊 Database Commands

### Test MariaDB Connection
```bash
python -c "from gui import get_connection; conn = get_connection(); print('✓ MariaDB connected')"
```

### Test MongoDB Connection
```bash
python -c "from gui import get_mongo_connection; c, d, coll = get_mongo_connection(); print('✓ MongoDB connected')"
```

### Check Database Tables
```bash
python -c "from gui import get_connection; conn = get_connection(); cur = conn.cursor(); cur.execute('SHOW TABLES'); print(cur.fetchall())"
```

## 🛠️ Troubleshooting Commands

### Clear Streamlit Cache
```bash
streamlit cache clear
```

### Reinstall Dependencies
```bash
pip install -r requirements.txt --force-reinstall
```

### Check for Import Errors
```bash
python -c "import streamlit_app"
```

### View Streamlit Config
```bash
streamlit config show
```

## 📁 File Management

### List Project Files
```bash
# Windows PowerShell
Get-ChildItem -Recurse -File | Select-Object FullName
```

### Check File Size
```bash
# Windows PowerShell
Get-ChildItem streamlit_app.py | Select-Object Name, Length
```

### Find All Python Files
```bash
# Windows PowerShell
Get-ChildItem -Recurse -Filter "*.py"
```

## 🔍 Debugging

### Run with Verbose Output
```bash
streamlit run streamlit_app.py --logger.level=debug
```

### Check Python Path
```bash
python -c "import sys; print('\n'.join(sys.path))"
```

### Test Specific Import
```bash
python -c "from gui import authenticate_user; print('✓ Import successful')"
```

### Check Installed Packages
```bash
pip list
```

### Check Specific Package Version
```bash
pip show streamlit
pip show pymongo
pip show pymysql
```

## 🎨 Customization

### Generate New Secrets
```bash
# Windows PowerShell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Check Current Theme
```bash
# View config
type .streamlit\config.toml
```

## 📈 Performance

### Check App Memory Usage
```bash
# While app is running, in another terminal:
python -c "import psutil; print(f'Memory: {psutil.Process().memory_info().rss / 1024 / 1024:.2f} MB')"
```

### Profile App Performance
```bash
streamlit run streamlit_app.py --server.enableStaticServing=false
```

## 🔄 Updates & Maintenance

### Update Streamlit
```bash
pip install --upgrade streamlit
```

### Update All Packages
```bash
pip install --upgrade -r requirements.txt
```

### Check for Outdated Packages
```bash
pip list --outdated
```

### Create New Requirements File
```bash
pip freeze > requirements_backup.txt
```

## 📝 Quick Start Workflow

### First Time Setup
```bash
# 1. Clone/navigate to project
cd "c:\Users\chanb\Documents\Y2T1\INF2003 (DB)\Proj\INF2003_P1-9"

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run pre-flight check
python test_deployment.py

# 4. Test locally
streamlit run streamlit_app.py

# 5. If working, push to GitHub
git add .
git commit -m "Add Streamlit deployment"
git push origin main

# 6. Deploy on Streamlit Cloud (via web UI)
```

### Daily Development Workflow
```bash
# 1. Make changes to streamlit_app.py

# 2. Test locally
streamlit run streamlit_app.py

# 3. If working, commit
git add .
git commit -m "Update feature X"
git push origin main

# 4. Streamlit Cloud auto-deploys!
```

## 🆘 Emergency Commands

### Kill Streamlit Process
```bash
# Windows PowerShell
Get-Process streamlit | Stop-Process -Force
```

### Remove Cache
```bash
# Windows
Remove-Item -Recurse -Force .streamlit\cache
```

### Reset Git (CAREFUL!)
```bash
# Discard all local changes
git reset --hard HEAD
git clean -fd
```

## ✅ Validation Commands

### Full System Check
```bash
# Run all checks
python test_deployment.py
```

### Quick Import Test
```bash
python -c "import streamlit; import pandas; import plotly; import pymysql; import pymongo; print('✓ All imports OK')"
```

### Database Connection Test
```bash
python -c "from gui import get_connection, get_mongo_connection; get_connection(); get_mongo_connection(); print('✓ Databases OK')"
```

---

## 📞 Quick Help

**Can't run Streamlit?**
```bash
pip install streamlit
```

**Import errors?**
```bash
pip install -r requirements.txt
```

**Database connection fails?**
```bash
# Check .env file exists and has correct values
type .env
```

**App won't deploy?**
- Check Streamlit Cloud logs
- Verify secrets are configured
- Ensure requirements.txt is committed

---

**Save this file for quick reference during deployment! 📌**
