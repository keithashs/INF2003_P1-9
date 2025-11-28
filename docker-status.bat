@echo off
REM ============================================================
REM Check Docker Container Status
REM ============================================================

echo ============================================================
echo   Docker Container Status Check
echo ============================================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker is not running!
    echo Please start Docker Desktop.
    pause
    exit /b 1
)

echo [Docker] Running
echo.

echo ============================================================
echo   Container Status
echo ============================================================
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo.
echo ============================================================
echo   Testing Database Connections
echo ============================================================
echo.

echo Testing MariaDB connection...
docker exec movies_mariadb mysql -u root -p123456 -e "SELECT 'MariaDB OK' as status;" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [FAIL] MariaDB not responding
) else (
    echo [OK] MariaDB connected
)

echo.
echo Testing MongoDB connection...
docker exec movies_mongodb mongosh --quiet -u admin -p admin123 --authenticationDatabase admin --eval "print('MongoDB OK')" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [FAIL] MongoDB not responding
) else (
    echo [OK] MongoDB connected
)

echo.
echo ============================================================
echo   Quick Commands
echo ============================================================
echo.
echo   Start services:     docker-compose up -d
echo   Stop services:      docker-compose down
echo   View logs:          docker-compose logs -f
echo   MariaDB shell:      docker exec -it movies_mariadb mysql -u root -p123456 movies_db
echo   MongoDB shell:      docker exec -it movies_mongodb mongosh -u admin -p admin123 --authenticationDatabase admin
echo.
pause
