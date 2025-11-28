# Setup Guide

## Prerequisites
- Python 3.11+
- MariaDB 10.5+ or MySQL 8.0+
- MongoDB Atlas connection (already configured)

## Step 1: Install Python Dependencies
```bash
pip install -r requirements.txt
```

## Step 2: Configure MariaDB
Create a root user with password `12345` or update `DB_PASS` in `2_import_data.py`.

## Step 3: Run SQL Scripts (in order)
```bash
mysql -u root -p < 1_create_schema.sql
python 2_import_data.py
mysql -u root -p movies_db < 3_create_indexes.sql
mysql -u root -p movies_db < 4_add_security_features.sql
mysql -u root -p movies_db < 5_update_user_names.sql
mysql -u root -p movies_db < 6_create_watchlist.sql
mysql -u root -p movies_db < 7_renumber_user_ids.sql
mysql -u root -p movies_db < 8_update_ratings_schema.sql
```

## Step 4: Launch Application
```bash
python gui.py
```

## Test Accounts
See `TEST_CREDENTIALS.md` for login credentials.
