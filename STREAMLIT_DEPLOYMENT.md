# Streamlit Deployment Guide

This guide will help you deploy your Movie Database application using Streamlit.

## 📋 Prerequisites

- Python 3.8 or higher
- Git installed
- A GitHub account
- Your MongoDB Atlas credentials
- Access to your MariaDB database

## 🚀 Quick Start (Local Testing)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```env
# MariaDB Configuration
DB_HOST=localhost
DB_USER=root
DB_PASS=your_password
DB_NAME=movies_db

# MongoDB Atlas Configuration
USE_LOCAL_MONGO=false
MONGO_USERNAME=your_mongo_username
MONGO_PASSWORD=your_mongo_password
MONGO_CLUSTER=your_cluster.mongodb.net
MONGO_DB=movies_nosql
MONGO_COLL=tmdb_movies
```

### 3. Run Locally

```bash
streamlit run streamlit_app.py
```

The application will open in your browser at `http://localhost:8501`

## 🌐 Deploy to Streamlit Cloud (FREE)

### Step 1: Prepare Your Repository

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Add Streamlit app"
   git push origin main
   ```

2. **Verify Required Files**
   - `streamlit_app.py` (main application)
   - `gui.py` (backend functions)
   - `requirements.txt` (dependencies)
   - `.streamlit/config.toml` (configuration)

### Step 2: Deploy on Streamlit Cloud

1. **Sign up for Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with your GitHub account

2. **Create New App**
   - Click "New app"
   - Select your repository: `keithashs/INF2003_P1-9`
   - Branch: `main`
   - Main file path: `streamlit_app.py`
   - Click "Deploy"

### Step 3: Configure Secrets

In Streamlit Cloud dashboard:

1. Click on your app → "Settings" → "Secrets"
2. Add your credentials in TOML format:

```toml
# Database credentials
DB_HOST = "your_mariadb_host"
DB_USER = "your_mariadb_user"
DB_PASS = "your_mariadb_password"
DB_NAME = "movies_db"

# MongoDB Atlas
USE_LOCAL_MONGO = "false"
MONGO_USERNAME = "nkt12385_db_user"
MONGO_PASSWORD = "Keetian12345"
MONGO_CLUSTER = "cluster0.qrc4kkf.mongodb.net"
MONGO_DB = "movies_nosql"
MONGO_COLL = "tmdb_movies"
```

3. Save secrets - your app will automatically restart

### Step 4: Access Your Secrets in Code

Your `gui.py` already uses `os.getenv()` which works with Streamlit secrets:

```python
DB_HOST = os.getenv("DB_HOST", "localhost")
MONGO_USERNAME = os.getenv("MONGO_USERNAME")
```

Streamlit automatically loads secrets as environment variables!

## 🔧 Database Setup

### Option 1: Cloud MariaDB (Recommended for Production)

Use a cloud database service:

**AWS RDS MariaDB** (Free Tier Available)
- 20 GB storage
- db.t3.micro instance free for 12 months
- [AWS RDS Setup Guide](https://aws.amazon.com/rds/mariadb/)

**PlanetScale** (MySQL-compatible, Free Tier)
- 5 GB storage
- 1 billion row reads/month
- [PlanetScale Setup](https://planetscale.com/)

**DigitalOcean Managed Database** ($15/month)
- 1 GB RAM, 10 GB storage
- Automated backups
- [DigitalOcean Database](https://www.digitalocean.com/products/managed-databases)

### Option 2: Keep MariaDB Local (Development Only)

If using local MariaDB, you'll need to expose it:
- ⚠️ **Not recommended for production**
- Use ngrok or similar tunneling service
- Or migrate data to cloud database

### MongoDB Atlas Setup (Already Configured)

Your MongoDB Atlas is ready:
- ✅ Cluster: `cluster0.qrc4kkf.mongodb.net`
- ✅ Database: `movies_nosql`
- ✅ Collection: `tmdb_movies`

**Important:** Whitelist Streamlit Cloud IPs:
1. Go to MongoDB Atlas → Network Access
2. Add IP: `0.0.0.0/0` (allow all)
   - Or specific Streamlit Cloud IPs if available
3. Save changes

## 📊 Cost Breakdown

### FREE Option (Recommended)
- **Streamlit Cloud**: FREE (unlimited public apps)
- **MongoDB Atlas**: FREE (M0 cluster, 512 MB storage)
- **AWS RDS MariaDB**: FREE for 12 months (then ~$15/month)

**Total Cost: $0/month for first year**

### Production Option
- **Streamlit Cloud**: FREE
- **MongoDB Atlas**: FREE (M0)
- **DigitalOcean MariaDB**: $15/month
- **Total: $15/month**

## 🔒 Security Best Practices

### 1. Environment Variables
Never commit credentials to GitHub:
```bash
# Add to .gitignore
.env
.streamlit/secrets.toml
*.log
logs/
```

### 2. Database Security
- Use strong passwords
- Enable SSL/TLS connections
- Whitelist specific IPs when possible
- Use read-only credentials for guest access

### 3. Application Security
- Implement rate limiting
- Add CAPTCHA for registration
- Monitor for suspicious activity
- Regular security updates

## 🧪 Testing Deployment

### Local Testing
```bash
# Install dependencies
pip install -r requirements.txt

