#!/bin/bash
set -e

# Clean up any stale X11 lock files from previous runs
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99 2>/dev/null || true

echo "Starting virtual display..."
Xvfb :99 -screen 0 1400x900x24 &
export DISPLAY=:99
sleep 2

echo "Starting window manager..."
fluxbox &
sleep 1

echo "Starting VNC server..."
x11vnc -display :99 -forever -shared -rfbport 5900 -nopw &
sleep 1

echo "Starting noVNC web server on port 6080..."
websockify --web /usr/share/novnc 6080 localhost:5900 &

echo "Waiting for database to be ready..."
DB_HOST="${DB_HOST:-mariadb}"
DB_USER="${DB_USER:-root}"
DB_PASS="${DB_PASS:-12345}"
DB_NAME="${DB_NAME:-movies_db}"

# Use mysql client with explicit protocol for Docker networking
for i in $(seq 1 60); do
  echo "Trying to connect to database (attempt $i)..."
  if mysql -h "$DB_HOST" -P 3306 --protocol=tcp --skip-ssl -u "$DB_USER" -p"$DB_PASS" -e "SELECT 1"; then
    echo "Database is ready!"
    break
  fi
  echo "Waiting for database... ($i/60)"
  sleep 2
done

echo "Importing data..."
python 2_import_data.py || echo "Data import completed (may have already existed)"

echo "Running additional SQL scripts..."
mysql -h "$DB_HOST" -P 3306 --protocol=tcp --skip-ssl -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" < 3_create_indexes.sql 2>&1 || echo "Indexes script done"
mysql -h "$DB_HOST" -P 3306 --protocol=tcp --skip-ssl -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" < 4_add_security_features.sql 2>&1 || echo "Security features script done"
mysql -h "$DB_HOST" -P 3306 --protocol=tcp --skip-ssl -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" < 5_update_user_names.sql 2>&1 || echo "User names script done"
mysql -h "$DB_HOST" -P 3306 --protocol=tcp --skip-ssl -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" < 6_create_watchlist.sql 2>&1 || echo "Watchlist script done"
mysql -h "$DB_HOST" -P 3306 --protocol=tcp --skip-ssl -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" < 7_renumber_user_ids.sql 2>&1 || echo "Renumber script done"
mysql -h "$DB_HOST" -P 3306 --protocol=tcp --skip-ssl -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" < 8_update_ratings_schema.sql 2>&1 || echo "Ratings schema script done"
mysql -h "$DB_HOST" -P 3306 --protocol=tcp --skip-ssl -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" < 9_clean_test_accounts.sql 2>&1 || echo "Clean test accounts done"

echo "Starting GUI application..."
python gui.py
