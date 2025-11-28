@echo off
REM ============================================================
REM Start MariaDB in Docker for Remote Access
REM ============================================================
REM This starts MariaDB in Docker, accessible from other computers
REM ============================================================

echo ============================================================
echo Starting MariaDB Database in Docker
echo ============================================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running!
    echo Please start Docker Desktop first.
    pause
    exit /b 1
)

REM Stop any existing containers
echo Stopping existing containers...
docker-compose down 2>nul

REM Start only MariaDB (not MongoDB or app)
echo.
echo Starting MariaDB container...
docker-compose up -d mariadb

REM Wait for MariaDB to be ready
echo.
echo Waiting for MariaDB to initialize...
timeout /t 10 /nobreak >nul

REM Check if MariaDB is healthy
echo.
echo Checking MariaDB status...
docker-compose ps mariadb

REM Get the IP address
echo.
echo ============================================================
echo YOUR IP ADDRESS (share this with User B):
echo ============================================================
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4" ^| findstr "192.168"') do (
    echo   %%a
)
echo.
echo MariaDB is running on port 3306
echo User B should set DB_HOST to your IP address above
echo ============================================================
echo.

REM Create remote user with proper authentication
echo Creating remote access user...
docker exec movies_mariadb mysql -uroot -p123456 -e "CREATE USER IF NOT EXISTS 'root'@'%%' IDENTIFIED BY '123456'; GRANT ALL PRIVILEGES ON *.* TO 'root'@'%%' WITH GRANT OPTION; FLUSH PRIVILEGES;" 2>nul

echo.
echo MariaDB is ready for remote connections!
echo.
pause
