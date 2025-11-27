@echo off
REM ============================================================
REM Docker Setup Script for Windows
REM ============================================================
REM This script automates the Docker setup process on Windows
REM ============================================================

echo ============================================================
echo   TMDB Movie Database - Docker Setup (Windows)
echo ============================================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed or not in PATH
    echo.
    echo Please install Docker Desktop from:
    echo https://www.docker.com/products/docker-desktop/
    echo.
    pause
    exit /b 1
)

echo [OK] Docker is installed
docker --version
echo.

REM Check if Docker is running
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running
    echo.
    echo Please start Docker Desktop and try again.
    echo.
    pause
    exit /b 1
)

echo [OK] Docker is running
echo.

REM Build and start containers
echo ============================================================
echo Step 1: Building Docker images...
echo ============================================================
echo.
docker-compose build

if %errorlevel% neq 0 (
    echo [ERROR] Failed to build Docker images
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Step 2: Starting containers...
echo ============================================================
echo.
docker-compose up -d

if %errorlevel% neq 0 (
    echo [ERROR] Failed to start containers
    pause
    exit /b 1
)

echo.
echo [OK] Containers started successfully
echo.
echo Waiting for MariaDB to initialize (30 seconds)...
timeout /t 30 /nobreak >nul

echo.
echo ============================================================
echo Step 3: Importing data...
echo ============================================================
echo.
docker-compose exec -T app python 2_import_data.py

if %errorlevel% neq 0 (
    echo [ERROR] Failed to import data
    echo.
    echo Try running manually:
    echo   docker-compose exec app python 2_import_data.py
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Step 4: Running additional setup scripts...
echo ============================================================
echo.

echo Running: 3_create_indexes.sql
docker-compose exec -T mariadb mysql -u root -proot_password movies_db < 3_create_indexes.sql

echo Running: 4_add_security_features.sql
docker-compose exec -T mariadb mysql -u root -proot_password movies_db < 4_add_security_features.sql

echo Running: 5_update_user_names.sql
docker-compose exec -T mariadb mysql -u root -proot_password movies_db < 5_update_user_names.sql

echo Running: 6_create_watchlist.sql
docker-compose exec -T mariadb mysql -u root -proot_password movies_db < 6_create_watchlist.sql

echo Running: 7_renumber_user_ids.sql
docker-compose exec -T mariadb mysql -u root -proot_password movies_db < 7_renumber_user_ids.sql

echo Running: 8_update_ratings_schema.sql
docker-compose exec -T mariadb mysql -u root -proot_password movies_db < 8_update_ratings_schema.sql

echo.
echo ============================================================
echo   Setup Complete! 🎉
echo ============================================================
echo.
echo The database is now running in Docker containers.
echo.
echo To run the GUI on Windows:
echo   1. Install Python dependencies:
echo      python -m pip install pymysql pymongo bcrypt
echo.
echo   2. Run the GUI:
echo      python gui.py
echo.
echo To view logs:
echo   docker-compose logs -f
echo.
echo To stop containers:
echo   docker-compose down
echo.
echo To connect to MariaDB:
echo   docker-compose exec mariadb mysql -u root -proot_password movies_db
echo.
pause
