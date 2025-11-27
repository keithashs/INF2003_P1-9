# 🐳 Docker Setup Guide for TMDB Movie Database

## Overview

This guide will help you run the TMDB Movie Database (Hybrid SQL-NoSQL system) in Docker containers. The setup includes:

- **MariaDB 10.11** - SQL database for relational data (users, movies, ratings)
- **Python 3.11** - Application container for the GUI and data processing
- **MongoDB Atlas** - Cloud-based NoSQL database (already configured)

---

## Prerequisites

### 1. Install Docker

**Windows:**
- Download and install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
- After installation, restart your computer
- Verify installation: Open PowerShell and run:
  ```powershell
  docker --version
  docker-compose --version
  ```

**Mac:**
- Download and install [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)
- Verify installation:
  ```bash
  docker --version
  docker-compose --version
  ```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install docker.io docker-compose

# Verify installation
docker --version
docker-compose --version
```

### 2. Configure X11 for GUI (Linux/Mac Only)

The GUI application requires X11 forwarding to display windows from Docker.

**Linux:**
```bash
# Allow Docker to access X11
xhost +local:docker
```

**Mac:**
```bash
# Install XQuartz (X11 server for Mac)
brew install --cask xquartz

# Open XQuartz and enable "Allow connections from network clients"
# Then run:
xhost +localhost
```

**Windows:**
- GUI in Docker on Windows requires additional setup (VcXsrv or WSL2 with X11)
- **Recommended for Windows:** Run the GUI directly on host machine (not in Docker)
  - Use Docker only for MariaDB database
  - Run `python gui.py` on Windows host

---

## Quick Start (Recommended)

### Step 1: Start Services

```bash
# Navigate to project directory
cd c:\Users\Pavi_lab\Desktop\INF2003_P1-9

# Start MariaDB and application containers
docker-compose up -d
```

This command will:
- Pull required Docker images (MariaDB, Python)
- Build the application container
- Create a Docker network
- Start MariaDB with automatic schema creation
- Start the application container

### Step 2: Import Data

Wait for MariaDB to initialize (30 seconds), then run:

```bash
# Import CSV data into MariaDB
docker-compose exec app python 2_import_data.py
```

This will:
- Load data from `links_small.csv`, `ratings_small.csv`, `movies_metadata.csv`
- Create users, movies, ratings, and links tables
- Display import statistics

### Step 3: Run Additional Setup Scripts

```bash
# Apply indexes for performance
docker-compose exec app bash -c "mysql -h mariadb -u root -proot_password movies_db < 3_create_indexes.sql"

# Add security features (password hashing, roles)
docker-compose exec app bash -c "mysql -h mariadb -u root -proot_password movies_db < 4_add_security_features.sql"

# Update user names
docker-compose exec app bash -c "mysql -h mariadb -u root -proot_password movies_db < 5_update_user_names.sql"

# Create watchlist feature
docker-compose exec app bash -c "mysql -h mariadb -u root -proot_password movies_db < 6_create_watchlist.sql"

# Renumber user IDs
docker-compose exec app bash -c "mysql -h mariadb -u root -proot_password movies_db < 7_renumber_user_ids.sql"

# Update ratings schema
docker-compose exec app bash -c "mysql -h mariadb -u root -proot_password movies_db < 8_update_ratings_schema.sql"
```

**Or run all at once:**
```bash
docker-compose exec app bash /app/docker/init_data.sh
```

### Step 4: Launch the GUI

**Linux/Mac (X11 configured):**
```bash
docker-compose exec app python gui.py
```

**Windows (Recommended):**
```powershell
# Install Python dependencies on host
python -m pip install pymysql pymongo bcrypt

# Run GUI directly on Windows
python gui.py
```

---

## Manual Setup (Step-by-Step)

### 1. Build Docker Images

```bash
# Build the Python application image
docker-compose build
```

### 2. Start MariaDB Only

```bash
# Start just the database
docker-compose up -d mariadb

# Wait for MariaDB to initialize (check logs)
docker-compose logs -f mariadb

# Look for: "mariadb  | [Note] mysqld: ready for connections"
```

### 3. Verify Database Connection

```bash
# Connect to MariaDB using Docker
docker-compose exec mariadb mysql -u root -proot_password movies_db

# Inside MySQL shell:
SHOW TABLES;
EXIT;
```

### 4. Start Application Container

```bash
# Start the app container
docker-compose up -d app

# Enter the container
docker-compose exec app bash

