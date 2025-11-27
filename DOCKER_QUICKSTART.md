# 🚀 Docker Quick Start Guide

## Fastest Way to Get Started (Windows)

### Option 1: Automated Setup (Recommended)
```cmd
docker-setup.bat
```
This script will:
- ✅ Check Docker installation
- ✅ Build containers
- ✅ Start services
- ✅ Import data
- ✅ Run setup scripts

### Option 2: Manual Steps
```cmd
# 1. Start containers
docker-compose up -d

# 2. Wait 30 seconds for MariaDB initialization
timeout /t 30

# 3. Import data
docker-compose exec app python 2_import_data.py

# 4. Run GUI on Windows
python gui.py
```

---

## For Linux/Mac

### Option 1: Automated Setup
```bash
chmod +x docker-setup.sh
./docker-setup.sh
```

### Option 2: Manual Steps
```bash
# 1. Start containers
docker-compose up -d

# 2. Wait for MariaDB
sleep 30

# 3. Import data
docker-compose exec app python 2_import_data.py

# 4. Enable X11 and run GUI
xhost +local:docker
docker-compose exec app python gui.py
```

---

## Essential Commands

```bash
# Start everything
docker-compose up -d

# Stop everything
docker-compose down

# View logs
docker-compose logs -f

# Restart a service
docker-compose restart mariadb

# Access database
docker-compose exec mariadb mysql -u root -proot_password movies_db

# Run GUI in Docker (Linux/Mac only)
docker-compose exec app python gui.py

# Access app shell
docker-compose exec app bash
```

---

## Windows Recommendation

Run **MariaDB in Docker** + **GUI on host**:

1. Start Docker containers:
   ```cmd
   docker-compose up -d mariadb
   ```

2. Install Python packages on Windows:
   ```cmd
   python -m pip install pymysql pymongo bcrypt
   ```

3. Run GUI on Windows:
   ```cmd
   python gui.py
   ```

This avoids X11 complexity on Windows!

---

## Troubleshooting

### "Docker is not running"
- Open Docker Desktop
- Wait for it to fully start (green icon)

### "Port 3306 already in use"
- Stop local MySQL/MariaDB
- Or change port in docker-compose.yml

### "Connection refused"
- Wait longer for MariaDB (use `docker-compose logs mariadb`)
- Look for: "mysqld: ready for connections"

### GUI doesn't show
- **Windows:** Run GUI directly on host (not in Docker)
- **Linux:** Run `xhost +local:docker`
- **Mac:** Install XQuartz first

---

## Default Credentials

**MariaDB:**
- Host: `localhost` (or `mariadb` from inside Docker)
- Port: `3306`
- User: `root`
- Password: `root_password`
- Database: `movies_db`

**MongoDB Atlas:**
- Already configured in docker-compose.yml
- Cloud-based (no local setup needed)

---

## Need Help?

See full documentation: `DOCKER_README.md`
