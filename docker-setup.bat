@echo off
REM ============================================================
REM Docker Setup Script for Windows
REM ============================================================
REM This script starts both MariaDB and MongoDB containers
REM and initializes the databases
REM ============================================================

echo ============================================================
echo   TMDB Movie Database - Docker Setup (Windows)
echo ============================================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo [OK] Docker is running
echo.

REM Check if docker-compose is available
docker-compose --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] docker-compose not found, trying 'docker compose'...
    set COMPOSE_CMD=docker compose
) else (
    set COMPOSE_CMD=docker-compose
)

echo [STEP 1/5] Stopping any existing containers...
%COMPOSE_CMD% down 2>nul

echo.
echo [STEP 2/5] Building containers...
%COMPOSE_CMD% build

echo.
echo [STEP 3/5] Starting MariaDB and MongoDB...
%COMPOSE_CMD% up -d mariadb mongodb

echo.
echo [STEP 4/5] Waiting for databases to initialize (30 seconds)...
echo            MariaDB: localhost:3306
echo            MongoDB: localhost:27017
timeout /t 30 /nobreak >nul

REM Check if MariaDB is ready
echo.
echo [INFO] Checking MariaDB connection...
docker exec movies_mariadb mysql -u root -p123456 -e "SELECT 1" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] MariaDB not ready yet, waiting 15 more seconds...
    timeout /t 15 /nobreak >nul
)

REM Check if MongoDB is ready
echo [INFO] Checking MongoDB connection...
docker exec movies_mongodb mongosh --eval "db.adminCommand('ping')" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] MongoDB not ready yet, waiting 15 more seconds...
    timeout /t 15 /nobreak >nul
)

echo.
echo [STEP 5/5] Starting application container...
%COMPOSE_CMD% up -d app

echo.
echo ============================================================
echo   Setup Complete!
echo ============================================================
echo.
echo   Services running:
echo   - MariaDB:  localhost:3306 (user: root, pass: 123456)
echo   - MongoDB:  localhost:27017 (user: admin, pass: admin123)
echo.
echo   Connection strings for gui.py:
echo   - MariaDB: DB_HOST=localhost, DB_PASS=123456
echo   - MongoDB: mongodb://admin:admin123@localhost:27017/movies_nosql
echo.
echo   Next steps:
echo   1. Import data:    docker-compose exec app python 2_import_data.py
echo   2. Run GUI:        python gui.py
echo.
echo   Useful commands:
echo   - View logs:       docker-compose logs -f
echo   - Stop services:   docker-compose down
echo   - MariaDB shell:   docker exec -it movies_mariadb mysql -u root -p123456 movies_db
echo   - MongoDB shell:   docker exec -it movies_mongodb mongosh -u admin -p admin123
echo.
pause
