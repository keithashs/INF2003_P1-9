# 🐳 Docker Setup - MariaDB + MongoDB (Local)

## Overview

This Docker setup hosts **both databases locally** on your machine:

| Service | Container Name | Port | Purpose |
|---------|---------------|------|---------|
| **MariaDB** | movies_mariadb | 3306 | SQL database (users, movies, ratings, links) |
| **MongoDB** | movies_mongodb | 27017 | NoSQL database (TMDB metadata, rich movie data) |
| **Python App** | movies_app | - | Application container (optional) |

All services communicate via Docker network using container names as hostnames.

---

## Quick Start (Windows)

### Step 1: Start Docker Desktop
Make sure Docker Desktop is running (look for the whale icon in your system tray).

### Step 2: Run Setup Script
```cmd
cd c:\Users\Pavi_lab\Desktop\INF2003_P1-9
docker-setup.bat
```

This will:
- ✅ Build all containers
- ✅ Start MariaDB on port 3306
- ✅ Start MongoDB on port 27017
- ✅ Initialize databases with schemas

### Step 3: Import Data (First Time Only)
```cmd
docker-compose exec app python 2_import_data.py
```

### Step 4: Run the GUI
```cmd
python gui.py
```

---

## Manual Setup

### Start Services
```cmd
# Start all services
docker-compose up -d

# Or start specific services
docker-compose up -d mariadb mongodb
```

### Check Status
```cmd
# View running containers
docker-compose ps

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f mariadb
docker-compose logs -f mongodb
```

### Stop Services
```cmd
# Stop all services (keeps data)
docker-compose down

# Stop and remove all data (CAUTION!)
docker-compose down -v
```

---

## Connection Details

### MariaDB (SQL)
```
Host: localhost (or 'mariadb' from inside Docker)
Port: 3306
User: root
Password: 123456
Database: movies_db
```

**Connection String:**
```
mysql://root:123456@localhost:3306/movies_db
```

### MongoDB (NoSQL)
```
Host: localhost (or 'mongodb' from inside Docker)
Port: 27017
User: admin
Password: admin123
Database: movies_nosql
Collection: tmdb_movies
```

**Connection String:**
```
mongodb://admin:admin123@localhost:27017/movies_nosql?authSource=admin
```

---

## Using with gui.py

### Option 1: Use Local Docker MongoDB (Recommended)
Set environment variable before running:

**Windows CMD:**
```cmd
set USE_LOCAL_MONGO=true
set MONGO_USERNAME=admin
set MONGO_PASSWORD=admin123
python gui.py
```

**Windows PowerShell:**
```powershell
$env:USE_LOCAL_MONGO="true"
$env:MONGO_USERNAME="admin"
$env:MONGO_PASSWORD="admin123"
python gui.py
```

### Option 2: Keep Using MongoDB Atlas (Cloud)
Just run normally - it will use Atlas by default:
```cmd
python gui.py
```

### Option 3: Create a .env File
Create `.env` in the project folder:
```
USE_LOCAL_MONGO=true
MONGO_USERNAME=admin
MONGO_PASSWORD=admin123
DB_HOST=localhost
DB_PASS=123456
```

Then use a library like `python-dotenv` to load it.

---

## Database Access

### MariaDB Shell
```cmd
docker exec -it movies_mariadb mysql -u root -p123456 movies_db
```

Inside MySQL:
```sql
SHOW TABLES;
SELECT COUNT(*) FROM MOVIES;
SELECT * FROM USERS LIMIT 5;
```

### MongoDB Shell
```cmd
docker exec -it movies_mongodb mongosh -u admin -p admin123 --authenticationDatabase admin
```

Inside MongoDB:
```javascript
use movies_nosql
db.tmdb_movies.countDocuments()
db.tmdb_movies.findOne()
db.tmdb_movies.find({title: /Batman/i}).limit(5)
```

---

## Import MongoDB Data

If you need to import movie metadata into local MongoDB:

### Option 1: From JSON file
```cmd
docker exec -it movies_mongodb mongoimport --db movies_nosql --collection tmdb_movies --file /data/movies.json --jsonArray -u admin -p admin123 --authSource admin
```

