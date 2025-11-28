@echo off
REM ============================================================
REM Run GUI - Connect to REMOTE MariaDB + MongoDB Atlas
REM ============================================================
REM For teammates connecting to another computer's MariaDB
REM ============================================================

echo Setting up environment for REMOTE database connection...
echo.

REM ============================================================
REM EDIT THIS: Set the IP address of the computer running MariaDB
REM ============================================================
set DB_HOST=172.22.32.1
set DB_USER=root
set DB_PASS=123456
set DB_NAME=movies_db

REM MongoDB Atlas settings (cloud - shared by all users)
set USE_LOCAL_MONGO=false
set MONGO_USERNAME=nkt12385_db_user
set MONGO_PASSWORD=Keetian12345
set MONGO_CLUSTER=cluster0.qrc4kkf.mongodb.net
set MONGO_DB=movies_nosql
set MONGO_COLL=tmdb_movies

echo Database Configuration:
echo   MariaDB: %DB_HOST%:3306 (REMOTE)
echo   MongoDB: Atlas - %MONGO_CLUSTER% (cloud)
echo.

echo Starting GUI application...
python gui.py

pause