# Inside container, you can run:
python gui.py
python setup.py
```

---

## Configuration

### Environment Variables

Edit `docker-compose.yml` to customize database credentials:

```yaml
environment:
  # MariaDB settings
  DB_HOST: mariadb
  DB_USER: root
  DB_PASS: root_password  # Change this!
  DB_NAME: movies_db
  
  # MongoDB Atlas (cloud)
  MONGO_USERNAME: nkt12385_db_user
  MONGO_PASSWORD: Keetian12345
  MONGO_CLUSTER: cluster0.qrc4kkf.mongodb.net
  MONGO_DB: movies_nosql
  MONGO_COLL: tmdb_movies
```

### Ports

- **MariaDB:** `3306` (exposed to host)
- **Application:** `5000` (reserved for future web interface)

---

## Common Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# Restart a service
docker-compose restart mariadb
docker-compose restart app

# Access MariaDB shell
docker-compose exec mariadb mysql -u root -proot_password movies_db

# Access application shell
docker-compose exec app bash

# Remove all containers and volumes (CAUTION: deletes data!)
docker-compose down -v
```

---

## Troubleshooting

### Issue: GUI doesn't display (Linux/Mac)

**Solution:**
```bash
# Allow X11 access
xhost +local:docker

# Set DISPLAY variable
export DISPLAY=:0

# Run GUI
docker-compose exec app python gui.py
```

### Issue: MariaDB connection refused

**Solution:**
```bash
# Check if MariaDB is running
docker-compose ps

# Check MariaDB logs
docker-compose logs mariadb

# Wait for "ready for connections" message
# Then restart app
docker-compose restart app
```

### Issue: Data import fails

**Solution:**
```bash
# Ensure CSV files exist
ls -lh *.csv

# Check file paths in 2_import_data.py
# Re-run import
docker-compose exec app python 2_import_data.py
```

### Issue: Permission denied (Linux)

**Solution:**
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Logout and login again
```

### Issue: Port 3306 already in use

**Solution:**
```bash
# Change port in docker-compose.yml
ports:
  - "3307:3306"  # Use port 3307 on host

# Update DB_HOST in gui.py if needed
```

---

## Development Workflow

### Option 1: Hot Reload (Recommended for Development)

```bash
# Mount application directory as volume (already in docker-compose.yml)
docker-compose up -d

# Edit files on host machine
# Changes reflect immediately in container
```

### Option 2: Rebuild on Changes

```bash
# After modifying Dockerfile or requirements.txt
docker-compose build

# Restart containers
docker-compose down
docker-compose up -d
```

---

## Data Persistence

Data is stored in Docker volumes:

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect movies_mariadb_data

# Backup database
docker-compose exec mariadb mysqldump -u root -proot_password movies_db > backup.sql

# Restore database
docker-compose exec -T mariadb mysql -u root -proot_password movies_db < backup.sql
```

---

## Security Notes

1. **Change default passwords** in `docker-compose.yml` before production use
2. **Never commit passwords** to Git
3. Use `.env` file for sensitive credentials:
   ```bash
   # Create .env file
   cat > .env << EOF
   MYSQL_ROOT_PASSWORD=secure_password_here
   MONGO_PASSWORD=secure_password_here
   EOF
   
   # Reference in docker-compose.yml
   environment:
     DB_PASS: ${MYSQL_ROOT_PASSWORD}
   ```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                   Docker Host                       │
│                                                     │
│  ┌─────────────────┐         ┌─────────────────┐  │
│  │  MariaDB        │         │  Python App     │  │
│  │  Container      │◄────────┤  Container      │  │
│  │  (Port 3306)    │  SQL    │  - gui.py       │  │
│  │                 │         │  - imports      │  │
│  └─────────────────┘         └─────────────────┘  │
│         │                            │             │
│         │                            │             │
│         ▼                            ▼             │
│  ┌─────────────┐            ┌────────────────┐    │
│  │  Volume:    │            │  MongoDB Atlas │    │
│  │  mariadb_   │            │  (Cloud)       │    │
│  │  data       │            │  Port 27017    │    │
│  └─────────────┘            └────────────────┘    │
│                                     ▲              │
└─────────────────────────────────────┼──────────────┘
                                      │
                                  Internet
```

---

## Next Steps

1. ✅ Start Docker containers
2. ✅ Import data from CSV files
3. ✅ Run additional SQL scripts
4. ✅ Launch GUI application
5. 🎬 Start exploring the movie database!

For more information, see `README_simplified.md`.
