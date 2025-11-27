"""
Setup Script for TMDB Movie Database
=====================================
This script helps users quickly install dependencies and verify the setup.
All required packages are defined in this file - no external requirements.txt needed.

Usage:
    python setup.py
"""

import subprocess
import sys
import os

# Required packages with minimum versions
REQUIRED_PACKAGES = [
    "pymysql>=1.1.0",      # MariaDB/MySQL connector
    "pymongo>=4.6.0",      # MongoDB connector
    "bcrypt>=4.1.0",       # Password hashing for security
]

def print_header(text):
    """Print a formatted header."""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")

def check_python_version():
    """Check if Python version is compatible."""
    print_header("Checking Python Version")
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ ERROR: Python 3.8 or higher is required!")
        print("   Please upgrade Python and try again.")
        return False
    
    print("✅ Python version is compatible")
    return True

def install_dependencies():
    """Install required packages directly (no requirements.txt needed)."""
    print_header("Installing Dependencies")
    
    try:
        print("Installing required packages:")
        for package in REQUIRED_PACKAGES:
            print(f"  - {package}")
        
        print("\nInstalling...")
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + REQUIRED_PACKAGES)
        print("\n✅ All dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ ERROR: Failed to install dependencies: {e}")
        print("\nTry installing manually:")
        for package in REQUIRED_PACKAGES:
            print(f"  pip install {package}")
        return False

def verify_imports():
    """Verify that all required packages can be imported."""
    print_header("Verifying Installations")
    
    packages = {
        "pymysql": "PyMySQL (MariaDB connector)",
        "pymongo": "PyMongo (MongoDB connector)",
        "bcrypt": "bcrypt (Password hashing)",
        "tkinter": "tkinter (GUI framework)"
    }
    
    all_ok = True
    for package, description in packages.items():
        try:
            __import__(package)
            print(f"✅ {description}")
        except ImportError:
            print(f"❌ {description} - NOT FOUND")
            all_ok = False
    
    return all_ok

def check_database_config():
    """Check if database environment variables are set."""
    print_header("Checking Database Configuration")
    
    # MariaDB variables
    mariadb_vars = ["DB_HOST", "DB_USER", "DB_PASS", "DB_NAME"]
    # MongoDB variables
    mongo_vars = ["MONGO_USERNAME", "MONGO_PASSWORD", "MONGO_CLUSTER", "MONGO_DB", "MONGO_COLL"]
    
    print("MariaDB Configuration:")
    mariadb_ok = True
    for var in mariadb_vars:
        value = os.getenv(var)
        if value:
            # Mask password
            display_value = "***" if "PASS" in var else value
            print(f"  ✅ {var} = {display_value}")
        else:
            print(f"  ⚠️  {var} not set (will use default)")
            mariadb_ok = False
    
    print("\nMongoDB Configuration:")
    mongo_ok = True
    for var in mongo_vars:
        value = os.getenv(var)
        if value:
            # Mask password
            display_value = "***" if "PASSWORD" in var else value
            print(f"  ✅ {var} = {display_value}")
        else:
            print(f"  ⚠️  {var} not set (will use default)")
            mongo_ok = False
    
    if not mariadb_ok or not mongo_ok:
        print("\n⚠️  WARNING: Some environment variables not set.")
        print("   The application will use default values from gui.py")
        print("   For production, set environment variables for security.")
    
    return True

def print_next_steps():
    """Print instructions for next steps."""
    print_header("Setup Complete!")
    
    print("Next steps:")
    print("\n1. Set up MariaDB database:")
    print("   mysql -u root -p < 1_create_schema.sql")
    print("   python 2_import_data.py")
    print("   mysql -u root -p movies_db < 3_create_indexes.sql")
    print("   mysql -u root -p movies_db < 4_add_security_features.sql")
    print("   mysql -u root -p movies_db < 5_update_user_names.sql")
    print("   mysql -u root -p movies_db < 6_create_watchlist.sql")
    print("   mysql -u root -p movies_db < 7_renumber_user_ids.sql")
    print("   mysql -u root -p movies_db < 8_update_ratings_schema.sql")
    
    print("\n2. Verify MongoDB Atlas connection")
    print("   Connection: mongodb+srv://nkt12385_db_user:***@cluster0.qrc4kkf.mongodb.net/")
    print("   Database: movies_nosql")
    print("   Collection: tmdb_movies")
    
    print("\n3. Run the application:")
    print("   python gui.py")
    
    print("\n" + "="*60)

def main():
    """Main setup function."""
    print("""
╔══════════════════════════════════════════════════════════╗
║     TMDB Movie Database - Setup Script                  ║
║     Hybrid SQL-NoSQL Movie Database System               ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    # Step 1: Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Step 2: Install dependencies
    if not install_dependencies():
        print("\n❌ Setup failed at dependency installation.")
        sys.exit(1)
    
    # Step 3: Verify imports
    if not verify_imports():
        print("\n❌ Setup failed at import verification.")
        print("   Please check error messages above and install missing packages.")
        sys.exit(1)
    
    # Step 4: Check database configuration
    check_database_config()
    
    # Step 5: Print next steps
    print_next_steps()

if __name__ == "__main__":
    main()
