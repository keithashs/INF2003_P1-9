# ============================================================
# Docker Setup Script for Linux/Mac
# ============================================================
# This script automates the Docker setup process
# ============================================================

#!/bin/bash
set -e

echo "============================================================"
echo "  TMDB Movie Database - Docker Setup"
echo "============================================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "[ERROR] Docker is not installed"
    echo ""
    echo "Please install Docker from: https://www.docker.com/get-started"
    exit 1
fi

echo "[OK] Docker is installed: $(docker --version)"

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "[ERROR] Docker Compose is not installed"
    echo ""
    echo "Please install Docker Compose"
    exit 1
fi

echo "[OK] Docker Compose is installed: $(docker-compose --version)"
echo ""

# Check if Docker is running
if ! docker ps &> /dev/null; then
    echo "[ERROR] Docker daemon is not running"
    echo ""
    echo "Please start Docker and try again"
    exit 1
fi

echo "[OK] Docker daemon is running"
echo ""

# Build and start containers
echo "============================================================"
echo "Step 1: Building Docker images..."
echo "============================================================"
echo ""
docker-compose build

echo ""
echo "============================================================"
echo "Step 2: Starting containers..."
echo "============================================================"
echo ""
docker-compose up -d

echo ""
echo "[OK] Containers started successfully"
echo ""
echo "Waiting for MariaDB to initialize (30 seconds)..."
sleep 30

echo ""
echo "============================================================"
echo "Step 3: Importing data..."
echo "============================================================"
echo ""
docker-compose exec -T app python 2_import_data.py

echo ""
echo "============================================================"
echo "Step 4: Running additional setup scripts..."
echo "============================================================"
echo ""

echo "Running: 3_create_indexes.sql"
docker-compose exec -T mariadb mysql -u root -proot_password movies_db < 3_create_indexes.sql

echo "Running: 4_add_security_features.sql"
docker-compose exec -T mariadb mysql -u root -proot_password movies_db < 4_add_security_features.sql

echo "Running: 5_update_user_names.sql"
docker-compose exec -T mariadb mysql -u root -proot_password movies_db < 5_update_user_names.sql

echo "Running: 6_create_watchlist.sql"
docker-compose exec -T mariadb mysql -u root -proot_password movies_db < 6_create_watchlist.sql

echo "Running: 7_renumber_user_ids.sql"
docker-compose exec -T mariadb mysql -u root -proot_password movies_db < 7_renumber_user_ids.sql

echo "Running: 8_update_ratings_schema.sql"
docker-compose exec -T mariadb mysql -u root -proot_password movies_db < 8_update_ratings_schema.sql

echo ""
echo "============================================================"
echo "  Setup Complete! 🎉"
echo "============================================================"
echo ""
echo "The database is now running in Docker containers."
echo ""
echo "To run the GUI (requires X11):"
echo "  xhost +local:docker"
echo "  docker-compose exec app python gui.py"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f"
echo ""
echo "To stop containers:"
echo "  docker-compose down"
echo ""
echo "To connect to MariaDB:"
echo "  docker-compose exec mariadb mysql -u root -proot_password movies_db"
echo ""