### Option 2: Using Python script
Create `import_mongo_data.py`:
```python
import os
os.environ['USE_LOCAL_MONGO'] = 'true'
os.environ['MONGO_USERNAME'] = 'admin'
os.environ['MONGO_PASSWORD'] = 'admin123'

from gui import tmdb_collection

# Your import logic here
data = [
    {"id": 1, "title": "Example Movie", "overview": "A great movie"},
    # ... more movies
]

tmdb_collection.insert_many(data)
print(f"Imported {len(data)} movies")
```

---

## Network Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Host (Your PC)                     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Docker Network (movies_network)          │   │
│  │                   172.28.0.0/16                       │   │
│  │                                                       │   │
│  │   ┌─────────────────┐     ┌─────────────────┐        │   │
│  │   │    MariaDB      │     │    MongoDB      │        │   │
│  │   │  (movies_mariadb)│     │ (movies_mongodb)│        │   │
│  │   │                 │     │                 │        │   │
│  │   │  Port: 3306     │     │  Port: 27017    │        │   │
│  │   │  SQL Database   │     │  NoSQL Database │        │   │
│  │   └────────┬────────┘     └────────┬────────┘        │   │
│  │            │                       │                  │   │
│  │            └───────────┬───────────┘                  │   │
│  │                        │                              │   │
│  │               ┌────────┴────────┐                     │   │
│  │               │   Python App    │                     │   │
│  │               │  (movies_app)   │                     │   │
│  │               │                 │                     │   │
│  │               │   gui.py        │                     │   │
│  │               └─────────────────┘                     │   │
│  │                                                       │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                  │
│        ┌──────────────────┴──────────────────┐              │
│        │         Host Port Mapping           │              │
│        │   localhost:3306 → mariadb:3306     │              │
│        │   localhost:27017 → mongodb:27017   │              │
│        └─────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

### "Port 3306 already in use"
Stop local MySQL/MariaDB or change port in `docker-compose.yml`:
```yaml
ports:
  - "3307:3306"  # Use 3307 instead
```

### "Port 27017 already in use"
Stop local MongoDB or change port in `docker-compose.yml`:
```yaml
ports:
  - "27018:27017"  # Use 27018 instead
```

### "Connection refused"
Wait longer for databases to start:
```cmd
docker-compose logs -f mariadb
docker-compose logs -f mongodb
```
Look for "ready for connections" messages.

### "Authentication failed" (MongoDB)
Make sure you're using the correct credentials:
- Username: `admin`
- Password: `admin123`
- Auth database: `admin`

### Container keeps restarting
Check logs for errors:
```cmd
docker-compose logs mariadb
docker-compose logs mongodb
```

---

## Data Persistence

Data is stored in Docker volumes and persists between restarts:

```cmd
# List volumes
docker volume ls

# Inspect volume
docker volume inspect movies_mariadb_data
docker volume inspect movies_mongodb_data

# Backup MariaDB
docker exec movies_mariadb mysqldump -u root -p123456 movies_db > backup.sql

# Backup MongoDB
docker exec movies_mongodb mongodump -u admin -p admin123 --authenticationDatabase admin --db movies_nosql --out /data/backup

# Restore MariaDB
docker exec -i movies_mariadb mysql -u root -p123456 movies_db < backup.sql
```

---

## Useful Commands Reference

| Action | Command |
|--------|---------|
| Start all services | `docker-compose up -d` |
| Stop all services | `docker-compose down` |
| View logs | `docker-compose logs -f` |
| Restart service | `docker-compose restart mariadb` |
| Access MariaDB | `docker exec -it movies_mariadb mysql -u root -p123456` |
| Access MongoDB | `docker exec -it movies_mongodb mongosh -u admin -p admin123 --authenticationDatabase admin` |
| Run Python in container | `docker-compose exec app python` |
| Shell access | `docker-compose exec app bash` |

---

## Security Notes

⚠️ **For Production Use:**

1. Change default passwords in `.env` file
2. Never commit `.env` to Git
3. Use Docker secrets for sensitive data
4. Restrict network access appropriately

```cmd
# Create .env from template
copy .env.example .env

# Edit with your secure passwords
notepad .env
```
