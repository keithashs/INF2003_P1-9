#!/bin/bash
# ============================================================
# Database Initialization Script
# ============================================================
# This script runs inside the app container to import data
# ============================================================

set -e

echo "============================================================"
echo "  TMDB Movie Database - Data Import"
echo "============================================================"

# Wait for MariaDB to be fully ready
echo "Waiting for MariaDB to be ready..."
until mysql -h mariadb -u root -proot_password -e "SELECT 1" > /dev/null 2>&1; do
    echo "MariaDB not ready yet, waiting..."
    sleep 2
done

echo "✅ MariaDB is ready!"

# Check if data is already imported
TABLES_COUNT=$(mysql -h mariadb -u root -proot_password movies_db -sse "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='movies_db' AND table_name IN ('MOVIES', 'RATINGS', 'LINKS')")

if [ "$TABLES_COUNT" -eq 3 ]; then
    echo "✅ Database schema already exists"
    
    # Check if data is imported
    MOVIES_COUNT=$(mysql -h mariadb -u root -proot_password movies_db -sse "SELECT COUNT(*) FROM MOVIES")
    
    if [ "$MOVIES_COUNT" -gt 0 ]; then
        echo "✅ Data already imported ($MOVIES_COUNT movies)"
        echo "Skipping data import..."
        exit 0
    fi
fi

echo "📂 Importing data from CSV files..."

# Import data using Python script
python /app/2_import_data.py

echo ""
echo "✅ Data import completed!"
echo ""
echo "Running additional SQL scripts..."

# Run additional SQL scripts in order
for script in 3_create_indexes.sql 4_add_security_features.sql 5_update_user_names.sql 6_create_watchlist.sql 7_renumber_user_ids.sql 8_update_ratings_schema.sql; do
    if [ -f "/app/$script" ]; then
        echo "  Running $script..."
        mysql -h mariadb -u root -proot_password movies_db < /app/$script
    fi
done

echo ""
echo "============================================================"
echo "  Database Setup Complete! 🎉"
echo "============================================================"
echo ""
echo "You can now run the application:"
echo "  docker-compose exec app python gui.py"
echo ""
