@echo off
REM ============================================================
REM Run GUI with MongoDB Atlas (Cloud)
REM ============================================================
REM Uses MongoDB Atlas cloud database instead of local Docker
REM ============================================================

echo Setting up environment for MongoDB Atlas...
echo.

REM MariaDB settings (local)
set DB_HOST=localhost
set DB_USER=root
set DB_PASS=123456
set DB_NAME=movies_db

REM MongoDB Atlas settings (cloud)
set USE_LOCAL_MONGO=false
set MONGO_USERNAME=nkt12385_db_user
set MONGO_PASSWORD=Keetian12345
set MONGO_CLUSTER=cluster0.qrc4kkf.mongodb.net
set MONGO_DB=movies_nosql
set MONGO_COLL=tmdb_movies

echo Database Configuration:
echo   MariaDB: %DB_HOST%:3306 (local)
echo   MongoDB: Atlas - %MONGO_CLUSTER% (cloud)
echo.

echo Starting GUI application...
python gui.py

pause
