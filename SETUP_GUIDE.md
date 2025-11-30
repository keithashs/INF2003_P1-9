# Setup Guide

## Prerequisites
- Python 3.11+
- MariaDB 10.5+ or MySQL 8.0+
- MongoDB Atlas connection (already configured)

## Step 1: Install Python Dependencies
Run in **VS Code Terminal**:
```bash
pip install -r requirements.txt
```

## Step 2: Configure Your Database Password
**Important:** Update the database password to match your own MariaDB/MySQL configuration:
- In `2_import_data.py` (line 22): Change `DB_PASS` to your password
- In `gui.py` (line 51): Change `DB_PASS` to your password

## Step 3: Run SQL Scripts (in order)
Run scripts **1, 3-8 in SQL** (MySQL Workbench or command line) and **script 2 in VS Code Terminal**:

```bash
# Run in SQL (MySQL Workbench or mysql command line)
mysql -u root -p < 1_create_schema.sql

# Run in VS Code Terminal
python 2_import_data.py

# Run in SQL (MySQL Workbench or mysql command line)
mysql -u root -p movies_db < 3_create_indexes.sql
mysql -u root -p movies_db < 4_add_security_features.sql
mysql -u root -p movies_db < 5_update_user_names.sql
mysql -u root -p movies_db < 6_create_watchlist.sql
mysql -u root -p movies_db < 7_renumber_user_ids.sql
mysql -u root -p movies_db < 8_update_ratings_schema.sql
mysql -u root -p movies_db < 9_clean_test_accounts.sql
```

## Step 4: Launch Application
Run in **VS Code Terminal**:
```bash
python gui.py
```

## Test Accounts
See `TEST_CREDENTIALS.md` for login credentials.
