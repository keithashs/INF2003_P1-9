"""
INF2003 Movie Database - Data Import Script
Imports CSV data into MariaDB with proper data cleaning and validation
"""

import pymysql
import csv
import json
import ast
from datetime import datetime
from pathlib import Path
import sys

# ============================================================
# Configuration
# ============================================================
import os

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASS', '12345'),
    'database': os.getenv('DB_NAME', 'movies_db'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# File paths (adjust if needed)
BASE_DIR = Path(__file__).parent
FILES = {
    'links': BASE_DIR / 'links_small.csv',
    'ratings': BASE_DIR / 'ratings_small.csv',
    'movies': BASE_DIR / 'movies_metadata.csv'
}

# ============================================================
# Helper Functions
# ============================================================

def connect_db():
    """Connect to MariaDB database"""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        print(f"✅ Connected to MariaDB database: {DB_CONFIG['database']}")
        return conn
    except pymysql.Error as err:
        print(f"❌ Error connecting to database: {err}")
        sys.exit(1)

def parse_json_field(field_value):
    """
    Parse JSON-like strings from movies_metadata.csv
    Returns None if parsing fails
    """
    if not field_value or field_value == '':
        return None
    try:
        # Try to evaluate as Python literal (safer than eval)
        return ast.literal_eval(field_value)
    except (ValueError, SyntaxError):
        return None

def extract_genres(genres_str):
    """
    Extract genre names from JSON string like:
    "[{'id': 16, 'name': 'Animation'}, {'id': 35, 'name': 'Comedy'}]"
    Returns: "Animation, Comedy" or None
    """
    genres_list = parse_json_field(genres_str)
    if genres_list and isinstance(genres_list, list):
        return ', '.join([g['name'] for g in genres_list if 'name' in g])
    return None

def parse_date(date_str):
    """Parse date string to YYYY-MM-DD format"""
    if not date_str or date_str == '':
        return None
    try:
        # Try parsing as YYYY-MM-DD
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        try:
            # Try other formats
            dt = datetime.strptime(date_str, '%m/%d/%Y')
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            return None

def safe_int(value, default=None):
    """Safely convert value to int"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_float(value, default=None):
    """Safely convert value to float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

# ============================================================
# Import Functions
# ============================================================

def import_links(conn):
    """Import links_small.csv into LINKS table"""
    print("\n📂 Importing LINKS data...")
    cursor = conn.cursor()
    
    # First, load into staging
    cursor.execute("TRUNCATE TABLE links_staging")
    
    with open(FILES['links'], 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        batch = []
        count = 0
        
        for row in reader:
            movie_id = safe_int(row['movieId'])
            imdb_id = row['imdbId'].strip()
            tmdb_id = safe_int(row['tmdbId'])
            
            if movie_id and imdb_id and tmdb_id:
                batch.append((movie_id, imdb_id, tmdb_id))
                count += 1
                
                # Insert in batches of 1000
                if len(batch) >= 1000:
                    cursor.executemany(
                        "INSERT INTO links_staging (movieId, imdbId, tmdbId) VALUES (%s, %s, %s)",
                        batch
                    )
                    conn.commit()
                    batch = []
                    print(f"  Processed {count} rows...", end='\r')
        
        # Insert remaining rows
        if batch:
            cursor.executemany(
                "INSERT INTO links_staging (movieId, imdbId, tmdbId) VALUES (%s, %s, %s)",
                batch
            )
            conn.commit()
    
    print(f"✅ Loaded {count} rows into links_staging")
    cursor.close()

def import_ratings(conn):
    """Import ratings_small.csv into RATINGS table"""
    print("\n📂 Importing RATINGS data...")
    cursor = conn.cursor()
    
    # First, load into staging
    cursor.execute("TRUNCATE TABLE ratings_staging")
    
    with open(FILES['ratings'], 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        batch = []
        count = 0
        
        for row in reader:
            user_id = safe_int(row['userId'])
            movie_id = safe_int(row['movieId'])
            rating = safe_float(row['rating'])
            timestamp = safe_int(row['timestamp'])
            
            # Validate rating range
            if user_id and movie_id and rating and timestamp:
                if 0.5 <= rating <= 5.0:
                    batch.append((user_id, movie_id, rating, timestamp))
                    count += 1
                    
                    # Insert in batches of 1000
                    if len(batch) >= 1000:
                        cursor.executemany(
                            "INSERT INTO ratings_staging (userId, movieId, rating, timestamp) VALUES (%s, %s, %s, %s)",
                            batch
                        )
                        conn.commit()
                        batch = []
                        print(f"  Processed {count} rows...", end='\r')
        
        # Insert remaining rows
        if batch:
            cursor.executemany(
                "INSERT INTO ratings_staging (userId, movieId, rating, timestamp) VALUES (%s, %s, %s, %s)",
                batch
            )
            conn.commit()
    
    print(f"✅ Loaded {count} rows into ratings_staging")
    cursor.close()

def import_movies(conn):
    """
    Import movies_metadata.csv into MOVIES table
    Note: This extracts only basic info. Complex JSON fields go to MongoDB!
    """
    print("\n📂 Importing MOVIES basic data...")
    cursor = conn.cursor()
    
    movie_data = []
    count = 0
    skipped = 0
    
    with open(FILES['movies'], 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            try:
                # Extract basic fields for SQL
                movie_id = safe_int(row.get('id'))
                title = row.get('title', '').strip()
                release_date = parse_date(row.get('release_date', ''))
                
                if movie_id and title:
                    # Update existing movie with title and date
                    movie_data.append((title, release_date, movie_id))
                    count += 1
                    
                    if len(movie_data) >= 1000:
                        cursor.executemany(
                            """UPDATE MOVIES 
                               SET title = %s, release_date = %s 
                               WHERE movieId = %s""",
                            movie_data
                        )
                        conn.commit()
                        movie_data = []
                        print(f"  Processed {count} rows...", end='\r')
                else:
                    skipped += 1
                    
            except Exception as e:
                skipped += 1
                continue
        
        # Update remaining rows
        if movie_data:
            cursor.executemany(
                """UPDATE MOVIES 
                   SET title = %s, release_date = %s 
                   WHERE movieId = %s""",
                movie_data
            )
            conn.commit()
    
    print(f"✅ Updated {count} movie records")
    print(f"⚠️  Skipped {skipped} invalid rows")
    cursor.close()

def load_staging_to_final(conn):
    """Call stored procedure to move data from staging to final tables"""
    print("\n🔄 Loading data from staging to final tables...")
    cursor = conn.cursor()
    
    try:
        cursor.callproc('load_from_staging')
        conn.commit()
        print("✅ Data successfully loaded into final tables")
    except pymysql.Error as err:
        print(f"❌ Error loading staging data: {err}")
        conn.rollback()
    finally:
        cursor.close()

def show_statistics(conn):
    """Display import statistics"""
    print("\n" + "="*60)
    print("📊 IMPORT STATISTICS")
    print("="*60)
    
    cursor = conn.cursor()
    
    tables = ['USERS', 'MOVIES', 'RATINGS', 'LINKS']
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table:20s}: {count:,} rows")
    
    # Show sample popular movies
    print("\n📈 Top 10 Movies by Average Rating:")
    cursor.execute("""
        SELECT title, rating_count, ROUND(avg_rating, 2) as avg_rating
        FROM popular_movies
        LIMIT 10
    """)
    
    for i, (title, count, avg) in enumerate(cursor.fetchall(), 1):
        print(f"  {i:2d}. {title[:50]:50s} | {count:5d} ratings | ⭐ {avg}")
    
    cursor.close()

# ============================================================
# Main Execution
# ============================================================

def main():
    """Main import process"""
    print("\n" + "="*60)
    print("🎬 INF2003 MOVIE DATABASE - DATA IMPORT")
    print("="*60)
    
    # Check if files exist
    for name, path in FILES.items():
        if not path.exists():
            print(f"❌ File not found: {path}")
            sys.exit(1)
        print(f"✅ Found {name}: {path.name}")
    
    # Connect to database
    conn = connect_db()
    
    try:
        # Import data in order (respecting foreign keys)
        import_links(conn)      # 1. Links first (creates movies)
        import_ratings(conn)    # 2. Ratings (creates users and references movies)
        
        # Load staging to final tables
        load_staging_to_final(conn)
        
        # Update movie details
        import_movies(conn)     # 3. Update movie titles and dates
        
        # Show statistics
        show_statistics(conn)
        
        print("\n" + "="*60)
        print("✅ IMPORT COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\n💡 Next steps:")
        print("   1. Import TMDB_movie_dataset_v11.csv into MongoDB")
        print("   2. Create indexes for performance (see indexing script)")
        print("   3. Test queries and build your application!")
        
    except Exception as e:
        print(f"\n❌ Error during import: {e}")
        conn.rollback()
    finally:
        conn.close()
        print("\n🔌 Database connection closed")

if __name__ == "__main__":
    main()