# Run app
streamlit run streamlit_app.py
```

### Test Features
- ✅ User registration and login
- ✅ Movie search (SQL and MongoDB)
- ✅ Rating system with locks
- ✅ Watchlist functionality
- ✅ Analytics dashboard
- ✅ Admin features (if admin user)

## 📱 Features Available

### Guest Users
- Browse movies
- Search movies (title, genre, advanced)
- View movie details with TMDB metadata
- View analytics and statistics

### Registered Users
All guest features plus:
- Rate movies (with concurrency locks)
- Manage personal watchlist
- View rating history
- Get personalized recommendations

### Admin Users
All user features plus:
- User management
- Movie CRUD operations
- System analytics
- Database management

## 🐛 Troubleshooting

### App Won't Start
- Check Streamlit Cloud logs for errors
- Verify all secrets are configured
- Ensure requirements.txt is up to date

### Database Connection Fails
- Verify MongoDB Atlas network access
- Check MariaDB connection string
- Test credentials locally first

### Import Errors
- Make sure `gui.py` is in the repository
- Check Python version compatibility
- Verify all dependencies in requirements.txt

## 📈 Performance Optimization

### 1. Add Caching
Already implemented with Streamlit decorators:
```python
@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_top_rated_movies(limit=20):
    # Your function
```

### 2. Database Indexing
Make sure these indexes exist:
```sql
-- MariaDB indexes
CREATE INDEX idx_title ON MOVIES(title);
CREATE INDEX idx_rating ON RATINGS(userId, movieId);

-- MongoDB indexes
db.tmdb_movies.createIndex({ "title": 1 })
db.tmdb_movies.createIndex({ "genres.name": 1 })
```

### 3. Connection Pooling
Consider using connection pooling for better performance:
```python
from pymysql.pooling import Pool
# Configure in gui.py
```

## 🔄 Continuous Deployment

### Automatic Updates
Streamlit Cloud automatically redeploys when you push to GitHub:

```bash
# Make changes
git add .
git commit -m "Update feature"
git push origin main

# Streamlit Cloud will automatically rebuild and deploy!
```

### Manual Reboot
If needed:
1. Go to Streamlit Cloud dashboard
2. Click "Reboot app"
3. Wait for restart (~30 seconds)

## 📞 Support Resources

- **Streamlit Docs**: https://docs.streamlit.io
- **Streamlit Community**: https://discuss.streamlit.io
- **MongoDB Atlas Docs**: https://docs.atlas.mongodb.com
- **AWS RDS Docs**: https://docs.aws.amazon.com/rds

## ✅ Post-Deployment Checklist

- [ ] App is accessible via public URL
- [ ] User registration works
- [ ] Login functionality works
- [ ] Movie search returns results
- [ ] Rating system saves to database
- [ ] Watchlist operations work
- [ ] Analytics display correctly
- [ ] MongoDB Atlas connection stable
- [ ] MariaDB connection stable
- [ ] No sensitive data exposed in logs
- [ ] All secrets configured in Streamlit Cloud
- [ ] Custom domain configured (optional)

## 🎉 You're Live!

Once deployed, your app will be available at:
```
https://your-app-name.streamlit.app
```

Share this URL with your users and enjoy your cloud-deployed movie database! 🎬
