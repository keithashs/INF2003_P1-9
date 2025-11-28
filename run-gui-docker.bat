@echo off
REM ============================================================
REM Run GUI with Local Docker MongoDB
REM ============================================================
REM Sets environment variables to use local Docker databases
REM ============================================================

echo Setting up environment for Local Docker databases...
echo.

REM MariaDB settings (local Docker)
set DB_HOST=localhost
set DB_USER=root
set DB_PASS=123456
set DB_NAME=movies_db

REM MongoDB settings (local Docker)
set USE_LOCAL_MONGO=true
set MONGO_HOST=localhost
set MONGO_PORT=27017
set MONGO_USERNAME=admin
set MONGO_PASSWORD=admin123
set MONGO_DB=movies_nosql
set MONGO_COLL=tmdb_movies

echo Database Configuration:
echo   MariaDB: %DB_HOST%:3306
echo   MongoDB: %MONGO_HOST%:%MONGO_PORT%
echo.

echo Starting GUI application...
python gui.py

pause
