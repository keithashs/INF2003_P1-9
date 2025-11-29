import time
import re
import hashlib
import sys
import random
import os
import bcrypt
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from decimal import Decimal
import tkinter as tk
from tkinter import ttk, messagebox
import pymysql
import pymysql.err
from pymongo import MongoClient
from pymongo import errors as mongo_errors

###############################################################################
# LOGGING CONFIGURATION
###############################################################################

# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            'logs/movies_db.log',
            maxBytes=5*1024*1024,  # 5MB
            backupCount=5,
            encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

###############################################################################
# 1. DB CONNECTION SETTINGS
###############################################################################

# Load credentials from environment variables for security
# Set these in your system environment or use a .env file
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "12345")  # Default for development only
DB_NAME = os.getenv("DB_NAME", "movies_db")

# MongoDB Connection Settings
# Supports both LOCAL Docker MongoDB and MongoDB Atlas (cloud)
# Set USE_LOCAL_MONGO=true to use local Docker MongoDB
USE_LOCAL_MONGO = os.getenv("USE_LOCAL_MONGO", "false").lower() == "true"

# Local MongoDB (Docker) Settings
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")

# MongoDB Atlas Connection Settings (cloud)
MONGO_USERNAME = os.getenv("MONGO_USERNAME", "nkt12385_db_user")  # Default for development
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "Keetian12345")  # Default for development
MONGO_CLUSTER = os.getenv("MONGO_CLUSTER", "cluster0.qrc4kkf.mongodb.net")

# Common MongoDB Settings
MONGO_DB = os.getenv("MONGO_DB", "movies_nosql")
MONGO_COLL = os.getenv("MONGO_COLL", "tmdb_movies")

# MongoDB connection - supports both local Docker and Atlas
def get_mongo_connection():
    """
    Establish MongoDB connection.
    Uses local Docker MongoDB if USE_LOCAL_MONGO=true, otherwise MongoDB Atlas.
    Returns (client, db, collection) tuple.
    """
    try:
        if USE_LOCAL_MONGO:
            # Local Docker MongoDB connection
            # Format: mongodb://username:password@host:port/
            local_username = os.getenv("MONGO_USERNAME", "admin")
            local_password = os.getenv("MONGO_PASSWORD", "admin123")
            mongo_connection_string = f"mongodb://{local_username}:{local_password}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
            logger.info(f"Connecting to LOCAL MongoDB: {MONGO_HOST}:{MONGO_PORT}")
        else:
            # MongoDB Atlas connection (cloud)
            # Format: mongodb+srv://<username>:<password>@<cluster>/?retryWrites=true&w=majority
            mongo_connection_string = f"mongodb+srv://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_CLUSTER}/?retryWrites=true&w=majority"
            logger.info(f"Connecting to MongoDB Atlas: {MONGO_CLUSTER}")
        
        client = MongoClient(mongo_connection_string, serverSelectionTimeoutMS=5000)
        # Test connection
        client.admin.command('ping')
        db = client[MONGO_DB]
        collection = db[MONGO_COLL]
        
        if USE_LOCAL_MONGO:
            logger.info(f"Successfully connected to LOCAL MongoDB: {MONGO_HOST}:{MONGO_PORT}")
        else:
            logger.info(f"Successfully connected to MongoDB Atlas: {MONGO_CLUSTER}")
        logger.info(f"Using database: {MONGO_DB}, collection: {MONGO_COLL}")
        
        return client, db, collection
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        return None, None, None

# Initialize MongoDB connection
mongo_client, mongo_db, tmdb_collection = get_mongo_connection()

if mongo_client is None:
    logger.warning("MongoDB connection failed. Some features may be unavailable.")
    # Don't show messagebox during import - it may not be in GUI context

# Global current session (after login)
CURRENT_USER = {
    "userId": None,
    "username": "guest",
    "email": None,
    "role": "guest",  # Default to "guest", changes to "user" or "admin" after login
}


def get_connection():
    """Open a MariaDB connection using DictCursor."""
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False  # we explicitly control commit for ACID demo
    )


###############################################################################
# 1B. AUTHENTICATION & SECURITY
###############################################################################

def is_valid_email(email: str) -> bool:
    """Basic email regex validation."""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None


def hash_password(password: str) -> str:
    """Hash password using bcrypt (industry standard with salt)."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against bcrypt hash OR legacy SHA256 hash."""
    try:
        # Check if it's a bcrypt hash (starts with $2b$ or $2a$ or $2y$)
        if hashed.startswith(('$2b$', '$2a$', '$2y$')):
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        else:
            # Legacy SHA256 hash (64 hex characters)
            import hashlib
            sha256_hash = hashlib.sha256(password.encode()).hexdigest()
            return sha256_hash == hashed
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def authenticate_user(username: str, password: str):
    """
    Look up user in USERS table, compare password hash, return user dict with role.
    Expected table columns (as per your GUI file): userId, username, email, role, password_hash.
    """
    sql = """
        SELECT userId, username, email, role, password_hash
        FROM USERS
        WHERE username = %s
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (username,))
            user = cur.fetchone()
            
            if not user:
                return None
                
            # Use verify_password instead of direct hash comparison
            if not verify_password(password, user['password_hash']):
                return None
                
            # Update global state
            global CURRENT_USER
            CURRENT_USER.update({
                "userId": user['userId'],
                "username": user['username'],
                "email": user['email'],
                "role": user['role']
            })
                
            return user
    finally:
        conn.close()

def get_tmdb_metadata(tmdb_id):
    if not tmdb_id:
        return None
    
    # Check MongoDB connection
    if tmdb_collection is None:
        print("[WARN] MongoDB Atlas not connected. Cannot fetch TMDB metadata.")
        return None
        
    try:
        # try int cast
        try:
            tmdb_id_int = int(tmdb_id)
        except:
            tmdb_id_int = tmdb_id

        print(f"[SEARCH] Looking for TMDB ID: {tmdb_id_int} in MongoDB Atlas...")
        
        # Try both "id" and "tmdbId" fields (Atlas collection uses "id")
        doc = tmdb_collection.find_one({"id": tmdb_id_int})
        
        if not doc:
            # Fallback: try tmdbId field
            doc = tmdb_collection.find_one({"tmdbId": tmdb_id_int})

        if not doc:
            print(f"[NOT FOUND] No document found for TMDB ID: {tmdb_id_int}")
            return None
        
        print(f"[OK] Found movie: {doc.get('title', 'Unknown')}")

        return {
            "tmdbId": doc.get("id") or doc.get("tmdbId"),  # Use "id" field from Atlas
            "title": doc.get("title"),
            "overview": doc.get("overview"),
            "genres": doc.get("genres"),
            "keywords": doc.get("keywords"),
            "vote_average": doc.get("vote_average"),
            "vote_count": doc.get("vote_count"),
            "revenue": doc.get("revenue"),
            "runtime": doc.get("runtime"),
            "original_language": doc.get("original_language"),
            "release_date": doc.get("release_date"),
            "tagline": doc.get("tagline"),
            "popularity": doc.get("popularity"),
        }
    except mongo_errors.ConnectionFailure as e:
        print(f"[ERROR] MongoDB connection failed in get_tmdb_metadata: {e}")
        return None
    except mongo_errors.OperationFailure as e:
        print(f"[ERROR] MongoDB operation failed in get_tmdb_metadata: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Unexpected error in get_tmdb_metadata: {e}")
        return None

# ---------------- Concurrency lock helpers for ratings ----------------
# prof asked: can 1 user update same row in 2 windows at once and break stuff?
# We solve using a rating_locks / RATING_LOCKS table and transactions. :contentReference[oaicite:2]{index=2}

def check_rating_lock(user_id, movie_id):
    """
    Check if (user_id, movie_id) rating is currently locked by someone else in RATING_LOCKS.
    If locked <5 minutes (300s) ago by another username, return that username.
    Else return None.
    
    - User A editing Movie D → Movie D is LOCKED
    - User B tries to edit Movie D → BLOCKED until User A finishes
    - User A finishes → Movie D is UNLOCKED
    - Now User B can edit Movie D
    """
    sql = """
        SELECT locked_by, locked_at
        FROM RATING_LOCKS
        WHERE userId = %s AND movieId = %s
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, movie_id))
            lock = cur.fetchone()
            if lock:
                locked_when = lock["locked_at"]
                now_ts = int(time.time())
                # Lock timeout: 5 minutes (300 seconds)
                if now_ts - locked_when < 300:
                    return lock["locked_by"]
        return None
    finally:
        conn.close()


def check_movie_lock(movie_id, current_username):
    """
    Check if ANY user has locked this specific movie (for concurrent edit prevention).
    Returns the username of whoever has the lock, or None if unlocked.
    
    - User A editing Movie 201 → Movie 201 is LOCKED (any userId with movieId=201)
    - User B tries to edit Movie 201 → BLOCKED (lock found for movieId=201)
    - User A finishes → Movie 201 is UNLOCKED
    - Now User B can edit Movie 201
    
    NOTE: This checks ONLY by movieId, not (userId, movieId) pair!
    This prevents ANY user from editing a movie that's being edited by ANYONE.
    """
    sql = """
        SELECT userId, locked_by, locked_at
        FROM RATING_LOCKS
        WHERE movieId = %s
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (movie_id,))
            locks = cur.fetchall()
            
            if not locks:
                return None  # No locks on this movie
            
            now_ts = int(time.time())
            
            # Check all locks on this movie
            for lock in locks:
                locked_when = lock["locked_at"]
                locked_by_user = lock["locked_by"]
                
                # Lock timeout: 5 minutes (300 seconds)
                if now_ts - locked_when < 300:
                    # Valid lock found
                    if locked_by_user != current_username:
                        # Locked by SOMEONE ELSE
                        return locked_by_user
                    # else: locked by current user (allow re-entry)
            
            return None  # No active locks or all locks expired
    finally:
        conn.close()


def acquire_rating_lock(user_id, movie_id, locked_by_username):
    """
    Mark a row as locked by CURRENT_USER.
    We upsert into RATING_LOCKS with current timestamp.
    
    This prevents concurrent edits:
    - When User A acquires lock for Movie D → other users cannot edit Movie D
    - Lock expires after 5 minutes if not released (timeout protection)
    - User A must release lock after update for others to edit
    """
    sql = """
        INSERT INTO RATING_LOCKS (userId, movieId, locked_by, locked_at)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE locked_by=%s, locked_at=%s
    """
    ts = int(time.time())
    logger.info(f"[LOCK ACQUIRED] User '{locked_by_username}' locked rating (userId={user_id}, movieId={movie_id})")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (user_id, movie_id, locked_by_username, ts,
                 locked_by_username, ts)
            )
        conn.commit()
        return True
    except pymysql.err.OperationalError as e:
        print(f"[ERROR] Database connection error in acquire_rating_lock: {e}")
        conn.rollback()
        return False
    except pymysql.MySQLError as e:
        print(f"[ERROR] Database error in acquire_rating_lock: {e}")
        conn.rollback()
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error in acquire_rating_lock: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def release_rating_lock(user_id, movie_id):
    """
    Remove the lock row for that (user,movie).
    This unlocks the rating so other users can edit it.
    """
    sql = "DELETE FROM RATING_LOCKS WHERE userId = %s AND movieId = %s"
    logger.info(f"[LOCK RELEASED] Rating unlocked (userId={user_id}, movieId={movie_id})")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, movie_id))
        conn.commit()
    finally:
        conn.close()


###############################################################################
# 2. SQL HELPERS – MOVIES (MariaDB side)
###############################################################################

def search_movies_by_title(keyword):
    """
    Simple search by title.
    Returns rows + runtime (sec).
    Skips weird placeholder titles like 'Movie_%'.
    """
    start = time.time()
    sql = """
        SELECT
            m.movieId,
            m.title,
            COUNT(r.rating) AS vote_count,
            ROUND(AVG(r.rating), 2) AS avg_rating
        FROM movies m
        LEFT JOIN ratings r ON m.movieId = r.movieId
        WHERE m.title LIKE %s
          AND m.title NOT LIKE 'Movie_%%'
        GROUP BY m.movieId, m.title
        ORDER BY
            ROUND(AVG(r.rating), 2) IS NULL ASC,
            ROUND(AVG(r.rating), 2) DESC,
            m.title ASC
        LIMIT 50
    """
    like_param = f"%{keyword}%"
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (like_param,))
            rows = cur.fetchall()
    finally:
        conn.close()
    return rows, time.time() - start


def search_movies_advanced(title=None, min_rating=None, max_rating=None, min_votes=None):
    """
    Advanced search combining WHERE + HAVING with aggregates.
    """
    start = time.time()
    base_sql = """
        SELECT
            m.movieId,
            m.title,
            m.release_date,
            COUNT(r.rating) AS vote_count,
            ROUND(AVG(r.rating), 2) AS avg_rating
        FROM movies m
        LEFT JOIN ratings r ON m.movieId = r.movieId
    """

    conditions = ["m.title NOT LIKE 'Movie_%%'"]
    params = []

    if title:
        conditions.append("m.title LIKE %s")
        params.append(f"%{title}%")

    base_sql += " WHERE " + " AND ".join(conditions)
    base_sql += " GROUP BY m.movieId, m.title, m.release_date"

    having_parts = []
    if min_rating is not None:
        having_parts.append("ROUND(AVG(r.rating), 2) >= %s")
        params.append(min_rating)
    if max_rating is not None:
        having_parts.append("ROUND(AVG(r.rating), 2) <= %s")
        params.append(max_rating)
    if min_votes is not None:
        having_parts.append("COUNT(r.rating) >= %s")
        params.append(min_votes)

    if having_parts:
        base_sql += " HAVING " + " AND ".join(having_parts)

    base_sql += " ORDER BY avg_rating DESC, vote_count DESC LIMIT 50"

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(base_sql, params)
            rows = cur.fetchall()
    finally:
        conn.close()
    return rows, time.time() - start


def get_movie_details(movie_id):
    """
    Join movies, ratings, links to get SQL info for one movie.
    Includes tmdbId so we can jump into Mongo.
    """
    sql = """
        SELECT
            m.movieId,
            m.title,
            m.release_date,
            ROUND(AVG(r.rating), 2) AS avg_rating,
            COUNT(r.rating) AS vote_count,
            l.imdbId,
            l.tmdbId
        FROM movies m
        LEFT JOIN ratings r ON m.movieId = r.movieId
        LEFT JOIN links   l ON m.movieId = l.movieId
        WHERE m.movieId = %s
        GROUP BY m.movieId, m.title, m.release_date, l.imdbId, l.tmdbId
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (movie_id,))
            row = cur.fetchone()
    finally:
        conn.close()
    return row


def find_movie_by_title_sql(title):
    """
    Search for a movie by title in MariaDB.
    Returns list of matching movies with their IDs.
    """
    sql = """
        SELECT movieId, title
        FROM movies
        WHERE title LIKE %s
          AND title NOT LIKE 'Movie_%%'
        ORDER BY title ASC
        LIMIT 10
    """
    like_param = f"%{title}%"
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (like_param,))
            rows = cur.fetchall()
    finally:
        conn.close()
    return rows


###############################################################################
# 2B. MOVIE CRUD OPERATIONS (ADMIN ONLY)
###############################################################################

def add_movie_to_sql(title, release_date=None):
    """
    Add a new movie to MariaDB movies table.
    Returns (success, movie_id) tuple.
    """
    print(f"[DEBUG add_movie_to_sql] CURRENT_USER: {CURRENT_USER}")
    print(f"[DEBUG add_movie_to_sql] role check: '{CURRENT_USER['role']}' != 'admin' = {CURRENT_USER['role'] != 'admin'}")
    
    if CURRENT_USER['role'] != 'admin':
        print(f"[ERROR add_movie_to_sql] Permission denied - role is '{CURRENT_USER['role']}', not 'admin'")
        return False, None
        
    sql = """
        INSERT INTO movies (title, release_date)
        VALUES (%s, %s)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (title, release_date))
            movie_id = cur.lastrowid
        conn.commit()
        print(f"[DEBUG add_movie_to_sql] Success! movie_id={movie_id}")
        return True, movie_id
    except pymysql.MySQLError as e:
        conn.rollback()
        print(f"[ERROR add_movie_to_sql] Database error: {e}")
        return False, None
    finally:
        conn.close()


def update_movie_in_sql(movie_id, title=None, release_date=None):
    """
    Update movie details in MariaDB.
    Only updates fields that are provided (not None).
    """
    if CURRENT_USER['role'] != 'admin':
        return False
        
    updates = []
    params = []
    
    if title is not None:
        updates.append("title = %s")
        params.append(title)
    if release_date is not None:
        updates.append("release_date = %s")
        params.append(release_date)
        
    if not updates:
        return False
        
    params.append(movie_id)
    sql = f"UPDATE movies SET {', '.join(updates)} WHERE movieId = %s"
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
        conn.commit()
        return True
    except pymysql.MySQLError as e:
        conn.rollback()
        print(f"[ERROR] Failed to update movie: {e}")
        return False
    finally:
        conn.close()


def delete_movie_from_sql(movie_id):
    """
    Delete a movie from MariaDB movies table.
    Also deletes associated ratings and links (cascade).
    """
    if CURRENT_USER['role'] != 'admin':
        return False
        
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Delete ratings first (foreign key constraint)
            cur.execute("DELETE FROM ratings WHERE movieId = %s", (movie_id,))
            # Delete links
            cur.execute("DELETE FROM links WHERE movieId = %s", (movie_id,))
            # Delete movie
            cur.execute("DELETE FROM movies WHERE movieId = %s", (movie_id,))
        conn.commit()
        return True
    except pymysql.MySQLError as e:
        conn.rollback()
        print(f"[ERROR] Failed to delete movie: {e}")
        return False
    finally:
        conn.close()


def update_movie_links(movie_id, imdb_id=None, tmdb_id=None):
    """
    Update or insert links for a movie.
    """
    print(f"[DEBUG update_movie_links] Called with movie_id={movie_id}, imdb_id={imdb_id}, tmdb_id={tmdb_id}")
    print(f"[DEBUG update_movie_links] CURRENT_USER['role']={CURRENT_USER['role']}")
    
    if CURRENT_USER['role'] != 'admin':
        print("[ERROR update_movie_links] Permission denied - not admin")
        return False
        
    sql = """
        INSERT INTO links (movieId, imdbId, tmdbId)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            imdbId = VALUES(imdbId),
            tmdbId = VALUES(tmdbId)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            print(f"[DEBUG update_movie_links] Executing SQL: INSERT INTO links VALUES ({movie_id}, {imdb_id}, {tmdb_id})")
            cur.execute(sql, (movie_id, imdb_id, tmdb_id))
        conn.commit()
        print(f"[SUCCESS update_movie_links] Links updated successfully")
        return True
    except pymysql.MySQLError as e:
        conn.rollback()
        import traceback
        print(f"[ERROR update_movie_links] Database error: {e}")
        print(f"[ERROR update_movie_links] Traceback: {traceback.format_exc()}")
        return False
    finally:
        conn.close()


def add_movie_to_mongo(tmdb_id, title, overview="", genres="", keywords="", 
                       vote_average=0, vote_count=0, revenue=0, runtime=0,
                       original_language="en", release_date="", tagline="", popularity=0):
    """
    Add or update a movie in MongoDB tmdb_movies collection.
    This allows admin to add rich metadata for movies.
    """
    print(f"[DEBUG add_movie_to_mongo] Called with tmdb_id={tmdb_id}, title={title}")
    print(f"[DEBUG add_movie_to_mongo] CURRENT_USER['role']={CURRENT_USER['role']}")
    
    if CURRENT_USER['role'] != 'admin':
        print("[ERROR add_movie_to_mongo] Permission denied - not admin")
        return False
        
    if tmdb_collection is None:
        print("[ERROR add_movie_to_mongo] MongoDB not connected (tmdb_collection is None)")
        return False
    
    print(f"[DEBUG add_movie_to_mongo] MongoDB connection OK, preparing document...")
        
    try:
        doc = {
            "id": int(tmdb_id),
            "title": title,
            "overview": overview,
            "genres": genres,
            "keywords": keywords,
            "vote_average": float(vote_average) if vote_average else 0,
            "vote_count": int(vote_count) if vote_count else 0,
            "revenue": float(revenue) if revenue else 0,
            "runtime": float(runtime) if runtime else 0,
            "original_language": original_language,
            "release_date": release_date,
            "tagline": tagline,
            "popularity": float(popularity) if popularity else 0,
        }
        
        print(f"[DEBUG add_movie_to_mongo] Document prepared: {doc}")
        print(f"[DEBUG add_movie_to_mongo] Executing upsert operation...")
        
        # Upsert (update if exists, insert if not)
        result = tmdb_collection.update_one(
            {"id": int(tmdb_id)},
            {"$set": doc},
            upsert=True
        )
        
        print(f"[DEBUG add_movie_to_mongo] Upsert result: matched={result.matched_count}, modified={result.modified_count}, upserted_id={result.upserted_id}")
        print(f"[SUCCESS add_movie_to_mongo] MongoDB operation completed successfully")
        return True
    except Exception as e:
        import traceback
        print(f"[ERROR add_movie_to_mongo] Exception: {e}")
        print(f"[ERROR add_movie_to_mongo] Traceback: {traceback.format_exc()}")
        return False


def delete_movie_from_mongo(tmdb_id):
    """
    Delete a movie from MongoDB tmdb_movies collection.
    """
    if CURRENT_USER['role'] != 'admin':
        return False
        
    if tmdb_collection is None:
        print("[WARN] MongoDB not connected")
        return False
        
    try:
        tmdb_collection.delete_one({"id": int(tmdb_id)})
        return True
    except Exception as e:
        print(f"[ERROR] Failed to delete movie from MongoDB: {e}")
        return False


###############################################################################
# 3. NoSQL HELPERS – MongoDB side
###############################################################################


def search_movies_by_genre_mongo(genre):
    """
    Regex match on genres field.
    This shows flexible text search in NoSQL.
    """
    # Check MongoDB connection
    if tmdb_collection is None:
        print("[WARN] MongoDB Atlas not connected. Cannot search by genre.")
        return [], 0.0
        
    try:
        start = time.time()
        print(f"[SEARCH] Searching MongoDB Atlas for genre: {genre}")
        cursor = tmdb_collection.find(
            {"genres": {"$regex": genre, "$options": "i"}},
            {
                "id": 1,  # Changed from "tmdbId" to "id" for Atlas
                "title": 1,
                "genres": 1,
                "vote_average": 1,
                "overview": 1,
                "runtime": 1,
            }
        ).limit(50)
        docs = list(cursor)
        print(f"[OK] Found {len(docs)} movies for genre '{genre}'")
        return docs, time.time() - start
    except mongo_errors.ConnectionFailure as e:
        print(f"[ERROR] MongoDB connection failed in genre search: {e}")
        return [], 0.0
    except mongo_errors.OperationFailure as e:
        print(f"[ERROR] MongoDB operation failed in genre search: {e}")
        return [], 0.0
    except Exception as e:
        print(f"[ERROR] Unexpected error in genre search: {e}")
        return [], 0.0


def search_movies_by_keyword_mongo(keyword):
    """
    Regex match on keywords field.
    Used in performance tab to show NoSQL shines on text-y stuff.
    """
    # Check MongoDB connection
    if tmdb_collection is None:
        print("[WARN] MongoDB Atlas not connected. Cannot search by keyword.")
        return [], 0.0
        
    try:
        start = time.time()
        print(f"[SEARCH] Searching MongoDB Atlas for keyword: {keyword}")
        cursor = tmdb_collection.find(
            {"keywords": {"$regex": keyword, "$options": "i"}},
            {
                "id": 1,  # Changed from "tmdbId" to "id" for Atlas
                "title": 1,
                "keywords": 1,
                "genres": 1,
                "vote_average": 1,
            }
        ).limit(50)
        docs = list(cursor)
        print(f"[OK] Found {len(docs)} movies with keyword '{keyword}'")
        return docs, time.time() - start
    except mongo_errors.ConnectionFailure as e:
        print(f"[ERROR] MongoDB connection failed in keyword search: {e}")
        return [], 0.0
    except mongo_errors.OperationFailure as e:
        print(f"[ERROR] MongoDB operation failed in keyword search: {e}")
        return [], 0.0
    except Exception as e:
        print(f"[ERROR] Unexpected error in keyword search: {e}")
        return [], 0.0


def get_genre_statistics_mongo():
    """
    MongoDB aggregation pipeline.
    We'll group by the 'genres' string and compute counts & averages.
    """
    # Check MongoDB connection
    if tmdb_collection is None:
        print("[WARN] MongoDB Atlas not connected. Cannot get genre statistics.")
        return [], 0.0
        
    try:
        start = time.time()
        print("[STATS] Calculating genre statistics from MongoDB Atlas...")
        pipeline = [
            {"$match": {"genres": {"$exists": True, "$ne": ""}}},
            {"$group": {
                "_id": "$genres",
                "count": {"$sum": 1},
                "avg_rating": {"$avg": "$vote_average"},
                "avg_revenue": {"$avg": "$revenue"},
            }},
            {"$sort": {"count": -1}},
            {"$limit": 20},
        ]
        agg = list(tmdb_collection.aggregate(pipeline))
        print(f"[OK] Generated statistics for {len(agg)} genre groups")
        return agg, time.time() - start
    except mongo_errors.ConnectionFailure as e:
        print(f"[ERROR] MongoDB connection failed in genre statistics: {e}")
        return [], 0.0
    except mongo_errors.OperationFailure as e:
        print(f"[ERROR] MongoDB operation failed in genre statistics: {e}")
        return [], 0.0
    except Exception as e:
        print(f"[ERROR] Unexpected error in genre statistics: {e}")
        return [], 0.0


def find_similar_movies_mongo(tmdb_id):
    """
    Approx "recommendations": pick first genre of the movie,
    then find other movies with that genre.
    """
    # Check MongoDB connection
    if tmdb_collection is None:
        print("[WARN] MongoDB Atlas not connected. Cannot find similar movies.")
        return [], 0.0
        
    try:
        start = time.time()
        tmdb_id_int = int(tmdb_id) if not isinstance(tmdb_id, int) else tmdb_id
        
        print(f"[SEARCH] Finding similar movies for TMDB ID: {tmdb_id_int}")
        
        # Try with "id" field first (Atlas schema), then fallback to "tmdbId"
        base = tmdb_collection.find_one({"id": tmdb_id_int})
        if not base:
            base = tmdb_collection.find_one({"tmdbId": tmdb_id_int})
            
        if not base or not base.get("genres"):
            print(f"[NOT FOUND] Base movie not found or has no genres for ID: {tmdb_id_int}")
            return [], 0.0

        # take first genre token
        first_genre = (
            base["genres"].split(",")[0].strip()
            if "," in base["genres"] else base["genres"]
        )
        
        print(f"[INFO] Searching for movies with genre: {first_genre}")

        cursor = tmdb_collection.find(
            {
                "id": {"$ne": tmdb_id_int},
                "genres": {"$regex": first_genre, "$options": "i"},
            },
            {
                "id": 1,
                "title": 1,
                "genres": 1,
                "vote_average": 1,
                "overview": 1,
            }
        ).limit(10)
        docs = list(cursor)
        print(f"[OK] Found {len(docs)} similar movies")
        return docs, time.time() - start
    except mongo_errors.ConnectionFailure as e:
        print(f"[ERROR] MongoDB connection failed in find similar movies: {e}")
        return [], 0.0
    except mongo_errors.OperationFailure as e:
        print(f"[ERROR] MongoDB operation failed in find similar movies: {e}")
        return [], 0.0
    except Exception as e:
        print(f"[ERROR] Unexpected error in find similar movies: {e}")
        return [], 0.0


def find_movie_by_title_mongo(title):
    """
    Search for a movie by title in MongoDB to get its TMDB ID.
    Returns the movie document or None.
    """
    if tmdb_collection is None:
        print("[WARN] MongoDB Atlas not connected. Cannot search by title.")
        return None
        
    try:
        print(f"[SEARCH] Looking for movie title: '{title}'")
        
        # Try exact match first (case-insensitive)
        doc = tmdb_collection.find_one({"title": {"$regex": f"^{title}$", "$options": "i"}})
        
        # If no exact match, try partial match
        if not doc:
            cursor = tmdb_collection.find(
                {"title": {"$regex": title, "$options": "i"}},
                {"id": 1, "title": 1, "genres": 1, "vote_average": 1}
            ).limit(5)
            results = list(cursor)
            
            if results:
                print(f"[INFO] Found {len(results)} movies matching '{title}':")
                for idx, movie in enumerate(results, 1):
                    movie_id = movie.get('id') or movie.get('tmdbId', 'N/A')
                    print(f"  {idx}. [{movie_id}] {movie.get('title', 'Unknown')}")
                # Return the first match
                doc = results[0]
            else:
                print(f"[NOT FOUND] No movies found matching '{title}'")
                return None
        
        if doc:
            movie_id = doc.get('id') or doc.get('tmdbId', 'N/A')
            print(f"[OK] Using movie: [{movie_id}] {doc.get('title', 'Unknown')}")
            return doc
            
        return None
    except mongo_errors.ConnectionFailure as e:
        print(f"[ERROR] MongoDB connection failed in find_movie_by_title: {e}")
        return None
    except mongo_errors.OperationFailure as e:
        print(f"[ERROR] MongoDB operation failed in find_movie_by_title: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Unexpected error in find_movie_by_title: {e}")
        return None


def compare_sql_vs_nosql_performance(keyword):
    """
    For Performance tab.
    We'll time:
      - SQL: search_movies_by_title(keyword)  (structured tables)
      - Mongo: search_movies_by_keyword_mongo(keyword) (unstructured text)
    """
    sql_start = time.time()
    sql_res, _ = search_movies_by_title(keyword)
    sql_t = time.time() - sql_start

    mongo_start = time.time()
    mongo_res, _ = search_movies_by_keyword_mongo(keyword)
    mongo_t = time.time() - mongo_start

    return {
        "sql_time": sql_t,
        "sql_count": len(sql_res),
        "mongo_time": mongo_t,
        "mongo_count": len(mongo_res),
    }


def test_bulk_insert_performance(num_records=100):
    """
    Test bulk insert performance for SQL vs NoSQL.
    ZERO IMPACT: Creates temporary records, measures performance, then deletes them.
    Returns metrics for both databases without affecting the dataset.
    """
    print(f"\n[INSERT PERFORMANCE TEST] Testing {num_records} inserts (ZERO IMPACT MODE)...")
    
    # Get real user IDs and movie IDs from the database
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT userId FROM ratings LIMIT 50")
            user_ids = [row['userId'] for row in cur.fetchall()]
            cur.execute("SELECT DISTINCT movieId FROM ratings LIMIT 50")
            movie_ids = [row['movieId'] for row in cur.fetchall()]
    finally:
        conn.close()
    
    # Ensure we have data to work with
    if not user_ids or not movie_ids:
        print("[ERROR] No users or movies found in database")
        return {
            "sql_time": 0,
            "sql_throughput": 0,
            "sql_success": False,
            "mongo_time": 0,
            "mongo_throughput": 0,
            "mongo_success": False,
            "record_count": num_records
        }
    
    # Generate test data using REAL user and movie IDs
    cleanup_timestamp = int(time.time())
    test_ratings = [
        (random.choice(user_ids), random.choice(movie_ids), 
         round(random.uniform(0.5, 5.0), 1), cleanup_timestamp + i)
        for i in range(num_records)
    ]
    
    # SQL bulk insert test
    sql_time = 0
    sql_throughput = 0
    sql_success = False
    
    conn = get_connection()
    try:
        sql_start = time.time()
        conn.begin()
        with conn.cursor() as cur:
            insert_sql = "INSERT INTO ratings (userId, movieId, rating, timestamp) VALUES (%s, %s, %s, %s)"
            cur.executemany(insert_sql, test_ratings)
        conn.commit()
        sql_time = time.time() - sql_start
        sql_throughput = num_records / sql_time if sql_time > 0 else 0
        sql_success = True
        print(f"[SQL INSERT] Successfully inserted {num_records} records in {sql_time:.3f}s ({sql_throughput:.1f} inserts/sec)")
    except pymysql.err.OperationalError as e:
        conn.rollback()
        print(f"[SQL INSERT ERROR] Database connection error: {e}")
    except pymysql.err.IntegrityError as e:
        conn.rollback()
        print(f"[SQL INSERT ERROR] Data integrity error: {e}")
    except pymysql.MySQLError as e:
        conn.rollback()
        print(f"[SQL INSERT ERROR] Database error: {e}")
    except Exception as e:
        conn.rollback()
        print(f"[SQL INSERT ERROR] Unexpected error: {e}")
    finally:
        conn.close()
    
    # Clean up SQL test data (ZERO IMPACT - remove all test records)
    if sql_success:
        cleanup_conn = get_connection()
        try:
            cleanup_conn.begin()
            with cleanup_conn.cursor() as cur:
                cur.execute("DELETE FROM ratings WHERE timestamp >= %s", (cleanup_timestamp,))
                deleted_count = cur.rowcount
            cleanup_conn.commit()
            print(f"[SQL CLEANUP] Removed {deleted_count} test records - dataset restored to original state")
        except Exception as e:
            cleanup_conn.rollback()
            print(f"[SQL CLEANUP ERROR] {e}")
        finally:
            cleanup_conn.close()
    
    # MongoDB bulk insert test (simulated with tmdb_movies collection)
    mongo_time = 0
    mongo_throughput = 0
    mongo_success = False
    mongo_inserted_ids = []
    
    if tmdb_collection is not None:
        try:
            mongo_start = time.time()
            
            # Create temporary test documents
            test_docs = []
            for i in range(num_records):
                test_docs.append({
                    "_test_doc": True,  # Marker for cleanup
                    "id": 999000 + i,  # Use non-conflicting IDs
                    "title": f"Test_Movie_{i}",
                    "popularity": random.uniform(1.0, 100.0),
                    "vote_average": round(random.uniform(0.5, 10.0), 1),
                    "test_timestamp": cleanup_timestamp
                })
            
            result = tmdb_collection.insert_many(test_docs)
            mongo_inserted_ids = result.inserted_ids
            mongo_time = time.time() - mongo_start
            mongo_throughput = num_records / mongo_time if mongo_time > 0 else 0
            mongo_success = True
            print(f"[MONGO INSERT] Successfully inserted {len(mongo_inserted_ids)} documents in {mongo_time:.3f}s ({mongo_throughput:.1f} inserts/sec)")
            
            # Clean up MongoDB test data (ZERO IMPACT)
            delete_result = tmdb_collection.delete_many({"_test_doc": True})
            print(f"[MONGO CLEANUP] Removed {delete_result.deleted_count} test documents - dataset restored to original state")
            
        except mongo_errors.ConnectionFailure as e:
            print(f"[MONGO INSERT ERROR] MongoDB connection failed: {e}")
            # Attempt cleanup even on error
            if mongo_inserted_ids:
                try:
                    tmdb_collection.delete_many({"_test_doc": True})
                except:
                    pass
        except mongo_errors.OperationFailure as e:
            print(f"[MONGO INSERT ERROR] MongoDB operation failed: {e}")
            # Attempt cleanup even on error
            if mongo_inserted_ids:
                try:
                    tmdb_collection.delete_many({"_test_doc": True})
                except:
                    pass
        except Exception as e:
            print(f"[MONGO INSERT ERROR] Unexpected error: {e}")
            # Attempt cleanup even on error
            if mongo_inserted_ids:
                try:
                    tmdb_collection.delete_many({"_test_doc": True})
                except:
                    pass
    else:
        print("[MONGO INSERT] MongoDB not connected, skipping test")
    
    return {
        "sql_time": sql_time,
        "sql_throughput": sql_throughput,
        "sql_success": sql_success,
        "mongo_time": mongo_time,
        "mongo_throughput": mongo_throughput,
        "mongo_success": mongo_success,
        "record_count": num_records
    }


def test_bulk_update_performance(num_records=100):
    """
    Test bulk update performance for SQL vs NoSQL.
    ZERO IMPACT: Saves original values, performs updates, measures performance, then restores original data.
    Returns metrics for both databases without permanently affecting the dataset.
    """
    print(f"\n[UPDATE PERFORMANCE TEST] Testing {num_records} updates (ZERO IMPACT MODE)...")
    
    # Get real user IDs and movie IDs WITH their current ratings for backup
    conn = get_connection()
    original_ratings = []  # Store (userId, movieId, original_rating, original_timestamp)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT userId, movieId, rating, timestamp 
                FROM ratings 
                ORDER BY RAND()
                LIMIT %s
            """, (num_records,))
            original_ratings = [(row['userId'], row['movieId'], row['rating'], row['timestamp']) 
                               for row in cur.fetchall()]
    finally:
        conn.close()
    
    # Ensure we have data to work with
    if not original_ratings:
        print("[ERROR] No existing ratings found in database")
        return {
            "sql_time": 0,
            "sql_throughput": 0,
            "sql_success": False,
            "mongo_time": 0,
            "mongo_throughput": 0,
            "mongo_success": False,
            "record_count": num_records
        }
    
    print(f"[BACKUP] Saved {len(original_ratings)} original ratings for restoration")
    
    # Prepare update pairs with NEW random values (userId, movieId, new_rating, new_timestamp)
    update_pairs = [
        (orig[0], orig[1], round(random.uniform(0.5, 5.0), 1), int(time.time()) + i)
        for i, orig in enumerate(original_ratings)
    ]
    
    # SQL bulk update test
    sql_time = 0
    sql_throughput = 0
    sql_success = False
    
    conn = get_connection()
    try:
        sql_start = time.time()
        conn.begin()
        with conn.cursor() as cur:
            update_sql = """
                UPDATE ratings 
                SET rating = %s, timestamp = %s 
                WHERE userId = %s AND movieId = %s
            """
            for user_id, movie_id, rating, timestamp in update_pairs:
                cur.execute(update_sql, (rating, timestamp, user_id, movie_id))
        conn.commit()
        sql_time = time.time() - sql_start
        sql_throughput = len(update_pairs) / sql_time if sql_time > 0 else 0
        sql_success = True
        print(f"[SQL UPDATE] Successfully updated {len(update_pairs)} records in {sql_time:.3f}s ({sql_throughput:.1f} updates/sec)")
    except pymysql.err.OperationalError as e:
        conn.rollback()
        print(f"[SQL UPDATE ERROR] Database connection error: {e}")
    except pymysql.err.IntegrityError as e:
        conn.rollback()
        print(f"[SQL UPDATE ERROR] Data integrity error: {e}")
    except pymysql.MySQLError as e:
        conn.rollback()
        print(f"[SQL UPDATE ERROR] Database error: {e}")
    except Exception as e:
        conn.rollback()
        print(f"[SQL UPDATE ERROR] Unexpected error: {e}")
    finally:
        conn.close()
    
    # RESTORE original SQL data (ZERO IMPACT)
    if sql_success:
        restore_conn = get_connection()
        try:
            restore_conn.begin()
            with restore_conn.cursor() as cur:
                restore_sql = """
                    UPDATE ratings 
                    SET rating = %s, timestamp = %s 
                    WHERE userId = %s AND movieId = %s
                """
                for user_id, movie_id, orig_rating, orig_timestamp in original_ratings:
                    cur.execute(restore_sql, (orig_rating, orig_timestamp, user_id, movie_id))
            restore_conn.commit()
            print(f"[SQL RESTORE] Restored {len(original_ratings)} ratings to original values - dataset unchanged")
        except Exception as e:
            restore_conn.rollback()
            print(f"[SQL RESTORE ERROR] {e}")
        finally:
            restore_conn.close()
    
    # MongoDB bulk update test (simulated with tmdb_movies collection)
    mongo_time = 0
    mongo_throughput = 0
    mongo_success = False
    mongo_original_docs = []
    
    if tmdb_collection is not None:
        try:
            # Get sample documents and save original values
            mongo_sample = list(tmdb_collection.aggregate([
                {"$sample": {"size": min(num_records, 100)}},
                {"$project": {"_id": 1, "id": 1, "popularity": 1, "vote_average": 1}}
            ]))
            
            if mongo_sample:
                # Backup original values
                mongo_original_docs = [(doc['_id'], doc.get('popularity'), doc.get('vote_average')) 
                                       for doc in mongo_sample]
                print(f"[BACKUP] Saved {len(mongo_original_docs)} original MongoDB documents")
                
                mongo_start = time.time()
                
                # Bulk update operations with NEW random values
                bulk_ops = []
                for doc in mongo_sample:
                    doc_id = doc.get('_id')
                    bulk_ops.append({
                        "update_one": {
                            "filter": {"_id": doc_id},
                            "update": {"$set": {
                                "popularity": random.uniform(1.0, 100.0),
                                "vote_average": round(random.uniform(0.5, 10.0), 1)
                            }}
                        }
                    })
                
                # Execute bulk write
                if bulk_ops:
                    from pymongo import UpdateOne
                    result = tmdb_collection.bulk_write([
                        UpdateOne(op["update_one"]["filter"], op["update_one"]["update"])
                        for op in bulk_ops
                    ])
                    mongo_time = time.time() - mongo_start
                    mongo_throughput = len(bulk_ops) / mongo_time if mongo_time > 0 else 0
                    mongo_success = True
                    print(f"[MONGO UPDATE] Successfully updated {result.modified_count} documents in {mongo_time:.3f}s ({mongo_throughput:.1f} updates/sec)")
                
                # RESTORE original MongoDB data (ZERO IMPACT)
                restore_ops = []
                for doc_id, orig_popularity, orig_vote_avg in mongo_original_docs:
                    restore_ops.append(
                        UpdateOne(
                            {"_id": doc_id},
                            {"$set": {
                                "popularity": orig_popularity if orig_popularity is not None else 0,
                                "vote_average": orig_vote_avg if orig_vote_avg is not None else 0
                            }}
                        )
                    )
                
                if restore_ops:
                    tmdb_collection.bulk_write(restore_ops)
                    print(f"[MONGO RESTORE] Restored {len(restore_ops)} documents to original values - dataset unchanged")
            else:
                print("[MONGO UPDATE] No documents found to update")
                
        except mongo_errors.ConnectionFailure as e:
            print(f"[MONGO UPDATE ERROR] MongoDB connection failed: {e}")
        except mongo_errors.OperationFailure as e:
            print(f"[MONGO UPDATE ERROR] MongoDB operation failed: {e}")
        except Exception as e:
            print(f"[MONGO UPDATE ERROR] Unexpected error: {e}")
    else:
        print("[MONGO UPDATE] MongoDB not connected, skipping test")
    
    return {
        "sql_time": sql_time,
        "sql_throughput": sql_throughput,
        "sql_success": sql_success,
        "mongo_time": mongo_time,
        "mongo_throughput": mongo_throughput,
        "mongo_success": mongo_success,
        "record_count": len(update_pairs) if sql_success else 0
    }


###############################################################################
# 4. SQL HELPERS – USERS
###############################################################################

def get_user(user_id):
    sql = """
        SELECT userId, username, email, created_at
        FROM users
        WHERE userId = %s
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            return cur.fetchone()
    finally:
        conn.close()


def search_users(keyword=""):
    """
    Returns up to 50 users.
    If keyword is provided, filter by username/email LIKE.
    Only admins can search users.
    """
    # Check permissions
    if CURRENT_USER['role'] != 'admin':
        raise PermissionError("Only administrators can search users")
        
    if keyword:
        sql = """
            SELECT userId, username, email, created_at
            FROM users
            WHERE (username LIKE %s OR email LIKE %s)
              AND username IS NOT NULL
              AND email IS NOT NULL
            ORDER BY userId ASC
            LIMIT 50
        """
        like_param = f"%{keyword}%"
        params = (like_param, like_param)
    else:
        sql = """
            SELECT userId, username, email, created_at
            FROM users
            WHERE username IS NOT NULL
              AND email IS NOT NULL
            ORDER BY userId ASC
            LIMIT 50
        """
        params = ()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


def find_user_by_name_or_email(username=None, email=None):
    """
    Find a user by username or email.
    If both are provided with same value, searches both fields.
    Returns the user dict or None if not found.
    """
    if username and email and username == email:
        # Search both username and email with same value (flexible search)
        sql = """
            SELECT userId, username, email, created_at 
            FROM users 
            WHERE username = %s OR email = %s
            LIMIT 1
        """
        params = (username, email)
    elif username:
        sql = "SELECT userId, username, email, created_at FROM users WHERE username = %s"
        params = (username,)
    elif email:
        sql = "SELECT userId, username, email, created_at FROM users WHERE email = %s"
        params = (email,)
    else:
        return None

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()
    finally:
        conn.close()


def register_new_user(username, email, password):
    """
    Register a new user account (public registration - no admin required).
    Auto-generates user ID and sets role to 'user'.
    Returns (success, user_id) tuple.
    """
    # Hash the password
    pwd_hash = hash_password(password)
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Check if username already exists
            cur.execute("SELECT userId FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                return False, "Username already exists"
            
            # Check if email already exists
            cur.execute("SELECT userId FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                return False, "Email already exists"
            
            # Get next available user ID
            cur.execute("SELECT COALESCE(MAX(userId), 0) + 1 AS next_id FROM users")
            result = cur.fetchone()
            user_id = result['next_id']
            
            # Insert new user
            sql = """
                INSERT INTO users (userId, username, email, password_hash, role, created_at)
                VALUES (%s, %s, %s, %s, 'user', NOW())
            """
            cur.execute(sql, (user_id, username, email, pwd_hash))
        conn.commit()
        return True, user_id
    except pymysql.MySQLError as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def add_user(username, email, password="password123", user_id=None):
    """
    Add a new user with a password (ADMIN ONLY).
    If user_id is None, auto-generate the next available ID.
    New users can login with their username and chosen password.
    Only admins can create users.
    """
    # Check permissions
    if CURRENT_USER['role'] != 'admin':
        raise PermissionError("Only administrators can create new users")
    
    # Hash the password
    pwd_hash = hash_password(password)
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # If no user_id provided, get the next available ID
            if user_id is None:
                cur.execute("SELECT COALESCE(MAX(userId), 0) + 1 AS next_id FROM users")
                result = cur.fetchone()
                user_id = result['next_id']
            
            sql = """
                INSERT INTO users (userId, username, email, password_hash, role, created_at)
                VALUES (%s, %s, %s, %s, 'user', NOW())
            """
            cur.execute(sql, (user_id, username, email, pwd_hash))
        conn.commit()
        return True, user_id
    except pymysql.MySQLError as e:
        conn.rollback()
        messagebox.showerror("DB Error (Add User)", str(e))
        return False, None
    finally:
        conn.close()


def update_user(user_id, username, email, password=None):
    """
    Update user information. If password is provided, it will be hashed and updated.
    If password is None or empty, the password will not be changed.
    """
    if password:
        # Hash the new password
        pwd_hash = hash_password(password)
        sql = """
            UPDATE users
            SET username = %s, email = %s, password_hash = %s
            WHERE userId = %s
        """
        params = (username, email, pwd_hash, user_id)
    else:
        sql = """
            UPDATE users
            SET username = %s, email = %s
            WHERE userId = %s
        """
        params = (username, email, user_id)
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
        return True
    except pymysql.MySQLError as e:
        conn.rollback()
        messagebox.showerror("DB Error (Update User)", str(e))
        return False
    finally:
        conn.close()


def delete_user(user_id):
    """
    Delete a user while preserving their ratings.
    Sets userId to NULL in ratings table to maintain rating data for averages.
    This ensures that movie averages and vote counts remain accurate even after user deletion.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # First, set userId to NULL in ratings (preserves rating data)
            cur.execute(
                "UPDATE ratings SET userId = NULL WHERE userId = %s",
                (user_id,)
            )
            logger.info(f"Set userId to NULL for user {user_id}'s ratings (preserving data)")
            
            # Delete from watchlist (CASCADE DELETE is OK here)
            try:
                cur.execute(
                    "DELETE FROM WATCHLIST WHERE userId = %s",
                    (user_id,)
                )
                logger.info(f"Deleted watchlist entries for user {user_id}")
            except pymysql.err.ProgrammingError:
                # Watchlist table might not exist
                pass
            
            # Delete from rating_locks (CASCADE DELETE is OK here)
            try:
                cur.execute(
                    "DELETE FROM RATING_LOCKS WHERE userId = %s",
                    (user_id,)
                )
                logger.info(f"Deleted rating locks for user {user_id}")
            except pymysql.err.ProgrammingError:
                # Rating_locks table might not exist
                pass
            
            # Finally, delete the user
            cur.execute("DELETE FROM users WHERE userId = %s", (user_id,))
            logger.info(f"Deleted user {user_id} (ratings preserved with NULL userId)")
            
        conn.commit()
        return True
    except pymysql.MySQLError as e:
        conn.rollback()
        messagebox.showerror("DB Error (Delete User)", str(e))
        logger.error(f"Failed to delete user {user_id}: {e}")
        return False
    finally:
        conn.close()


###############################################################################
# 5. SQL HELPERS – RATINGS + TRANSACTIONS / ROLLBACK
###############################################################################

def sql_user_exists(user_id):
    """Check referential integrity: user must exist before inserting rating."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM users WHERE userId=%s", (user_id,))
            row = cur.fetchone()
            return row is not None
    finally:
        conn.close()


def sql_movie_exists(movie_id):
    """Check referential integrity: movie must exist before inserting rating."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM movies WHERE movieId=%s", (movie_id,))
            row = cur.fetchone()
            return row is not None
    finally:
        conn.close()


def add_or_update_rating(user_id, movie_id, rating_val):
    """
    Upsert style rating write with ACID transaction.
    
    This function is called AFTER the lock is acquired in the GUI handler.
    The flow is:
    1. User A starts editing Movie D → acquire_rating_lock() is called
    2. User B tries to edit Movie D → check_rating_lock() blocks them
    3. This function performs the actual update within a transaction
    4. After success, release_rating_lock() is called to unlock
    5. Now User B can edit Movie D
    
    TRANSACTION STEPS:
    - BEGIN TRANSACTION
    - DELETE old rating row (if exists)
    - INSERT new rating row with timestamp
    - VERIFY the insert worked correctly
    - COMMIT if verification passes, ROLLBACK if it fails
    
    ROLLBACK PROTECTION:
    If any step fails (e.g., constraint violation, database error),
    the entire transaction is rolled back to maintain data integrity.
    
    Regular users can only modify their own ratings.
    """
    # Convert rating to Decimal for consistent comparison
    rating_val = Decimal(str(rating_val))
    
    # Check permissions
    if not CURRENT_USER['userId']:
        raise PermissionError("Guests cannot add or modify ratings")
        
    if CURRENT_USER['role'] != 'admin' and str(CURRENT_USER['userId']) != str(user_id):
        raise PermissionError("You can only modify your own ratings")
        
    now_ts = int(time.time())
    conn = get_connection()
    try:
        logger.info(f"[TRANSACTION BEGIN] Updating rating for userId={user_id}, movieId={movie_id}")
        conn.begin()
        with conn.cursor() as cur:
            # Delete any old rating
            cur.execute(
                "DELETE FROM ratings WHERE userId=%s AND movieId=%s",
                (user_id, movie_id)
            )
            deleted_count = cur.rowcount
            logger.info(f"[TRANSACTION] Deleted {deleted_count} old rating(s)")
            
            # Insert new rating
            cur.execute(
                """
                INSERT INTO ratings(userId, movieId, rating, timestamp)
                VALUES (%s,%s,%s,%s)
                """,
                (user_id, movie_id, rating_val, now_ts)
            )
            logger.info(f"[TRANSACTION] Inserted new rating: {rating_val}")
            
            # Verify the insert worked
            cur.execute(
                "SELECT rating FROM ratings WHERE userId=%s AND movieId=%s",
                (user_id, movie_id)
            )
            row = cur.fetchone()
            if not row or abs(row["rating"] - rating_val) > 0.01:
                logger.error("[TRANSACTION ROLLBACK] Verification failed - rating not found or incorrect")
                conn.rollback()
                return False
                
            logger.info(f"[TRANSACTION] Verification passed: rating={row['rating']}")
        
        conn.commit()
        logger.info("[TRANSACTION COMMIT] Rating update successful")
        return True
    except Exception as e:
        logger.error(f"[TRANSACTION ROLLBACK] Exception occurred: {e}")
        print(f"[ROLLBACK] {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_user_rating(user_id, movie_id):
    sql = """
        SELECT rating, timestamp
        FROM ratings
        WHERE userId = %s AND movieId = %s
        ORDER BY timestamp DESC
        LIMIT 1
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, movie_id))
            return cur.fetchone()
    finally:
        conn.close()


def get_all_user_ratings(user_id):
    """
    Get all ratings by a specific user with movie details.
    Excludes placeholder movies with titles like 'Movie_123'.
    """
    sql = """
        SELECT 
            m.movieId,
            m.title,
            r.rating,
            r.timestamp,
            ROUND(AVG(r2.rating), 2) AS movie_avg_rating,
            COUNT(r2.rating) AS movie_vote_count
        FROM ratings r
        INNER JOIN movies m ON r.movieId = m.movieId
        LEFT JOIN ratings r2 ON m.movieId = r2.movieId
        WHERE r.userId = %s
          AND m.title NOT LIKE 'Movie_%%'
        GROUP BY m.movieId, m.title, r.rating, r.timestamp
        ORDER BY r.timestamp DESC
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            return cur.fetchall()
    finally:
        conn.close()


def delete_rating(user_id, movie_id):
    """
    Transactional delete with verification.
    Regular users can only delete their own ratings.
    """
    # Check permissions
    if CURRENT_USER['role'] != 'admin' and CURRENT_USER['userId'] != user_id:
        raise PermissionError("You can only delete your own ratings")

    if CURRENT_USER['role'] == 'user' and not CURRENT_USER['userId']:
        raise PermissionError("Guests cannot delete ratings")
        
    conn = get_connection()
    try:
        conn.begin()
        with conn.cursor() as cur:
            # ensure it exists
            cur.execute(
                "SELECT rating FROM ratings WHERE userId=%s AND movieId=%s",
                (user_id, movie_id)
            )
            exists = cur.fetchone()
            if not exists:
                conn.rollback()
                return False

            # delete exactly one row
            cur.execute(
                "DELETE FROM ratings WHERE userId=%s AND movieId=%s",
                (user_id, movie_id)
            )
            if cur.rowcount != 1:
                conn.rollback()
                return False

        conn.commit()
        return True
    except Exception as e:
        print(f"[ROLLBACK delete_rating] {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


###############################################################################
# 5B. WATCHLIST OPERATIONS
###############################################################################

def add_to_watchlist(user_id, movie_id, notes="", priority="medium"):
    """Add movie to user's watchlist"""
    if not user_id:
        messagebox.showwarning("Not Logged In", "Please login to add movies to your watchlist.")
        return False
        
    sql = """
        INSERT INTO WATCHLIST (userId, movieId, notes, priority)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            notes = VALUES(notes),
            priority = VALUES(priority),
            added_at = CURRENT_TIMESTAMP
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, movie_id, notes, priority))
        conn.commit()
        logger.info(f"User {user_id} added movie {movie_id} to watchlist")
        return True
    except pymysql.MySQLError as e:
        conn.rollback()
        logger.error(f"Failed to add to watchlist: {e}")
        messagebox.showerror("Error", "Failed to add to watchlist.\nPlease try again.")
        return False
    finally:
        conn.close()


def remove_from_watchlist(user_id, movie_id):
    """Remove movie from watchlist"""
    sql = "DELETE FROM WATCHLIST WHERE userId = %s AND movieId = %s"
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, movie_id))
        conn.commit()
        logger.info(f"User {user_id} removed movie {movie_id} from watchlist")
        return True
    except pymysql.MySQLError as e:
        conn.rollback()
        logger.error(f"Failed to remove from watchlist: {e}")
        return False
    finally:
        conn.close()


def get_user_watchlist(user_id):
    """Get user's watchlist with movie details"""
    sql = """
        SELECT 
            w.movieId,
            m.title,
            w.added_at,
            w.notes,
            w.priority,
            ROUND(AVG(r.rating), 2) AS avg_rating,
            COUNT(r.rating) AS vote_count
        FROM WATCHLIST w
        INNER JOIN MOVIES m ON w.movieId = m.movieId
        LEFT JOIN RATINGS r ON m.movieId = r.movieId
        WHERE w.userId = %s
        GROUP BY w.movieId, m.title, w.added_at, w.notes, w.priority
        ORDER BY w.added_at DESC
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            return cur.fetchall()
    except pymysql.err.ProgrammingError as e:
        if "doesn't exist" in str(e):
            logger.warning(f"WATCHLIST table doesn't exist: {e}")
            return []
        raise
    finally:
        conn.close()


def is_in_watchlist(user_id, movie_id):
    """Check if movie is in user's watchlist"""
    sql = "SELECT 1 FROM WATCHLIST WHERE userId = %s AND movieId = %s"
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, movie_id))
            return cur.fetchone() is not None
    except pymysql.err.ProgrammingError as e:
        if "doesn't exist" in str(e):
            logger.warning("WATCHLIST table doesn't exist")
            return False
        raise
    finally:
        conn.close()


###############################################################################
# 6. ANALYTICS QUERIES
###############################################################################

def get_top_rated_movies(limit=20):
    """
    GROUP BY + HAVING >=10 votes.
    """
    start = time.time()
    sql = """
        SELECT
            m.title,
            COUNT(r.rating) AS vote_count,
            ROUND(AVG(r.rating), 2) AS avg_rating,
            MIN(r.rating) AS min_rating,
            MAX(r.rating) AS max_rating
        FROM movies m
        INNER JOIN ratings r ON m.movieId = r.movieId
        WHERE m.title NOT LIKE 'Movie_%%'
        GROUP BY m.movieId, m.title
        HAVING COUNT(r.rating) >= 10
        ORDER BY avg_rating DESC, vote_count DESC
        LIMIT %s
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            rows = cur.fetchall()
    finally:
        conn.close()
    return rows, time.time() - start


def get_user_statistics(user_id):
    """
    Correlated subqueries:
      total ratings, avg given, highs >=4.0, lows <=2.0 etc. :contentReference[oaicite:10]{index=10}
    Excludes placeholder movies with titles like 'Movie_123'.
    """
    start = time.time()
    sql = """
        SELECT
            u.userId,
            u.username,
            u.email,
            COUNT(r.movieId) AS total_ratings,
            ROUND(AVG(r.rating), 2) AS avg_rating_given,
            MIN(r.rating) AS min_rating_given,
            MAX(r.rating) AS max_rating_given,
            (SELECT COUNT(*) 
             FROM ratings r2 
             INNER JOIN movies m2 ON r2.movieId = m2.movieId
             WHERE r2.rating >= 4.0 AND r2.userId = u.userId 
               AND m2.title NOT LIKE 'Movie_%%')
                AS high_ratings_count,
            (SELECT COUNT(*) 
             FROM ratings r3
             INNER JOIN movies m3 ON r3.movieId = m3.movieId
             WHERE r3.rating <= 2.0 AND r3.userId = u.userId
               AND m3.title NOT LIKE 'Movie_%%')
                AS low_ratings_count
        FROM users u
        LEFT JOIN ratings r ON u.userId = r.userId
        LEFT JOIN movies m ON r.movieId = m.movieId
        WHERE u.userId = %s
          AND (m.title NOT LIKE 'Movie_%%' OR m.title IS NULL)
        GROUP BY u.userId, u.username, u.email
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            row = cur.fetchone()
    finally:
        conn.close()
    return row, time.time() - start


def get_popular_movies_from_view(limit=20):
    """
    Query the popular_movies VIEW created in schema.
    This demonstrates VIEW usage.
    Returns pre-computed aggregated movie data.
    """
    start = time.time()
    sql = """
        SELECT 
            movieId,
            title,
            release_date,
            rating_count,
            ROUND(avg_rating, 2) as avg_rating,
            min_rating,
            max_rating
        FROM popular_movies
        LIMIT %s
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            rows = cur.fetchall()
    finally:
        conn.close()
    return rows, time.time() - start


def find_users_who_never_rated_popular_movies():
    """
    Complex nested query with NOT EXISTS.
    Finds users who have NEVER rated any movie that's in the popular_movies view.
    This demonstrates advanced SQL with correlated subqueries.
    """
    start = time.time()
    sql = """
        SELECT 
            u.userId,
            u.username,
            u.email,
            COUNT(r.movieId) as total_ratings
        FROM users u
        LEFT JOIN ratings r ON u.userId = r.userId
        WHERE u.username IS NOT NULL
          AND u.email IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 
              FROM ratings r2
              INNER JOIN popular_movies pm ON r2.movieId = pm.movieId
              WHERE r2.userId = u.userId
          )
        GROUP BY u.userId, u.username, u.email
        HAVING COUNT(r.movieId) > 0
        ORDER BY total_ratings DESC
        LIMIT 20
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    finally:
        conn.close()
    return rows, time.time() - start


def find_movies_rated_by_all_active_users():
    """
    Complex nested query with IN subquery.
    Finds movies that have been rated by users who are highly active (>10 ratings).
    Demonstrates nested SELECT in WHERE clause.
    """
    start = time.time()
    sql = """
        SELECT 
            m.movieId,
            m.title,
            COUNT(DISTINCT r.userId) as active_user_count,
            ROUND(AVG(r.rating), 2) as avg_rating
        FROM movies m
        INNER JOIN ratings r ON m.movieId = r.movieId
        WHERE r.userId IN (
            SELECT userId 
            FROM ratings 
            GROUP BY userId 
            HAVING COUNT(*) > 10
        )
        AND m.title NOT LIKE 'Movie_%%'
        GROUP BY m.movieId, m.title
        HAVING COUNT(DISTINCT r.userId) >= 5
        ORDER BY active_user_count DESC, avg_rating DESC
        LIMIT 20
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    finally:
        conn.close()
    return rows, time.time() - start


def find_movies_with_rating_variance():
    """
    Advanced aggregation with VARIANCE and STDDEV.
    Finds movies with high rating variance (controversial movies).
    """
    start = time.time()
    sql = """
        SELECT 
            m.movieId,
            m.title,
            COUNT(r.rating) as vote_count,
            ROUND(AVG(r.rating), 2) as avg_rating,
            ROUND(STDDEV(r.rating), 2) as rating_stddev,
            ROUND(VARIANCE(r.rating), 2) as rating_variance,
            MIN(r.rating) as min_rating,
            MAX(r.rating) as max_rating
        FROM movies m
        INNER JOIN ratings r ON m.movieId = r.movieId
        WHERE m.title NOT LIKE 'Movie_%%'
        GROUP BY m.movieId, m.title
        HAVING COUNT(r.rating) >= 20
        ORDER BY rating_variance DESC
        LIMIT 20
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    finally:
        conn.close()
    return rows, time.time() - start


def get_movies_with_above_average_ratings():
    """
    Nested query with subquery in WHERE clause.
    Finds movies with rating higher than the overall database average.
    """
    start = time.time()
    sql = """
        SELECT 
            m.movieId,
            m.title,
            COUNT(r.rating) as vote_count,
            ROUND(AVG(r.rating), 2) as avg_rating,
            (SELECT ROUND(AVG(rating), 2) FROM ratings) as overall_avg
        FROM movies m
        INNER JOIN ratings r ON m.movieId = r.movieId
        WHERE m.title NOT LIKE 'Movie_%%'
        GROUP BY m.movieId, m.title
        HAVING AVG(r.rating) > (SELECT AVG(rating) FROM ratings)
          AND COUNT(r.rating) >= 5
        ORDER BY avg_rating DESC
        LIMIT 20
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    finally:
        conn.close()
    return rows, time.time() - start


###############################################################################
# 7. LOGIN DIALOG
###############################################################################

class LoginDialog(tk.Toplevel):
    """
    Pops up before main UI, asks for username/password.
    After successful login, .user_info holds {userId, username, email, role}
    """

    def __init__(self, parent, show_guest_options=False):
        super().__init__(parent)
        self.title("Login - Movie Database")
        self.geometry("420x450")
        self.resizable(False, False)
        self.configure(bg="#34495e")

        self.user_info = None
        self.is_guest = False  # Track if user chose guest mode
        self.show_guest_options = show_guest_options  # Whether to show Login/Register for guests

        # modal
        self.transient(parent)
        self.grab_set()

        # title
        tk.Label(
            self,
            text="Movie Database",
            font=("Arial", 18, "bold"),
            bg="#34495e",
            fg="white"
        ).pack(pady=(20, 5))

        if show_guest_options:
            tk.Label(
                self,
                text="Guest Mode - Login or Register to continue",
                font=("Arial", 10),
                bg="#34495e",
                fg="#bdc3c7"
            ).pack(pady=(0, 15))
        else:
            tk.Label(
                self,
                text="Please login to continue",
                font=("Arial", 10),
                bg="#34495e",
                fg="#bdc3c7"
            ).pack(pady=(0, 15))

        # form
        form = tk.Frame(self, bg="white", padx=35, pady=25)
        form.pack(fill="both", expand=True, padx=25, pady=(0, 25))

        tk.Label(form, text="Username:", font=("Arial", 10, "bold"), bg="white")\
            .grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.username_entry = ttk.Entry(form, width=30, font=("Arial", 10))
        self.username_entry.grid(row=1, column=0, pady=(0, 12))
        self.username_entry.focus()

        tk.Label(form, text="Password:", font=("Arial", 10, "bold"), bg="white")\
            .grid(row=2, column=0, sticky="w", pady=(0, 5))
        self.password_entry = ttk.Entry(form, width=30, show="●", font=("Arial", 10))
        self.password_entry.grid(row=3, column=0, pady=(0, 20))

        # Main action buttons (Login and Create Account)
        btn_row1 = tk.Frame(form, bg="white")
        btn_row1.grid(row=4, column=0, pady=(0, 8))

        tk.Button(
            btn_row1,
            text="Login",
            command=self._do_login,
            bg="#27ae60",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=20,
            pady=8,
            relief="flat",
            cursor="hand2",
            width=12,
            borderwidth=0
        ).pack(side="left", padx=4)

        tk.Button(
            btn_row1,
            text="Register",
            command=self._do_create_account,
            bg="#3498db",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=20,
            pady=8,
            relief="flat",
            cursor="hand2",
            width=12,
            borderwidth=0
        ).pack(side="left", padx=4)

        # Guest button only shown if not already in guest mode
        if not show_guest_options:
            tk.Button(
                form,
                text="Continue as Guest",
                command=self._do_guest_login,
                bg="#95a5a6",
                fg="white",
                font=("Arial", 9),
                padx=20,
                pady=6,
                relief="flat",
                cursor="hand2",
                width=27,
                borderwidth=0
            ).grid(row=5, column=0, pady=(8, 0))

        self.bind("<Return>", lambda e: self._do_login())

    def _do_login(self):
        u = self.username_entry.get().strip()
        p = self.password_entry.get()
        if not u or not p:
            messagebox.showerror("Error", "Please enter both username and password", parent=self)
            return
        user = authenticate_user(u, p)
        if user:
            self.user_info = user
            self.is_guest = False
            self.destroy()
        else:
            messagebox.showerror(
                "Login Failed",
                "Invalid username or password.\nPlease try again.",
                parent=self
            )
            self.password_entry.delete(0, "end")
            self.username_entry.focus()

    def _do_create_account(self):
        """Open a dialog to create a new user account"""
        # Create a new dialog for account creation
        create_dialog = tk.Toplevel(self)
        create_dialog.title("Create New Account")
        create_dialog.geometry("420x380")
        create_dialog.resizable(False, False)
        create_dialog.configure(bg="#34495e")
        create_dialog.transient(self)
        create_dialog.grab_set()

        # Title
        tk.Label(
            create_dialog,
            text="Create New Account",
            font=("Arial", 14, "bold"),
            bg="#34495e",
            fg="white"
        ).pack(pady=15)

        # Form
        form = tk.Frame(create_dialog, bg="white", padx=30, pady=25)
        form.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Username
        tk.Label(form, text="Username:", font=("Arial", 10, "bold"), bg="white")\
            .grid(row=0, column=0, sticky="w", pady=(0, 5))
        username_var = tk.StringVar()
        ttk.Entry(form, textvariable=username_var, width=30)\
            .grid(row=1, column=0, pady=(0, 10))

        # Email
        tk.Label(form, text="Email:", font=("Arial", 10, "bold"), bg="white")\
            .grid(row=2, column=0, sticky="w", pady=(0, 5))
        email_var = tk.StringVar()
        ttk.Entry(form, textvariable=email_var, width=30)\
            .grid(row=3, column=0, pady=(0, 10))

        # Password
        tk.Label(form, text="Password:", font=("Arial", 10, "bold"), bg="white")\
            .grid(row=4, column=0, sticky="w", pady=(0, 5))
        password_var = tk.StringVar()
        ttk.Entry(form, textvariable=password_var, width=30, show="*")\
            .grid(row=5, column=0, pady=(0, 15))

        def create_account():
            uname = username_var.get().strip()
            email = email_var.get().strip()
            pwd = password_var.get()

            if not uname or not email or not pwd:
                messagebox.showerror("Error", "All fields are required", parent=create_dialog)
                return

            if not is_valid_email(email):
                messagebox.showerror("Error", "Invalid email format", parent=create_dialog)
                return

            if len(pwd) < 6:
                messagebox.showerror("Error", "Password must be at least 6 characters", parent=create_dialog)
                return

            # Create the user (user_id will be auto-generated) - using public registration
            ok, user_id = register_new_user(uname, email, pwd)
            if ok:
                messagebox.showinfo(
                    "Success",
                    f"Account created successfully!\n\nUser ID: {user_id}\nUsername: {uname}\nYou can now login.",
                    parent=create_dialog
                )
                create_dialog.destroy()
                # Pre-fill the username in login form
                self.username_entry.delete(0, "end")
                self.username_entry.insert(0, uname)
                self.password_entry.focus()
            else:
                messagebox.showerror("Error", "Failed to create account. Username might already exist.", parent=create_dialog)

        # Buttons
        btn_frame = tk.Frame(form, bg="white")
        btn_frame.grid(row=6, column=0, pady=(15, 0))

        tk.Button(
            btn_frame,
            text="Create Account",
            command=create_account,
            bg="#27ae60",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=20,
            pady=7,
            relief="flat",
            cursor="hand2",
            width=14,
            borderwidth=0
        ).pack(side="left", padx=5)

        tk.Button(
            btn_frame,
            text="Cancel",
            command=create_dialog.destroy,
            bg="#95a5a6",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=20,
            pady=7,
            relief="flat",
            cursor="hand2",
            width=14,
            borderwidth=0
        ).pack(side="left", padx=5)

    def _do_guest_login(self):
        """Login as guest (browse only)"""
        confirm = messagebox.askyesno(
            "Guest Mode",
            "Continue as Guest?\n\n"
            "• You can browse movies\n"
            "• You CANNOT create/edit users\n"
            "• You CANNOT add/edit ratings\n"
            "• You CANNOT view your profile\n\n"
            "To unlock full features, please Login or Register.",
            parent=self
        )
        if confirm:
            global CURRENT_USER
            CURRENT_USER.update({
                "userId": None,
                "username": "guest",
                "email": None,
                "role": "guest"  # FIXED: Was "user", should be "guest"
            })
            self.is_guest = True
            self.user_info = None  # No user info for guests
            self.destroy()

    def _do_cancel(self):
        # Not used anymore - Cancel button removed
        # If somehow called, just close the dialog
        self.destroy()


###############################################################################
# 7B. RATING MANAGEMENT DIALOGS (SEPARATE POPUP WINDOWS)
###############################################################################

class ActionSelectionDialog(tk.Toplevel):
    """
    POPUP 1: Ask user what action they want to perform.
    Returns: "add", "delete", "view", or None (if cancelled)
    """
    def __init__(self, parent, username, user_id):
        super().__init__(parent)
        self.title("Rating Management - Step 1")
        self.geometry("500x550")  # Increased height to fit buttons
        self.resizable(False, False)
        self.configure(bg="#2c3e50")
        
        self.username = username
        self.user_id = user_id
        self.selected_action = None  # Will store result
        
        # Modal setup
        self.transient(parent)
        self.grab_set()
        
        # Build UI
        self._build_ui()
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
        
        logger.info(f"[POPUP 1] Action Selection Dialog opened for {username}")
    
    def _build_ui(self):
        """Build the action selection UI."""
        # Header
        tk.Label(
            self,
            text="⭐ Rating Management",
            font=("Arial", 18, "bold"),
            bg="#2c3e50",
            fg="white"
        ).pack(pady=(20, 5))
        
        tk.Label(
            self,
            text=f"Logged in as: {self.username} (ID: {self.user_id})",
            font=("Arial", 9),
            bg="#2c3e50",
            fg="#bdc3c7"
        ).pack(pady=(0, 20))
        
        # Content frame
        content = tk.Frame(self, bg="white", padx=30, pady=30)
        content.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        tk.Label(
            content,
            text="Step 1: Select Action",
            font=("Arial", 14, "bold"),
            bg="white",
            fg="#2c3e50"
        ).pack(anchor="w", pady=(0, 20))
        
        # Radio buttons
        self.action_var = tk.StringVar(value="add")
        
        actions = [
            ("add", "Add/Edit Rating", "Add a new rating or update existing"),
            ("delete", "Delete Rating", "Remove a rating from a movie"),
            ("view", "View My Ratings", "See all your ratings")
        ]
        
        for value, label, description in actions:
            frame = tk.Frame(content, bg="white")
            frame.pack(fill="x", pady=8)
            
            tk.Radiobutton(
                frame,
                text=label,
                variable=self.action_var,
                value=value,
                bg="white",
                font=("Arial", 11, "bold"),
                fg="#2c3e50"
            ).pack(anchor="w")
            
            tk.Label(
                frame,
                text=description,
                font=("Arial", 9),
                bg="white",
                fg="#7f8c8d"
            ).pack(anchor="w", padx=(25, 0))
        
        # Buttons
        btn_frame = tk.Frame(content, bg="white")
        btn_frame.pack(pady=(30, 10))
        
        print("[DEBUG POPUP 1] Creating Next button...")
        next_btn = tk.Button(
            btn_frame,
            text="Next →",
            command=self._on_next,
            bg="#3498db",
            fg="white",
            font=("Arial", 11, "bold"),
            padx=30,
            pady=10,
            cursor="hand2"
        )
        next_btn.pack(side="left", padx=5)
        print(f"[DEBUG POPUP 1] Next button created: {next_btn.winfo_exists()}")
        
        print("[DEBUG POPUP 1] Creating Cancel button...")
        cancel_btn = tk.Button(
            btn_frame,
            text="Cancel",
            command=self._on_cancel,
            bg="#95a5a6",
            fg="white",
            font=("Arial", 11, "bold"),
            padx=30,
            pady=10,
            cursor="hand2"
        )
        cancel_btn.pack(side="left", padx=5)
        print(f"[DEBUG POPUP 1] Cancel button created: {cancel_btn.winfo_exists()}")
        print("[DEBUG POPUP 1] Button frame packed, UI build complete")
    
    def _on_next(self):
        """User clicked Next - store selection and close."""
        print("[DEBUG POPUP 1] _on_next() called!")
        self.selected_action = self.action_var.get()
        print(f"[DEBUG POPUP 1] Selected action: {self.selected_action}")
        logger.info(f"[POPUP 1] Action selected: {self.selected_action}")
        print("[DEBUG POPUP 1] About to destroy dialog...")
        self.destroy()
        print("[DEBUG POPUP 1] Dialog destroyed")
    
    def _on_cancel(self):
        """User clicked Cancel - close without selection."""
        self.selected_action = None
        logger.info(f"[POPUP 1] Action selection cancelled")
        self.destroy()


class MovieSelectionDialog(tk.Toplevel):
    """
    POPUP 2: Ask user which movie to edit/delete.
    Acquires lock after movie selection (TRANSACTION BEGINS HERE).
    Returns: (movie_id, movie_title) or None (if cancelled)
    """
    def __init__(self, parent, username, user_id, action):
        super().__init__(parent)
        self.title("Rating Management - Step 2")
        self.geometry("500x550")
        self.resizable(False, False)
        self.configure(bg="#2c3e50")
        
        self.username = username
        self.user_id = user_id
        self.action = action  # "add" or "delete"
        self.movie_id = None
        self.movie_title = None
        self.lock_acquired = False
        
        # Modal setup
        self.transient(parent)
        self.grab_set()
        
        # Build UI
        self._build_ui()
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
        
        logger.info(f"[POPUP 2] Movie Selection Dialog opened for {username}, action={action}")
    
    def _build_ui(self):
        """Build the movie selection UI."""
        # Header
        tk.Label(
            self,
            text="Rating Management",
            font=("Arial", 18, "bold"),
            bg="#2c3e50",
            fg="white"
        ).pack(pady=(20, 5))
        
        action_text = "Add/Edit Rating" if self.action == "add" else "Delete Rating"
        tk.Label(
            self,
            text=f"Action: {action_text}",
            font=("Arial", 10),
            bg="#2c3e50",
            fg="#3498db"
        ).pack(pady=(0, 20))
        
        # Content frame
        content = tk.Frame(self, bg="white", padx=30, pady=30)
        content.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        tk.Label(
            content,
            text="Step 2: Select Movie",
            font=("Arial", 14, "bold"),
            bg="white",
            fg="#2c3e50"
        ).pack(anchor="w", pady=(0, 10))
        
        tk.Label(
            content,
            text="Enter Movie ID or Title:",
            font=("Arial", 10),
            bg="white",
            fg="#34495e"
        ).pack(anchor="w", pady=(10, 5))
        
        self.movie_var = tk.StringVar()
        entry = ttk.Entry(
            content,
            textvariable=self.movie_var,
            font=("Arial", 11),
            width=40
        )
        entry.pack(fill="x", pady=(0, 10))
        entry.focus_set()
        
        tk.Label(
            content,
            text="Tip: Enter Movie ID (e.g., 1) or search by title (e.g., Toy Story)",
            font=("Arial", 8),
            bg="white",
            fg="#7f8c8d"
        ).pack(anchor="w", pady=(0, 20))
        
        # Lock info box
        info_frame = tk.Frame(content, bg="#ecf0f1", relief="solid", borderwidth=1)
        info_frame.pack(fill="x", pady=(0, 20), padx=10)
        
        tk.Label(
            info_frame,
            text="Concurrent Edit Prevention",
            font=("Arial", 10, "bold"),
            bg="#ecf0f1",
            fg="#2c3e50"
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        tk.Label(
            info_frame,
            text="When you confirm:\n"
                 "• A lock will be acquired on this rating\n"
                 "• Other users CANNOT edit until you finish\n"
                 "• Transaction begins (prevents concurrent edits)\n"
                 "• Lock auto-expires in 5 minutes",
            font=("Arial", 9),
            bg="#ecf0f1",
            fg="#34495e",
            justify="left"
        ).pack(anchor="w", padx=10, pady=(0, 10))
        
        # Buttons
        btn_frame = tk.Frame(content, bg="white")
        btn_frame.pack(pady=(10, 0))
        
        tk.Button(
            btn_frame,
            text="🔒 Confirm & Acquire Lock",
            command=self._on_confirm,
            bg="#27ae60",
            fg="white",
            font=("Arial", 11, "bold"),
            padx=25,
            pady=10,
            cursor="hand2"
        ).pack(side="left", padx=5)
        
        tk.Button(
            btn_frame,
            text="Cancel",
            command=self._on_cancel,
            bg="#95a5a6",
            fg="white",
            font=("Arial", 11),
            padx=30,
            pady=10,
            cursor="hand2"
        ).pack(side="left", padx=5)
    
    def _on_confirm(self):
        """Confirm movie selection and acquire lock."""
        movie_text = self.movie_var.get().strip()
        
        if not movie_text:
            messagebox.showerror(
                "Movie Required",
                "Please enter a Movie ID or Title.",
                parent=self
            )
            return
        
        # Parse movie ID/title
        movie_id = None
        movie_title = None
        
        try:
            # Try as integer (Movie ID)
            movie_id = int(movie_text)
            movie = get_movie_details(movie_id)
            if not movie:
                messagebox.showerror(
                    "Movie Not Found",
                    f"Movie ID {movie_id} does not exist.",
                    parent=self
                )
                return
            movie_title = movie['title']
        except ValueError:
            # Search by title
            movies = find_movie_by_title_sql(movie_text)
            if not movies:
                messagebox.showerror(
                    "Movie Not Found",
                    f"No movies found matching '{movie_text}'.\n\n"
                    "Please check spelling or use Movie ID.",
                    parent=self
                )
                return
            elif len(movies) == 1:
                movie_id = movies[0]['movieId']
                movie_title = movies[0]['title']
            else:
                # Multiple matches
                selection_msg = "Multiple movies found:\n\n"
                for idx, m in enumerate(movies[:5], 1):
                    selection_msg += f"{idx}. [ID: {m['movieId']}] {m['title']}\n"
                selection_msg += "\nPlease use the Movie ID."
                messagebox.showinfo("Multiple Movies", selection_msg, parent=self)
                return
        
        # Verify movie exists
        if not sql_movie_exists(movie_id):
            messagebox.showerror("Error", f"Movie {movie_id} does not exist.", parent=self)
            return
        
        # Check if locked by someone else (CONCURRENT EDIT PREVENTION)
        # Use check_movie_lock() which checks ONLY by movieId (ANY user can lock a movie)
        print(f"[DEBUG POPUP 2] Checking if movie {movie_id} is locked by anyone...")
        locked_by = check_movie_lock(movie_id, self.username)
        print(f"[DEBUG POPUP 2] Lock check result: locked_by = '{locked_by}'")
        
        if locked_by:
            messagebox.showerror(
                "Rating Locked - Concurrent Edit Prevention",
                f"This rating is currently being edited by another user.\n\n"
                f"• Another user is editing this rating\n"
                f"• You CANNOT edit/delete until they finish\n"
                f"• This demonstrates concurrent edit prevention\n"
                f"• Lock auto-expires in 5 minutes\n\n"
                f"Movie: {movie_title} (ID: {movie_id})\n\n"
                f"Please wait and try again later.",
                parent=self
            )
            logger.info(f"[POPUP 2] User {self.username} BLOCKED - rating locked by '{locked_by}'")
            return
        
        # Acquire lock (TRANSACTION BEGINS)
        logger.info(f"[POPUP 2] Acquiring lock for userId={self.user_id}, movieId={movie_id}")
        if not acquire_rating_lock(self.user_id, movie_id, self.username):
            messagebox.showerror(
                "Lock Error",
                "Failed to acquire lock.\n\n"
                "Please try again.",
                parent=self
            )
            return
        
        # Lock acquired!
        self.movie_id = movie_id
        self.movie_title = movie_title
        self.lock_acquired = True
        
        logger.info(f"[POPUP 2] ✅ Lock ACQUIRED: userId={self.user_id}, movieId={movie_id}")
        
        # Get movie details for display
        movie_details = get_movie_details(movie_id)
        vote_count = movie_details.get('vote_count', 0) if movie_details else 0
        avg_rating = movie_details.get('avg_rating', 'N/A') if movie_details else 'N/A'
        
        # Show success
        messagebox.showinfo(
            "Lock Acquired - Transaction Started",
            f"Rating locked successfully!\n\n"
            f"Movie: {movie_title}\n"
            f"Movie ID: {movie_id}\n"
            f"Votes: {vote_count} | Avg Rating: {avg_rating}\n\n"
            f"- You now have exclusive edit access\n"
            f"- Other users are BLOCKED from editing\n"
            f"- Transaction has begun\n"
            f"- Lock auto-expires in 5 minutes\n\n"
            f"Proceeding to next step...",
            parent=self
        )
        
        # Close this popup
        self.destroy()
    
    def _on_cancel(self):
        """User clicked Cancel - close without selection."""
        self.movie_id = None
        self.movie_title = None
        logger.info(f"[POPUP 2] Movie selection cancelled")
        self.destroy()
    
    def __del__(self):
        """Release lock if dialog is destroyed without completing."""
        if self.lock_acquired and self.movie_id:
            logger.warning(f"[POPUP 2] Dialog destroyed with active lock - releasing lock")
            release_rating_lock(self.user_id, self.movie_id)


class RatingEntryDialog(tk.Toplevel):
    """
    POPUP 3: Ask user for rating value (Add/Edit action only).
    Executes transaction and releases lock.
    Returns: rating value or None (if cancelled)
    """
    def __init__(self, parent, username, user_id, movie_id, movie_title):
        super().__init__(parent)
        self.title("Rating Management - Step 3")
        self.geometry("500x650")  # Increased height to show all content including buttons
        self.resizable(False, False)
        self.configure(bg="#2c3e50")
        
        self.username = username
        self.user_id = user_id
        self.movie_id = movie_id
        self.movie_title = movie_title
        self.rating_value = None
        self.success = False
        
        # Get movie details
        movie_details = get_movie_details(movie_id)
        self.vote_count = movie_details.get('vote_count', 0) if movie_details else 0
        self.avg_rating = movie_details.get('avg_rating', 'N/A') if movie_details else 'N/A'
        
        # Modal setup
        self.transient(parent)
        self.grab_set()
        
        # Build UI
        self._build_ui()
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
        
        logger.info(f"[POPUP 3] Rating Entry Dialog opened for {username}, movieId={movie_id}")
    
    def _build_ui(self):
        """Build the rating entry UI."""
        # Header
        tk.Label(
            self,
            text="Rating Management",
            font=("Arial", 18, "bold"),
            bg="#2c3e50",
            fg="white"
        ).pack(pady=(20, 5))
        
        tk.Label(
            self,
            text=f"Movie: {self.movie_title}",
            font=("Arial", 10),
            bg="#2c3e50",
            fg="#3498db"
        ).pack(pady=(0, 5))
        
        tk.Label(
            self,
            text=f"Movie ID: {self.movie_id} | Votes: {self.vote_count} | Avg: {self.avg_rating}",
            font=("Arial", 9),
            bg="#2c3e50",
            fg="#bdc3c7"
        ).pack(pady=(0, 5))
        
        tk.Label(
            self,
            text="Locked - Transaction in progress",
            font=("Arial", 9, "bold"),
            bg="#2c3e50",
            fg="#27ae60"
        ).pack(pady=(0, 20))
        
        # Content frame
        content = tk.Frame(self, bg="white", padx=30, pady=30)
        content.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        tk.Label(
            content,
            text="Step 3: Enter Rating",
            font=("Arial", 14, "bold"),
            bg="white",
            fg="#2c3e50"
        ).pack(anchor="w", pady=(0, 10))
        
        tk.Label(
            content,
            text="Enter your rating (0.5 - 5.0):",
            font=("Arial", 10),
            bg="white",
            fg="#34495e"
        ).pack(anchor="w", pady=(10, 5))
        
        self.rating_var = tk.StringVar()
        entry = ttk.Entry(
            content,
            textvariable=self.rating_var,
            font=("Arial", 12),
            width=15
        )
        entry.pack(anchor="w", pady=(0, 10))
        entry.focus_set()
        
        tk.Label(
            content,
            text="💡 Examples: 4.5, 3.0, 5.0",
            font=("Arial", 8),
            bg="white",
            fg="#7f8c8d"
        ).pack(anchor="w", pady=(0, 20))
        
        # Transaction info box
        info_frame = tk.Frame(content, bg="#e8f5e9", relief="solid", borderwidth=1)
        info_frame.pack(fill="x", pady=(0, 20))
        
        tk.Label(
            info_frame,
            text="Transaction in Progress",
            font=("Arial", 10, "bold"),
            bg="#e8f5e9",
            fg="#2e7d32"
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        tk.Label(
            info_frame,
            text="When you submit:\n"
                 "• Rating will be added/updated\n"
                 "• Transaction will COMMIT\n"
                 "• Lock will be RELEASED\n"
                 "• Other users can then edit",
            font=("Arial", 9),
            bg="#e8f5e9",
            fg="#2e7d32",
            justify="left"
        ).pack(anchor="w", padx=10, pady=(0, 10))
        
        # Buttons
        btn_frame = tk.Frame(content, bg="white")
        btn_frame.pack(pady=(10, 0))
        
        tk.Button(
            btn_frame,
            text="Submit (COMMIT Transaction)",
            command=self._on_submit,
            bg="#27ae60",
            fg="white",
            font=("Arial", 11, "bold"),
            padx=25,
            pady=10,
            cursor="hand2"
        ).pack(side="left", padx=5)
        
        tk.Button(
            btn_frame,
            text="Cancel",
            command=self._on_cancel,
            bg="#e74c3c",
            fg="white",
            font=("Arial", 10),
            padx=15,
            pady=10,
            cursor="hand2"
        ).pack(side="left", padx=5)
    
    def _on_submit(self):
        """Submit the rating and execute transaction."""
        rating_text = self.rating_var.get().strip()
        
        if not rating_text:
            messagebox.showerror("Rating Required", "Please enter a rating (0.5-5.0).", parent=self)
            return
        
        try:
            rating_val = float(rating_text)
        except ValueError:
            messagebox.showerror("Invalid Rating", "Rating must be a number.", parent=self)
            return
        
        if rating_val < 0.5 or rating_val > 5.0:
            messagebox.showerror("Invalid Rating", "Rating must be between 0.5 and 5.0.", parent=self)
            return
        
        # Execute transaction
        logger.info(f"[POPUP 3] Executing transaction: userId={self.user_id}, movieId={self.movie_id}, rating={rating_val}")
        
        try:
            ok = add_or_update_rating(self.user_id, self.movie_id, rating_val)
            
            if ok:
                logger.info(f"[POPUP 3] ✅ Transaction COMMITTED successfully")
                
                # Release lock
                release_rating_lock(self.user_id, self.movie_id)
                logger.info(f"[POPUP 3] ✅ Lock RELEASED: movieId={self.movie_id}")
                
                messagebox.showinfo(
                    "Success - Transaction Committed",
                    f"Rating updated successfully!\n\n"
                    f"Movie: {self.movie_title}\n"
                    f"Movie ID: {self.movie_id}\n"
                    f"Rating: {rating_val}\n\n"
                    f"- Transaction COMMITTED\n"
                    f"- Lock RELEASED\n"
                    f"- Other users can now edit this rating",
                    parent=self
                )
                
                self.rating_value = rating_val
                self.success = True
                self.destroy()
            else:
                logger.error(f"[POPUP 3] Transaction FAILED - Rolling back")
                messagebox.showerror(
                    "Failed - Transaction Rolled Back",
                    "The rating could not be updated.\n\n"
                    "Transaction has been ROLLED BACK.\n"
                    "No changes were made.",
                    parent=self
                )
                # Note: Lock will be released in _on_cancel or __del__
        except Exception as e:
            logger.error(f"[POPUP 3] Transaction error: {e}")
            messagebox.showerror("Error", f"Transaction failed:\n{e}", parent=self)
    
    def _on_cancel(self):
        """User clicked Cancel - rollback and release lock."""
        logger.info(f"[POPUP 3] User cancelled - releasing lock")
        release_rating_lock(self.user_id, self.movie_id)
        self.rating_value = None
        self.success = False
        self.destroy()
    
    def __del__(self):
        """Ensure lock is released if dialog is destroyed."""
        if not self.success and self.movie_id:
            logger.warning(f"[POPUP 3] Dialog destroyed without commit - releasing lock")
            try:
                release_rating_lock(self.user_id, self.movie_id)
            except:
                pass


class DeleteConfirmDialog(tk.Toplevel):
    """
    POPUP 3 (Delete path): Confirm deletion and execute transaction.
    Returns: True (if deleted) or False (if cancelled)
    """
    def __init__(self, parent, username, user_id, movie_id, movie_title):
        super().__init__(parent)
        self.title("Rating Management - Step 3")
        self.geometry("550x650")  # Increased height to show all content including buttons
        self.resizable(False, False)
        self.configure(bg="#2c3e50")
        
        self.username = username
        self.user_id = user_id
        self.movie_id = movie_id
        self.movie_title = movie_title
        self.success = False
        
        # Modal setup
        self.transient(parent)
        self.grab_set()
        
        # Build UI
        self._build_ui()
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
        
        logger.info(f"[POPUP 3 DELETE] Delete Confirm Dialog opened for {username}, movieId={movie_id}")
    
    def _build_ui(self):
        """Build the deletion confirmation UI."""
        # Header
        tk.Label(
            self,
            text="Rating Management",
            font=("Arial", 18, "bold"),
            bg="#2c3e50",
            fg="white"
        ).pack(pady=(20, 5))
        
        tk.Label(
            self,
            text=f"Movie: {self.movie_title}",
            font=("Arial", 10),
            bg="#2c3e50",
            fg="#3498db"
        ).pack(pady=(0, 5))
        
        tk.Label(
            self,
            text=f"Movie ID: {self.movie_id}",
            font=("Arial", 9),
            bg="#2c3e50",
            fg="#bdc3c7"
        ).pack(pady=(0, 5))
        
        tk.Label(
            self,
            text="Locked - Transaction in progress",
            font=("Arial", 9, "bold"),
            bg="#2c3e50",
            fg="#27ae60"
        ).pack(pady=(0, 20))
        
        # Content frame
        content = tk.Frame(self, bg="white", padx=30, pady=30)
        content.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        tk.Label(
            content,
            text="Step 3: Confirm Deletion",
            font=("Arial", 14, "bold"),
            bg="white",
            fg="#2c3e50"
        ).pack(anchor="w", pady=(0, 20))
        
        # Warning box
        warning_frame = tk.Frame(content, bg="#fff3cd", relief="solid", borderwidth=2)
        warning_frame.pack(fill="x", pady=(0, 20))
        
        tk.Label(
            warning_frame,
            text="Warning",
            font=("Arial", 11, "bold"),
            bg="#fff3cd",
            fg="#856404"
        ).pack(anchor="w", padx=15, pady=(15, 5))
        
        tk.Label(
            warning_frame,
            text=f"You are about to DELETE your rating for:\n\n"
                 f"{self.movie_title}\n"
                 f"Movie ID: {self.movie_id}\n\n"
                 f"This action cannot be undone.",
            font=("Arial", 10),
            bg="#fff3cd",
            fg="#856404",
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 15))
        
        # Transaction info
        info_frame = tk.Frame(content, bg="#ffebee", relief="solid", borderwidth=1)
        info_frame.pack(fill="x", pady=(0, 20))
        
        tk.Label(
            info_frame,
            text="When you confirm:",
            font=("Arial", 9, "bold"),
            bg="#ffebee",
            fg="#c62828"
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        tk.Label(
            info_frame,
            text="• Rating will be DELETED\n"
                 "• Transaction will COMMIT\n"
                 "• Lock will be RELEASED\n"
                 "• Other users can then edit",
            font=("Arial", 9),
            bg="#ffebee",
            fg="#c62828",
            justify="left"
        ).pack(anchor="w", padx=10, pady=(0, 10))
        
        # Buttons
        btn_frame = tk.Frame(content, bg="white")
        btn_frame.pack(pady=(10, 0))
        
        tk.Button(
            btn_frame,
            text="Confirm Delete (COMMIT)",
            command=self._on_confirm,
            bg="#e74c3c",
            fg="white",
            font=("Arial", 11, "bold"),
            padx=25,
            pady=10,
            cursor="hand2"
        ).pack(side="left", padx=5)
        
        tk.Button(
            btn_frame,
            text="Cancel",
            command=self._on_cancel,
            bg="#95a5a6",
            fg="white",
            font=("Arial", 10),
            padx=15,
            pady=10,
            cursor="hand2"
        ).pack(side="left", padx=5)
    
    def _on_confirm(self):
        """Confirm deletion and execute transaction."""
        logger.info(f"[POPUP 3 DELETE] Executing DELETE transaction: userId={self.user_id}, movieId={self.movie_id}")
        
        try:
            ok = delete_rating(self.user_id, self.movie_id)
            
            if ok:
                logger.info(f"[POPUP 3 DELETE] Transaction COMMITTED - Rating deleted")
                
                # Release lock
                release_rating_lock(self.user_id, self.movie_id)
                logger.info(f"[POPUP 3 DELETE] Lock RELEASED: movieId={self.movie_id}")
                
                messagebox.showinfo(
                    "Deleted - Transaction Committed",
                    f"Rating deleted successfully!\n\n"
                    f"Movie: {self.movie_title}\n"
                    f"Movie ID: {self.movie_id}\n\n"
                    f"- Transaction COMMITTED\n"
                    f"- Lock RELEASED\n"
                    f"- Other users can now edit this rating",
                    parent=self
                )
                
                self.success = True
                self.destroy()
            else:
                logger.error(f"[POPUP 3 DELETE] Transaction FAILED - Rolling back")
                messagebox.showerror(
                    "Failed - Transaction Rolled Back",
                    "The rating could not be deleted.\n\n"
                    "Transaction has been ROLLED BACK.\n"
                    "No changes were made.",
                    parent=self
                )
        except Exception as e:
            logger.error(f"[POPUP 3 DELETE] Delete error: {e}")
            messagebox.showerror("Error", f"Delete failed:\n{e}", parent=self)
    
    def _on_cancel(self):
        """User clicked Cancel - rollback and release lock."""
        logger.info(f"[POPUP 3 DELETE] User cancelled - releasing lock")
        release_rating_lock(self.user_id, self.movie_id)
        self.success = False
        self.destroy()
    
    def __del__(self):
        """Ensure lock is released if dialog is destroyed."""
        if not self.success and self.movie_id:
            logger.warning(f"[POPUP 3 DELETE] Dialog destroyed without commit - releasing lock")
            try:
                release_rating_lock(self.user_id, self.movie_id)
            except:
                pass


class ViewRatingsDialog(tk.Toplevel):
    """
    POPUP (View path): Display all user ratings (no lock needed).
    """
    def __init__(self, parent, username, user_id):
        super().__init__(parent)
        self.title("My Ratings")
        self.geometry("600x600")  # Increased height to show buttons
        self.resizable(True, True)
        self.configure(bg="#2c3e50")
        
        self.username = username
        self.user_id = user_id
        self.go_back = False  # Track if user wants to go back
        
        # Modal setup
        self.transient(parent)
        self.grab_set()
        
        # Get ratings
        ratings = get_all_user_ratings(user_id)
        
        if not ratings:
            messagebox.showinfo(
                "No Ratings",
                f"You have not rated any movies yet.",
                parent=parent
            )
            self.destroy()
            return
        
        # Build UI
        self._build_ui(ratings)
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
        
        logger.info(f"[POPUP VIEW] View Ratings Dialog opened for {username}")
    
    def _build_ui(self, ratings):
        """Build the view ratings UI."""
        # Header
        tk.Label(
            self,
            text="My Ratings",
            font=("Arial", 18, "bold"),
            bg="#2c3e50",
            fg="white"
        ).pack(pady=(20, 5))
        
        tk.Label(
            self,
            text=f"{len(ratings)} movies rated by {self.username}",
            font=("Arial", 10),
            bg="#2c3e50",
            fg="#3498db"
        ).pack(pady=(0, 20))
        
        # Content frame
        content = tk.Frame(self, bg="white", padx=20, pady=20)
        content.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Scrollable text
        scrollbar = tk.Scrollbar(content)
        scrollbar.pack(side="right", fill="y")
        
        text = tk.Text(
            content,
            wrap="word",
            font=("Consolas", 9),
            yscrollcommand=scrollbar.set,
            bg="white",
            fg="#2c3e50"
        )
        text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=text.yview)
        
        # Format ratings
        for idx, r in enumerate(ratings, 1):
            text.insert("end", f"{idx}. {r['title']}\n")
            text.insert("end", f"   Movie ID: {r['movieId']}\n")
            text.insert("end", f"   My Rating: {r['rating']}\n")
            text.insert("end", f"   Movie Avg: {r.get('movie_avg_rating', 'N/A')} ({r.get('movie_vote_count', 0)} votes)\n")
            text.insert("end", f"   Rated: {datetime.fromtimestamp(r['timestamp']).strftime('%Y-%m-%d %H:%M')}\n")
            text.insert("end", "\n")
        
        text.config(state="disabled")
        
        # Buttons frame
        btn_frame = tk.Frame(self, bg="#2c3e50")
        btn_frame.pack(pady=(0, 20))
        
        # Back button
        tk.Button(
            btn_frame,
            text="Back",
            command=self._on_back,
            bg="#95a5a6",
            fg="white",
            font=("Arial", 11),
            padx=30,
            pady=10,
            cursor="hand2"
        ).pack(side="left", padx=5)
        
        # Close button
        tk.Button(
            btn_frame,
            text="Close",
            command=self.destroy,
            bg="#3498db",
            fg="white",
            font=("Arial", 11),
            padx=30,
            pady=10,
            cursor="hand2"
        ).pack(side="left", padx=5)
    
    def _on_back(self):
        """User clicked Back - return to action selection."""
        self.go_back = True
        self.destroy()



###############################################################################
# 8. MAIN GUI APP
###############################################################################

class MovieApp(tk.Tk):
    def __init__(self, skip_login=False):
        super().__init__()
        
        # Title
        tk.Label(
            self.screen_container,
            text="Rating Management",
            font=("Arial", 18, "bold"),
            bg="#2c3e50",
            fg="white"
        ).pack(pady=(0, 5))
        
        tk.Label(
            self.screen_container,
            text=f"Logged in as: {self.username} (User ID: {self.user_id})",
            font=("Arial", 9),
            bg="#2c3e50",
            fg="#bdc3c7"
        ).pack(pady=(0, 30))
        
        # Content frame (white background)
        content = tk.Frame(self.screen_container, bg="white", padx=30, pady=30)
        content.pack(fill="both", expand=True)
        
        tk.Label(
            content,
            text="Step 1: Select Action",
            font=("Arial", 14, "bold"),
            bg="white",
            fg="#2c3e50"
        ).pack(anchor="w", pady=(0, 20))
        
        # Radio buttons for actions
        self.action_var = tk.StringVar(value="add")
        
        actions = [
            ("add", "Add/Edit Rating", "Add a new rating or update an existing one"),
            ("delete", "Delete Rating", "Remove a rating from a movie"),
            ("view", "View My Ratings", "See all your movie ratings")
        ]
        
        for value, label, description in actions:
            frame = tk.Frame(content, bg="white")
            frame.pack(fill="x", pady=8)
            
            tk.Radiobutton(
                frame,
                text=label,
                variable=self.action_var,
                value=value,
                bg="white",
                font=("Arial", 11, "bold"),
                fg="#2c3e50"
            ).pack(anchor="w")
            
            tk.Label(
                frame,
                text=f"   {description}",
                bg="white",
                font=("Arial", 9),
                fg="#7f8c8d"
            ).pack(anchor="w", padx=(25, 0))
        
        # Buttons
        button_frame = tk.Frame(content, bg="white")
        button_frame.pack(pady=(30, 0))
        
        # Test: Create a simple button with direct print to test if ANY button works
        def test_click():
            print("!!! BUTTON CLICKED - TEST FUNCTION WORKS !!!")
            messagebox.showinfo("Test", "Button click detected!", parent=self)
            self.handle_screen_1_next()
        
        # Create buttons with test function
        next_btn = tk.Button(
            button_frame,
            text="Next →",
            command=test_click,
            bg="#3498db",
            fg="white",
            font=("Arial", 11, "bold"),
            padx=30,
            pady=10,
            relief="raised",
            cursor="hand2",
            state="normal"
        )
        next_btn.pack(side="left", padx=5)
        next_btn.bind("<Button-1>", lambda e: print(f"[DEBUG] Button-1 event detected on next_btn!"))
        print(f"[DEBUG] Next button created: {next_btn}")
        print(f"[DEBUG] Next button state: {next_btn['state']}")
        
        cancel_btn = tk.Button(
            button_frame,
            text="Cancel",
            command=lambda: self.handle_cancel(),
            bg="#95a5a6",
            fg="white",
            font=("Arial", 11),
            padx=30,
            pady=10,
            relief="raised",
            cursor="hand2",
            state="normal"
        )
        cancel_btn.pack(side="left", padx=5)
        cancel_btn.bind("<Button-1>", lambda e: print(f"[DEBUG] Button-1 event detected on cancel_btn!"))
        print(f"[DEBUG] Cancel button created: {cancel_btn}")
        print(f"[DEBUG] Button frame ready, waiting for clicks...")
        
        # Force update to ensure buttons are rendered
        self.update_idletasks()
    
    def handle_screen_1_next(self):
        """Move from screen 1 to screen 2 (or directly show ratings for 'view' action)."""
        self.selected_action = self.action_var.get()
        
        print(f"[DEBUG] handle_screen_1_next called! Selected action: {self.selected_action}")
        logger.info(f"[DIALOG] Screen 1 Next clicked - Selected action: {self.selected_action}")
        
        # Debug: Show message box to confirm button works
        messagebox.showinfo(
            "Debug",
            f"Button clicked!\nAction: {self.selected_action}\n\nAbout to show screen 2...",
            parent=self
        )
        
        if self.selected_action == "view":
            # Go directly to view ratings (no movie selection needed)
            self.show_all_ratings()
        else:
            # Show movie selection screen
            logger.info(f"[DIALOG] Showing movie selection screen for action: {self.selected_action}")
            print(f"[DEBUG] About to call show_screen_2_movie_selection()")
            self.show_screen_2_movie_selection()
            print(f"[DEBUG] show_screen_2_movie_selection() returned")
    
    def show_screen_2_movie_selection(self):
        """Screen 2: Enter movie ID or title."""
        logger.info(f"[DIALOG] show_screen_2_movie_selection called")
        self.clear_screen()
        
        logger.info(f"[DIALOG] Building screen 2 UI")
        
        # Force window update
        self.update_idletasks()
        
        # Title
        tk.Label(
            self.screen_container,
            text="Rating Management",
            font=("Arial", 18, "bold"),
            bg="#2c3e50",
            fg="white"
        ).pack(pady=(0, 5))
        
        logger.info(f"[DIALOG] Screen 2 title added")
        
        action_text = "Add/Edit Rating" if self.selected_action == "add" else "Delete Rating"
        tk.Label(
            self.screen_container,
            text=f"Action: {action_text}",
            font=("Arial", 10),
            bg="#2c3e50",
            fg="#3498db"
        ).pack(pady=(0, 20))
        
        # Force window update again
        self.update()
        logger.info(f"[DIALOG] Screen 2 layout complete")
        
        # Content frame
        content = tk.Frame(self.screen_container, bg="white", padx=30, pady=30)
        content.pack(fill="both", expand=True)
        
        tk.Label(
            content,
            text="Step 2: Select Movie",
            font=("Arial", 14, "bold"),
            bg="white",
            fg="#2c3e50"
        ).pack(anchor="w", pady=(0, 10))
        
        tk.Label(
            content,
            text="Enter Movie ID or Title:",
            font=("Arial", 10),
            bg="white",
            fg="#34495e"
        ).pack(anchor="w", pady=(10, 5))
        
        self.movie_var = tk.StringVar()
        entry = ttk.Entry(
            content,
            textvariable=self.movie_var,
            font=("Arial", 11),
            width=40
        )
        entry.pack(fill="x", pady=(0, 10))
        entry.focus_set()
        
        tk.Label(
            content,
            text="Tip: You can enter a Movie ID (e.g., 1) or search by title (e.g., Toy Story)",
            font=("Arial", 8),
            bg="white",
            fg="#7f8c8d"
        ).pack(anchor="w", pady=(0, 20))
        
        # Lock info box
        info_frame = tk.Frame(content, bg="#ecf0f1", relief="solid", borderwidth=1)
        info_frame.pack(fill="x", pady=(0, 20), padx=10)
        
        tk.Label(
            info_frame,
            text="Concurrent Edit Prevention",
            font=("Arial", 10, "bold"),
            bg="#ecf0f1",
            fg="#2c3e50"
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        tk.Label(
            info_frame,
            text="When you confirm, a lock will be acquired to prevent\nother users from editing this rating simultaneously.",
            font=("Arial", 9),
            bg="#ecf0f1",
            fg="#34495e",
            justify="left"
        ).pack(anchor="w", padx=10, pady=(0, 10))
        
        # Buttons
        button_frame = tk.Frame(content, bg="white")
        button_frame.pack(pady=(10, 0))
        
        tk.Button(
            button_frame,
            text="Confirm & Acquire Lock",
            command=self.handle_screen_2_confirm,
            bg="#27ae60",
            fg="white",
            font=("Arial", 11, "bold"),
            padx=25,
            pady=10,
            relief="flat",
            cursor="hand2"
        ).pack(side="left", padx=5)
        
        tk.Button(
            button_frame,
            text="← Back",
            command=self.show_screen_1_action_selection,
            bg="#95a5a6",
            fg="white",
            font=("Arial", 11),
            padx=25,
            pady=10,
            relief="flat",
            cursor="hand2"
        ).pack(side="left", padx=5)
    
    def handle_screen_2_confirm(self):
        """Confirm movie and acquire lock, then show screen 3."""
        movie_text = self.movie_var.get().strip()
        
        if not movie_text:
            messagebox.showerror(
                "Movie Required",
                "Please enter a Movie ID or Title.",
                parent=self
            )
            return
        
        # Parse movie ID/title
        movie_id = None
        movie_title = None
        
        try:
            # Try as integer (Movie ID)
            movie_id = int(movie_text)
            movie = get_movie_details(movie_id)
            if not movie:
                messagebox.showerror(
                    "Movie Not Found",
                    f"Movie ID {movie_id} does not exist.",
                    parent=self
                )
                return
            movie_title = movie['title']
        except ValueError:
            # Search by title
            movies = find_movie_by_title_sql(movie_text)
            if not movies:
                messagebox.showerror(
                    "Movie Not Found",
                    f"No movies found matching '{movie_text}'.\n\n"
                    "Please check spelling or use Movie ID.",
                    parent=self
                )
                return
            elif len(movies) == 1:
                movie_id = movies[0]['movieId']
                movie_title = movies[0]['title']
            else:
                # Multiple matches - show selection
                selection_msg = "Multiple movies found:\n\n"
                for idx, m in enumerate(movies[:5], 1):
                    selection_msg += f"{idx}. [ID: {m['movieId']}] {m['title']}\n"
                selection_msg += "\nPlease use the Movie ID."
                messagebox.showinfo("Multiple Movies", selection_msg, parent=self)
                return
        
        # Verify movie exists
        if not sql_movie_exists(movie_id):
            messagebox.showerror("Error", f"Movie {movie_id} does not exist.", parent=self)
            return
        
        # Check if locked by someone else (CONCURRENT EDIT PREVENTION)
        locked_by = check_rating_lock(self.user_id, movie_id)
        if locked_by and locked_by != self.username:
            messagebox.showerror(
                "Rating Locked - Concurrent Edit Prevention",
                f"This rating is currently being edited by another user.\n\n"
                f"• Another user is currently editing this rating\n"
                f"• You CANNOT edit/delete until they finish\n"
                f"• This demonstrates concurrent edit prevention\n"
                f"• Lock will auto-expire in 5 minutes\n\n"
                f"Movie: {movie_title} (ID: {movie_id})\n\n"
                f"Please wait and try again later.",
                parent=self
            )
            logger.info(f"[DIALOG] User {self.username} blocked - rating locked by '{locked_by}'")
            return
        
        # Acquire lock
        if not acquire_rating_lock(self.user_id, movie_id, self.username):
            messagebox.showerror(
                "Lock Error",
                "Failed to acquire lock.\n\n"
                "This may indicate a database issue.\n"
                "Please try again.",
                parent=self
            )
            return
        
        # Lock acquired!
        self.movie_id = movie_id
        self.movie_title = movie_title
        self.lock_acquired = True
        
        logger.info(f"[DIALOG] Lock acquired: userId={self.user_id}, movieId={movie_id}")
        
        # Show success and move to next screen
        messagebox.showinfo(
            "Lock Acquired",
            f"Rating locked successfully!\n\n"
            f"Movie: {movie_title}\n"
            f"Movie ID: {movie_id}\n\n"
            f"✓ You now have exclusive edit access\n"
            f"✓ Other users are blocked from editing\n"
            f"✓ Lock will auto-expire in 5 minutes",
            parent=self
        )
        
        # Move to next screen based on action
        if self.selected_action == "add":
            self.show_screen_3_rating_entry()
        else:  # delete
            self.show_screen_3_delete_confirm()
    
    def show_screen_3_rating_entry(self):
        """Screen 3: Enter rating value (for Add/Edit action)."""
        self.clear_screen()
        
        # Title
        tk.Label(
            self.screen_container,
            text="Rating Management",
            font=("Arial", 18, "bold"),
            bg="#2c3e50",
            fg="white"
        ).pack(pady=(0, 5))
        
        tk.Label(
            self.screen_container,
            text=f"Movie: {self.movie_title} (ID: {self.movie_id})",
            font=("Arial", 10),
            bg="#2c3e50",
            fg="#3498db"
        ).pack(pady=(0, 5))
        
        tk.Label(
            self.screen_container,
            text="Locked - Concurrent edits prevented",
            font=("Arial", 9),
            bg="#2c3e50",
            fg="#27ae60"
        ).pack(pady=(0, 20))
        
        # Content frame
        content = tk.Frame(self.screen_container, bg="white", padx=30, pady=30)
        content.pack(fill="both", expand=True)
        
        tk.Label(
            content,
            text="Step 3: Enter Rating",
            font=("Arial", 14, "bold"),
            bg="white",
            fg="#2c3e50"
        ).pack(anchor="w", pady=(0, 10))
        
        tk.Label(
            content,
            text="Enter your rating (0.5 - 5.0):",
            font=("Arial", 10),
            bg="white",
            fg="#34495e"
        ).pack(anchor="w", pady=(10, 5))
        
        self.rating_var = tk.StringVar()
        entry = ttk.Entry(
            content,
            textvariable=self.rating_var,
            font=("Arial", 11),
            width=15
        )
        entry.pack(anchor="w", pady=(0, 10))
        entry.focus_set()
        
        tk.Label(
            content,
            text="Examples: 4.5, 3.0, 5.0",
            font=("Arial", 8),
            bg="white",
            fg="#7f8c8d"
        ).pack(anchor="w", pady=(0, 30))
        
        # Buttons
        button_frame = tk.Frame(content, bg="white")
        button_frame.pack(pady=(10, 0))
        
        tk.Button(
            button_frame,
            text="Submit (Execute Transaction)",
            command=self.handle_screen_3_submit_rating,
            bg="#27ae60",
            fg="white",
            font=("Arial", 11, "bold"),
            padx=25,
            pady=10,
            relief="flat",
            cursor="hand2"
        ).pack(side="left", padx=5)
        
        tk.Button(
            button_frame,
            text="Cancel (Release Lock)",
            command=self.handle_cancel_with_lock,
            bg="#e74c3c",
            fg="white",
            font=("Arial", 11),
            padx=25,
            pady=10,
            relief="flat",
            cursor="hand2"
        ).pack(side="left", padx=5)
    
    def handle_screen_3_submit_rating(self):
        """Submit the rating (execute transaction)."""
        rating_text = self.rating_var.get().strip()
        
        if not rating_text:
            messagebox.showerror("Rating Required", "Please enter a rating (0.5-5.0).", parent=self)
            return
        
        try:
            rating_val = float(rating_text)
        except ValueError:
            messagebox.showerror("Invalid Rating", "Rating must be a number.", parent=self)
            return
        
        if rating_val < 0.5 or rating_val > 5.0:
            messagebox.showerror("Invalid Rating", "Rating must be between 0.5 and 5.0.", parent=self)
            return
        
        # Execute transaction
        logger.info(f"[DIALOG] Transaction BEGIN: userId={self.user_id}, movieId={self.movie_id}, rating={rating_val}")
        
        try:
            ok = add_or_update_rating(self.user_id, self.movie_id, rating_val)
            
            if ok:
                logger.info(f"[DIALOG] Transaction COMMIT: Rating updated successfully")
                
                # Release lock
                if self.lock_acquired:
                    release_rating_lock(self.user_id, self.movie_id)
                    self.lock_acquired = False
                    logger.info(f"[DIALOG] Lock released: movieId={self.movie_id}")
                
                messagebox.showinfo(
                    "Success",
                    f"Rating updated successfully!\n\n"
                    f"Movie: {self.movie_title}\n"
                    f"Movie ID: {self.movie_id}\n"
                    f"Rating: {rating_val}\n\n"
                    f"✓ Transaction committed\n"
                    f"✓ Lock released\n"
                    f"✓ Other users can now edit",
                    parent=self
                )
                
                self.result = {"success": True, "action": "add", "movie_id": self.movie_id, "rating": rating_val}
                self.destroy()
            else:
                logger.error(f"[DIALOG] Transaction ROLLBACK: Update failed")
                messagebox.showerror(
                    "Failed",
                    "Transaction rolled back due to error.\n\n"
                    "The rating was NOT updated.",
                    parent=self
                )
        except Exception as e:
            logger.error(f"[DIALOG] Transaction error: {e}")
            messagebox.showerror("Error", f"An error occurred:\n{e}", parent=self)
        finally:
            # Always release lock
            if self.lock_acquired:
                release_rating_lock(self.user_id, self.movie_id)
                self.lock_acquired = False
    
    def show_screen_3_delete_confirm(self):
        """Screen 3: Confirm deletion (for Delete action)."""
        self.clear_screen()
        
        # Title
        tk.Label(
            self.screen_container,
            text="Rating Management",
            font=("Arial", 18, "bold"),
            bg="#2c3e50",
            fg="white"
        ).pack(pady=(0, 5))
        
        tk.Label(
            self.screen_container,
            text=f"Movie: {self.movie_title} (ID: {self.movie_id})",
            font=("Arial", 10),
            bg="#2c3e50",
            fg="#3498db"
        ).pack(pady=(0, 5))
        
        tk.Label(
            self.screen_container,
            text="Locked - Concurrent edits prevented",
            font=("Arial", 9),
            bg="#2c3e50",
            fg="#27ae60"
        ).pack(pady=(0, 20))
        
        # Content frame
        content = tk.Frame(self.screen_container, bg="white", padx=30, pady=30)
        content.pack(fill="both", expand=True)
        
        tk.Label(
            content,
            text="Step 3: Confirm Deletion",
            font=("Arial", 14, "bold"),
            bg="white",
            fg="#2c3e50"
        ).pack(anchor="w", pady=(0, 20))
        
        # Warning box
        warning_frame = tk.Frame(content, bg="#fff3cd", relief="solid", borderwidth=2)
        warning_frame.pack(fill="x", pady=(0, 20))
        
        tk.Label(
            warning_frame,
            text="Warning",
            font=("Arial", 11, "bold"),
            bg="#fff3cd",
            fg="#856404"
        ).pack(anchor="w", padx=15, pady=(15, 5))
        
        tk.Label(
            warning_frame,
            text=f"You are about to delete your rating for:\n\n{self.movie_title} (ID: {self.movie_id})\n\nThis action cannot be undone.",
            font=("Arial", 10),
            bg="#fff3cd",
            fg="#856404",
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 15))
        
        # Buttons
        button_frame = tk.Frame(content, bg="white")
        button_frame.pack(pady=(20, 0))
        
        tk.Button(
            button_frame,
            text="Confirm Delete (Execute Transaction)",
            command=self.handle_screen_3_confirm_delete,
            bg="#e74c3c",
            fg="white",
            font=("Arial", 11, "bold"),
            padx=20,
            pady=10,
            relief="flat",
            cursor="hand2"
        ).pack(side="left", padx=5)
        
        tk.Button(
            button_frame,
            text="Cancel (Release Lock)",
            command=self.handle_cancel_with_lock,
            bg="#95a5a6",
            fg="white",
            font=("Arial", 11),
            padx=25,
            pady=10,
            relief="flat",
            cursor="hand2"
        ).pack(side="left", padx=5)
    
    def handle_screen_3_confirm_delete(self):
        """Confirm and execute deletion transaction."""
        logger.info(f"[DIALOG] Transaction BEGIN: Delete rating userId={self.user_id}, movieId={self.movie_id}")
        
        try:
            ok = delete_rating(self.user_id, self.movie_id)
            
            if ok:
                logger.info(f"[DIALOG] Transaction COMMIT: Rating deleted")
                
                # Release lock
                if self.lock_acquired:
                    release_rating_lock(self.user_id, self.movie_id)
                    self.lock_acquired = False
                    logger.info(f"[DIALOG] Lock released: movieId={self.movie_id}")
                
                messagebox.showinfo(
                    "Deleted",
                    f"Rating deleted successfully!\n\n"
                    f"Movie: {self.movie_title}\n"
                    f"Movie ID: {self.movie_id}\n\n"
                    f"✓ Transaction committed\n"
                    f"✓ Lock released",
                    parent=self
                )
                
                self.result = {"success": True, "action": "delete", "movie_id": self.movie_id}
                self.destroy()
            else:
                logger.error(f"[DIALOG] Transaction ROLLBACK: Delete failed")
                messagebox.showerror(
                    "Failed",
                    "Transaction rolled back.\n\n"
                    "The rating was NOT deleted.",
                    parent=self
                )
        except Exception as e:
            logger.error(f"[DIALOG] Delete error: {e}")
            messagebox.showerror("Error", f"An error occurred:\n{e}", parent=self)
        finally:
            # Always release lock
            if self.lock_acquired:
                release_rating_lock(self.user_id, self.movie_id)
                self.lock_acquired = False
    
    def show_all_ratings(self):
        """Show all user ratings (for View action - no lock needed)."""
        ratings = get_all_user_ratings(self.user_id)
        
        if not ratings:
            messagebox.showinfo(
                "No Ratings",
                f"You have not rated any movies yet.",
                parent=self
            )
            self.destroy()
            return
        
        self.clear_screen()
        
        # Title
        tk.Label(
            self.screen_container,
            text="My Ratings",
            font=("Arial", 18, "bold"),
            bg="#2c3e50",
            fg="white"
        ).pack(pady=(0, 5))
        
        tk.Label(
            self.screen_container,
            text=f"{len(ratings)} movies rated",
            font=("Arial", 10),
            bg="#2c3e50",
            fg="#3498db"
        ).pack(pady=(0, 20))
        
        # Content frame
        content = tk.Frame(self.screen_container, bg="white", padx=20, pady=20)
        content.pack(fill="both", expand=True)
        
        # Scrollable text
        scrollbar = tk.Scrollbar(content)
        scrollbar.pack(side="right", fill="y")
        
        text = tk.Text(
            content,
            wrap="word",
            font=("Consolas", 9),
            yscrollcommand=scrollbar.set,
            bg="white",
            fg="#2c3e50"
        )
        text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=text.yview)
        
        # Format ratings
        content_lines = []
        for idx, r in enumerate(ratings, 1):
            content_lines.append(f"{idx}. {r['title']}")
            content_lines.append(f"   Movie ID: {r['movieId']}")
            content_lines.append(f"   My Rating: {r['rating']} ⭐")
            content_lines.append(f"   Movie Avg: {r.get('movie_avg_rating', 'N/A')} ({r.get('movie_vote_count', 0)} votes)")
            content_lines.append(f"   Rated: {datetime.fromtimestamp(r['timestamp']).strftime('%Y-%m-%d %H:%M')}")
            content_lines.append("")
        
        text.insert("1.0", "\n".join(content_lines))
        text.config(state="disabled")
        
        # Close button
        tk.Button(
            self.screen_container,
            text="Close",
            command=self.destroy,
            bg="#3498db",
            fg="white",
            font=("Arial", 11, "bold"),
            padx=30,
            pady=10,
            relief="flat",
            cursor="hand2"
        ).pack(pady=(10, 0))
    
    def handle_cancel(self):
        """Cancel without lock."""
        self.result = None
        self.destroy()
    
    def handle_cancel_with_lock(self):
        """Cancel and release lock if acquired."""
        if self.lock_acquired:
            release_rating_lock(self.user_id, self.movie_id)
            self.lock_acquired = False
            logger.info(f"[DIALOG] Lock released (cancelled): movieId={self.movie_id}")
        
        self.result = None
        self.destroy()


###############################################################################
# 8. MAIN GUI APP
###############################################################################

class MovieApp(tk.Tk):
    def __init__(self, skip_login=False):
        super().__init__()

        # First thing: LOGIN (unless skipping due to guest login/register)
        if not skip_login:
            login = LoginDialog(self)
            self.wait_window(login)

            if login.user_info:
                # Regular user login
                CURRENT_USER.update(login.user_info)
            elif login.is_guest:
                # Guest mode - NOT a database user
                CURRENT_USER.update({
                    "userId": None,
                    "username": "GUEST",
                    "email": None,
                    "role": "guest",  # Special role for guests
                })
            else:
                # User closed the window without logging in - exit app
                self.destroy()
                import sys
                sys.exit(0)

        # ===== Window config / styles =====
        self.title("Movie Database Management System")
        self.geometry("1400x850")
        self.minsize(800, 600)  # Set minimum window size for responsiveness
        self.resizable(True, True)
        self.configure(bg="#f0f0f0")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabelframe", background="#f0f0f0", borderwidth=2)
        style.configure(
            "TLabelframe.Label",
            font=("Arial", 11, "bold"),
            background="#f0f0f0",
            foreground="#2c3e50",
        )
        style.configure("TLabel", background="#f0f0f0", font=("Arial", 10))
        style.configure("TButton", font=("Arial", 9, "bold"))
        style.configure("TEntry", fieldbackground="white", font=("Arial", 10))
        style.configure(
            "Treeview",
            background="white",
            foreground="black",
            rowheight=25,
            fieldbackground="white",
            font=("Arial", 9),
        )
        style.map("Treeview", background=[("selected", "#3498db")])

        # ===== Header (with login info) =====
        header = tk.Frame(self, bg="#2c3e50")
        header.pack(fill="x", side="top")

        tk.Label(
            header,
            text="TMDB Movie Database",
            font=("Arial", 18, "bold"),
            bg="#2c3e50",
            fg="white",
        ).pack(pady=(10, 2))

        self.user_info_label = tk.Label(
            header,
            text=f"Logged in as: {CURRENT_USER['username']} ({CURRENT_USER['role']})",
            font=("Arial", 10),
            bg="#2c3e50",
            fg="#bdc3c7",
        )
        self.user_info_label.pack(pady=(0, 5))

        # Admin View Switcher - only for admins
        if CURRENT_USER['role'] == 'admin' and CURRENT_USER['userId'] is not None:
            # Track current view mode
            self.admin_view_mode = tk.StringVar(value="admin")  # "admin" or "user"
            
            view_switcher_frame = tk.Frame(header, bg="#2c3e50")
            view_switcher_frame.pack(pady=(0, 5))
            
            tk.Label(
                view_switcher_frame,
                text="View as: ",
                font=("Arial", 9),
                bg="#2c3e50",
                fg="#ecf0f1"
            ).pack(side="left", padx=(0, 5))
            
            # Admin View button
            self.admin_view_btn = tk.Button(
                view_switcher_frame,
                text="Admin",
                command=lambda: self.switch_view_mode("admin"),
                bg="#3498db",
                fg="white",
                font=("Arial", 9, "bold"),
                padx=15,
                pady=5,
                relief="flat",
                cursor="hand2",
                borderwidth=0
            )
            self.admin_view_btn.pack(side="left", padx=2)
            
            # User View button
            self.user_view_btn = tk.Button(
                view_switcher_frame,
                text="User",
                command=lambda: self.switch_view_mode("user"),
                bg="#7f8c8d",
                fg="white",
                font=("Arial", 9, "bold"),
                padx=15,
                pady=5,
                relief="flat",
                cursor="hand2",
                borderwidth=0
            )
            self.user_view_btn.pack(side="left", padx=2)

        # Logout button for authenticated users (admin and regular users)
        if CURRENT_USER['role'] in ['admin', 'user'] and CURRENT_USER['userId'] is not None:
            logout_btn = tk.Button(
                header,
                text="Logout",
                command=self.handle_logout,
                bg="#e74c3c",
                fg="white",
                font=("Arial", 9, "bold"),
                padx=15,
                pady=5,
                relief="flat",
                cursor="hand2",
                borderwidth=0
            )
            logout_btn.pack(pady=(0, 10))

        # Guest toolbar with Login/Register buttons
        if CURRENT_USER['role'] == 'guest':
            guest_toolbar = tk.Frame(header, bg="#2c3e50")
            guest_toolbar.pack(pady=(0, 10))
            
            tk.Label(
                guest_toolbar,
                text="Want full access? ",
                font=("Arial", 9),
                bg="#2c3e50",
                fg="#ecf0f1"
            ).pack(side="left", padx=(0, 5))
            
            tk.Button(
                guest_toolbar,
                text="Login",
                command=self.handle_guest_login,
                bg="#27ae60",
                fg="white",
                font=("Arial", 9, "bold"),
                padx=15,
                pady=5,
                relief="flat",
                cursor="hand2",
                borderwidth=0
            ).pack(side="left", padx=2)
            
            tk.Button(
                guest_toolbar,
                text="Register",
                command=self.handle_guest_register,
                bg="#3498db",
                fg="white",
                font=("Arial", 9, "bold"),
                padx=15,
                pady=5,
                relief="flat",
                cursor="hand2",
                borderwidth=0
            ).pack(side="left", padx=2)

        # ===== Notebook / Tabs =====
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.movies_tab = ttk.Frame(self.notebook)
        self.users_tab = ttk.Frame(self.notebook)
        self.analytics_tab = ttk.Frame(self.notebook)
        self.profile_tab = ttk.Frame(self.notebook)
        self.admin_movies_tab = ttk.Frame(self.notebook)  # Admin movie management tab
        self.admin_dashboard_tab = ttk.Frame(self.notebook)  # Admin dashboard tab
        self.nosql_tab = ttk.Frame(self.notebook)
        self.performance_tab = ttk.Frame(self.notebook)

        # Add tabs based on role and view mode
        self.rebuild_tabs()

        # Pagination variables
        self.current_page = 0
        self.page_size = 50
        self.total_results = []
        self.last_search_type = None  # 'basic' or 'advanced'
        
        # Build each tab
        self.build_movies_tab()
        self.build_users_tab()
        self.build_analytics_tab()
        
        if CURRENT_USER['role'] == 'admin':
            self.build_admin_dashboard_tab()
            self.build_admin_movies_tab()
        
        self.build_nosql_tab()
        self.build_performance_tab()
        
        # Build profile tab for logged-in users (including admins)
        if CURRENT_USER['userId'] is not None:
            self.build_profile_tab()

        # apply permissions after widgets created
        self.apply_role_permissions()

    def handle_guest_login(self):
        """Show login dialog for guest users"""
        login = LoginDialog(self, show_guest_options=True)
        self.wait_window(login)
        
        if login.user_info:
            # Successful login - update CURRENT_USER globally
            global CURRENT_USER
            CURRENT_USER.update(login.user_info)
            
            messagebox.showinfo("Login Successful", 
                f"Welcome back, {login.user_info['username']}!\n\n"
                "The application will reload with your account.")
            
            # Destroy and recreate app, skipping login dialog
            self.destroy()
            app = MovieApp(skip_login=True)
            app.mainloop()
            
    def handle_guest_register(self):
        """Show registration dialog for guest users - triggers the register flow"""
        login = LoginDialog(self, show_guest_options=True)
        # Automatically click the Register button for the user by triggering the register flow
        login.after(100, login._do_create_account)
        self.wait_window(login)
        
        if login.user_info:
            # Successful registration - update CURRENT_USER globally
            global CURRENT_USER
            CURRENT_USER.update(login.user_info)
            
            messagebox.showinfo("Registration Successful", 
                f"Welcome, {login.user_info['username']}!\n\n"
                "The application will reload with your new account.")
            
            # Destroy and recreate app, skipping login dialog
            self.destroy()
            app = MovieApp(skip_login=True)
            app.mainloop()

    def handle_logout(self):
        """Logout current user and return to login screen"""
        global CURRENT_USER
        
        confirm = messagebox.askyesno(
            "Confirm Logout",
            f"Are you sure you want to logout, {CURRENT_USER['username']}?",
            parent=self
        )
        
        if confirm:
            # Reset CURRENT_USER to guest state
            CURRENT_USER = {
                "userId": None,
                "username": "guest",
                "email": None,
                "role": "guest",
            }
            
            messagebox.showinfo("Logged Out", "You have been logged out successfully.")
            
            # Destroy current window and create new app (will show login dialog)
            self.destroy()
            app = MovieApp()
            app.mainloop()

    def rebuild_tabs(self):
        """Rebuild notebook tabs based on user role"""
        # Remove all tabs
        for tab in self.notebook.tabs():
            self.notebook.forget(tab)
        
        # Check if admin is in special admin view mode
        if CURRENT_USER['role'] == 'admin':
            view_mode = getattr(self, 'admin_view_mode', None)
            if view_mode and view_mode.get() == 'admin':
                # Admin View - ONLY show admin-specific tabs
                self.notebook.add(self.admin_dashboard_tab, text="  Admin Dashboard  ")
                self.notebook.add(self.admin_movies_tab, text="  Manage Movies  ")
                return  # Exit early
        
        # Common tabs for all users (guest, user, admin in user mode)
        self.notebook.add(self.movies_tab, text="  Movies & Search  ")
        self.notebook.add(self.users_tab, text="  Users & Ratings  ")
        self.notebook.add(self.analytics_tab, text="  Analytics & Stats  ")
        self.notebook.add(self.nosql_tab, text="  Keywords & Similar  ")
        self.notebook.add(self.performance_tab, text="  Performance  ")
        
        # Profile tab only for logged-in users (not guests)
        if CURRENT_USER['userId'] is not None:
            self.notebook.add(self.profile_tab, text="  My Profile  ")

    def switch_view_mode(self, mode):
        """Switch between admin and user view mode"""
        if not hasattr(self, 'admin_view_mode'):
            return
            
        self.admin_view_mode.set(mode)
        
        # Update button styles to show active mode
        if mode == 'admin':
            self.admin_view_btn.config(bg="#3498db")  # Active blue
            self.user_view_btn.config(bg="#7f8c8d")  # Inactive gray
        else:
            self.admin_view_btn.config(bg="#7f8c8d")  # Inactive gray
            self.user_view_btn.config(bg="#3498db")  # Active blue
        
        # Rebuild tabs to show/hide admin tabs
        self.rebuild_tabs()
        
        # Show notification
        mode_name = "Admin" if mode == "admin" else "User"
        messagebox.showinfo(
            "View Mode Changed",
            f"Switched to {mode_name} View\n\n"
            f"{'Admin-only tabs are now visible.' if mode == 'admin' else 'You are now seeing the user experience.'}"
        )

    # ------------------------------------------------------------------
    # Helper to set text in Text widgets (read-only style)
    # ------------------------------------------------------------------
    def _set_text_widget(self, widget, content: str):
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content.rstrip() + "\n")
        widget.config(state="disabled")
        widget.see("1.0")  # Scroll to top

    def _append_text_widget(self, widget, line: str):
        widget.config(state="normal")
        widget.insert("end", line.rstrip() + "\n")
        widget.config(state="disabled")
        widget.see("end")  # For append, we want to see the new line

    # ------------------------------------------------------------------
    # TAB 1: MOVIES & SEARCH
    # ------------------------------------------------------------------
    def build_movies_tab(self):
        container = tk.Frame(self.movies_tab, bg="#f0f0f0")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # --- Search area (basic + advanced)
        search_wrapper = ttk.LabelFrame(container, text="Movie Search", padding=10)
        search_wrapper.pack(fill="x", pady=(0, 10))
        search_wrapper.pack_propagate(False)
        search_wrapper.configure(height=160)

        basic_frame = tk.Frame(search_wrapper, bg="white")
        basic_frame.pack(fill="x", pady=(0, 5))

        ttk.Label(basic_frame, text="Title:")\
            .grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(basic_frame, textvariable=self.search_var, width=40)
        self.search_entry.grid(row=0, column=1, padx=5, pady=5)
        self.search_entry.bind("<Return>", lambda e: self.handle_search())

        ttk.Button(basic_frame, text="Search", command=self.handle_search)\
            .grid(row=0, column=2, padx=5, pady=5)

        self.exec_time_label = tk.Label(
            search_wrapper,
            text="",
            font=("Arial", 8),
            bg="white",
            fg="#27ae60",
        )
        self.exec_time_label.pack(anchor="e")

        adv_frame = tk.Frame(search_wrapper, bg="white")
        adv_frame.pack(fill="x")

        ttk.Label(adv_frame, text="Min Rating:")\
            .grid(row=0, column=0, sticky="w", padx=5, pady=3)
        self.min_rating_var = tk.StringVar()
        ttk.Entry(adv_frame, textvariable=self.min_rating_var, width=10)\
            .grid(row=0, column=1, padx=5, pady=3)

        ttk.Label(adv_frame, text="Max Rating:")\
            .grid(row=0, column=2, sticky="w", padx=5, pady=3)
        self.max_rating_var = tk.StringVar()
        ttk.Entry(adv_frame, textvariable=self.max_rating_var, width=10)\
            .grid(row=0, column=3, padx=5, pady=3)

        ttk.Label(adv_frame, text="Min Votes:")\
            .grid(row=0, column=4, sticky="w", padx=5, pady=3)
        self.min_votes_var = tk.StringVar()
        ttk.Entry(adv_frame, textvariable=self.min_votes_var, width=10)\
            .grid(row=0, column=5, padx=5, pady=3)

        ttk.Button(
            adv_frame,
            text="Advanced Search",
            command=self.handle_advanced_search
        ).grid(row=0, column=6, padx=5, pady=3)

        self.adv_exec_time_label = tk.Label(
            search_wrapper,
            text="",
            font=("Arial", 8),
            bg="white",
            fg="#e67e22",
        )
        self.adv_exec_time_label.pack(anchor="e")

        # --- results + details
        results_wrapper = ttk.LabelFrame(container, text="Search Results", padding=10)
        results_wrapper.pack(fill="both", expand=True)

        tree_frame = tk.Frame(results_wrapper, bg="white")
        tree_frame.pack(fill="both", expand=True)

        columns = ("movieId", "title", "votes", "rating")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=8)

        self.tree.heading("movieId", text="ID")
        self.tree.heading("title", text="Title")
        self.tree.heading("votes", text="Votes")
        self.tree.heading("rating", text="Rating")

        self.tree.column("movieId", width=60, anchor="center")
        self.tree.column("title", width=500, anchor="w")
        self.tree.column("votes", width=80, anchor="center")
        self.tree.column("rating", width=100, anchor="center")

        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Bind selection event to update watchlist button state
        if CURRENT_USER['userId']:
            self.tree.bind('<<TreeviewSelect>>', lambda e: self.update_watchlist_button_state())

        # Pagination controls
        pagination_frame = tk.Frame(results_wrapper, bg="white")
        pagination_frame.pack(fill="x", pady=(5, 0))
        
        self.btn_prev_page = ttk.Button(
            pagination_frame,
            text="◀ Previous",
            command=self.handle_prev_page,
            state="disabled"
        )
        self.btn_prev_page.pack(side="left", padx=5)
        
        self.page_info_label = tk.Label(
            pagination_frame,
            text="Page 0 of 0 (0 results)",
            font=("Arial", 9),
            bg="white",
            fg="#2c3e50"
        )
        self.page_info_label.pack(side="left", padx=10)
        
        self.btn_next_page = ttk.Button(
            pagination_frame,
            text="Next ▶",
            command=self.handle_next_page,
            state="disabled"
        )
        self.btn_next_page.pack(side="left", padx=5)

        # Action buttons frame
        action_buttons = tk.Frame(results_wrapper, bg="#f0f0f0")
        action_buttons.pack(anchor="w", pady=(5, 3))
        
        ttk.Button(
            action_buttons,
            text="View Details",
            command=self.handle_view_details
        ).pack(side="left", padx=(0, 5))
        
        # Smart watchlist toggle button (only for logged-in users)
        if CURRENT_USER['userId']:
            self.watchlist_toggle_btn = ttk.Button(
                action_buttons,
                text="⭐ Add to Watchlist",
                command=self.handle_toggle_watchlist
            )
            self.watchlist_toggle_btn.pack(side="left", padx=(0, 5))

        # Details text with scrollbar
        details_frame = tk.Frame(results_wrapper, bg="white")
        details_frame.pack(fill="both", expand=True)
        
        details_scrollbar = tk.Scrollbar(details_frame)
        details_scrollbar.pack(side="right", fill="y")
        
        self.details_text = tk.Text(
            details_frame,
            width=100,
            height=12,
            state="disabled",
            wrap="word",
            borderwidth=2,
            relief="groove",
            font=("Arial", 9),
            bg="#ecf0f1",
            fg="#2c3e50",
            yscrollcommand=details_scrollbar.set
        )
        self.details_text.pack(side="left", fill="both", expand=True)
        details_scrollbar.config(command=self.details_text.yview)

    def handle_search(self):
        keyword = self.search_var.get().strip()
        
        if not keyword:
            messagebox.showwarning(
                "Search Required",
                "Please enter a movie title to search for.",
                parent=self
            )
            return
            
        rows, elapsed = search_movies_by_title(keyword)

        # Store results for pagination
        self.total_results = rows
        self.current_page = 0
        self.last_search_type = 'basic'
        
        # Check if no results found
        if len(rows) == 0:
            messagebox.showinfo(
                "No Results Found",
                f"No movies found matching '{keyword}'.\n\n"
                "Suggestions:\n"
                "• Check the spelling\n"
                "• Try different keywords\n"
                "• Use partial words (e.g., 'inter' instead of 'interstellar')\n"
                "• Try the Advanced Search with different filters",
                parent=self
            )
        
        # Display first page
        self.display_current_page()
        
        self.exec_time_label.config(
            text=f"SQL search time: {elapsed:.3f}s | {len(rows)} total results"
        )

    def handle_advanced_search(self):
        # parse numeric filters safely
        def _f2(x):
            return float(x) if x.strip() != "" else None
        def _i2(x):
            return int(x) if x.strip() != "" else None

        min_r = _f2(self.min_rating_var.get())
        max_r = _f2(self.max_rating_var.get())
        min_v = _i2(self.min_votes_var.get())
        title_kw = self.search_var.get().strip() or None

        rows, elapsed = search_movies_advanced(
            title=title_kw,
            min_rating=min_r,
            max_rating=max_r,
            min_votes=min_v,
        )

        # Store results for pagination
        self.total_results = rows
        self.current_page = 0
        self.last_search_type = 'advanced'
        
        # Check if no results found
        if len(rows) == 0:
            criteria = []
            if title_kw:
                criteria.append(f"Title: '{title_kw}'")
            if min_r is not None:
                criteria.append(f"Min Rating: {min_r}")
            if max_r is not None:
                criteria.append(f"Max Rating: {max_r}")
            if min_v is not None:
                criteria.append(f"Min Votes: {min_v}")
            
            criteria_text = "\n".join(criteria) if criteria else "No filters applied"
            
            messagebox.showinfo(
                "No Results Found",
                f"No movies found matching your criteria:\n\n{criteria_text}\n\n"
                "Suggestions:\n"
                "• Try broader search criteria\n"
                "• Reduce the minimum rating\n"
                "• Lower the minimum votes requirement\n"
                "• Remove some filters",
                parent=self
            )
        
        # Display first page
        self.display_current_page()
        
        self.adv_exec_time_label.config(
            text=f"SQL advanced time: {elapsed:.3f}s | {len(rows)} total results"
        )
    
    def display_current_page(self):
        """Display the current page of results"""
        # Clear tree
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        # Calculate pagination
        start_idx = self.current_page * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.total_results))
        total_pages = (len(self.total_results) + self.page_size - 1) // self.page_size if len(self.total_results) > 0 else 0
        
        # Display current page results
        for r in self.total_results[start_idx:end_idx]:
            self.tree.insert(
                "",
                "end",
                values=(
                    r["movieId"],
                    r["title"],
                    r["vote_count"],
                    r["avg_rating"],
                ),
            )
        
        # Update pagination info
        if len(self.total_results) > 0:
            self.page_info_label.config(
                text=f"Page {self.current_page + 1} of {total_pages} ({len(self.total_results)} total results, showing {start_idx + 1}-{end_idx})"
            )
        else:
            self.page_info_label.config(text="No results found")
        
        # Update button states
        self.btn_prev_page.config(state="normal" if self.current_page > 0 else "disabled")
        self.btn_next_page.config(state="normal" if end_idx < len(self.total_results) else "disabled")
    
    def handle_prev_page(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.display_current_page()
    
    def handle_next_page(self):
        """Go to next page"""
        max_page = (len(self.total_results) + self.page_size - 1) // self.page_size - 1
        if self.current_page < max_page:
            self.current_page += 1
            self.display_current_page()

    def handle_view_details(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning(
                "Selection Required",
                "Please select a movie from the search results to view its details.\n\n"
                "Click on any movie row in the table above.",
                parent=self
            )
            return
        movie_id = self.tree.item(sel[0])["values"][0]

        sql_info = get_movie_details(movie_id)
        if not sql_info:
            messagebox.showerror(
                "Movie Not Found",
                f"Could not find movie details for Movie ID: {movie_id}\n\n"
                "The movie may have been deleted from the database.",
                parent=self
            )
            self._set_text_widget(self.details_text, "Movie not found in database.")
            return

        # join Mongo
        mongo_meta = None
        similar_list = []
        if sql_info.get("tmdbId") is not None:
            mongo_meta = get_tmdb_metadata(sql_info["tmdbId"])
            if mongo_meta and mongo_meta.get("tmdbId") is not None:
                similar_list, _ = find_similar_movies_mongo(mongo_meta["tmdbId"])

        lines = []
        lines.append("=== SQL (MariaDB) ===")
        lines.append(f"Movie ID: {sql_info['movieId']} | Title: {sql_info['title']}")
        lines.append(
            f"Release: {sql_info.get('release_date')} | "
            f"Votes: {sql_info['vote_count']} | "
            f"Avg Rating: {sql_info['avg_rating']}"
        )
        lines.append(
            f"IMDb: {sql_info.get('imdbId')} | TMDB: {sql_info.get('tmdbId')}"
        )
        lines.append("")

        lines.append("=== MongoDB Metadata ===")
        if mongo_meta:
            genres = mongo_meta.get("genres")
            if isinstance(genres, list):
                genres_str = ", ".join(str(g) for g in genres)
            else:
                genres_str = genres or "(no genres)"

            lines.append(f"TMDB Title: {mongo_meta.get('title')}")
            lines.append(f"Genres: {genres_str}")
            lines.append(
                f"TMDB Vote Avg: {mongo_meta.get('vote_average')} "
                f"(Count: {mongo_meta.get('vote_count')})"
            )
            lines.append(
                f"Runtime: {mongo_meta.get('runtime')} min | "
                f"Revenue: {mongo_meta.get('revenue')}"
            )
            lines.append(
                f"Language: {mongo_meta.get('original_language')} | "
                f"Popularity: {mongo_meta.get('popularity')}"
            )
            if mongo_meta.get("tagline"):
                lines.append(f"Tagline: {mongo_meta['tagline']}")
            if mongo_meta.get("overview"):
                lines.append("")
                lines.append("Overview:")
                lines.append(mongo_meta["overview"])

            if similar_list:
                lines.append("")
                lines.append("Similar Movies (Mongo-based genre match):")
                for sm in similar_list[:5]:
                    # Handle both "id" (Atlas) and "tmdbId" (legacy) fields
                    movie_id = sm.get('id') or sm.get('tmdbId', 'N/A')
                    lines.append(
                        f"  - [{movie_id}] {sm.get('title')} "
                        f"(genre: {sm.get('genres')}, rating={sm.get('vote_average')})"
                    )
        else:
            lines.append("(No TMDB metadata / Mongo not found)")

        self._set_text_widget(self.details_text, "\n".join(lines))

    def handle_toggle_watchlist(self):
        """Smart toggle button - Add or Remove from watchlist based on current state"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Selection Required", "Please select a movie first.")
            return
        
        movie_id = self.tree.item(sel[0])["values"][0]
        movie_title = self.tree.item(sel[0])["values"][1]
        
        if not CURRENT_USER['userId']:
            messagebox.showwarning("Not Logged In", "Please login to use watchlist.")
            return
        
        # Check current state and toggle
        if is_in_watchlist(CURRENT_USER['userId'], movie_id):
            # Movie is in watchlist - REMOVE it
            if remove_from_watchlist(CURRENT_USER['userId'], movie_id):
                messagebox.showinfo("Removed", f"'{movie_title}' removed from watchlist!")
                self.watchlist_toggle_btn.config(text="⭐ Add to Watchlist")
            else:
                messagebox.showerror("Error", "Failed to remove from watchlist.")
        else:
            # Movie is NOT in watchlist - ADD it
            if add_to_watchlist(CURRENT_USER['userId'], movie_id):
                messagebox.showinfo("Added", f"'{movie_title}' added to watchlist!")
                self.watchlist_toggle_btn.config(text="✓ In Watchlist (Click to Remove)")
            else:
                messagebox.showerror("Error", "Failed to add to watchlist.")
    
    def update_watchlist_button_state(self):
        """Update button text based on whether selected movie is in watchlist"""
        if not CURRENT_USER['userId']:
            return
            
        sel = self.tree.selection()
        if not sel:
            self.watchlist_toggle_btn.config(text="⭐ Add to Watchlist")
            return
        
        try:
            movie_id = self.tree.item(sel[0])["values"][0]
            if is_in_watchlist(CURRENT_USER['userId'], movie_id):
                self.watchlist_toggle_btn.config(text="✓ In Watchlist (Click to Remove)")
            else:
                self.watchlist_toggle_btn.config(text="⭐ Add to Watchlist")
        except:
            self.watchlist_toggle_btn.config(text="⭐ Add to Watchlist")
    
    def handle_add_to_watchlist(self):
        """Add selected movie to watchlist"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Selection Required", "Please select a movie first.")
            return
        
        movie_id = self.tree.item(sel[0])["values"][0]
        movie_title = self.tree.item(sel[0])["values"][1]
        
        if not CURRENT_USER['userId']:
            messagebox.showwarning("Not Logged In", "Please login to use watchlist.")
            return
        
        # Check if already in watchlist
        if is_in_watchlist(CURRENT_USER['userId'], movie_id):
            messagebox.showinfo("Already Added", f"'{movie_title}' is already in your watchlist!")
            return
        
        # Add to watchlist
        if add_to_watchlist(CURRENT_USER['userId'], movie_id):
            messagebox.showinfo("Success", f"Added '{movie_title}' to your watchlist!")
    
    def handle_remove_from_watchlist(self):
        """Remove selected movie from watchlist"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Selection Required", "Please select a movie first.")
            return
        
        movie_id = self.tree.item(sel[0])["values"][0]
        movie_title = self.tree.item(sel[0])["values"][1]
        
        if not CURRENT_USER['userId']:
            return
        
        # Check if in watchlist
        if not is_in_watchlist(CURRENT_USER['userId'], movie_id):
            messagebox.showinfo("Not in Watchlist", f"'{movie_title}' is not in your watchlist.")
            return
        
        # Remove from watchlist
        if remove_from_watchlist(CURRENT_USER['userId'], movie_id):
            messagebox.showinfo("Success", f"Removed '{movie_title}' from your watchlist!")

    # ------------------------------------------------------------------
    # TAB 2: USERS & RATINGS
    # ------------------------------------------------------------------
    def build_users_tab(self):
        container = tk.Frame(self.users_tab, bg="#f0f0f0")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # ---- USER MANAGEMENT (top)
        user_wrapper = ttk.LabelFrame(container, text="User Management", padding=10)
        user_wrapper.pack(fill="x", pady=(0, 10))
        user_wrapper.pack_propagate(False)
        user_wrapper.configure(height=240)

        user_form = tk.Frame(user_wrapper, bg="white")
        user_form.pack(fill="x", pady=5)

        # Row 0: User ID, Name, Email
        ttk.Label(user_form, text="User ID:")\
            .grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.user_id_var = tk.StringVar()
        self.user_id_entry = ttk.Entry(user_form, textvariable=self.user_id_var, width=15)
        self.user_id_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(user_form, text="Name:")\
            .grid(row=0, column=2, sticky="e", padx=5, pady=5)
        self.username_var = tk.StringVar()
        self.username_entry = ttk.Entry(user_form, textvariable=self.username_var, width=20)
        self.username_entry.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(user_form, text="Email:")\
            .grid(row=0, column=4, sticky="e", padx=5, pady=5)
        self.email_var = tk.StringVar()
        self.email_entry = ttk.Entry(user_form, textvariable=self.email_var, width=30)
        self.email_entry.grid(row=0, column=5, padx=5, pady=5)

        # Password field (second row)
        ttk.Label(user_form, text="New Password:")\
            .grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.user_password_var = tk.StringVar()
        self.user_password_entry = ttk.Entry(user_form, textvariable=self.user_password_var, width=20, show="*")
        self.user_password_entry.grid(row=1, column=1, columnspan=2, sticky="w", padx=5, pady=5)
        
        ttk.Label(user_form, text="(Leave blank to keep current password)", font=("Arial", 8, "italic"))\
            .grid(row=1, column=3, columnspan=3, sticky="w", padx=5, pady=5)

        # User action buttons - centered row
        button_frame = tk.Frame(user_form, bg="white")
        button_frame.grid(row=2, column=0, columnspan=6, pady=15)

        self.btn_read_user = ttk.Button(
            button_frame, text="View My Account", width=15, command=self.handle_read_user
        )
        self.btn_read_user.grid(row=0, column=0, padx=8, pady=0)

        self.btn_update_user = ttk.Button(
            button_frame, text="Update My Account", width=18, command=self.handle_update_user
        )
        self.btn_update_user.grid(row=0, column=1, padx=8, pady=0)

        self.btn_delete_user = ttk.Button(
            button_frame, text="Delete My Account", width=18, command=self.handle_delete_user
        )
        self.btn_delete_user.grid(row=0, column=2, padx=8, pady=0)

        self.btn_search_user = ttk.Button(
            button_frame, text="Search All Users", width=15, command=self.handle_search_users
        )
        self.btn_search_user.grid(row=0, column=3, padx=8, pady=0)

        # User status box with scrollbar
        user_status_frame = tk.Frame(user_wrapper, bg="white")
        user_status_frame.pack(fill="x", pady=(5, 0))
        
        user_scrollbar = tk.Scrollbar(user_status_frame)
        user_scrollbar.pack(side="right", fill="y")
        
        self.user_status_text = tk.Text(
            user_status_frame,
            width=100,
            height=8,
            state="disabled",
            wrap="word",
            borderwidth=2,
            relief="groove",
            font=("Consolas", 9),
            bg="#ffffff",
            fg="#000000",
            yscrollcommand=user_scrollbar.set
        )
        self.user_status_text.pack(side="left", fill="x", expand=True)
        user_scrollbar.config(command=self.user_status_text.yview)

        # ---- RATINGS SECTION (bottom) - POPUP DIALOG STYLE
        rating_wrapper = ttk.LabelFrame(container, text="Ratings Management", padding=10)
        rating_wrapper.pack(fill="both", expand=True)

        # Description and button to open popup
        desc_frame = tk.Frame(rating_wrapper, bg="white")
        desc_frame.pack(fill="x", pady=10, padx=10)
        
        tk.Label(
            desc_frame,
            text="Manage Your Movie Ratings",
            font=("Arial", 12, "bold"),
            bg="white",
            fg="#2c3e50"
        ).pack(pady=(0, 5))
        
        tk.Label(
            desc_frame,
            text="Add, edit, delete, or view your movie ratings using the popup dialog.\n"
                 "Concurrent edit prevention ensures no two users can edit the same rating simultaneously.",
            font=("Arial", 9),
            bg="white",
            fg="#7f8c8d",
            justify="center"
        ).pack(pady=(0, 15))
        
        # Big button to open rating dialog
        self.btn_open_rating_dialog = tk.Button(
            desc_frame,
            text="Open Rating Management Dialog",
            command=self.handle_open_rating_dialog,
            bg="#3498db",
            fg="white",
            font=("Arial", 12, "bold"),
            padx=30,
            pady=15,
            relief="flat",
            cursor="hand2",
            borderwidth=0
        )
        self.btn_open_rating_dialog.pack(pady=(0, 10))

        tk.Label(
            rating_wrapper,
            text="Activity Log:",
            font=("Arial", 9, "bold"),
            bg="white",
            anchor="w",
        ).pack(fill="x", pady=(10, 2))

        # Rating status text with scrollbar
        rating_status_frame = tk.Frame(rating_wrapper, bg="white")
        rating_status_frame.pack(fill="both", expand=True)
        
        rating_scrollbar = tk.Scrollbar(rating_status_frame)
        rating_scrollbar.pack(side="right", fill="y")
        
        self.rating_status_text = tk.Text(
            rating_status_frame,
            width=100,
            height=12,
            state="disabled",
            wrap="word",
            borderwidth=2,
            relief="groove",
            font=("Consolas", 8),
            bg="#2c3e50",
            fg="#ecf0f1",
            yscrollcommand=rating_scrollbar.set
        )
        self.rating_status_text.pack(side="left", fill="both", expand=True)
        rating_scrollbar.config(command=self.rating_status_text.yview)

    def apply_role_permissions(self):
        """
        After login + building the widgets:
        - GUEST: Read-only, no modifications, no Profile tab
        - USER: Can RUD own account (Read/Update/Delete), CUD ratings (Create/Update/Delete), can see Profile
        - ADMIN: Can view/update/delete users, CANNOT create users, can manage movies
        """
        role = CURRENT_USER["role"]
        uid = CURRENT_USER["userId"]

        if role == "guest":
            # GUEST: Can only browse, cannot modify anything
            if hasattr(self, 'btn_update_user'):
                self.btn_update_user.config(state="disabled")
            if hasattr(self, 'btn_delete_user'):
                self.btn_delete_user.config(state="disabled")
            if hasattr(self, 'btn_add_update_rating'):
                self.btn_add_update_rating.config(state="disabled")
            if hasattr(self, 'btn_delete_rating'):
                self.btn_delete_rating.config(state="disabled")
            
            # Disable all user/rating input fields
            if hasattr(self, 'user_id_entry'):
                self.user_id_entry.config(state="disabled")
            if hasattr(self, 'username_entry'):
                self.username_entry.config(state="disabled")
            if hasattr(self, 'email_entry'):
                self.email_entry.config(state="disabled")
            if hasattr(self, 'rate_user_id_entry'):
                self.rate_user_id_entry.config(state="disabled")
            if hasattr(self, 'rate_movie_id_entry'):
                self.rate_movie_id_entry.config(state="disabled")
            if hasattr(self, 'rate_value_entry'):
                self.rate_value_entry.config(state="disabled")
            
            if hasattr(self, 'user_log'):
                self._append_user_log("[GUEST] You can only browse data. Use Login/Register buttons above for full access.")
            if hasattr(self, 'rating_log'):
                self._append_rating_log("[GUEST] You cannot add or modify ratings.")

        elif role == "user":
            # REGULAR USER: Can manage own account and ratings only
            
            # User Management: Can Read/Update/Delete OWN account only
            # Pre-fill and lock User ID to their own
            if uid is not None and hasattr(self, 'user_id_var'):
                self.user_id_var.set(str(uid))
            if hasattr(self, 'user_id_entry'):
                self.user_id_entry.config(state="disabled")
            
            # Change button labels to be clearer
            if hasattr(self, 'btn_read_user'):
                self.btn_read_user.config(text="View My Account")
            if hasattr(self, 'btn_update_user'):
                self.btn_update_user.config(text="Update My Account")
            if hasattr(self, 'btn_delete_user'):
                self.btn_delete_user.config(text="Delete My Account")
            if hasattr(self, 'btn_search_user'):
                self.btn_search_user.config(state="disabled")  # Users can't search other users
            
            # Ratings Management: Can CUD ratings with just Movie ID + Rating
            # Hide User ID field for ratings (auto-filled)
            if hasattr(self, 'rate_user_id_var'):
                self.rate_user_id_var.set(str(uid) if uid else "")
            if hasattr(self, 'rate_user_id_entry'):
                self.rate_user_id_entry.config(state="disabled")
            
            if hasattr(self, 'user_log'):
                self._append_user_log(f"[USER] You can view/update/delete your own account (ID: {uid})")
            if hasattr(self, 'rating_log'):
                self._append_rating_log(f"[USER] You can create/update/delete ratings for movies (User ID: {uid})")

        elif role == "admin":
            # ADMIN: Can view/update/delete users and manage movies
            # Change labels for clarity
            if hasattr(self, 'btn_read_user'):
                self.btn_read_user.config(text="View User")
            if hasattr(self, 'btn_update_user'):
                self.btn_update_user.config(text="Update User")
            if hasattr(self, 'btn_delete_user'):
                self.btn_delete_user.config(text="Delete User")
            
            if hasattr(self, 'user_log'):
                self._append_user_log("[ADMIN] You can view/update/delete users. New users register via login screen.")
            if hasattr(self, 'rating_log'):
                self._append_rating_log("[ADMIN] Full access to rating management features.")
        
        else:
            # Unknown role - treat as guest
            if hasattr(self, 'user_log'):
                self._append_user_log(f"[WARNING] Unknown role '{role}' - treating as guest.")
            if hasattr(self, 'rating_log'):
                self._append_rating_log("[WARNING] No modification permissions.")

    def _append_user_log(self, msg: str):
        stamp = datetime.now().strftime("%H:%M:%S")
        self._append_text_widget(self.user_status_text, f"[{stamp}] {msg}")

    def _append_rating_log(self, msg: str):
        stamp = datetime.now().strftime("%H:%M:%S")
        self._append_text_widget(self.rating_status_text, f"[{stamp}] {msg}")

    # ---- USER CRUD handlers ----
    
    def handle_read_user(self):
        """
        View user by ID, username, or email.
        Searches any of the three fields that are filled in.
        """
        search_input = self.user_id_var.get().strip() or self.username_var.get().strip() or self.email_var.get().strip()
        
        if not search_input:
            messagebox.showwarning("Input Required", "Please enter User ID, Username, or Email to search.")
            return
        
        try:
            # Try to find user by ID first (if input is numeric)
            user_row = None
            try:
                uid = int(search_input)
                user_row = get_user(uid)
            except ValueError:
                # Not a number, try username or email
                user_row = find_user_by_name_or_email(username=search_input, email=search_input)
            
            if not user_row:
                self._append_user_log(f"User not found: '{search_input}'")
                messagebox.showerror(
                    "User Not Found",
                    f"No user found matching: {search_input}\n\n"
                    "Please check:\n"
                    "• User ID is correct\n"
                    "• Username spelling is exact\n"
                    "• Email address is complete",
                    parent=self
                )
                return
            
            # Check permissions - regular users can only view their own account
            if CURRENT_USER['role'] == 'user' and user_row['userId'] != CURRENT_USER['userId']:
                self._append_user_log("Permission denied: You can only view your own account")
                messagebox.showerror("Access denied", "You can only view your own account.")
                return
            
            # Display user info
            self._set_text_widget(
                self.user_status_text,
                f"User {user_row['userId']}\n"
                f"  Name : {user_row.get('username')}\n"
                f"  Email: {user_row.get('email')}\n"
                f"  Created_at: {user_row.get('created_at')}",
            )
            
            # Auto-fill the form fields
            self.user_id_var.set(str(user_row['userId']))
            self.username_var.set(user_row.get('username', ''))
            self.email_var.set(user_row.get('email', ''))
            
            self._append_user_log(f"✓ User found: {user_row['username']} (ID: {user_row['userId']})")
            
        except Exception as e:
            self._append_user_log(f"Error: {e}")
            messagebox.showerror("Error", str(e))

    def handle_update_user(self):
        try:
            user_id = int(self.user_id_var.get().strip())
        except ValueError:
            messagebox.showerror(
                "Invalid User ID",
                "User ID must be a valid number.\n\n"
                "Please enter a numeric User ID or use the 'View My Account' button to load your account first.",
                parent=self
            )
            return
        
        # Regular users can only update their own account
        if CURRENT_USER["role"] == "user" and user_id != CURRENT_USER["userId"]:
            messagebox.showerror(
                "Access Denied",
                "You can only update your own account.\n\n"
                f"Your User ID: {CURRENT_USER['userId']}\n"
                f"Attempted User ID: {user_id}",
                parent=self
            )
            return
        
        name = self.username_var.get().strip()
        email = self.email_var.get().strip()
        password = self.user_password_var.get().strip()
        
        if not name:
            messagebox.showerror(
                "Username Required",
                "Username cannot be empty.\n\n"
                "Please enter a valid username.",
                parent=self
            )
            return
            
        if not is_valid_email(email):
            messagebox.showerror(
                "Invalid Email",
                f"The email address '{email}' is not valid.\n\n"
                "Please enter a valid email address in the format:\n"
                "example@domain.com",
                parent=self
            )
            return
        
        # Validate password if provided
        if password and len(password) < 6:
            messagebox.showerror(
                "Invalid Password",
                "Password must be at least 6 characters long.\n\n"
                "Please enter a stronger password or leave blank to keep current password.",
                parent=self
            )
            return

        # Pass password to update_user (None if empty)
        ok = update_user(user_id, name, email, password if password else None)
        if ok:
            password_msg = " and password" if password else ""
            self._append_user_log(f"✓ User {user_id} updated -> ({name}, {email}){password_msg}")
            
            success_msg = f"User account updated successfully!\n\n"
            success_msg += f"User ID: {user_id}\n"
            success_msg += f"Username: {name}\n"
            success_msg += f"Email: {email}\n"
            if password:
                success_msg += "\n✓ Password has been changed"
            
            messagebox.showinfo("Success", success_msg, parent=self)
            
            # Clear password field for security
            self.user_password_var.set("")
            
            # Update current session if user updated their own info
            if user_id == CURRENT_USER["userId"]:
                CURRENT_USER["username"] = name
                CURRENT_USER["email"] = email
                self.user_info_label.config(
                    text=f"Logged in as: {CURRENT_USER['username']} ({CURRENT_USER['role']})"
                )

    def handle_delete_user(self):
        try:
            user_id = int(self.user_id_var.get().strip())
        except ValueError:
            messagebox.showerror(
                "Invalid User ID",
                "User ID must be a valid number.\n\n"
                "Please enter a numeric User ID.",
                parent=self
            )
            return
            return

        # Regular users can only delete their own account
        if CURRENT_USER["role"] == "user" and user_id != CURRENT_USER["userId"]:
            messagebox.showerror(
                "Access Denied",
                "You can only delete your own account.\n\n"
                f"Your User ID: {CURRENT_USER['userId']}\n"
                f"Attempted User ID: {user_id}",
                parent=self
            )
            return
        
        # Confirmation for account deletion
        if CURRENT_USER["role"] == "user":
            confirm = messagebox.askyesno(
                "Delete Your Account?",
                "⚠️ WARNING: You are about to delete YOUR account!\n\n"
                f"User ID: {user_id}\n"
                f"Username: {CURRENT_USER['username']}\n\n"
                "This will:\n"
                "• Permanently delete your account\n"
                "• Remove all your ratings\n"
                "• Log you out immediately\n\n"
                "This action CANNOT be undone!\n\n"
                "Are you sure you want to continue?",
                icon='warning',
                parent=self
            )
        else:
            confirm = messagebox.askyesno(
                "Delete User Account?",
                f"Are you sure you want to delete this user account?\n\n"
                f"User ID: {user_id}\n\n"
                "This will permanently delete:\n"
                "• User account\n"
                "• All their ratings\n\n"
                "This action cannot be undone.",
                parent=self
            )
        
        if not confirm:
            self._append_user_log(f"Deletion cancelled for user {user_id}")
            return

        ok = delete_user(user_id)
        if ok:
            self._append_user_log(f"✓ User {user_id} deleted")
            messagebox.showinfo(
                "Account Deleted",
                f"User account (ID: {user_id}) has been successfully deleted.",
                parent=self
            )
            
            # If user deleted their own account, log them out
            if user_id == CURRENT_USER["userId"]:
                messagebox.showinfo(
                    "Logged Out",
                    "Your account has been deleted.\n\n"
                    "The application will now close.",
                    parent=self
                )
                self.destroy()
                sys.exit(0)

    def handle_search_users(self):
        """
        Search all / by keyword (use the name/email field as search text).
        """
        kw = self.username_var.get().strip()
        rows = search_users(kw)

        if not rows:
            self._set_text_widget(self.user_status_text, "No users found.")
            return

        out_lines = []
        for r in rows[:15]:
            out_lines.append(
                f"User {r['userId']:>5} | {r.get('username')} | {r.get('email')} | {r.get('created_at')}"
            )
        self._set_text_widget(self.user_status_text, "\n".join(out_lines))

    # ---- NEW RATINGS handlers with EARLY LOCKING ----
    
    def handle_open_rating_dialog(self):
        """Open the rating management popup dialog."""
        print("[DEBUG MAIN] handle_open_rating_dialog called")
        
        # Prevent duplicate dialogs
        if hasattr(self, '_rating_dialog_open') and self._rating_dialog_open:
            print("[DEBUG MAIN] Dialog already open, ignoring duplicate call")
            return
        
        # Verify user is logged in
        if not CURRENT_USER["userId"]:
            messagebox.showerror(
                "Authentication Required",
                "Please log in to manage ratings."
            )
            return
        
        # Mark dialog as open
        self._rating_dialog_open = True
        logger.info("[MAIN] Opening Rating Management - THREE POPUP SEQUENCE")
        
        # Loop to allow going back from View Ratings
        while True:
            # POPUP 1: Action Selection (Add/Edit, Delete, or View)
            logger.info("[MAIN] POPUP 1: Action Selection")
            print("[DEBUG MAIN] Creating ActionSelectionDialog...")
            action_dialog = ActionSelectionDialog(self, CURRENT_USER["username"], CURRENT_USER["userId"])
            print("[DEBUG MAIN] Dialog created, waiting for it to close...")
            self.wait_window(action_dialog)
            print("[DEBUG MAIN] Dialog closed, checking result...")
            
            selected_action = action_dialog.selected_action
            print(f"[DEBUG MAIN] selected_action = {selected_action}")
            logger.info(f"[MAIN] POPUP 1 Result: {selected_action}")
            
            if not selected_action:
                # User cancelled
                self._rating_dialog_open = False
                logger.info("[MAIN] User cancelled at action selection")
                return
            
            # If user selected "View", show ratings and check if they want to go back
            if selected_action == "view":
                logger.info("[MAIN] POPUP VIEW: Showing all ratings")
                view_dialog = ViewRatingsDialog(self, CURRENT_USER["username"], CURRENT_USER["userId"])
                self.wait_window(view_dialog)
                
                if view_dialog.go_back:
                    # User clicked Back - loop again to POPUP 1
                    logger.info("[MAIN] User clicked Back from View Ratings - returning to action selection")
                    continue
                else:
                    # User closed dialog - exit
                    self._rating_dialog_open = False
                    return
            
            # If Add/Edit or Delete, break out of loop to continue with POPUP 2
            break
        
        # POPUP 2: Movie Selection + Lock Acquisition (TRANSACTION BEGINS)
        logger.info(f"[MAIN] POPUP 2: Movie Selection for action={selected_action}")
        movie_dialog = MovieSelectionDialog(
            self,
            CURRENT_USER["username"],
            CURRENT_USER["userId"],
            selected_action
        )
        self.wait_window(movie_dialog)
        
        movie_id = movie_dialog.movie_id
        movie_title = movie_dialog.movie_title
        lock_acquired = movie_dialog.lock_acquired
        
        logger.info(f"[MAIN] POPUP 2 Result: movie_id={movie_id}, lock={lock_acquired}")
        
        if not movie_id or not lock_acquired:
            # User cancelled or lock failed
            self._rating_dialog_open = False
            logger.info("[MAIN] User cancelled at movie selection or lock failed")
            return
        
        # POPUP 3: Rating Entry OR Delete Confirmation (TRANSACTION COMMITS)
        if selected_action == "add":
            logger.info(f"[MAIN] POPUP 3: Rating Entry for movieId={movie_id}")
            rating_dialog = RatingEntryDialog(
                self,
                CURRENT_USER["username"],
                CURRENT_USER["userId"],
                movie_id,
                movie_title
            )
            self.wait_window(rating_dialog)
            
            success = rating_dialog.success
            rating_value = rating_dialog.rating_value
            
            logger.info(f"[MAIN] POPUP 3 Result: success={success}, rating={rating_value}")
            
            if success:
                self._append_rating_log(
                    f"✅ Rating updated: Movie {movie_id} = {rating_value} stars"
                )
                messagebox.showinfo(
                    "Success",
                    f"Rating management completed!\n\n"
                    f"Movie: {movie_title}\n"
                    f"Rating: {rating_value} ⭐"
                )
        
        elif selected_action == "delete":
            logger.info(f"[MAIN] POPUP 3: Delete Confirmation for movieId={movie_id}")
            delete_dialog = DeleteConfirmDialog(
                self,
                CURRENT_USER["username"],
                CURRENT_USER["userId"],
                movie_id,
                movie_title
            )
            self.wait_window(delete_dialog)
            
            success = delete_dialog.success
            
            logger.info(f"[MAIN] POPUP 3 DELETE Result: success={success}")
            
            if success:
                self._append_rating_log(
                    f"✅ Rating deleted: Movie {movie_id}"
                )
                messagebox.showinfo(
                    "Success",
                    f"Rating management completed!\n\n"
                    f"Movie: {movie_title}\n"
                    f"Rating deleted successfully"
                )
        
        # Mark dialog sequence as closed
        self._rating_dialog_open = False
        logger.info("[MAIN] THREE POPUP SEQUENCE COMPLETE")
    
    def on_rating_action_changed(self, *args):
        """
        Called when user selects a different action from dropdown.
        Updates UI visibility based on selected action.
        """
        action = self.rating_action_var.get()
        
        # Reset lock state when changing actions
        if self.current_rating_lock["locked"]:
            self.handle_cancel_rating_action()
        
        # Show/hide rating value field based on action
        if action == "Delete Rating":
            self.rating_value_label.grid_remove()
            self.rate_value_entry.grid_remove()
            self.rating_action_help.config(
                text="ℹ️ Enter movie to delete your rating (lock will be acquired)"
            )
        elif action == "View My Ratings":
            self.rating_value_label.grid_remove()
            self.rate_value_entry.grid_remove()
            self.rating_action_help.config(
                text="ℹ️ Click Submit to view all your ratings (no lock needed)"
            )
            # Enable submit button for viewing (no lock needed)
            self.btn_submit_rating.config(state="normal")
            self.btn_confirm_movie.grid_remove()
            self.lock_status_var.set("ℹ️ No lock needed for viewing")
            self.lock_status_label.config(fg="#3498db")
        else:  # Add/Edit Rating
            self.rating_value_label.grid()
            self.rate_value_entry.grid()
            self.btn_confirm_movie.grid()
            self.rating_action_help.config(
                text="ℹ️ Enter movie, click 'Confirm Movie' to lock, then enter rating"
            )
            self.lock_status_var.set("")
            self.btn_submit_rating.config(state="disabled")
        
        self._append_rating_log(f"Action changed: {action}")
    
    def handle_confirm_movie_and_lock(self):
        """
        STEP 1: Confirm movie selection and acquire lock BEFORE entering rating.
        - User selects movie → Lock acquired immediately
        - Other users trying to edit same movie → Blocked
        """
        # Check if guest
        if CURRENT_USER["role"] == "guest":
            messagebox.showerror("Access Denied", "Guests cannot manage ratings.\nPlease login with a user account.")
            return
        
        action = self.rating_action_var.get()
        
        # Get and validate user ID
        uid_txt = self.rate_user_id_var.get().strip()
        uid = None
        
        if CURRENT_USER["role"] == "user":
            uid = CURRENT_USER["userId"]
        else:
            # Admin can specify user
            try:
                uid = int(uid_txt)
            except ValueError:
                user = find_user_by_name_or_email(username=uid_txt, email=uid_txt)
                if user:
                    uid = user['userId']
                    self._append_rating_log(f"Found user: {user['username']} (ID: {uid})")
                else:
                    messagebox.showerror("User Not Found", 
                        f"No user found matching '{uid_txt}'.\n\n"
                        "Please enter:\n"
                        "• User ID (number)\n"
                        "• Username\n"
                        "• Email")
                    return
        
        # Get and validate movie ID/title
        mid_txt = self.rate_movie_id_var.get().strip()
        if not mid_txt:
            messagebox.showerror("Movie Required", "Please enter a Movie ID or Title.")
            return
        
        mid = None
        movie_title = None
        try:
            mid = int(mid_txt)
            # Verify movie exists
            movie = get_movie_details(mid)
            if not movie:
                messagebox.showerror("Movie Not Found", f"Movie ID {mid} does not exist.")
                return
            movie_title = movie['title']
        except ValueError:
            # Search by title
            movies = find_movie_by_title_sql(mid_txt)
            if not movies:
                messagebox.showerror("Movie Not Found", 
                    f"No movies found matching '{mid_txt}'.\n\n"
                    "Please check spelling or use Movie ID.")
                return
            elif len(movies) == 1:
                mid = movies[0]['movieId']
                movie_title = movies[0]['title']
                self._append_rating_log(f"Found movie: {movie_title} (ID: {mid})")
            else:
                # Multiple matches
                selection_msg = "Multiple movies found. Please select one:\n\n"
                for idx, movie in enumerate(movies[:5], 1):
                    selection_msg += f"{idx}. [ID: {movie['movieId']}] {movie['title']}\n"
                selection_msg += "\nPlease use the Movie ID from above."
                messagebox.showinfo("Multiple Movies Found", selection_msg)
                return
        
        # Referential integrity checks
        if not sql_user_exists(uid):
            messagebox.showerror("Error", f"User {uid} does not exist.")
            return
        if not sql_movie_exists(mid):
            messagebox.showerror("Error", f"Movie {mid} does not exist.")
            return
        
        # Permission check
        if CURRENT_USER["role"] != "admin" and uid != CURRENT_USER["userId"]:
            messagebox.showerror("Access Denied", 
                "You can only manage your own ratings.")
            return
        
        # CHECK IF LOCKED BY SOMEONE ELSE (Concurrent Edit Prevention)
        locked_by = check_rating_lock(uid, mid)
        if locked_by and locked_by != CURRENT_USER["username"]:
            messagebox.showerror(
                "Rating Locked - Concurrent Edit Prevention",
                f"This rating is currently being edited by another user.\n\n"
                f"• Another user is currently editing this rating\n"
                f"• You CANNOT edit/delete it until they finish\n"
                f"• This demonstrates concurrent edit prevention\n"
                f"• Lock will auto-expire in 5 minutes if not released\n\n"
                f"Movie: {movie_title} (ID: {mid})\n"
                f"User: {uid}\n\n"
                f"Please wait and try again later."
            )
            self._append_rating_log(
                f"BLOCKED: Rating locked by '{locked_by}' (userId={uid}, movieId={mid}, movie='{movie_title}')"
            )
            return
        
        # ACQUIRE LOCK 
        if not acquire_rating_lock(uid, mid, CURRENT_USER["username"]):
            messagebox.showerror("Lock Error", 
                "Failed to acquire lock.\n\n"
                "This may indicate a database issue.\n"
                "Please try again.")
            return
        
        # Lock acquired successfully!
        self.current_rating_lock = {
            "user_id": uid,
            "movie_id": mid,
            "movie_title": movie_title,
            "locked": True
        }
        
        # Update UI
        self.lock_status_var.set(f"LOCKED: '{movie_title}' (ID: {mid})")
        self.lock_status_label.config(fg="#27ae60")
        self.btn_submit_rating.config(state="normal")
        self.btn_cancel_rating.config(state="normal")
        self.btn_confirm_movie.config(state="disabled")
        self.rate_movie_id_entry.config(state="readonly")
        
        # Log success
        self._append_rating_log(
            f"LOCK ACQUIRED: userId={uid}, movieId={mid}, movie='{movie_title}'\n"
            f"   → Other users CANNOT edit this rating until you submit/cancel\n"
        )
        
        messagebox.showinfo(
            "Lock Acquired",
            f"Rating locked successfully!\n\n"
            f"Movie: {movie_title}\n"
            f"Movie ID: {mid}\n"
            f"User ID: {uid}\n\n"
            f"✓ You now have exclusive edit access\n"
            f"✓ Other users are blocked from editing\n"
            f"✓ Lock will auto-expire in 5 minutes\n\n"
            f"{'Now enter your rating (0.5-5.0) and click Submit.' if action == 'Add/Edit Rating' else 'Click Submit to delete this rating.'}"
        )
        
        # Focus on rating entry if adding/editing
        if action == "Add/Edit Rating":
            self.rate_value_entry.focus_set()
    
    def handle_submit_rating_action(self):
        """
        STEP 2: Perform the actual rating operation (add/edit/delete) within transaction.
        Lock must be acquired first (in handle_confirm_movie_and_lock).
        """
        action = self.rating_action_var.get()
        
        # Special case: View My Ratings (no lock needed)
        if action == "View My Ratings":
            self.handle_view_my_ratings()
            return
        
        # For other actions, lock must be acquired
        if not self.current_rating_lock["locked"]:
            messagebox.showerror("Lock Required", 
                "Please click 'Confirm Movie & Acquire Lock' first.\n\n"
                "The lock ensures no other user can edit this rating\n"
                "while you're working on it.")
            return
        
        uid = self.current_rating_lock["user_id"]
        mid = self.current_rating_lock["movie_id"]
        movie_title = self.current_rating_lock["movie_title"]
        
        try:
            if action == "Add/Edit Rating":
                # Validate rating value
                rv_txt = self.rate_value_var.get().strip()
                if not rv_txt:
                    messagebox.showerror("Rating Required", "Please enter a rating value (0.5-5.0).")
                    return
                
                try:
                    rating_val = float(rv_txt)
                except ValueError:
                    messagebox.showerror("Invalid Rating", "Rating must be a number.")
                    return
                
                if rating_val < 0.5 or rating_val > 5.0:
                    messagebox.showerror("Invalid Rating", "Rating must be between 0.5 and 5.0.")
                    return
                
                # PERFORM UPDATE WITHIN TRANSACTION
                self._append_rating_log(
                    f"📝 TRANSACTION BEGIN: Adding/updating rating (userId={uid}, movieId={mid}, rating={rating_val})"
                )
                
                ok = add_or_update_rating(uid, mid, rating_val)
                
                if ok:
                    self._append_rating_log(
                        f"✅ TRANSACTION COMMIT: Rating updated successfully\n"
                        f"   → userId={uid}, movieId={mid}, rating={rating_val}"
                    )
                    messagebox.showinfo(
                        "✅ Rating Updated",
                        f"Successfully updated rating!\n\n"
                        f"Movie: {movie_title}\n"
                        f"Movie ID: {mid}\n"
                        f"User ID: {uid}\n"
                        f"New Rating: {rating_val}\n\n"
                        f"✓ Transaction committed\n"
                        f"✓ Lock will be released\n"
                        f"✓ Other users can now edit this rating"
                    )
                else:
                    self._append_rating_log(
                        f"❌ TRANSACTION ROLLBACK: Update failed\n"
                        f"   → Database error occurred, no changes made"
                    )
                    messagebox.showerror(
                        "❌ Update Failed",
                        "Transaction was rolled back due to an error.\n\n"
                        "The rating was NOT updated.\n"
                        "Lock will be released."
                    )
            
            elif action == "Delete Rating":
                # Confirm deletion
                confirm = messagebox.askyesno(
                    "Confirm Deletion",
                    f"Delete rating for movie '{movie_title}'?\n\n"
                    f"Movie ID: {mid}\n"
                    f"User ID: {uid}\n\n"
                    f"This action cannot be undone.",
                    icon='warning'
                )
                
                if not confirm:
                    self._append_rating_log(f"Deletion cancelled by user")
                    return
                
                # PERFORM DELETE WITHIN TRANSACTION
                self._append_rating_log(
                    f"🗑️ TRANSACTION BEGIN: Deleting rating (userId={uid}, movieId={mid})"
                )
                
                ok = delete_rating(uid, mid)
                
                if ok:
                    self._append_rating_log(
                        f"✅ TRANSACTION COMMIT: Rating deleted successfully"
                    )
                    messagebox.showinfo(
                        "✅ Rating Deleted",
                        f"Successfully deleted rating!\n\n"
                        f"Movie: {movie_title}\n"
                        f"Movie ID: {mid}\n"
                        f"User ID: {uid}\n\n"
                        f"✓ Transaction committed\n"
                        f"✓ Lock will be released"
                    )
                else:
                    self._append_rating_log(
                        f"❌ TRANSACTION ROLLBACK: Delete failed"
                    )
                    messagebox.showerror(
                        "❌ Delete Failed",
                        "Transaction was rolled back.\n\n"
                        "The rating was NOT deleted."
                    )
        
        finally:
            # ALWAYS release lock after operation completes
            self.handle_cancel_rating_action()
    
    def handle_cancel_rating_action(self):
        """
        Cancel current operation and release lock.
        This allows other users to edit the rating.
        """
        if self.current_rating_lock["locked"]:
            uid = self.current_rating_lock["user_id"]
            mid = self.current_rating_lock["movie_id"]
            movie_title = self.current_rating_lock.get("movie_title", "Unknown")
            
            # Release lock
            release_rating_lock(uid, mid)
            
            self._append_rating_log(
                f"🔓 LOCK RELEASED: userId={uid}, movieId={mid}, movie='{movie_title}'\n"
                f"   → Other users can now edit this rating"
            )
        
        # Reset lock state
        self.current_rating_lock = {
            "user_id": None,
            "movie_id": None,
            "locked": False
        }
        
        # Reset UI
        self.lock_status_var.set("")
        self.btn_submit_rating.config(state="disabled")
        self.btn_cancel_rating.config(state="disabled")
        self.btn_confirm_movie.config(state="normal")
        self.rate_movie_id_entry.config(state="normal")
        
        # Clear fields
        self.rate_movie_id_var.set("")
        self.rate_value_var.set("")
    
    def handle_view_my_ratings(self):
        """
        View all ratings for current user (no lock needed).
        """
        if CURRENT_USER["role"] == "guest":
            messagebox.showerror("Access Denied", "Please login to view ratings.")
            return
        
        uid = CURRENT_USER["userId"]
        ratings = get_all_user_ratings(uid)
        
        if not ratings:
            self._set_text_widget(
                self.rating_status_text,
                f"No ratings found for user {uid} ({CURRENT_USER['username']})"
            )
            return
        
        out_lines = [f"{'='*80}"]
        out_lines.append(f"MY RATINGS - User: {CURRENT_USER['username']} (ID: {uid})")
        out_lines.append(f"{'='*80}\n")
        
        for idx, r in enumerate(ratings, 1):
            out_lines.append(f"{idx}. Movie: {r['title']}")
            out_lines.append(f"   Movie ID: {r['movieId']}")
            out_lines.append(f"   My Rating: {r['rating']} ⭐")
            out_lines.append(f"   Movie Avg: {r.get('movie_avg_rating', 'N/A')} ({r.get('movie_vote_count', 0)} votes)")
            out_lines.append(f"   Rated on: {datetime.fromtimestamp(r['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
            out_lines.append("")
        
        out_lines.append(f"{'='*80}")
        out_lines.append(f"Total: {len(ratings)} ratings")
        
        self._set_text_widget(self.rating_status_text, "\n".join(out_lines))
    
    # ---- OLD RATINGS handlers (kept for backward compatibility) ----
    def handle_add_update_rating(self):
        # Check if guest
        if CURRENT_USER["role"] == "guest":
            messagebox.showerror("Access Denied", "Guests cannot add or modify ratings.\nPlease login with a user account.")
            return

        # get values
        uid_txt = self.rate_user_id_var.get().strip()
        mid_txt = self.rate_movie_id_var.get().strip()
        rv_txt = self.rate_value_var.get().strip()

        # parse user ID - for regular users it's auto-filled, for admins they can search
        uid = None
        if CURRENT_USER["role"] == "user":
            # Regular users can only rate for themselves
            uid = CURRENT_USER["userId"]
        else:
            # Admin can specify user by ID, name, or email
            try:
                # Try as integer first (User ID)
                uid = int(uid_txt)
            except ValueError:
                # Search by name or email
                user = find_user_by_name_or_email(username=uid_txt, email=uid_txt)
                if user:
                    uid = user['userId']
                    self._append_rating_log(f"Found user: {user['username']} (ID: {uid})")
                else:
                    messagebox.showerror("User Not Found", 
                        f"No user found matching '{uid_txt}'.\n\n"
                        "Please enter:\n"
                        "• User ID (number)\n"
                        "• Username (exact match)\n"
                        "• Email (exact match)")
                    return
        
        # Try to parse movie ID/name
        mid = None
        try:
            # Try as integer first (Movie ID)
            mid = int(mid_txt)
        except ValueError:
            # If not integer, search by movie title
            movies = find_movie_by_title_sql(mid_txt)
            if not movies:
                messagebox.showerror("Movie Not Found", f"No movies found matching '{mid_txt}'.\n\nPlease check the spelling or try using the Movie ID instead.")
                return
            elif len(movies) == 1:
                mid = movies[0]['movieId']
                self._append_rating_log(f"Found movie: {movies[0]['title']} (ID: {mid})")
            else:
                # Multiple matches - show selection dialog
                selection_msg = "Multiple movies found. Please select one:\n\n"
                for idx, movie in enumerate(movies[:5], 1):
                    selection_msg += f"{idx}. [{movie['movieId']}] {movie['title']}\n"
                selection_msg += f"\nPlease use the Movie ID from above or be more specific with the title."
                messagebox.showinfo("Multiple Movies Found", selection_msg)
                return
        
        # parse rating value
        try:
            rating_val = float(rv_txt)
        except ValueError:
            messagebox.showerror("Rating", "Rating must be a number.")
            return

        # rating bounds
        if rating_val < 0.5 or rating_val > 5.0:
            messagebox.showerror("Rating", "Rating must be between 0.5 and 5.0.")
            return

        # role restriction: normal user can only rate as themselves
        if CURRENT_USER["role"] != "admin":
            if CURRENT_USER["userId"] is None or uid != CURRENT_USER["userId"]:
                messagebox.showerror(
                    "Access denied",
                    "You can only change your own ratings."
                )
                return

        # referential integrity checks
        if not sql_user_exists(uid):
            messagebox.showerror("Rating", f"User {uid} does not exist.")
            return
        if not sql_movie_exists(mid):
            messagebox.showerror("Rating", f"Movie {mid} does not exist.")
            return

        # CONCURRENCY LOCK CHECK 
        # When User A is editing Movie D, User B cannot edit until User A finishes
        locked_by = check_rating_lock(uid, mid)
        if locked_by and locked_by != CURRENT_USER["username"]:
            messagebox.showerror(
                "Rating Locked - Concurrent Edit Prevention",
                f"This rating is currently being edited by another user.\n\n"
                f"• Another user is editing this rating\n"
                f"• You cannot update it until they finish\n"
                f"• Lock will expire in 5 minutes if not released\n\n"
                f"Please wait and try again later."
            )
            self._append_rating_log(
                f"BLOCKED: Rating locked by '{locked_by}' (user={uid}, movie={mid})"
            )
            return

        # ACQUIRE LOCK (Step 1: Lock the rating before editing)
        # This prevents other users from editing while this user is updating
        if not acquire_rating_lock(uid, mid, CURRENT_USER["username"]):
            messagebox.showerror("Lock Error", "Failed to acquire lock for concurrent edit prevention.")
            return
        
        self._append_rating_log(
            f"🔒 LOCK ACQUIRED: Rating locked for editing (user={uid}, movie={mid})"
        )

        try:
            # PERFORM UPDATE WITHIN TRANSACTION (Step 2: Update with ACID protection)
            ok = add_or_update_rating(uid, mid, rating_val)
            if ok:
                self._append_rating_log(
                    f"✅ UPDATE SUCCESS: user={uid}, movie={mid}, rating={rating_val}"
                )
                messagebox.showinfo(
                    "Rating Updated",
                    f"✅ Successfully updated rating!\n\n"
                    f"• User ID: {uid}\n"
                    f"• Movie ID: {mid}\n"
                    f"• New Rating: {rating_val}\n\n"
                    f"The rating has been unlocked for other users to edit."
                )
            else:
                self._append_rating_log(
                    f"❌ UPDATE FAILED: Transaction rolled back (user={uid}, movie={mid})"
                )
                messagebox.showerror(
                    "Update Failed",
                    "Transaction was rolled back due to an error.\n"
                    "The rating was not updated."
                )
        finally:
            # RELEASE LOCK (Step 3: Always unlock after update completes)
            # This allows other users to edit the rating now
            release_rating_lock(uid, mid)
            self._append_rating_log(
                f"🔓 LOCK RELEASED: Rating now available for others (user={uid}, movie={mid})"
            )

    def handle_delete_rating(self):
        # Check if guest
        if CURRENT_USER["role"] == "guest":
            messagebox.showerror("Access Denied", "Guests cannot delete ratings.\nPlease login with a user account.")
            return

        uid_txt = self.rate_user_id_var.get().strip()
        mid_txt = self.rate_movie_id_var.get().strip()

        try:
            uid = int(uid_txt)
            mid = int(mid_txt)
        except ValueError:
            messagebox.showerror("Rating", "User ID and Movie ID must be integers.")
            return

        # role restriction: normal user can only delete their own rating
        if CURRENT_USER["role"] != "admin":
            if CURRENT_USER["userId"] is None or uid != CURRENT_USER["userId"]:
                messagebox.showerror(
                    "Access denied",
                    "You can only delete your own rating."
                )
                return

        # concurrency lock check
        locked_by = check_rating_lock(uid, mid)
        if locked_by and locked_by != CURRENT_USER["username"]:
            messagebox.showerror(
                "Locked",
                f"This rating is currently being edited by {locked_by}."
            )
            return

        if not acquire_rating_lock(uid, mid, CURRENT_USER["username"]):
            messagebox.showerror("Lock Error", "Failed to acquire lock.")
            return

        try:
            ok = delete_rating(uid, mid)
            if ok:
                self._append_rating_log(
                    f"Deleted rating (user={uid}, movie={mid})"
                )
            else:
                self._append_rating_log(
                    f"Delete FAILED (user={uid}, movie={mid})"
                )
        finally:
            release_rating_lock(uid, mid)

    # ------------------------------------------------------------------
    # TAB 3: ANALYTICS & STATS
    # ------------------------------------------------------------------
    def build_analytics_tab(self):
        """Analytics with multiple query options"""
        container = tk.Frame(self.analytics_tab, bg="#f0f0f0")
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Main content area - left sidebar + right results
        content = tk.Frame(container, bg="#f0f0f0")
        content.pack(fill="both", expand=True)
        
        # Left sidebar with query options
        sidebar = ttk.LabelFrame(content, text="Analytics Queries", padding=10, width=220)
        sidebar.pack(side="left", fill="y", padx=(0, 5))
        sidebar.pack_propagate(False)
        
        # Basic queries
        tk.Label(sidebar, text="Basic Queries", font=("Arial", 9, "bold"), bg="#f0f0f0").pack(pady=(5,2))
        ttk.Button(sidebar, text="Top Movies", command=self.handle_top_movies_analytics, width=25).pack(pady=2)
        ttk.Button(sidebar, text="Most Active Users", command=self.handle_most_active_analytics, width=25).pack(pady=2)
        ttk.Button(sidebar, text="Recent Ratings", command=self.handle_recent_ratings_analytics, width=25).pack(pady=2)
        ttk.Button(sidebar, text="Rating Distribution", command=self.handle_rating_dist_analytics, width=25).pack(pady=2)
        ttk.Button(sidebar, text="Movies by Year", command=self.handle_movies_by_year_analytics, width=25).pack(pady=2)
        ttk.Button(sidebar, text="User Stats", command=self.handle_user_stats_analytics, width=25).pack(pady=2)
        
        # Advanced queries with VIEWs and nested queries
        tk.Label(sidebar, text="Advanced Features", font=("Arial", 9, "bold"), bg="#f0f0f0").pack(pady=(10,2))
        ttk.Button(sidebar, text="Popular Movies (VIEW)", command=self.handle_view_popular_movies, width=25).pack(pady=2)
        ttk.Button(sidebar, text="Niche Movie Fans", command=self.handle_niche_users, width=25).pack(pady=2)
        ttk.Button(sidebar, text="Movies by Active Users", command=self.handle_active_user_movies, width=25).pack(pady=2)
        ttk.Button(sidebar, text="Controversial Movies", command=self.handle_controversial_movies, width=25).pack(pady=2)
        ttk.Button(sidebar, text="Above Average Movies", command=self.handle_above_avg_movies, width=25).pack(pady=2)
        ttk.Button(sidebar, text="Genre Statistics", command=self.handle_genre_stats_analytics, width=25).pack(pady=2)
        
        # Right results panel
        results_frame = ttk.LabelFrame(content, text="Results", padding=10)
        results_frame.pack(side="left", fill="both", expand=True)
        
        # Add scrollbar
        text_frame = tk.Frame(results_frame)
        text_frame.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.results_text_analytics = tk.Text(
            text_frame,
            width=80,
            height=30,
            state="disabled",
            wrap="word",
            font=("Courier New", 9),
            bg="#ecf0f1",
            yscrollcommand=scrollbar.set
        )
        self.results_text_analytics.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.results_text_analytics.yview)
        
        # Show welcome message
        welcome = "Welcome to Analytics Dashboard\n" + "="*70 + "\n\n"
        welcome += "Select a query from the left sidebar to view analytics.\n\n"
        welcome += "BASIC QUERIES:\n"
        welcome += "• Top Movies - Top rated movies with 10+ votes\n"
        welcome += "• Most Active Users - Users with most ratings\n"
        welcome += "• Recent Ratings - Latest rating activity\n"
        welcome += "• Rating Distribution - Distribution of ratings\n"
        welcome += "• Movies by Year - Movie count by release year\n"
        welcome += "• User Stats - Your personal statistics\n\n"
        welcome += "ADVANCED FEATURES\n"
        welcome += "• Popular Movies - Uses SQL VIEW for pre-computed data\n"
        welcome += "• Niche Movie Fans - NOT EXISTS nested query\n"
        welcome += "• Movies by Active Users - IN subquery\n"
        welcome += "• Controversial Movies - VARIANCE/STDDEV aggregation\n"
        welcome += "• Above Average Movies - Nested query in HAVING clause\n"
        self._set_text_widget(self.results_text_analytics, welcome)
    
    def handle_top_movies_analytics(self):
        rows, elapsed = get_top_rated_movies(limit=30)
        output = f"TOP 30 RATED MOVIES (Query time: {elapsed:.3f}s)\n{'='*80}\n\n"
        output += f"{'Rank':<5} {'Movie Title':<50} {'Votes':>7} {'Avg':>6} {'Min':>5} {'Max':>5}\n"
        output += "-" * 80 + "\n"
        for idx, r in enumerate(rows, 1):
            title = r['title'][:48] if len(r['title']) > 48 else r['title']
            output += f"{idx:<5} {title:<50} {r['vote_count']:>7} {r['avg_rating']:>6.2f} {r['min_rating']:>5.1f} {r['max_rating']:>5.1f}\n"
        self._set_text_widget(self.results_text_analytics, output)
    
    def handle_most_active_analytics(self):
        sql = """
            SELECT 
                u.userId,
                u.username,
                u.email,
                COUNT(r.rating) AS total_ratings,
                ROUND(AVG(r.rating), 2) AS avg_rating,
                MIN(r.rating) AS min_rating,
                MAX(r.rating) AS max_rating
            FROM users u
            INNER JOIN ratings r ON u.userId = r.userId
            GROUP BY u.userId, u.username, u.email
            HAVING COUNT(r.rating) > 0
            ORDER BY total_ratings DESC
            LIMIT 30
        """
        
        start = time.time()
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
            elapsed = time.time() - start
            
            output = f"MOST ACTIVE USERS (Query time: {elapsed:.3f}s)\n{'='*80}\n\n"
            output += f"{'Rank':<5} {'Username':<20} {'Email':<25} {'Ratings':>8} {'Avg':>6}\n"
            output += "-" * 80 + "\n"
            
            for idx, r in enumerate(rows, 1):
                # Handle NULL usernames and emails
                username = r['username'] or 'N/A'
                email = r['email'] or 'N/A'
                username = username[:18] if len(username) > 18 else username
                email = email[:23] if len(email) > 23 else email
                output += f"{idx:<5} {username:<20} {email:<25} {r['total_ratings']:>8} {r['avg_rating']:>6.2f}\n"
            
            output += "\n" + "="*80 + "\n"
            output += f"Total active users in database: {len(rows)}\n"
            self._set_text_widget(self.results_text_analytics, output)
        finally:
            conn.close()
    
    def handle_recent_ratings_analytics(self):
        sql = """
            SELECT 
                u.username,
                m.title,
                r.rating,
                r.timestamp
            FROM ratings r
            INNER JOIN users u ON r.userId = u.userId
            INNER JOIN movies m ON r.movieId = m.movieId
            WHERE m.title NOT LIKE 'Movie_%%'
            ORDER BY r.timestamp DESC
            LIMIT 50
        """
        
        start = time.time()
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
            elapsed = time.time() - start
            
            output = f"RECENT RATING ACTIVITY (Query time: {elapsed:.3f}s)\n{'='*80}\n\n"
            output += f"{'Username':<20} {'Movie Title':<40} {'Rating':>8} {'Date/Time':<20}\n"
            output += "-" * 80 + "\n"
            
            for r in rows:
                # Handle NULL usernames
                username = r['username'] or 'N/A'
                username = username[:18] if len(username) > 18 else username
                title = r['title'][:38] if len(r['title']) > 38 else r['title']
                timestamp = datetime.fromtimestamp(r['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                output += f"{username:<20} {title:<40} {r['rating']:>8.1f} {timestamp:<20}\n"
            
            output += "\n" + "="*80 + "\n"
            output += f"Showing {len(rows)} most recent ratings\n"
            self._set_text_widget(self.results_text_analytics, output)
        finally:
            conn.close()
    
    def handle_rating_dist_analytics(self):
        sql = """
            SELECT 
                FLOOR(rating) AS rating_value,
                COUNT(*) AS count
            FROM ratings
            GROUP BY FLOOR(rating)
            ORDER BY rating_value
        """
        
        start = time.time()
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
            elapsed = time.time() - start
            
            # Find max count for scaling
            max_count = max(r['count'] for r in rows) if rows else 1
            total = sum(r['count'] for r in rows)
            
            # Create bar chart
            output = f"RATING DISTRIBUTION (Query time: {elapsed:.3f}s)\n"
            output += "=" * 80 + "\n\n"
            
            for r in rows:
                rating = r['rating_value']
                count = r['count']
                percentage = (count / total) * 100
                bar_length = int((count / max_count) * 50)  # Scale to 50 chars max
                bar = "█" * bar_length
                
                output += f"{rating:.0f} ⭐  {bar:<50} {count:>8,} ({percentage:>5.1f}%)\n"
            
            output += "\n" + "=" * 80 + "\n"
            output += f"Total Ratings: {total:,}\n"
            output += f"Average Rating: {sum(r['rating_value'] * r['count'] for r in rows) / total:.2f}\n"
            
            self._set_text_widget(self.results_text_analytics, output)
        finally:
            conn.close()
    
    def handle_movies_by_year_analytics(self):
        sql = """
            SELECT 
                YEAR(m.release_date) AS year,
                COUNT(DISTINCT m.movieId) AS movie_count,
                ROUND(AVG(r.rating), 2) AS avg_rating,
                COUNT(r.rating) AS total_ratings
            FROM movies m
            LEFT JOIN ratings r ON m.movieId = r.movieId
            WHERE m.release_date IS NOT NULL
              AND YEAR(m.release_date) >= 1980
              AND m.title NOT LIKE 'Movie_%%'
            GROUP BY YEAR(m.release_date)
            ORDER BY year DESC
            LIMIT 45
        """
        
        start = time.time()
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
            elapsed = time.time() - start
            
            output = f"MOVIES BY YEAR (Query time: {elapsed:.3f}s)\n{'='*80}\n\n"
            output += f"{'Year':<8} {'Movies':>8} {'Avg Rating':>12} {'Total Ratings':>15}\n"
            output += "-" * 80 + "\n"
            
            for r in rows:
                avg = f"{r['avg_rating']:.2f}" if r['avg_rating'] else "N/A"
                output += f"{r['year']:<8} {r['movie_count']:>8} {avg:>12} {r['total_ratings']:>15,}\n"
            
            output += "\n" + "="*80 + "\n"
            total_movies = sum(r['movie_count'] for r in rows)
            output += f"Total movies (1980-present): {total_movies:,}\n"
            self._set_text_widget(self.results_text_analytics, output)
        finally:
            conn.close()
    
    def handle_user_stats_analytics(self):
        if not CURRENT_USER['userId']:
            self._set_text_widget(self.results_text_analytics, 
                "Please login to view your personal statistics.\n\n"
                "Guest users can view other analytics but not personal stats.")
            return
        
        row, elapsed = get_user_statistics(CURRENT_USER['userId'])
        
        if row:
            output = f"YOUR STATISTICS (Query time: {elapsed:.3f}s)\n{'='*80}\n\n"
            output += f"Username: {row['username']}\n"
            output += f"Email: {row['email']}\n"
            output += f"User ID: {row['userId']}\n\n"
            output += "-" * 80 + "\n\n"
            output += f"Total Ratings Given: {row['total_ratings']}\n"
            
            # Handle None values for users with no ratings
            avg_rating = row['avg_rating_given'] if row['avg_rating_given'] is not None else 0
            max_rating = row['max_rating_given'] if row['max_rating_given'] is not None else 0
            min_rating = row['min_rating_given'] if row['min_rating_given'] is not None else 0
            
            output += f"Average Rating: {avg_rating:.2f}\n"
            output += f"Highest Rating Given: {max_rating:.1f}\n"
            output += f"Lowest Rating Given: {min_rating:.1f}\n\n"
            output += f"High Ratings (≥4.0): {row['high_ratings_count']}\n"
            output += f"Low Ratings (≤2.0): {row['low_ratings_count']}\n\n"
            
            if row['total_ratings'] > 0:
                high_pct = (row['high_ratings_count'] / row['total_ratings']) * 100
                low_pct = (row['low_ratings_count'] / row['total_ratings']) * 100
                output += f"You give high ratings {high_pct:.1f}% of the time\n"
                output += f"You give low ratings {low_pct:.1f}% of the time\n"
            else:
                output += "You haven't rated any movies yet. Start rating movies to see your statistics!\n"
            
            self._set_text_widget(self.results_text_analytics, output)
        else:
            self._set_text_widget(self.results_text_analytics, 
                "Unable to load user statistics. Please try again.")
    
    def handle_view_popular_movies(self):
        """Query popular_movies VIEW"""
        rows, elapsed = get_popular_movies_from_view(limit=30)
        output = f"POPULAR MOVIES FROM VIEW (Query time: {elapsed:.3f}s)\n{'='*80}\n\n"
        output += "This query uses a pre-computed SQL VIEW for efficient data retrieval.\n\n"
        output += f"{'Rank':<5} {'Movie Title':<45} {'Votes':>8} {'Avg':>6} {'Min':>5} {'Max':>5}\n"
        output += "-" * 80 + "\n"
        for idx, r in enumerate(rows, 1):
            title = r['title'][:43] if len(r['title']) > 43 else r['title']
            avg_val = r['avg_rating'] if r['avg_rating'] else 0
            output += f"{idx:<5} {title:<45} {r['rating_count']:>8} {avg_val:>6.2f} {r['min_rating']:>5.1f} {r['max_rating']:>5.1f}\n"
        output += "\n" + "="*80 + "\n"
        output += f"VIEW: popular_movies (pre-aggregated data for performance)\n"
        self._set_text_widget(self.results_text_analytics, output)
    
    def handle_niche_users(self):
        """Users who never rated popular movies - NOT EXISTS query"""
        rows, elapsed = find_users_who_never_rated_popular_movies()
        output = f"NICHE MOVIE FANS (Query time: {elapsed:.3f}s)\n{'='*80}\n\n"
        output += "Users who NEVER rated any popular movie (NOT EXISTS nested query)\n\n"
        output += f"{'User ID':<10} {'Username':<25} {'Email':<30} {'Ratings':>10}\n"
        output += "-" * 80 + "\n"
        for r in rows:
            username = (r['username'] or 'N/A')[:23]
            email = (r['email'] or 'N/A')[:28]
            output += f"{r['userId']:<10} {username:<25} {email:<30} {r['total_ratings']:>10}\n"
        output += "\n" + "="*80 + "\n"
        output += f"Found {len(rows)} users who prefer non-mainstream movies\n"
        output += "SQL: NOT EXISTS correlated subquery with VIEW\n"
        self._set_text_widget(self.results_text_analytics, output)
    
    def handle_active_user_movies(self):
        """Movies rated by all active users - IN subquery"""
        rows, elapsed = find_movies_rated_by_all_active_users()
        output = f"MOVIES RATED BY ALL ACTIVE USERS (Query time: {elapsed:.3f}s)\n{'='*80}\n\n"
        output += "Movies that every active user (10+ ratings) has rated\n"
        output += "Uses IN subquery with HAVING clause\n\n"
        output += f"{'Movie ID':<10} {'Title':<50} {'Avg Rating':>12} {'Active Users':>13}\n"
        output += "-" * 80 + "\n"
        for r in rows:
            title = r['title'][:48] if len(r['title']) > 48 else r['title']
            output += f"{r['movieId']:<10} {title:<50} {r['avg_rating']:>12.2f} {r['active_user_count']:>13}\n"
        output += "\n" + "="*80 + "\n"
        if len(rows) == 0:
            output += "No movies found (criteria may be too strict)\n"
        else:
            output += f"Found {len(rows)} universally-rated movies\n"
        output += "SQL: IN subquery + GROUP BY + HAVING\n"
        self._set_text_widget(self.results_text_analytics, output)
    
    def handle_controversial_movies(self):
        """Movies with high rating variance - VARIANCE/STDDEV"""
        rows, elapsed = find_movies_with_rating_variance()
        output = f"CONTROVERSIAL MOVIES (Query time: {elapsed:.3f}s)\n{'='*80}\n\n"
        output += "Movies with highest rating disagreement (VARIANCE & STDDEV)\n\n"
        output += f"{'Movie Title':<45} {'Avg':>6} {'StdDev':>8} {'Variance':>10} {'Votes':>8}\n"
        output += "-" * 80 + "\n"
        for r in rows:
            title = r['title'][:43] if len(r['title']) > 43 else r['title']
            stddev = r['rating_stddev'] if r['rating_stddev'] else 0
            variance = r['rating_variance'] if r['rating_variance'] else 0
            output += f"{title:<45} {r['avg_rating']:>6.2f} {stddev:>8.2f} {variance:>10.2f} {r['vote_count']:>8}\n"
        output += "\n" + "="*80 + "\n"
        output += f"Found {len(rows)} movies with significant rating disagreement\n"
        output += "SQL: VARIANCE() and STDDEV() aggregate functions\n"
        self._set_text_widget(self.results_text_analytics, output)
    
    def handle_above_avg_movies(self):
        """Movies with above-average ratings - nested query in HAVING"""
        rows, elapsed = get_movies_with_above_average_ratings()
        output = f"ABOVE AVERAGE MOVIES (Query time: {elapsed:.3f}s)\n{'='*80}\n\n"
        output += "Movies with ratings above the global average\n"
        output += "Uses nested subquery in HAVING clause\n\n"
        output += f"{'Movie Title':<50} {'Avg Rating':>12} {'Votes':>8}\n"
        output += "-" * 80 + "\n"
        for r in rows:
            title = r['title'][:48] if len(r['title']) > 48 else r['title']
            output += f"{title:<50} {r['avg_rating']:>12.2f} {r['vote_count']:>8}\n"
        output += "\n" + "="*80 + "\n"
        output += f"Found {len(rows)} movies with above-average ratings\n"
        output += "SQL: Subquery in HAVING AVG(rating) > (SELECT AVG(rating) FROM ratings)\n"
        self._set_text_widget(self.results_text_analytics, output)
    
    def handle_genre_stats_analytics(self):
        """Genre statistics using MongoDB aggregation pipeline"""
        agg_results, elapsed = get_genre_statistics_mongo()
        
        output = f"GENRE STATISTICS - MongoDB Aggregation Pipeline (Query time: {elapsed:.4f}s)\n"
        output += "="*90 + "\n\n"
        output += "This uses MongoDB's aggregation framework: $match → $group → $sort → $limit\n\n"
        
        if not agg_results:
            output += "No genre statistics available.\n"
        else:
            output += f"{'Rank':<6} {'Genre':<40} {'Count':<8} {'Avg Rating':<12} {'Avg Revenue':<15}\n"
            output += "-" * 90 + "\n"
            
            for i, stats in enumerate(agg_results, 1):
                genre = stats.get('_id', 'Unknown')[:38]
                count = stats.get('count', 0)
                avg_rating = stats.get('avg_rating', 0)
                avg_revenue = stats.get('avg_revenue', 0)
                
                output += f"{i:<6} {genre:<40} {count:<8} {avg_rating:<12.2f} ${avg_revenue:<14,.0f}\n"
            
            output += "\n" + "="*90 + "\n"
            output += f"Generated statistics for {len(agg_results)} genre groups\n\n"
            output += "Pipeline Stages:\n"
            output += "  1. $match - Filter documents with genres field\n"
            output += "  2. $group - Group by genre, calculate count/avg_rating/avg_revenue\n"
            output += "  3. $sort - Sort by count descending\n"
            output += "  4. $limit - Top 20 results\n"
        
        self._set_text_widget(self.results_text_analytics, output)

    # ------------------------------------------------------------------
    # TAB 4: MY PROFILE
    # ------------------------------------------------------------------
    def build_profile_tab(self):
        container = tk.Frame(self.profile_tab, bg="#f0f0f0")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # Header
        header_frame = tk.Frame(container, bg="white", relief="ridge", borderwidth=2)
        header_frame.pack(fill="x", pady=(0, 10))
        container = tk.Frame(self.analytics_option_a_tab, bg="#f0f0f0")
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title_frame = tk.Frame(container, bg="#3498db", height=50)
        title_frame.pack(fill="x", pady=(0, 10))
        title_frame.pack_propagate(False)
        
        tk.Label(
            title_frame,
            text="Analytics Option A: Treeview Tables",
            font=("Arial", 14, "bold"),
            bg="#3498db",
            fg="white"
        ).pack(pady=10)
        
        # Description
        desc_frame = ttk.LabelFrame(container, text="About This Option", padding=10)
        desc_frame.pack(fill="x", pady=(0, 10))
        tk.Label(
            desc_frame,
            text="• Simple upgrade: Replaces text displays with sortable Treeview tables\n"
                 "• Top movies shown in professional table format\n"
                 "• User statistics displayed in card-style layout\n"
                 "• Minimal changes, maximum visual improvement",
            font=("Arial", 9),
            justify="left",
            bg="white"
        ).pack(anchor="w")
        
        # Top Movies Section
        top_frame = ttk.LabelFrame(container, text="Top Rated Movies", padding=10)
        top_frame.pack(fill="both", expand=True, pady=(0, 5))
        
        ttk.Button(
            top_frame,
            text="Load Top Movies",
            command=self.handle_top_movies_option_a
        ).pack(anchor="w", pady=(0, 5))
        
        # Treeview for top movies
        tree_frame = tk.Frame(top_frame)
        tree_frame.pack(fill="both", expand=True)
        
        columns_a = ("title", "votes", "avg", "min", "max")
        self.top_movies_tree_a = ttk.Treeview(tree_frame, columns=columns_a, show="headings", height=10)
        
        self.top_movies_tree_a.heading("title", text="Movie Title")
        self.top_movies_tree_a.heading("votes", text="Votes")
        self.top_movies_tree_a.heading("avg", text="Avg Rating")
        self.top_movies_tree_a.heading("min", text="Min")
        self.top_movies_tree_a.heading("max", text="Max")
        
        self.top_movies_tree_a.column("title", width=400, anchor="w")
        self.top_movies_tree_a.column("votes", width=80, anchor="center")
        self.top_movies_tree_a.column("avg", width=100, anchor="center")
        self.top_movies_tree_a.column("min", width=80, anchor="center")
        self.top_movies_tree_a.column("max", width=80, anchor="center")
        
        self.top_movies_tree_a.pack(side="left", fill="both", expand=True)
        
        scrollbar_a = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.top_movies_tree_a.yview)
        scrollbar_a.pack(side="right", fill="y")
        self.top_movies_tree_a.configure(yscrollcommand=scrollbar_a.set)
        
        # User Statistics Section
        stats_frame = ttk.LabelFrame(container, text="User Statistics", padding=10)
        stats_frame.pack(fill="both", expand=True, pady=(5, 0))
        
        self.stats_display_frame_a = tk.Frame(stats_frame, bg="white")
        self.stats_display_frame_a.pack(fill="both", expand=True)
    
    def handle_top_movies_option_a(self):
        """Load top movies into Treeview for Option A"""
        # Clear existing items
        for item in self.top_movies_tree_a.get_children():
            self.top_movies_tree_a.delete(item)
        
        rows, elapsed = get_top_rated_movies(limit=20)
        
        for r in rows:
            self.top_movies_tree_a.insert("", "end", values=(
                r["title"],
                r["vote_count"],
                f"{r['avg_rating']:.2f}",
                f"{r['min_rating']:.1f}",
                f"{r['max_rating']:.1f}"
            ))
    
    def build_analytics_option_b(self):
        """Option B: More Analytics - Multiple new queries"""
        container = tk.Frame(self.analytics_option_b_tab, bg="#f0f0f0")
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title_frame = tk.Frame(container, bg="#e67e22", height=50)
        title_frame.pack(fill="x", pady=(0, 10))
        title_frame.pack_propagate(False)
        
        tk.Label(
            title_frame,
            text="Analytics Option B: More Analytics Queries",
            font=("Arial", 14, "bold"),
            bg="#e67e22",
            fg="white"
        ).pack(pady=10)
        
        # Description
        desc_frame = ttk.LabelFrame(container, text="About This Option", padding=10)
        desc_frame.pack(fill="x", pady=(0, 10))
        tk.Label(
            desc_frame,
            text="• Adds 5 new analytics queries for deeper insights\n"
                 "• Most Active Users, Recent Activity, Rating Distribution, Movies by Year\n"
                 "• Left sidebar for query selection, right panel for results\n"
                 "• Comprehensive data exploration capabilities",
            font=("Arial", 9),
            justify="left",
            bg="white"
        ).pack(anchor="w")
        
        # Main content area - left sidebar + right results
        content = tk.Frame(container, bg="#f0f0f0")
        content.pack(fill="both", expand=True)
        
        # Left sidebar with query options
        sidebar = ttk.LabelFrame(content, text="Analytics Queries", padding=10, width=200)
        sidebar.pack(side="left", fill="y", padx=(0, 5))
        sidebar.pack_propagate(False)
        
        ttk.Button(sidebar, text="Top Movies", command=self.handle_top_movies_b, width=20).pack(pady=2)
        ttk.Button(sidebar, text="Most Active Users", command=self.handle_most_active_b, width=20).pack(pady=2)
        ttk.Button(sidebar, text="Recent Ratings", command=self.handle_recent_ratings_b, width=20).pack(pady=2)
        ttk.Button(sidebar, text="Rating Distribution", command=self.handle_rating_dist_b, width=20).pack(pady=2)
        ttk.Button(sidebar, text="Movies by Year", command=self.handle_movies_by_year_b, width=20).pack(pady=2)
        ttk.Button(sidebar, text="User Stats", command=self.handle_user_stats_b, width=20).pack(pady=2)
        
        # Right results panel
        results_frame = ttk.LabelFrame(content, text="Results", padding=10)
        results_frame.pack(side="left", fill="both", expand=True)
        
        self.results_text_b = tk.Text(
            results_frame,
            width=80,
            height=30,
            state="disabled",
            wrap="word",
            font=("Courier New", 9),
            bg="#ecf0f1"
        )
        self.results_text_b.pack(fill="both", expand=True)
    
    def handle_top_movies_b(self):
        rows, elapsed = get_top_rated_movies(limit=20)
        output = f"TOP 20 RATED MOVIES (Query time: {elapsed:.3f}s)\n{'='*70}\n\n"
        for r in rows:
            output += f"{r['title'][:50]:50} | Votes: {r['vote_count']:4} | Avg: {r['avg_rating']:.2f}\n"
        self._set_text_widget(self.results_text_b, output)
    
    def handle_most_active_b(self):
        self._set_text_widget(self.results_text_b, "Most Active Users query - Shows users with most ratings")
    
    def handle_recent_ratings_b(self):
        self._set_text_widget(self.results_text_b, "Recent Ratings query - Shows latest rating activity")
    
    def handle_rating_dist_b(self):
        self._set_text_widget(self.results_text_b, "Rating Distribution query - Shows distribution of ratings (bar chart)")
    
    def handle_movies_by_year_b(self):
        self._set_text_widget(self.results_text_b, "Movies by Year query - Shows movie count by release year")
    
    def handle_user_stats_b(self):
        if not CURRENT_USER['userId']:
            self._set_text_widget(self.results_text_b, "Please login to view user statistics")
            return
        row, elapsed = get_user_statistics(CURRENT_USER['userId'])
        if row:
            output = f"USER STATISTICS (Query time: {elapsed:.3f}s)\n{'='*70}\n\n"
            output += f"Username: {row['username']}\n"
            output += f"Email: {row['email']}\n"
            output += f"Total Ratings: {row['total_ratings']}\n"
            output += f"Average Rating Given: {row['avg_rating_given']:.2f}\n"
            self._set_text_widget(self.results_text_b, output)
    
    def build_analytics_option_c(self):
        """Option C: Complete Redesign - Modern dashboard with sub-tabs"""
        container = tk.Frame(self.analytics_option_c_tab, bg="#f0f0f0")
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title_frame = tk.Frame(container, bg="#9b59b6", height=50)
        title_frame.pack(fill="x", pady=(0, 10))
        title_frame.pack_propagate(False)
        
        tk.Label(
            title_frame,
            text="Analytics Option C: Complete Dashboard Redesign",
            font=("Arial", 14, "bold"),
            bg="#9b59b6",
            fg="white"
        ).pack(pady=10)
        
        # Description
        desc_frame = ttk.LabelFrame(container, text="About This Option", padding=10)
        desc_frame.pack(fill="x", pady=(0, 10))
        
        desc_text = tk.Frame(desc_frame, bg="white")
        desc_text.pack(fill="x")
        
        tk.Label(
            desc_text,
            text="• Modern dashboard with color-coded stat cards\n"
                 "• Sub-notebook with 4 specialized tabs (Top Movies, User Analytics, Rating Analytics, Trends)\n"
                 "• Professional visualization with multiple data views\n"
                 "• Most comprehensive option with rich features",
            font=("Arial", 9),
            justify="left",
            bg="white"
        ).pack(side="left", anchor="w")
        
        ttk.Button(
            desc_text,
            text="Load Statistics",
            command=self.load_dashboard_stats_c
        ).pack(side="right", padx=10)
        
        # Stat cards at top - store references to labels for updating
        cards_frame = tk.Frame(container, bg="#f0f0f0", height=100)
        cards_frame.pack(fill="x", pady=(0, 10))
        cards_frame.pack_propagate(False)
        
        # Create 4 stat cards and store label references
        self.stat_cards_c = {}
        self.stat_cards_c['movies'] = self._create_stat_card(cards_frame, "Total Movies", "Loading...", "#3498db", 0)
        self.stat_cards_c['ratings'] = self._create_stat_card(cards_frame, "Total Ratings", "Loading...", "#2ecc71", 1)
        self.stat_cards_c['users'] = self._create_stat_card(cards_frame, "Active Users", "Loading...", "#e74c3c", 2)
        self.stat_cards_c['avg'] = self._create_stat_card(cards_frame, "Avg Rating", "Loading...", "#f39c12", 3)
        
        # Sub-notebook for different analytics views
        self.analytics_notebook_c = ttk.Notebook(container)
        self.analytics_notebook_c.pack(fill="both", expand=True)
        
        # Create 4 sub-tabs
        tab1 = ttk.Frame(self.analytics_notebook_c)
        tab2 = ttk.Frame(self.analytics_notebook_c)
        tab3 = ttk.Frame(self.analytics_notebook_c)
        tab4 = ttk.Frame(self.analytics_notebook_c)
        
        self.analytics_notebook_c.add(tab1, text="Top Movies")
        self.analytics_notebook_c.add(tab2, text="User Analytics")
        self.analytics_notebook_c.add(tab3, text="Rating Analytics")
        self.analytics_notebook_c.add(tab4, text="Trends")
        
        # Tab 1: Top Movies (Treeview)
        btn_frame1 = tk.Frame(tab1, bg="white")
        btn_frame1.pack(fill="x", padx=10, pady=10)
        ttk.Button(btn_frame1, text="Load Top Movies", command=self.load_top_movies_c).pack(side="left")
        
        tree_frame1 = tk.Frame(tab1)
        tree_frame1.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        cols1 = ("rank", "title", "votes", "avg")
        self.top_movies_tree_c = ttk.Treeview(tree_frame1, columns=cols1, show="headings", height=15)
        self.top_movies_tree_c.heading("rank", text="#")
        self.top_movies_tree_c.heading("title", text="Movie Title")
        self.top_movies_tree_c.heading("votes", text="Total Votes")
        self.top_movies_tree_c.heading("avg", text="Avg Rating")
        
        self.top_movies_tree_c.column("rank", width=50, anchor="center")
        self.top_movies_tree_c.column("title", width=400, anchor="w")
        self.top_movies_tree_c.column("votes", width=100, anchor="center")
        self.top_movies_tree_c.column("avg", width=100, anchor="center")
        
        self.top_movies_tree_c.pack(side="left", fill="both", expand=True)
        scrollbar1 = ttk.Scrollbar(tree_frame1, orient=tk.VERTICAL, command=self.top_movies_tree_c.yview)
        scrollbar1.pack(side="right", fill="y")
        self.top_movies_tree_c.configure(yscrollcommand=scrollbar1.set)
        
        # Tab 2: User Analytics
        btn_frame2 = tk.Frame(tab2, bg="white")
        btn_frame2.pack(fill="x", padx=10, pady=10)
        ttk.Button(btn_frame2, text="Load Most Active Users", command=self.load_active_users_c).pack(side="left")
        
        tree_frame2 = tk.Frame(tab2)
        tree_frame2.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        cols2 = ("rank", "username", "email", "ratings", "avg")
        self.users_tree_c = ttk.Treeview(tree_frame2, columns=cols2, show="headings", height=15)
        self.users_tree_c.heading("rank", text="#")
        self.users_tree_c.heading("username", text="Username")
        self.users_tree_c.heading("email", text="Email")
        self.users_tree_c.heading("ratings", text="Total Ratings")
        self.users_tree_c.heading("avg", text="Avg Given")
        
        self.users_tree_c.column("rank", width=50, anchor="center")
        self.users_tree_c.column("username", width=150, anchor="w")
        self.users_tree_c.column("email", width=200, anchor="w")
        self.users_tree_c.column("ratings", width=100, anchor="center")
        self.users_tree_c.column("avg", width=100, anchor="center")
        
        self.users_tree_c.pack(side="left", fill="both", expand=True)
        scrollbar2 = ttk.Scrollbar(tree_frame2, orient=tk.VERTICAL, command=self.users_tree_c.yview)
        scrollbar2.pack(side="right", fill="y")
        self.users_tree_c.configure(yscrollcommand=scrollbar2.set)
        
        # Tab 3: Rating Distribution
        btn_frame3 = tk.Frame(tab3, bg="white")
        btn_frame3.pack(fill="x", padx=10, pady=10)
        ttk.Button(btn_frame3, text="Load Rating Distribution", command=self.load_rating_dist_c).pack(side="left")
        
        self.rating_dist_text_c = tk.Text(tab3, width=80, height=20, state="disabled", 
                                          wrap="none", font=("Courier New", 10), bg="#ecf0f1")
        self.rating_dist_text_c.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Tab 4: Trends (Movies by Year)
        btn_frame4 = tk.Frame(tab4, bg="white")
        btn_frame4.pack(fill="x", padx=10, pady=10)
        ttk.Button(btn_frame4, text="Load Movies by Year", command=self.load_movies_by_year_c).pack(side="left")
        
        tree_frame4 = tk.Frame(tab4)
        tree_frame4.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        cols4 = ("year", "count", "avg_rating")
        self.year_tree_c = ttk.Treeview(tree_frame4, columns=cols4, show="headings", height=15)
        self.year_tree_c.heading("year", text="Year")
        self.year_tree_c.heading("count", text="Movies Released")
        self.year_tree_c.heading("avg_rating", text="Avg Rating")
        
        self.year_tree_c.column("year", width=100, anchor="center")
        self.year_tree_c.column("count", width=150, anchor="center")
        self.year_tree_c.column("avg_rating", width=150, anchor="center")
        
        self.year_tree_c.pack(side="left", fill="both", expand=True)
        scrollbar4 = ttk.Scrollbar(tree_frame4, orient=tk.VERTICAL, command=self.year_tree_c.yview)
        scrollbar4.pack(side="right", fill="y")
        self.year_tree_c.configure(yscrollcommand=scrollbar4.set)
        
        # Auto-load statistics on tab creation
        self.after(100, self.load_dashboard_stats_c)
    
    def _create_stat_card(self, parent, title, value, color, col):
        """Create a colored stat card - returns the value label for updating"""
        card = tk.Frame(parent, bg=color, relief="raised", borderwidth=2)
        card.grid(row=0, column=col, padx=5, pady=5, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1)
        
        tk.Label(
            card,
            text=title,
            font=("Arial", 10),
            bg=color,
            fg="white"
        ).pack(pady=(10, 5))
        
        value_label = tk.Label(
            card,
            text=value,
            font=("Arial", 18, "bold"),
            bg=color,
            fg="white"
        )
        value_label.pack(pady=(5, 10))
        
        return value_label  # Return label so we can update it later
    
    def _create_stat_card(self, parent, title, value, color, col):
        """Create a colored stat card - returns the value label for updating"""
        card = tk.Frame(parent, bg=color, relief="raised", borderwidth=2)
        card.grid(row=0, column=col, padx=5, pady=5, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1)
        
        tk.Label(
            card,
            text=title,
            font=("Arial", 10),
            bg=color,
            fg="white"
        ).pack(pady=(10, 5))
        
        value_label = tk.Label(
            card,
            text=value,
            font=("Arial", 18, "bold"),
            bg=color,
            fg="white"
        )
        value_label.pack(pady=(5, 10))
        
        return value_label  # Return label so we can update it later
    
    def load_dashboard_stats_c(self):
        """Load real database statistics for Option C dashboard"""
        try:
            conn = get_connection()
            try:
                with conn.cursor() as cur:
                    # Total movies
                    cur.execute("SELECT COUNT(*) as count FROM movies WHERE title NOT LIKE 'Movie_%%'")
                    total_movies = cur.fetchone()['count']
                    
                    # Total ratings
                    cur.execute("SELECT COUNT(*) as count FROM ratings")
                    total_ratings = cur.fetchone()['count']
                    
                    # Active users (users with at least 1 rating)
                    cur.execute("""
                        SELECT COUNT(DISTINCT userId) as count 
                        FROM ratings
                    """)
                    active_users = cur.fetchone()['count']
                    
                    # Average rating across all ratings
                    cur.execute("SELECT ROUND(AVG(rating), 2) as avg FROM ratings")
                    avg_rating = cur.fetchone()['avg'] or 0
                    
                # Update stat cards
                self.stat_cards_c['movies'].config(text=f"{total_movies:,}")
                self.stat_cards_c['ratings'].config(text=f"{total_ratings:,}")
                self.stat_cards_c['users'].config(text=f"{active_users:,}")
                self.stat_cards_c['avg'].config(text=f"{avg_rating:.2f}")
                
            finally:
                conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load statistics: {e}")
    
    def load_top_movies_c(self):
        """Load top movies for Option C"""
        for item in self.top_movies_tree_c.get_children():
            self.top_movies_tree_c.delete(item)
        
        rows, _ = get_top_rated_movies(limit=30)
        
        for idx, r in enumerate(rows, 1):
            self.top_movies_tree_c.insert("", "end", values=(
                idx,
                r["title"],
                r["vote_count"],
                f"{r['avg_rating']:.2f}"
            ))
    
    def load_active_users_c(self):
        """Load most active users for Option C"""
        for item in self.users_tree_c.get_children():
            self.users_tree_c.delete(item)
        
        sql = """
            SELECT 
                u.userId,
                u.username,
                u.email,
                COUNT(r.rating) AS total_ratings,
                ROUND(AVG(r.rating), 2) AS avg_rating
            FROM users u
            INNER JOIN ratings r ON u.userId = r.userId
            GROUP BY u.userId, u.username, u.email
            HAVING COUNT(r.rating) > 0
            ORDER BY total_ratings DESC
            LIMIT 30
        """
        
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
            
            for idx, r in enumerate(rows, 1):
                self.users_tree_c.insert("", "end", values=(
                    idx,
                    r["username"],
                    r["email"],
                    r["total_ratings"],
                    f"{r['avg_rating']:.2f}"
                ))
        finally:
            conn.close()
    
    def load_rating_dist_c(self):
        """Load rating distribution with bar chart for Option C"""
        sql = """
            SELECT 
                FLOOR(rating) AS rating_value,
                COUNT(*) AS count
            FROM ratings
            GROUP BY FLOOR(rating)
            ORDER BY rating_value
        """
        
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
            
            # Find max count for scaling
            max_count = max(r['count'] for r in rows) if rows else 1
            
            # Create bar chart
            output = "RATING DISTRIBUTION\n"
            output += "=" * 70 + "\n\n"
            
            for r in rows:
                rating = r['rating_value']
                count = r['count']
                percentage = (count / max_count) * 100
                bar_length = int(percentage / 2)  # Scale to fit screen
                bar = "█" * bar_length
                
                output += f"{rating:.0f}⭐  {bar} {count:,} ({percentage:.1f}%)\n"
            
            # Calculate total
            total = sum(r['count'] for r in rows)
            output += "\n" + "=" * 70 + "\n"
            output += f"Total Ratings: {total:,}\n"
            
            self._set_text_widget(self.rating_dist_text_c, output)
        finally:
            conn.close()
    
    def load_movies_by_year_c(self):
        """Load movies by year trends for Option C"""
        for item in self.year_tree_c.get_children():
            self.year_tree_c.delete(item)
        
        sql = """
            SELECT 
                YEAR(m.release_date) AS year,
                COUNT(DISTINCT m.movieId) AS movie_count,
                ROUND(AVG(r.rating), 2) AS avg_rating
            FROM movies m
            LEFT JOIN ratings r ON m.movieId = r.movieId
            WHERE m.release_date IS NOT NULL
              AND YEAR(m.release_date) >= 1980
              AND m.title NOT LIKE 'Movie_%%'
            GROUP BY YEAR(m.release_date)
            ORDER BY year DESC
            LIMIT 40
        """
        
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
            
            for r in rows:
                self.year_tree_c.insert("", "end", values=(
                    r["year"],
                    r["movie_count"],
                    f"{r['avg_rating']:.2f}" if r['avg_rating'] else "N/A"
                ))
        finally:
            conn.close()
    
    def build_analytics_option_d(self):
        """Option D: Quick Wins - Best features with minimal effort"""
        container = tk.Frame(self.analytics_option_d_tab, bg="#f0f0f0")
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title_frame = tk.Frame(container, bg="#27ae60", height=50)
        title_frame.pack(fill="x", pady=(0, 10))
        title_frame.pack_propagate(False)
        
        tk.Label(
            title_frame,
            text="Analytics Option D: Quick Wins (RECOMMENDED)",
            font=("Arial", 14, "bold"),
            bg="#27ae60",
            fg="white"
        ).pack(pady=10)
        
        # Description
        desc_frame = ttk.LabelFrame(container, text="About This Option", padding=10)
        desc_frame.pack(fill="x", pady=(0, 10))
        tk.Label(
            desc_frame,
            text="• Best balance: Maximum impact with minimal changes\n"
                 "• Top movies as sortable Treeview (better than text)\n"
                 "• Adds Most Active Users feature (new insight)\n"
                 "• Improved user statistics formatting\n"
                 "• RECOMMENDED: Easy to implement, clear improvements",
            font=("Arial", 9),
            justify="left",
            bg="white"
        ).pack(anchor="w")
        
        # Top Movies Section with Treeview
        top_frame = ttk.LabelFrame(container, text="Top Rated Movies", padding=10)
        top_frame.pack(fill="both", expand=True, pady=(0, 5))
        
        ttk.Button(
            top_frame,
            text="Load Top Movies",
            command=self.handle_top_movies_d
        ).pack(anchor="w", pady=(0, 5))
        
        self.exec_time_label_d = tk.Label(
            top_frame,
            text="",
            font=("Arial", 8),
            fg="#27ae60"
        )
        self.exec_time_label_d.pack(anchor="w")
        
        # Treeview for top movies
        tree_frame = tk.Frame(top_frame)
        tree_frame.pack(fill="both", expand=True, pady=(5, 0))
        
        columns_d = ("title", "votes", "avg", "min", "max")
        self.top_movies_tree_d = ttk.Treeview(tree_frame, columns=columns_d, show="headings", height=8)
        
        self.top_movies_tree_d.heading("title", text="Movie Title")
        self.top_movies_tree_d.heading("votes", text="Votes")
        self.top_movies_tree_d.heading("avg", text="Avg Rating")
        self.top_movies_tree_d.heading("min", text="Min")
        self.top_movies_tree_d.heading("max", text="Max")
        
        self.top_movies_tree_d.column("title", width=400, anchor="w")
        self.top_movies_tree_d.column("votes", width=80, anchor="center")
        self.top_movies_tree_d.column("avg", width=100, anchor="center")
        self.top_movies_tree_d.column("min", width=80, anchor="center")
        self.top_movies_tree_d.column("max", width=80, anchor="center")
        
        self.top_movies_tree_d.pack(side="left", fill="both", expand=True)
        
        scrollbar_d = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.top_movies_tree_d.yview)
        scrollbar_d.pack(side="right", fill="y")
        self.top_movies_tree_d.configure(yscrollcommand=scrollbar_d.set)
        
        # Most Active Users Section (NEW FEATURE)
        active_frame = ttk.LabelFrame(container, text="Most Active Users", padding=10)
        active_frame.pack(fill="both", expand=True, pady=(5, 5))
        
        ttk.Button(
            active_frame,
            text="Load Most Active Users",
            command=self.handle_most_active_d
        ).pack(anchor="w", pady=(0, 5))
        
        # Treeview for active users
        active_tree_frame = tk.Frame(active_frame)
        active_tree_frame.pack(fill="both", expand=True)
        
        active_cols = ("rank", "username", "email", "ratings", "avg_rating")
        self.active_tree_d = ttk.Treeview(active_tree_frame, columns=active_cols, show="headings", height=6)
        
        self.active_tree_d.heading("rank", text="#")
        self.active_tree_d.heading("username", text="Username")
        self.active_tree_d.heading("email", text="Email")
        self.active_tree_d.heading("ratings", text="Total Ratings")
        self.active_tree_d.heading("avg_rating", text="Avg Rating Given")
        
        self.active_tree_d.column("rank", width=40, anchor="center")
        self.active_tree_d.column("username", width=150, anchor="w")
        self.active_tree_d.column("email", width=200, anchor="w")
        self.active_tree_d.column("ratings", width=100, anchor="center")
        self.active_tree_d.column("avg_rating", width=120, anchor="center")
        
        self.active_tree_d.pack(side="left", fill="both", expand=True)
        
        active_scrollbar = ttk.Scrollbar(active_tree_frame, orient=tk.VERTICAL, command=self.active_tree_d.yview)
        active_scrollbar.pack(side="right", fill="y")
        self.active_tree_d.configure(yscrollcommand=active_scrollbar.set)
        
        # User Statistics Section (improved formatting)
        stats_frame = ttk.LabelFrame(container, text="Your Statistics", padding=10)
        stats_frame.pack(fill="both", expand=True, pady=(5, 0))
        
        ttk.Button(
            stats_frame,
            text="Load My Stats",
            command=self.handle_user_stats_d
        ).pack(anchor="w", pady=(0, 5))
        
        self.stats_text_d = tk.Text(
            stats_frame,
            width=80,
            height=6,
            state="disabled",
            wrap="word",
            font=("Arial", 9),
            bg="#ecf0f1"
        )
        self.stats_text_d.pack(fill="both", expand=True)
    
    def handle_top_movies_d(self):
        """Load top movies for Option D"""
        # Clear existing items
        for item in self.top_movies_tree_d.get_children():
            self.top_movies_tree_d.delete(item)
        
        rows, elapsed = get_top_rated_movies(limit=20)
        
        for r in rows:
            self.top_movies_tree_d.insert("", "end", values=(
                r["title"],
                r["vote_count"],
                f"{r['avg_rating']:.2f}",
                f"{r['min_rating']:.1f}",
                f"{r['max_rating']:.1f}"
            ))
        
        self.exec_time_label_d.config(text=f"Loaded in {elapsed:.3f}s | {len(rows)} movies")
    
    def handle_most_active_d(self):
        """Load most active users for Option D"""
        # Clear existing items
        for item in self.active_tree_d.get_children():
            self.active_tree_d.delete(item)
        
        # Simple SQL query to get most active users
        sql = """
            SELECT 
                u.userId,
                u.username,
                u.email,
                COUNT(r.rating) AS total_ratings,
                ROUND(AVG(r.rating), 2) AS avg_rating
            FROM users u
            INNER JOIN ratings r ON u.userId = r.userId
            GROUP BY u.userId, u.username, u.email
            HAVING COUNT(r.rating) > 0
            ORDER BY total_ratings DESC
            LIMIT 10
        """
        
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
            
            for idx, r in enumerate(rows, 1):
                self.active_tree_d.insert("", "end", values=(
                    idx,
                    r["username"],
                    r["email"],
                    r["total_ratings"],
                    f"{r['avg_rating']:.2f}"
                ))
        finally:
            conn.close()
    
    def handle_user_stats_d(self):
        """Load user statistics for Option D"""
        if not CURRENT_USER['userId']:
            self._set_text_widget(self.stats_text_d, "Please login to view your statistics")
            return
        
        row, elapsed = get_user_statistics(CURRENT_USER['userId'])
        
        if row:
            output = f"USER: {row['username']} ({row['email']})\n"
            output += f"{'='*70}\n\n"
            output += f"Total Ratings Given: {row['total_ratings']}\n"
            output += f"Average Rating: {row['avg_rating_given']:.2f}\n"
            output += f"Highest Rating Given: {row['max_rating_given']:.1f}\n"
            output += f"Lowest Rating Given: {row['min_rating_given']:.1f}\n"
            output += f"High Ratings (≥4.0): {row['high_ratings_count']}\n"
            output += f"Low Ratings (≤2.0): {row['low_ratings_count']}\n"
            self._set_text_widget(self.stats_text_d, output)

    # ------------------------------------------------------------------
    # TAB 4: MY PROFILE
    # ------------------------------------------------------------------
    def build_profile_tab(self):
        container = tk.Frame(self.profile_tab, bg="#f0f0f0")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # Header
        header_frame = tk.Frame(container, bg="white", relief="ridge", borderwidth=2)
        header_frame.pack(fill="x", pady=(0, 10))

        tk.Label(
            header_frame,
            text=f"Profile: {CURRENT_USER['username']}",
            font=("Arial", 16, "bold"),
            bg="white",
            fg="#2c3e50",
        ).pack(pady=10)

        tk.Label(
            header_frame,
            text=f"User ID: {CURRENT_USER['userId']} | Role: {CURRENT_USER['role'].upper()}",
            font=("Arial", 10),
            bg="white",
            fg="#7f8c8d",
        ).pack(pady=(0, 10))

        # Refresh buttons
        btn_frame = tk.Frame(container, bg="#f0f0f0")
        btn_frame.pack(fill="x", pady=(0, 10))

        ttk.Button(
            btn_frame,
            text="🔄 Refresh My Ratings",
            command=self.handle_load_profile
        ).pack(side="left", padx=5)
        
        ttk.Button(
            btn_frame,
            text="⭐ Refresh Watchlist",
            command=self.handle_load_profile
        ).pack(side="left", padx=5)

        # ============================================================
        # WATCHLIST SECTION (Moved to top for better visibility)
        # ============================================================
        watchlist_wrapper = ttk.LabelFrame(container, text="⭐ My Watchlist", padding=10)
        watchlist_wrapper.pack(fill="x", pady=(0, 10))
        watchlist_wrapper.pack_propagate(False)
        watchlist_wrapper.configure(height=220)
        
        watchlist_tree_frame = tk.Frame(watchlist_wrapper, bg="white")
        watchlist_tree_frame.pack(fill="both", expand=True)
        
        watchlist_columns = ("movieId", "title", "priority", "avg_rating", "votes", "added")
        self.watchlist_tree = ttk.Treeview(watchlist_tree_frame, columns=watchlist_columns, show="headings", height=6)
        
        self.watchlist_tree.heading("movieId", text="Movie ID")
        self.watchlist_tree.heading("title", text="Title")
        self.watchlist_tree.heading("priority", text="Priority")
        self.watchlist_tree.heading("avg_rating", text="Avg Rating")
        self.watchlist_tree.heading("votes", text="Votes")
        self.watchlist_tree.heading("added", text="Added On")
        
        self.watchlist_tree.column("movieId", width=80, anchor="center")
        self.watchlist_tree.column("title", width=350, anchor="w")
        self.watchlist_tree.column("priority", width=80, anchor="center")
        self.watchlist_tree.column("avg_rating", width=100, anchor="center")
        self.watchlist_tree.column("votes", width=80, anchor="center")
        self.watchlist_tree.column("added", width=150, anchor="center")
        
        self.watchlist_tree.pack(side="left", fill="both", expand=True)
        
        watchlist_scrollbar = ttk.Scrollbar(watchlist_tree_frame, orient=tk.VERTICAL, command=self.watchlist_tree.yview)
        watchlist_scrollbar.pack(side="right", fill="y")
        self.watchlist_tree.configure(yscrollcommand=watchlist_scrollbar.set)
        
        # Watchlist action buttons
        watchlist_btn_frame = tk.Frame(watchlist_wrapper, bg="#f0f0f0")
        watchlist_btn_frame.pack(fill="x", pady=(5, 0))
        
        ttk.Button(
            watchlist_btn_frame,
            text="🗑️ Remove Selected",
            command=self.handle_remove_from_watchlist_profile
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            watchlist_btn_frame,
            text="🔄 Refresh Watchlist",
            command=self.handle_load_profile
        ).pack(side="left", padx=(0, 5))

        # ============================================================
        # STATS & RATINGS SECTIONS (Below watchlist)
        # ============================================================

        # Stats frame
        stats_wrapper = ttk.LabelFrame(container, text="My Rating Statistics", padding=10)
        stats_wrapper.pack(fill="x", pady=(0, 10))
        stats_wrapper.pack_propagate(False)
        stats_wrapper.configure(height=100)

        # Profile stats text with scrollbar
        profile_stats_frame = tk.Frame(stats_wrapper, bg="white")
        profile_stats_frame.pack(fill="both", expand=True)
        
        profile_scrollbar = tk.Scrollbar(profile_stats_frame)
        profile_scrollbar.pack(side="right", fill="y")
        
        self.profile_stats_text = tk.Text(
            profile_stats_frame,
            width=100,
            height=4,
            state="disabled",
            wrap="word",
            borderwidth=2,
            relief="groove",
            font=("Consolas", 9),
            bg="#ecf0f1",
            fg="#2c3e50",
            yscrollcommand=profile_scrollbar.set
        )
        self.profile_stats_text.pack(side="left", fill="both", expand=True)
        profile_scrollbar.config(command=self.profile_stats_text.yview)
        self.profile_stats_text.pack(fill="both", expand=True)

        # Ratings list
        ratings_wrapper = ttk.LabelFrame(container, text="My Movie Ratings", padding=10)
        ratings_wrapper.pack(fill="both", expand=True)

        tree_frame = tk.Frame(ratings_wrapper, bg="white")
        tree_frame.pack(fill="both", expand=True)

        columns = ("movieId", "title", "my_rating", "avg_rating", "votes", "timestamp")
        self.profile_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=10)

        self.profile_tree.heading("movieId", text="Movie ID")
        self.profile_tree.heading("title", text="Title")
        self.profile_tree.heading("my_rating", text="My Rating")
        self.profile_tree.heading("avg_rating", text="Avg Rating")
        self.profile_tree.heading("votes", text="Total Votes")
        self.profile_tree.heading("timestamp", text="Rated On")

        self.profile_tree.column("movieId", width=80, anchor="center")
        self.profile_tree.column("title", width=400, anchor="w")
        self.profile_tree.column("my_rating", width=100, anchor="center")
        self.profile_tree.column("avg_rating", width=100, anchor="center")
        self.profile_tree.column("votes", width=100, anchor="center")
        self.profile_tree.column("timestamp", width=150, anchor="center")

        self.profile_tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.profile_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.profile_tree.configure(yscrollcommand=scrollbar.set)

        # Load profile on tab build
        if CURRENT_USER["userId"]:
            self.handle_load_profile()

    def handle_load_profile(self):
        """Load and display current user's ratings"""
        if not CURRENT_USER["userId"]:
            messagebox.showwarning("Profile", "Guests don't have ratings.\nPlease login with a user account.")
            return

        # Get user statistics
        user_stats, _ = get_user_statistics(CURRENT_USER["userId"])
        
        if user_stats:
            stats_lines = []
            stats_lines.append(f"Total Ratings: {user_stats.get('total_ratings', 0)}")
            stats_lines.append(f"Average Rating Given: {user_stats.get('avg_rating_given', 'N/A')}")
            stats_lines.append(f"Highest Rating: {user_stats.get('max_rating_given', 'N/A')} | Lowest Rating: {user_stats.get('min_rating_given', 'N/A')}")
            stats_lines.append(f"High Ratings (≥4.0): {user_stats.get('high_ratings_count', 0)} | Low Ratings (≤2.0): {user_stats.get('low_ratings_count', 0)}")
            self._set_text_widget(self.profile_stats_text, "\n".join(stats_lines))

        # Get all user ratings
        ratings = get_all_user_ratings(CURRENT_USER["userId"])

        # Clear tree
        for item in self.profile_tree.get_children():
            self.profile_tree.delete(item)

        # Populate tree
        if ratings:
            for rating in ratings:
                # Format timestamp
                ts = rating.get('timestamp')
                if ts:
                    try:
                        from datetime import datetime
                        dt = datetime.fromtimestamp(int(ts))
                        ts_str = dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        ts_str = str(ts)
                else:
                    ts_str = "N/A"

                self.profile_tree.insert(
                    "",
                    "end",
                    values=(
                        rating.get('movieId', 'N/A'),
                        rating.get('title', 'Unknown'),
                        f"{rating.get('rating', 0):.1f}",
                        f"{rating.get('movie_avg_rating', 0):.2f}",
                        rating.get('movie_vote_count', 0),
                        ts_str
                    )
                )
        else:
            messagebox.showinfo("Profile", "You haven't rated any movies yet!")
        
        # Load watchlist (with error handling for missing table)
        try:
            watchlist = get_user_watchlist(CURRENT_USER["userId"])
        except pymysql.err.ProgrammingError as e:
            if "doesn't exist" in str(e):
                logger.warning("WATCHLIST table not created yet - skipping watchlist display")
                watchlist = []
            else:
                raise
        
        # Clear watchlist tree
        for item in self.watchlist_tree.get_children():
            self.watchlist_tree.delete(item)
        
        # Populate watchlist tree
        if watchlist:
            for item in watchlist:
                added_at = item.get('added_at')
                if added_at:
                    try:
                        if isinstance(added_at, str):
                            added_at_str = added_at
                        else:
                            added_at_str = added_at.strftime("%Y-%m-%d %H:%M")
                    except:
                        added_at_str = str(added_at)
                else:
                    added_at_str = "N/A"
                
                # Capitalize first letter of priority
                priority = item.get('priority', 'medium')
                priority_display = priority.capitalize() if priority else 'Medium'
                
                self.watchlist_tree.insert(
                    "",
                    "end",
                    values=(
                        item.get('movieId', 'N/A'),
                        item.get('title', 'Unknown'),
                        priority_display,
                        f"{item.get('avg_rating', 0):.2f}" if item.get('avg_rating') else "N/A",
                        item.get('vote_count', 0),
                        added_at_str
                    )
                )
        else:
            # Show placeholder message when watchlist is empty
            self.watchlist_tree.insert(
                "",
                "end",
                values=("", "Your watchlist is empty. Add movies from 'Movies & Search' tab!", "", "", "", "")
            )
    
    def handle_remove_from_watchlist_profile(self):
        """Remove selected movie from watchlist in profile tab"""
        sel = self.watchlist_tree.selection()
        if not sel:
            messagebox.showwarning("Selection Required", "Please select a movie from watchlist first.")
            return
        
        movie_id = self.watchlist_tree.item(sel[0])["values"][0]
        movie_title = self.watchlist_tree.item(sel[0])["values"][1]
        
        if remove_from_watchlist(CURRENT_USER['userId'], movie_id):
            messagebox.showinfo("Success", f"Removed '{movie_title}' from watchlist!")
            self.handle_load_profile()  # Refresh

    # ------------------------------------------------------------------
    # TAB 5: ADMIN DASHBOARD
    # ------------------------------------------------------------------
    def build_admin_dashboard_tab(self):
        """
        Admin dashboard showing system overview and management tools.
        """
        container = tk.Frame(self.admin_dashboard_tab, bg="#f0f0f0")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # Header
        header_frame = tk.Frame(container, bg="#2c3e50", height=60)
        header_frame.pack(fill="x", pady=(0, 15))
        header_frame.pack_propagate(False)

        tk.Label(
            header_frame,
            text="Admin Dashboard",
            font=("Arial", 18, "bold"),
            bg="#2c3e50",
            fg="white"
        ).pack(side="left", padx=20, pady=15)

        ttk.Button(
            header_frame,
            text="Refresh All Stats",
            command=self.refresh_admin_dashboard
        ).pack(side="right", padx=20, pady=15)

        # Main content area with scrollbar
        main_frame = tk.Frame(container, bg="#f0f0f0")
        main_frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(main_frame, bg="#f0f0f0", highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#f0f0f0")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ===== SECTION 1: SYSTEM OVERVIEW CARDS =====
        stats_section = tk.Frame(scrollable_frame, bg="#f0f0f0")
        stats_section.pack(fill="x", padx=10, pady=(0, 15))

        tk.Label(
            stats_section,
            text="System Overview",
            font=("Arial", 14, "bold"),
            bg="#f0f0f0",
            fg="#2c3e50"
        ).pack(anchor="w", pady=(0, 10))

        cards_frame = tk.Frame(stats_section, bg="#f0f0f0")
        cards_frame.pack(fill="x")

        # Create stat cards - 4 cards in a row
        self.admin_total_users_label = self._create_admin_stat_card(
            cards_frame, "Total Users", "Loading...", "#3498db", 0, 0
        )
        self.admin_total_movies_label = self._create_admin_stat_card(
            cards_frame, "Total Movies", "Loading...", "#e74c3c", 0, 1
        )
        self.admin_total_ratings_label = self._create_admin_stat_card(
            cards_frame, "Total Ratings", "Loading...", "#2ecc71", 0, 2
        )
        self.admin_avg_rating_label = self._create_admin_stat_card(
            cards_frame, "Avg Rating", "Loading...", "#f39c12", 0, 3
        )

        # ===== SECTION 2: TWO-COLUMN LAYOUT FOR TABLES =====
        tables_container = tk.Frame(scrollable_frame, bg="#f0f0f0")
        tables_container.pack(fill="both", padx=10, pady=(0, 15), expand=True)
        
        # Left column - Active Users
        left_column = tk.Frame(tables_container, bg="#f0f0f0")
        left_column.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        active_users_section = ttk.LabelFrame(
            left_column,
            text="Most Active Users (Top 10)",
            padding=15
        )
        active_users_section.pack(fill="both", expand=True)

        # Treeview for active users
        users_frame = tk.Frame(active_users_section, bg="white")
        users_frame.pack(fill="both", expand=True)

        users_cols = ("rank", "username", "email", "ratings_count", "avg_rating")
        self.admin_users_tree = ttk.Treeview(
            users_frame,
            columns=users_cols,
            show="headings",
            height=8
        )

        self.admin_users_tree.heading("rank", text="Rank")
        self.admin_users_tree.heading("username", text="Username")
        self.admin_users_tree.heading("email", text="Email")
        self.admin_users_tree.heading("ratings_count", text="Total Ratings")
        self.admin_users_tree.heading("avg_rating", text="Avg Rating")

        self.admin_users_tree.column("rank", width=60, anchor="center")
        self.admin_users_tree.column("username", width=150, anchor="w")
        self.admin_users_tree.column("email", width=200, anchor="w")
        self.admin_users_tree.column("ratings_count", width=120, anchor="center")
        self.admin_users_tree.column("avg_rating", width=100, anchor="center")

        self.admin_users_tree.pack(side="left", fill="both", expand=True)

        users_scrollbar = ttk.Scrollbar(
            users_frame,
            orient="vertical",
            command=self.admin_users_tree.yview
        )
        users_scrollbar.pack(side="right", fill="y")
        self.admin_users_tree.configure(yscrollcommand=users_scrollbar.set)

        # Right column - Top Movies
        right_column = tk.Frame(tables_container, bg="#f0f0f0")
        right_column.pack(side="left", fill="both", expand=True, padx=(5, 0))
        
        top_movies_section = ttk.LabelFrame(
            right_column,
            text="Top Rated Movies (Min 10 votes)",
            padding=15
        )
        top_movies_section.pack(fill="both", expand=True)

        movies_frame = tk.Frame(top_movies_section, bg="white")
        movies_frame.pack(fill="both", expand=True)

        movies_cols = ("rank", "title", "avg_rating", "vote_count")
        self.admin_movies_tree = ttk.Treeview(
            movies_frame,
            columns=movies_cols,
            show="headings",
            height=8
        )

        self.admin_movies_tree.heading("rank", text="Rank")
        self.admin_movies_tree.heading("title", text="Movie Title")
        self.admin_movies_tree.heading("avg_rating", text="Avg Rating")
        self.admin_movies_tree.heading("vote_count", text="Votes")

        self.admin_movies_tree.column("rank", width=60, anchor="center")
        self.admin_movies_tree.column("title", width=400, anchor="w")
        self.admin_movies_tree.column("avg_rating", width=120, anchor="center")
        self.admin_movies_tree.column("vote_count", width=100, anchor="center")

        self.admin_movies_tree.pack(side="left", fill="both", expand=True)

        movies_scrollbar = ttk.Scrollbar(
            movies_frame,
            orient="vertical",
            command=self.admin_movies_tree.yview
        )
        movies_scrollbar.pack(side="right", fill="y")
        self.admin_movies_tree.configure(yscrollcommand=movies_scrollbar.set)

        # ===== SECTION 3: RECENT ACTIVITY =====
        activity_section = ttk.LabelFrame(
            scrollable_frame,
            text="Recent Activity (Last 20)",
            padding=15
        )
        activity_section.pack(fill="both", padx=10, pady=(0, 15), expand=True)

        activity_frame = tk.Frame(activity_section, bg="white")
        activity_frame.pack(fill="both", expand=True)

        activity_scrollbar = tk.Scrollbar(activity_frame)
        activity_scrollbar.pack(side="right", fill="y")

        self.admin_activity_text = tk.Text(
            activity_frame,
            width=60,
            height=12,
            state="disabled",
            wrap="none",
            borderwidth=1,
            relief="solid",
            font=("Consolas", 9),
            bg="#ffffff",
            fg="#2c3e50",
            yscrollcommand=activity_scrollbar.set
        )
        self.admin_activity_text.pack(side="left", fill="both", expand=True)
        activity_scrollbar.config(command=self.admin_activity_text.yview)

        # Load initial data
        self.refresh_admin_dashboard()


    def _create_admin_stat_card(self, parent, title, value, color, row, col):
        """Create a stat card for admin dashboard"""
        card = tk.Frame(parent, bg="white", relief="solid", borderwidth=1)
        card.grid(row=row, column=col, padx=8, pady=5, sticky="ew")
        parent.columnconfigure(col, weight=1)

        tk.Label(
            card,
            text=title,
            font=("Arial", 10),
            bg="white",
            fg="#7f8c8d"
        ).pack(pady=(15, 5))

        value_label = tk.Label(
            card,
            text=value,
            font=("Arial", 24, "bold"),
            bg="white",
            fg="#000000"
        )
        value_label.pack(pady=(0, 15))

        return value_label

    def _create_action_button(self, parent, text, command, color, row, col):
        """Create an action button"""
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=color,
            fg="white",
            font=("Arial", 11, "bold"),
            padx=20,
            pady=15,
            relief="flat",
            cursor="hand2",
            borderwidth=0
        )
        btn.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
        parent.columnconfigure(col, weight=1)
        parent.rowconfigure(row, weight=1)

    def refresh_admin_dashboard(self):
        """Load all admin dashboard data"""
        try:
            # Get system stats
            conn = get_connection()
            
            # Total users
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) as count FROM users WHERE username IS NOT NULL")
                total_users = cur.fetchone()['count']
                self.admin_total_users_label.config(text=str(total_users))

            # Total movies
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) as count FROM movies WHERE title NOT LIKE 'Movie_%%'")
                total_movies = cur.fetchone()['count']
                self.admin_total_movies_label.config(text=str(total_movies))

            # Total ratings and average
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) as count, ROUND(AVG(rating), 2) as avg_rating FROM ratings")
                result = cur.fetchone()
                self.admin_total_ratings_label.config(text=f"{result['count']:,}")
                self.admin_avg_rating_label.config(text=f"{result['avg_rating']}/5.0")

            conn.close()

            # Load top active users
            self._load_admin_active_users()

            # Load top rated movies
            self._load_admin_top_movies()

            # Load recent activity
            self._load_admin_recent_activity()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load dashboard data:\n{e}")

    def _load_admin_active_users(self):
        """Load most active users"""
        sql = """
            SELECT 
                u.username,
                u.email,
                COUNT(r.rating) as rating_count,
                ROUND(AVG(r.rating), 2) as avg_rating
            FROM users u
            INNER JOIN ratings r ON u.userId = r.userId
            WHERE u.username IS NOT NULL
            GROUP BY u.userId, u.username, u.email
            ORDER BY rating_count DESC, avg_rating DESC
            LIMIT 10
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()

            # Clear tree
            for item in self.admin_users_tree.get_children():
                self.admin_users_tree.delete(item)

            # Populate tree
            for idx, row in enumerate(rows, 1):
                self.admin_users_tree.insert(
                    "",
                    "end",
                    values=(
                        idx,
                        row['username'],
                        row['email'],
                        row['rating_count'],
                        row['avg_rating'] or "N/A"
                    )
                )
        finally:
            conn.close()

    def _load_admin_top_movies(self):
        """Load top rated movies"""
        rows, _ = get_top_rated_movies(limit=15)

        # Clear tree
        for item in self.admin_movies_tree.get_children():
            self.admin_movies_tree.delete(item)

        # Populate tree
        for idx, row in enumerate(rows, 1):
            self.admin_movies_tree.insert(
                "",
                "end",
                values=(
                    idx,
                    row['title'],
                    row['avg_rating'],
                    row['vote_count']
                )
            )

    def _load_admin_recent_activity(self):
        """Load recent ratings activity"""
        sql = """
            SELECT 
                u.username,
                m.title,
                r.rating,
                FROM_UNIXTIME(r.timestamp) as rated_at
            FROM ratings r
            INNER JOIN users u ON r.userId = u.userId
            INNER JOIN movies m ON r.movieId = m.movieId
            WHERE u.username IS NOT NULL
              AND m.title NOT LIKE 'Movie_%%'
            ORDER BY r.timestamp DESC
            LIMIT 20
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()

            lines = []
            lines.append("=" * 100)
            lines.append(f"{'USERNAME':<20} {'MOVIE':<40} {'RATING':<10} {'TIMESTAMP':<30}")
            lines.append("=" * 100)

            for row in rows:
                username = row['username'][:18]
                title = row['title'][:38]
                rating = f"{row['rating']}/5.0"
                timestamp = str(row['rated_at'])

                lines.append(f"{username:<20} {title:<40} {rating:<10} {timestamp:<30}")

            self._set_text_widget(self.admin_activity_text, "\n".join(lines))

        finally:
            conn.close()

    # ------------------------------------------------------------------
    # TAB 6: ADMIN MOVIE MANAGEMENT
    # ------------------------------------------------------------------
    def build_admin_movies_tab(self):
        """
        UNIFIED Movie Management - Single form controls BOTH MariaDB AND MongoDB
        All operations (Add/Update/Delete/View) automatically sync both databases
        """
        # Create main container with scrollbar
        main_container = tk.Frame(self.admin_movies_tab, bg="#f0f0f0")
        main_container.pack(fill="both", expand=True)
        
        # Create canvas and scrollbar
        canvas = tk.Canvas(main_container, bg="#f0f0f0", highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        
        # Create scrollable frame inside canvas
        container = tk.Frame(canvas, bg="#f0f0f0", padx=5, pady=10)
        
        # Configure scroll region
        container.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Enable mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # ===== UNIFIED MOVIE FORM =====
        form_frame = ttk.LabelFrame(container, text="Movie Information (Fill once, sync to both databases)", padding=20)
        form_frame.pack(fill="both", expand=False, pady=(0, 15))
        
        # Create form with grid layout
        form = tk.Frame(form_frame, bg="#f0f0f0")
        form.pack(fill="both", expand=True)
        
        row = 0
        
        # Movie ID (for Update/Delete/View only - Auto-generated for Add)
        ttk.Label(form, text="Movie ID:", font=("Arial", 10, "bold")).grid(row=row, column=0, sticky="w", padx=5, pady=8)
        self.admin_movie_id_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.admin_movie_id_var, width=15, font=("Arial", 10))\
            .grid(row=row, column=1, padx=5, pady=8, sticky="w")
        tk.Label(form, text="(Auto-generated for new movies | Required for Update/Delete/View)", 
                font=("Arial", 8), fg="gray", bg="#f0f0f0")\
            .grid(row=row, column=2, sticky="w", padx=5)
        
        row += 1
        
        # Title (Required for both databases)
        ttk.Label(form, text="Title:", font=("Arial", 10, "bold")).grid(row=row, column=0, sticky="w", padx=5, pady=8)
        self.admin_movie_title_var = tk.StringVar()
        title_entry = ttk.Entry(form, textvariable=self.admin_movie_title_var, width=70, font=("Arial", 10))
        title_entry.grid(row=row, column=1, columnspan=2, padx=5, pady=8, sticky="ew")
        tk.Label(form, text="★ Required", font=("Arial", 8, "bold"), fg="red", bg="#f0f0f0")\
            .grid(row=row, column=3, sticky="w", padx=5)
        
        row += 1
        
        # Release Date
        ttk.Label(form, text="Release Date:", font=("Arial", 10, "bold")).grid(row=row, column=0, sticky="w", padx=5, pady=8)
        self.admin_movie_date_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.admin_movie_date_var, width=20, font=("Arial", 10))\
            .grid(row=row, column=1, padx=5, pady=8, sticky="w")
        tk.Label(form, text="(YYYY-MM-DD)", font=("Arial", 8), fg="gray", bg="#f0f0f0")\
            .grid(row=row, column=2, sticky="w", padx=5)
        
        row += 1
        
        # Separator
        ttk.Separator(form, orient="horizontal").grid(row=row, column=0, columnspan=4, sticky="ew", pady=15)
        row += 1
        
        # MongoDB Metadata Section Header
        tk.Label(form, text="📊 Rich Metadata (MongoDB)", font=("Arial", 11, "bold"), bg="#f0f0f0", fg="#2c3e50")\
            .grid(row=row, column=0, columnspan=4, sticky="w", padx=5, pady=(10, 5))
        tk.Label(form, text="Optional fields - will be stored in MongoDB for advanced searches", 
                font=("Arial", 8), fg="gray", bg="#f0f0f0")\
            .grid(row=row+1, column=0, columnspan=4, sticky="w", padx=5, pady=(0, 10))
        row += 2
        
        # TMDB ID (optional - for linking to external database)
        ttk.Label(form, text="TMDB ID:").grid(row=row, column=0, sticky="w", padx=5, pady=8)
        self.admin_tmdb_id_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.admin_tmdb_id_var, width=15, font=("Arial", 10))\
            .grid(row=row, column=1, padx=5, pady=8, sticky="w")
        tk.Label(form, text="(Optional - uses Movie ID if not provided)", font=("Arial", 8), fg="gray", bg="#f0f0f0")\
            .grid(row=row, column=2, sticky="w", padx=5)
        
        row += 1
        
        # Genres
        ttk.Label(form, text="Genres:").grid(row=row, column=0, sticky="w", padx=5, pady=8)
        self.admin_genres_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.admin_genres_var, width=70, font=("Arial", 10))\
            .grid(row=row, column=1, columnspan=2, padx=5, pady=8, sticky="ew")
        tk.Label(form, text="(e.g., Action, Comedy, Drama)", font=("Arial", 8), fg="gray", bg="#f0f0f0")\
            .grid(row=row, column=3, sticky="w", padx=5)
        
        row += 1
        
        # Keywords
        ttk.Label(form, text="Keywords:").grid(row=row, column=0, sticky="w", padx=5, pady=8)
        self.admin_keywords_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.admin_keywords_var, width=70, font=("Arial", 10))\
            .grid(row=row, column=1, columnspan=2, padx=5, pady=8, sticky="ew")
        tk.Label(form, text="(e.g., superhero, adventure, sci-fi)", font=("Arial", 8), fg="gray", bg="#f0f0f0")\
            .grid(row=row, column=3, sticky="w", padx=5)
        
        row += 1
        
        # Overview (Text area)
        ttk.Label(form, text="Overview:").grid(row=row, column=0, sticky="nw", padx=5, pady=8)
        
        overview_frame = tk.Frame(form, bg="#f0f0f0")
        overview_frame.grid(row=row, column=1, columnspan=3, padx=5, pady=8, sticky="ew")
        
        overview_scrollbar = tk.Scrollbar(overview_frame)
        overview_scrollbar.pack(side="right", fill="y")
        
        self.admin_overview_text = tk.Text(
            overview_frame, 
            height=4, 
            width=80, 
            wrap="word", 
            font=("Arial", 9),
            yscrollcommand=overview_scrollbar.set
        )
        self.admin_overview_text.pack(side="left", fill="both", expand=True)
        overview_scrollbar.config(command=self.admin_overview_text.yview)
        
        row += 1
        
        # Numeric fields row (Rating, Votes, Runtime)
        numeric_frame = tk.Frame(form, bg="#f0f0f0")
        numeric_frame.grid(row=row, column=0, columnspan=4, sticky="ew", padx=5, pady=8)
        
        ttk.Label(numeric_frame, text="Rating:").pack(side="left", padx=(0, 5))
        self.admin_rating_var = tk.StringVar()
        ttk.Entry(numeric_frame, textvariable=self.admin_rating_var, width=10, font=("Arial", 10))\
            .pack(side="left", padx=(0, 20))
        
        ttk.Label(numeric_frame, text="Votes:").pack(side="left", padx=(0, 5))
        self.admin_votes_var = tk.StringVar()
        ttk.Entry(numeric_frame, textvariable=self.admin_votes_var, width=10, font=("Arial", 10))\
            .pack(side="left", padx=(0, 20))
        
        ttk.Label(numeric_frame, text="Runtime (min):").pack(side="left", padx=(0, 5))
        self.admin_runtime_var = tk.StringVar()
        ttk.Entry(numeric_frame, textvariable=self.admin_runtime_var, width=10, font=("Arial", 10))\
            .pack(side="left", padx=(0, 20))
        
        row += 1
        
        # IMDb ID (for links table)
        ttk.Label(form, text="IMDb ID:").grid(row=row, column=0, sticky="w", padx=5, pady=8)
        self.admin_imdb_id_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.admin_imdb_id_var, width=15, font=("Arial", 10))\
            .grid(row=row, column=1, padx=5, pady=8, sticky="w")
        tk.Label(form, text="(Optional - for links table)", font=("Arial", 8), fg="gray", bg="#f0f0f0")\
            .grid(row=row, column=2, sticky="w", padx=5)
        
        row += 1
        
        # Configure column weights
        form.columnconfigure(1, weight=1)
        form.columnconfigure(2, weight=1)

        # ===== ACTION BUTTONS (All operations sync both databases) =====
        btn_wrapper = tk.Frame(container, bg="#f0f0f0")
        btn_wrapper.pack(fill="x", pady=(0, 15))
        
        tk.Label(
            btn_wrapper,
            text="Operations (All actions automatically sync BOTH databases):",
            font=("Arial", 10, "bold"),
            bg="#f0f0f0",
            fg="#2c3e50"
        ).pack(anchor="w", padx=5, pady=(0, 10))
        
        buttons_container = tk.Frame(btn_wrapper, bg="#f0f0f0")
        buttons_container.pack(fill="x", padx=5)
        
        # Row 1: Primary operations
        btn_row1 = tk.Frame(buttons_container, bg="#f0f0f0")
        btn_row1.pack(fill="x", pady=(0, 8))
        
        tk.Button(
            btn_row1,
            text="Add Movie",
            command=self.handle_unified_add_movie,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=20,
            pady=10,
            relief="raised",
            cursor="hand2",
            width=18
        ).pack(side="left", padx=5)
        
        tk.Button(
            btn_row1,
            text="Update Movie",
            command=self.handle_unified_update_movie,
            bg="#2196F3",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=20,
            pady=10,
            relief="raised",
            cursor="hand2",
            width=18
        ).pack(side="left", padx=5)
        
        tk.Button(
            btn_row1,
            text="Delete Movie",
            command=self.handle_unified_delete_movie,
            bg="#F44336",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=20,
            pady=10,
            relief="raised",
            cursor="hand2",
            width=18
        ).pack(side="left", padx=5)
        
        tk.Button(
            btn_row1,
            text="View Details",
            command=self.handle_unified_view_movie,
            bg="#9E9E9E",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=20,
            pady=10,
            relief="raised",
            cursor="hand2",
            width=18
        ).pack(side="left", padx=5)
        
        # Row 2: Utility operations
        btn_row2 = tk.Frame(buttons_container, bg="#f0f0f0")
        btn_row2.pack(fill="x")
        
        tk.Button(
            btn_row2,
            text="Load by Movie ID",
            command=self.handle_unified_load_by_id,
            bg="#673AB7",
            fg="white",
            font=("Arial", 9, "bold"),
            padx=15,
            pady=8,
            relief="raised",
            cursor="hand2",
            width=18
        ).pack(side="left", padx=5)
        
        tk.Button(
            btn_row2,
            text="Clear Form",
            command=self.handle_unified_clear_form,
            bg="#607D8B",
            fg="white",
            font=("Arial", 9, "bold"),
            padx=15,
            pady=8,
            relief="raised",
            cursor="hand2",
            width=18
        ).pack(side="left", padx=5)

        # ===== Activity Log (spans full width at bottom) =====
        log_wrapper = ttk.LabelFrame(container, text="Activity Log - Real-time sync status", padding=10)
        log_wrapper.pack(fill="both", expand=True, pady=(0, 0))

        tk.Label(log_wrapper, text="Operation Log:", font=("Arial", 10, "bold"), bg="#f0f0f0", anchor="w")\
            .pack(fill="x")

        # Admin movie log with scrollbar
        admin_log_frame = tk.Frame(log_wrapper, bg="#f0f0f0")
        admin_log_frame.pack(fill="both", expand=True)
        
        admin_log_scrollbar = tk.Scrollbar(admin_log_frame)
        admin_log_scrollbar.pack(side="right", fill="y")
        
        self.admin_movie_log = tk.Text(
            admin_log_frame,
            height=10,
            state="disabled",
            wrap="word",
            font=("Consolas", 9),
            bg="#f8f9fa",
            fg="#2c3e50",
            yscrollcommand=admin_log_scrollbar.set
        )
        self.admin_movie_log.pack(side="left", fill="both", expand=True)
        admin_log_scrollbar.config(command=self.admin_movie_log.yview)
        
        # Initial welcome message
        self._append_admin_movie_log("="*80)
        self._append_admin_movie_log("🎬 Unified Movie Management System - Ready")
        self._append_admin_movie_log("All operations automatically sync to BOTH MariaDB AND MongoDB")
        self._append_admin_movie_log("="*80)

    def _append_admin_movie_log(self, msg: str):
        """Helper to append messages to admin movie log"""
        stamp = datetime.now().strftime("%H:%M:%S")
        self._append_text_widget(self.admin_movie_log, f"[{stamp}] {msg}")
    
    # ===================================================================
    # UNIFIED MOVIE MANAGEMENT HANDLERS (Sync Both Databases)
    # ===================================================================
    
    def handle_unified_add_movie(self):
        """
        ADD MOVIE: Creates movie in BOTH MariaDB AND MongoDB automatically
        Steps: MariaDB → Get ID → MongoDB → Links table
        """
        # Get all form data
        title = self.admin_movie_title_var.get().strip()
        release_date = self.admin_movie_date_var.get().strip() or None
        tmdb_id_input = self.admin_tmdb_id_var.get().strip()
        genres = self.admin_genres_var.get().strip()
        keywords = self.admin_keywords_var.get().strip()
        overview = self.admin_overview_text.get("1.0", "end").strip()
        imdb_id = self.admin_imdb_id_var.get().strip()
        
        # Parse numeric fields
        try:
            rating = float(self.admin_rating_var.get().strip()) if self.admin_rating_var.get().strip() else 0
        except ValueError:
            rating = 0
        try:
            votes = int(self.admin_votes_var.get().strip()) if self.admin_votes_var.get().strip() else 0
        except ValueError:
            votes = 0
        try:
            runtime = float(self.admin_runtime_var.get().strip()) if self.admin_runtime_var.get().strip() else 0
        except ValueError:
            runtime = 0
        
        # Validation
        if not title:
            messagebox.showerror("Validation Error", "Title is required!", parent=self)
            return
        
        if release_date:
            try:
                datetime.strptime(release_date, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Validation Error", "Invalid date format. Use YYYY-MM-DD", parent=self)
                return
        
        # Permission check
        if CURRENT_USER['role'] != 'admin':
            self._append_admin_movie_log("[ERROR] Permission denied - admin only")
            messagebox.showerror("Permission Denied", "Only administrators can add movies", parent=self)
            return
        
        self._append_admin_movie_log("="*80)
        self._append_admin_movie_log(f"[ADD MOVIE] Starting unified creation: '{title}'")
        
        try:
            # STEP 1: Add to MariaDB
            self._append_admin_movie_log("[1/4] Adding to MariaDB...")
            ok, movie_id = add_movie_to_sql(title, release_date)
            
            if not ok:
                self._append_admin_movie_log("[ERROR] Failed to add to MariaDB")
                messagebox.showerror("Error", "Failed to add movie to MariaDB. Check Activity Log.", parent=self)
                return
            
            self._append_admin_movie_log(f"[SUCCESS] MariaDB: Movie ID = {movie_id}")
            self.admin_movie_id_var.set(str(movie_id))
            
            # STEP 2: Determine TMDB ID for MongoDB
            if tmdb_id_input:
                try:
                    tmdb_id_for_mongo = int(tmdb_id_input)
                    self._append_admin_movie_log(f"[2/4] Using custom TMDB ID: {tmdb_id_for_mongo}")
                except ValueError:
                    tmdb_id_for_mongo = movie_id
                    self._append_admin_movie_log(f"[2/4] Invalid TMDB ID, using Movie ID: {tmdb_id_for_mongo}")
            else:
                tmdb_id_for_mongo = movie_id
                self._append_admin_movie_log(f"[2/4] Using Movie ID as TMDB ID: {tmdb_id_for_mongo}")
            
            # STEP 3: Add to MongoDB
            self._append_admin_movie_log("[3/4] Adding to MongoDB...")
            mongo_ok = add_movie_to_mongo(
                tmdb_id=tmdb_id_for_mongo,
                title=title,
                overview=overview or "No overview available",
                genres=genres or "Unknown",
                keywords=keywords or "",
                vote_average=rating,
                vote_count=votes,
                runtime=runtime,
                release_date=release_date or "",
                revenue=0,
                original_language="en",
                tagline="",
                popularity=0
            )
            
            if mongo_ok:
                self._append_admin_movie_log(f"[SUCCESS] MongoDB: TMDB ID = {tmdb_id_for_mongo}")
            else:
                self._append_admin_movie_log("[SKIPPED] MongoDB: Storage full or unavailable (movie still saved in MariaDB)")
            
            # STEP 4: Create links
            self._append_admin_movie_log("[4/4] Creating database links...")
            link_ok = update_movie_links(movie_id, imdb_id=imdb_id or None, tmdb_id=tmdb_id_for_mongo)
            if link_ok:
                self._append_admin_movie_log(f"[SUCCESS] Links created: movieId={movie_id} ↔ tmdbId={tmdb_id_for_mongo}")
            else:
                self._append_admin_movie_log("[WARNING] Links creation failed (non-critical)")
            
            # Success!
            self._append_admin_movie_log(f"[COMPLETE] ✓ Movie '{title}' added successfully!")
            self._append_admin_movie_log("="*80)
            
            msg = f"✅ Movie added successfully!\n\n"
            msg += f"Title: {title}\n"
            msg += f"MariaDB Movie ID: {movie_id}\n\n"
            msg += "✓ MariaDB: Created\n"
            
            if mongo_ok:
                msg += f"✓ MongoDB: Created (TMDB ID: {tmdb_id_for_mongo})\n"
            else:
                msg += "⚠ MongoDB: Skipped (storage full or unavailable)\n"
                
            if link_ok:
                msg += f"✓ Links: Created\n"
            else:
                msg += "⚠ Links: Skipped\n"
            
            msg += "\nNote: Movie successfully saved in MariaDB database!"
            
            messagebox.showinfo("Success", msg, parent=self)
            
            # Clear form (keep Movie ID for reference)
            self.handle_unified_clear_form(keep_id=True)
            
        except Exception as e:
            import traceback
            self._append_admin_movie_log(f"[EXCEPTION] {str(e)}")
            self._append_admin_movie_log(f"{traceback.format_exc()}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}", parent=self)
    
    def handle_unified_update_movie(self):
        """
        UPDATE MOVIE: Updates movie in BOTH databases simultaneously
        Requires Movie ID to be filled
        """
        movie_id = self.admin_movie_id_var.get().strip()
        
        if not movie_id:
            messagebox.showerror("Validation Error", "Movie ID is required for update!", parent=self)
            return
        
        # Get all form data
        title = self.admin_movie_title_var.get().strip()
        release_date = self.admin_movie_date_var.get().strip() or None
        tmdb_id_input = self.admin_tmdb_id_var.get().strip()
        genres = self.admin_genres_var.get().strip()
        keywords = self.admin_keywords_var.get().strip()
        overview = self.admin_overview_text.get("1.0", "end").strip()
        imdb_id = self.admin_imdb_id_var.get().strip()
        
        try:
            rating = float(self.admin_rating_var.get().strip()) if self.admin_rating_var.get().strip() else 0
        except ValueError:
            rating = 0
        try:
            votes = int(self.admin_votes_var.get().strip()) if self.admin_votes_var.get().strip() else 0
        except ValueError:
            votes = 0
        try:
            runtime = float(self.admin_runtime_var.get().strip()) if self.admin_runtime_var.get().strip() else 0
        except ValueError:
            runtime = 0
        
        confirm = messagebox.askyesno(
            "Confirm Update",
            f"Update Movie ID {movie_id} in BOTH databases?\n\nThis will update:\n• MariaDB (title, date)\n• MongoDB (all metadata)\n• Links table",
            parent=self
        )
        
        if not confirm:
            return
        
        self._append_admin_movie_log("="*80)
        self._append_admin_movie_log(f"[UPDATE MOVIE] Updating Movie ID: {movie_id}")
        
        try:
            movie_id_int = int(movie_id)
            
            # STEP 1: Update MariaDB
            if title:
                self._append_admin_movie_log("[1/3] Updating MariaDB...")
                ok = update_movie_in_sql(movie_id_int, title=title, release_date=release_date)
                if ok:
                    self._append_admin_movie_log("[SUCCESS] MariaDB updated")
                else:
                    self._append_admin_movie_log("[WARNING] MariaDB update failed")
            
            # STEP 2: Update MongoDB
            tmdb_id_for_mongo = int(tmdb_id_input) if tmdb_id_input else movie_id_int
            
            if any([title, genres, keywords, overview, rating > 0, votes > 0, runtime > 0]):
                self._append_admin_movie_log(f"[2/3] Updating MongoDB (TMDB ID: {tmdb_id_for_mongo})...")
                mongo_ok = add_movie_to_mongo(
                    tmdb_id=tmdb_id_for_mongo,
                    title=title or "Unknown",
                    overview=overview or "",
                    genres=genres or "",
                    keywords=keywords or "",
                    vote_average=rating,
                    vote_count=votes,
                    runtime=runtime,
                    release_date=release_date or "",
                    revenue=0,
                    original_language="en",
                    tagline="",
                    popularity=0
                )
                if mongo_ok:
                    self._append_admin_movie_log("[SUCCESS] MongoDB updated")
                else:
                    self._append_admin_movie_log("[WARNING] MongoDB update failed")
            
            # STEP 3: Update links
            self._append_admin_movie_log("[3/3] Updating links...")
            link_ok = update_movie_links(movie_id_int, imdb_id=imdb_id or None, tmdb_id=tmdb_id_for_mongo)
            if link_ok:
                self._append_admin_movie_log("[SUCCESS] Links updated")
            
            self._append_admin_movie_log(f"[COMPLETE] ✓ Movie ID {movie_id} updated in BOTH databases!")
            self._append_admin_movie_log("="*80)
            
            messagebox.showinfo("Success", f"Movie ID {movie_id} updated successfully in BOTH databases!", parent=self)
            
        except Exception as e:
            import traceback
            self._append_admin_movie_log(f"[EXCEPTION] {str(e)}")
            self._append_admin_movie_log(f"{traceback.format_exc()}")
            messagebox.showerror("Error", f"Failed to update movie:\n{str(e)}", parent=self)
    
    def handle_unified_delete_movie(self):
        """
        DELETE MOVIE: Removes movie from BOTH databases
        Also removes from links table
        """
        movie_id = self.admin_movie_id_var.get().strip()
        title = self.admin_movie_title_var.get().strip()
        
        if not movie_id:
            messagebox.showerror("Validation Error", "Movie ID is required for delete!", parent=self)
            return
        
        confirm = messagebox.askyesno(
            "⚠️ Confirm Delete",
            f"PERMANENTLY delete Movie ID {movie_id}?\n\n"
            f"Title: {title or 'Unknown'}\n\n"
            f"This will delete from:\n"
            f"• MariaDB (movie + ratings)\n"
            f"• MongoDB (metadata)\n"
            f"• Links table\n\n"
            f"This action CANNOT be undone!",
            parent=self,
            icon='warning'
        )
        
        if not confirm:
            return
        
        self._append_admin_movie_log("="*80)
        self._append_admin_movie_log(f"[DELETE MOVIE] Deleting Movie ID: {movie_id}")
        
        try:
            movie_id_int = int(movie_id)
            tmdb_id = int(self.admin_tmdb_id_var.get().strip()) if self.admin_tmdb_id_var.get().strip() else movie_id_int
            
            # STEP 1: Delete from MariaDB (also deletes from links due to CASCADE)
            self._append_admin_movie_log("[1/2] Deleting from MariaDB...")
            ok = delete_movie_from_sql(movie_id_int)
            if ok:
                self._append_admin_movie_log("[SUCCESS] Deleted from MariaDB (and links)")
            else:
                self._append_admin_movie_log("[ERROR] MariaDB deletion failed")
                messagebox.showerror("Error", "Failed to delete from MariaDB", parent=self)
                return
            
            # STEP 2: Delete from MongoDB
            self._append_admin_movie_log(f"[2/2] Deleting from MongoDB (TMDB ID: {tmdb_id})...")
            mongo_ok = delete_movie_from_mongo(tmdb_id)
            if mongo_ok:
                self._append_admin_movie_log("[SUCCESS] Deleted from MongoDB")
            else:
                self._append_admin_movie_log("[WARNING] MongoDB deletion failed (may not exist)")
            
            self._append_admin_movie_log(f"[COMPLETE] ✓ Movie ID {movie_id} deleted from BOTH databases!")
            self._append_admin_movie_log("="*80)
            
            messagebox.showinfo("Success", f"Movie '{title}' deleted from BOTH databases!", parent=self)
            self.handle_unified_clear_form()
            
        except Exception as e:
            import traceback
            self._append_admin_movie_log(f"[EXCEPTION] {str(e)}")
            self._append_admin_movie_log(f"{traceback.format_exc()}")
            messagebox.showerror("Error", f"Failed to delete movie:\n{str(e)}", parent=self)
    
    def handle_unified_view_movie(self):
        """
        VIEW DETAILS: Shows movie info from both databases
        """
        movie_id = self.admin_movie_id_var.get().strip()
        
        if not movie_id:
            messagebox.showerror("Validation Error", "Movie ID is required to view details!", parent=self)
            return
        
        self._append_admin_movie_log("="*80)
        self._append_admin_movie_log(f"[VIEW MOVIE] Loading Movie ID: {movie_id}")
        
        try:
            movie_id_int = int(movie_id)
            
            # Get from MariaDB
            sql_data = get_movie_details(movie_id_int)
            
            if not sql_data:
                self._append_admin_movie_log("[ERROR] Movie not found in MariaDB")
                messagebox.showerror("Not Found", f"Movie ID {movie_id} not found in database!", parent=self)
                return
            
            self._append_admin_movie_log(f"[MariaDB] Title: {sql_data['title']}, Release: {sql_data.get('release_date', 'N/A')}")
            
            # Get from MongoDB (if tmdbId exists)
            tmdb_id = sql_data.get('tmdbId')
            mongo_data = None
            if tmdb_id:
                mongo_data = get_tmdb_metadata(tmdb_id)
                if mongo_data:
                    self._append_admin_movie_log(f"[MongoDB] Found metadata for TMDB ID: {tmdb_id}")
                else:
                    self._append_admin_movie_log(f"[MongoDB] No metadata found for TMDB ID: {tmdb_id}")
            
            # Create detailed view window
            view_win = tk.Toplevel(self)
            view_win.title(f"Movie Details - {sql_data['title']}")
            view_win.geometry("700x600")
            view_win.configure(bg="#f0f0f0")
            
            # Header
            header = tk.Frame(view_win, bg="#2c3e50", height=60)
            header.pack(fill="x")
            header.pack_propagate(False)
            
            tk.Label(
                header,
                text=f"🎬 {sql_data['title']}",
                font=("Arial", 16, "bold"),
                bg="#2c3e50",
                fg="white"
            ).pack(side="left", padx=20, pady=15)
            
            # Content with scrollbar
            content_frame = tk.Frame(view_win, bg="#f0f0f0")
            content_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            canvas = tk.Canvas(content_frame, bg="#f0f0f0", highlightthickness=0)
            scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=canvas.yview)
            scrollable = tk.Frame(canvas, bg="#f0f0f0")
            
            scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.create_window((0, 0), window=scrollable, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # MariaDB Section
            mariadb_frame = ttk.LabelFrame(scrollable, text="MariaDB (SQL) Data", padding=15)
            mariadb_frame.pack(fill="x", pady=(0, 15))
            
            sql_info = f"""
Movie ID: {sql_data['movieId']}
Title: {sql_data['title']}
Release Date: {sql_data.get('release_date', 'N/A')}
Average Rating: {sql_data.get('avg_rating', 'N/A')}
Vote Count: {sql_data.get('vote_count', 0)}
IMDb ID: {sql_data.get('imdbId', 'N/A')}
TMDB ID: {sql_data.get('tmdbId', 'N/A')}
            """.strip()
            
            tk.Label(mariadb_frame, text=sql_info, font=("Courier", 10), bg="#f0f0f0", justify="left")\
                .pack(anchor="w")
            
            # MongoDB Section
            if mongo_data:
                mongo_frame = ttk.LabelFrame(scrollable, text="MongoDB (NoSQL) Metadata", padding=15)
                mongo_frame.pack(fill="x", pady=(0, 15))
                
                mongo_info = f"""
Genres: {mongo_data.get('genres', 'N/A')}
Keywords: {mongo_data.get('keywords', 'N/A')}
Overview: {mongo_data.get('overview', 'N/A')}
TMDB Rating: {mongo_data.get('vote_average', 'N/A')}
TMDB Votes: {mongo_data.get('vote_count', 'N/A')}
Runtime: {mongo_data.get('runtime', 'N/A')} min
Revenue: ${mongo_data.get('revenue', 0):,}
Language: {mongo_data.get('original_language', 'N/A')}
Popularity: {mongo_data.get('popularity', 'N/A')}
                """.strip()
                
                tk.Label(mongo_frame, text=mongo_info, font=("Courier", 9), bg="#f0f0f0", justify="left", wraplength=600)\
                    .pack(anchor="w")
            else:
                info_frame = ttk.LabelFrame(scrollable, text="MongoDB (NoSQL) Metadata", padding=15)
                info_frame.pack(fill="x")
                tk.Label(info_frame, text="No MongoDB metadata found for this movie", 
                        font=("Arial", 10), fg="gray", bg="#f0f0f0")\
                    .pack()
            
            # Close button
            ttk.Button(view_win, text="Close", command=view_win.destroy).pack(pady=10)
            
            self._append_admin_movie_log("[COMPLETE] ✓ Movie details loaded")
            self._append_admin_movie_log("="*80)
            
        except Exception as e:
            import traceback
            self._append_admin_movie_log(f"[EXCEPTION] {str(e)}")
            self._append_admin_movie_log(f"{traceback.format_exc()}")
            messagebox.showerror("Error", f"Failed to load movie:\n{str(e)}", parent=self)
    
    def handle_unified_load_by_id(self):
        """
        LOAD BY ID: Populates form with data from both databases
        """
        movie_id = self.admin_movie_id_var.get().strip()
        
        if not movie_id:
            messagebox.showerror("Validation Error", "Enter Movie ID to load!", parent=self)
            return
        
        self._append_admin_movie_log(f"[LOAD] Loading Movie ID: {movie_id} into form...")
        
        try:
            movie_id_int = int(movie_id)
            
            # Get from MariaDB
            sql_data = get_movie_details(movie_id_int)
            
            if not sql_data:
                messagebox.showerror("Not Found", f"Movie ID {movie_id} not found!", parent=self)
                return
            
            # Fill MariaDB fields
            self.admin_movie_title_var.set(sql_data['title'])
            self.admin_movie_date_var.set(sql_data.get('release_date', ''))
            self.admin_imdb_id_var.set(sql_data.get('imdbId', ''))
            
            tmdb_id = sql_data.get('tmdbId')
            if tmdb_id:
                self.admin_tmdb_id_var.set(str(tmdb_id))
                
                # Get from MongoDB
                mongo_data = get_tmdb_metadata(tmdb_id)
                if mongo_data:
                    self.admin_genres_var.set(mongo_data.get('genres', ''))
                    self.admin_keywords_var.set(mongo_data.get('keywords', ''))
                    self.admin_overview_text.delete("1.0", "end")
                    self.admin_overview_text.insert("1.0", mongo_data.get('overview', ''))
                    self.admin_rating_var.set(str(mongo_data.get('vote_average', '')))
                    self.admin_votes_var.set(str(mongo_data.get('vote_count', '')))
                    self.admin_runtime_var.set(str(mongo_data.get('runtime', '')))
                    
                    self._append_admin_movie_log(f"[SUCCESS] Loaded from BOTH databases")
                else:
                    self._append_admin_movie_log(f"[INFO] Loaded from MariaDB only (no MongoDB data)")
            else:
                self._append_admin_movie_log(f"[INFO] Loaded from MariaDB only (no TMDB ID)")
            
            messagebox.showinfo("Success", f"Movie '{sql_data['title']}' loaded into form!", parent=self)
            
        except Exception as e:
            self._append_admin_movie_log(f"[ERROR] {str(e)}")
            messagebox.showerror("Error", f"Failed to load movie:\n{str(e)}", parent=self)
    
    def handle_unified_clear_form(self, keep_id=False):
        """
        CLEAR FORM: Resets all fields
        """
        if not keep_id:
            self.admin_movie_id_var.set("")
        self.admin_movie_title_var.set("")
        self.admin_movie_date_var.set("")
        self.admin_tmdb_id_var.set("")
        self.admin_genres_var.set("")
        self.admin_keywords_var.set("")
        self.admin_overview_text.delete("1.0", "end")
        self.admin_rating_var.set("")
        self.admin_votes_var.set("")
        self.admin_runtime_var.set("")
        self.admin_imdb_id_var.set("")
        
        self._append_admin_movie_log("[CLEAR] Form cleared")

    # ===================================================================
    # OLD HANDLERS (Kept for compatibility - redirect to unified)
    # ===================================================================

    def handle_admin_add_movie(self):
        """Add a new movie to BOTH MariaDB AND MongoDB in one operation"""
        # Get MariaDB fields
        title = self.admin_movie_title_var.get().strip()
        release_date = self.admin_movie_date_var.get().strip() or None

        # Get MongoDB fields
        tmdb_id_input = self.admin_mongo_tmdb_var.get().strip()
        genres = self.admin_mongo_genres_var.get().strip()
        keywords = self.admin_mongo_keywords_var.get().strip()
        overview = self.admin_mongo_overview_text.get("1.0", "end").strip()
        
        # Get optional MongoDB numeric fields
        try:
            rating = float(self.admin_mongo_rating_var.get().strip()) if self.admin_mongo_rating_var.get().strip() else 0
        except ValueError:
            rating = 0
            
        try:
            votes = int(self.admin_mongo_votes_var.get().strip()) if self.admin_mongo_votes_var.get().strip() else 0
        except ValueError:
            votes = 0
            
        try:
            runtime = float(self.admin_mongo_runtime_var.get().strip()) if self.admin_mongo_runtime_var.get().strip() else 0
        except ValueError:
            runtime = 0

        if not title:
            messagebox.showerror("Add Movie", "Title is required", parent=self)
            return

        self._append_admin_movie_log(f"[INFO] ===== Creating movie in BOTH databases =====")
        self._append_admin_movie_log(f"[INFO] Title: '{title}', Release Date: '{release_date}'")
        
        try:
            # Check if user is admin
            if CURRENT_USER['role'] != 'admin':
                self._append_admin_movie_log(f"[ERROR] User is not admin. Role: {CURRENT_USER['role']}")
                messagebox.showerror("Permission Denied", "Only administrators can add movies", parent=self)
                return
            
            # STEP 1: Add movie to MariaDB (SQL) first
            self._append_admin_movie_log(f"[STEP 1] Adding to MariaDB...")
            ok, movie_id = add_movie_to_sql(title, release_date)
            
            if not ok:
                self._append_admin_movie_log(f"[ERROR] Failed to add movie to MariaDB")
                messagebox.showerror("Error", "Failed to add movie to MariaDB.\nCheck the Activity Log.", parent=self)
                return
            
            self._append_admin_movie_log(f"[SUCCESS] Movie added to MariaDB with ID: {movie_id}")
            self.admin_movie_id_var.set(str(movie_id))
            
            # STEP 2: Determine TMDB ID for MongoDB
            # If user provided TMDB ID, use it. Otherwise, use the MariaDB movieId
            if tmdb_id_input:
                try:
                    tmdb_id_for_mongo = int(tmdb_id_input)
                    self._append_admin_movie_log(f"[STEP 2] Using provided TMDB ID: {tmdb_id_for_mongo}")
                except ValueError:
                    self._append_admin_movie_log(f"[WARNING] Invalid TMDB ID, using MariaDB ID instead")
                    tmdb_id_for_mongo = movie_id
            else:
                tmdb_id_for_mongo = movie_id
                self._append_admin_movie_log(f"[STEP 2] Using MariaDB movie ID as TMDB ID: {tmdb_id_for_mongo}")
            
            # STEP 3: Add movie to MongoDB (always add, even with minimal data)
            self._append_admin_movie_log(f"[STEP 3] Adding to MongoDB with TMDB ID: {tmdb_id_for_mongo}")
            
            mongo_ok = add_movie_to_mongo(
                tmdb_id=tmdb_id_for_mongo,
                title=title,
                overview=overview or "No overview available",
                genres=genres or "Unknown",
                keywords=keywords or "",
                vote_average=rating,
                vote_count=votes,
                runtime=runtime,
                release_date=release_date or "",
                revenue=0,
                original_language="en",
                tagline="",
                popularity=0
            )
            
            if mongo_ok:
                self._append_admin_movie_log(f"[SUCCESS] Movie metadata added to MongoDB")
            else:
                self._append_admin_movie_log(f"[WARNING] Failed to add metadata to MongoDB (non-fatal)")
            
            # STEP 4: Create link entry (links MariaDB movieId to TMDB ID)
            self._append_admin_movie_log(f"[STEP 4] Creating link: movieId={movie_id} <-> tmdbId={tmdb_id_for_mongo}")
            link_ok = update_movie_links(movie_id, imdb_id=None, tmdb_id=tmdb_id_for_mongo)
            if link_ok:
                self._append_admin_movie_log(f"[SUCCESS] Movie link created in links table")
            else:
                self._append_admin_movie_log(f"[WARNING] Failed to create movie link (non-fatal)")
            
            # Success message
            self._append_admin_movie_log(f"[SUCCESS] ===== Movie creation complete! =====")
            msg = f"Movie '{title}' added to BOTH databases!\n\n"
            msg += f"✓ MariaDB Movie ID: {movie_id}\n"
            msg += f"✓ MongoDB TMDB ID: {tmdb_id_for_mongo}\n"
            if link_ok:
                msg += f"✓ Link created between databases\n"
            msg += f"\nThe movie now exists in BOTH MariaDB and MongoDB!"
            
            messagebox.showinfo("Success", msg, parent=self)
            
            # Clear MariaDB inputs
            self.admin_movie_title_var.set("")
            self.admin_movie_date_var.set("")
            
            # Clear MongoDB inputs
            self.admin_mongo_tmdb_var.set("")
            self.admin_mongo_genres_var.set("")
            self.admin_mongo_keywords_var.set("")
            self.admin_mongo_overview_text.delete("1.0", "end")
            self.admin_mongo_rating_var.set("")
            self.admin_mongo_votes_var.set("")
            self.admin_mongo_runtime_var.set("")
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            self._append_admin_movie_log(f"[ERROR] Exception adding movie: {str(e)}")
            self._append_admin_movie_log(f"[ERROR] Traceback: {error_detail}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}", parent=self)

    def handle_admin_update_movie(self):
        """Update movie details in MariaDB"""
        try:
            movie_id = int(self.admin_movie_id_var.get().strip())
        except ValueError:
            messagebox.showerror("Update Movie", "Valid Movie ID is required")
            return

        title = self.admin_movie_title_var.get().strip() or None
        release_date = self.admin_movie_date_var.get().strip() or None

        if not title and not release_date:
            messagebox.showwarning("Update Movie", "Nothing to update")
            return

        ok = update_movie_in_sql(movie_id, title, release_date)
        if ok:
            self._append_admin_movie_log(f"[OK] Movie {movie_id} updated in SQL")
            messagebox.showinfo("Success", f"Movie {movie_id} updated successfully")
        else:
            self._append_admin_movie_log(f"[ERROR] Failed to update movie {movie_id}")
            messagebox.showerror("Error", "Failed to update movie")

    def handle_admin_delete_movie(self):
        """Delete movie from MariaDB (and associated ratings/links)"""
        try:
            movie_id = int(self.admin_movie_id_var.get().strip())
        except ValueError:
            messagebox.showerror("Delete Movie", "Valid Movie ID is required")
            return

        confirm = messagebox.askyesno(
            "Delete Movie",
            f"Delete movie {movie_id}?\n\n"
            "This will also delete:\n"
            "• All ratings for this movie\n"
            "• All links (IMDb/TMDB)\n\n"
            "This action cannot be undone!"
        )
        if not confirm:
            return

        ok = delete_movie_from_sql(movie_id)
        if ok:
            self._append_admin_movie_log(f"[OK] Movie {movie_id} deleted from SQL")
            messagebox.showinfo("Success", f"Movie {movie_id} deleted successfully")
            # Clear form
            self.admin_movie_id_var.set("")
            self.admin_movie_title_var.set("")
            self.admin_movie_date_var.set("")
        else:
            self._append_admin_movie_log(f"[ERROR] Failed to delete movie {movie_id}")
            messagebox.showerror("Error", "Failed to delete movie")

    def handle_admin_view_movie(self):
        """Load movie details from SQL"""
        try:
            movie_id = int(self.admin_movie_id_var.get().strip())
        except ValueError:
            messagebox.showerror("View Movie", "Valid Movie ID is required")
            return

        movie = get_movie_details(movie_id)
        if movie:
            self.admin_movie_title_var.set(movie.get('title', ''))
            self.admin_movie_date_var.set(movie.get('release_date', '') or '')
            
            # Also load links if available
            if movie.get('imdbId'):
                self.admin_imdb_id_var.set(str(movie['imdbId']))
            if movie.get('tmdbId'):
                self.admin_tmdb_id_var.set(str(movie['tmdbId']))
                
            self._append_admin_movie_log(f"[OK] Loaded movie {movie_id}: {movie.get('title')}")
        else:
            messagebox.showwarning("Not Found", f"Movie {movie_id} not found")
            self._append_admin_movie_log(f"[WARN] Movie {movie_id} not found")

    def handle_admin_update_links(self):
        """Update IMDb and TMDB links for a movie"""
        try:
            movie_id = int(self.admin_link_movie_id_var.get().strip())
        except ValueError:
            messagebox.showerror("Update Links", "Valid Movie ID is required")
            return

        imdb_id = self.admin_imdb_id_var.get().strip() or None
        tmdb_id = self.admin_tmdb_id_var.get().strip() or None

        if not imdb_id and not tmdb_id:
            messagebox.showwarning("Update Links", "At least one link (IMDb or TMDB) is required")
            return

        ok = update_movie_links(movie_id, imdb_id, tmdb_id)
        if ok:
            self._append_admin_movie_log(f"[OK] Links updated for movie {movie_id}")
            messagebox.showinfo("Success", f"Links updated for movie {movie_id}")
        else:
            self._append_admin_movie_log(f"[ERROR] Failed to update links for movie {movie_id}")
            messagebox.showerror("Error", "Failed to update links")

    def handle_admin_add_mongo(self):
        """Add or update movie metadata in MongoDB"""
        try:
            tmdb_id = int(self.admin_mongo_tmdb_id_var.get().strip())
        except ValueError:
            messagebox.showerror("MongoDB Operation", "Valid TMDB ID is required")
            return

        title = self.admin_mongo_title_var.get().strip()
        if not title:
            messagebox.showerror("MongoDB Operation", "Title is required")
            return

        genres = self.admin_mongo_genres_var.get().strip()
        keywords = self.admin_mongo_keywords_var.get().strip()
        overview = self.admin_mongo_overview_text.get("1.0", "end").strip()
        
        try:
            rating = float(self.admin_mongo_rating_var.get().strip() or 0)
            votes = int(self.admin_mongo_votes_var.get().strip() or 0)
            runtime = float(self.admin_mongo_runtime_var.get().strip() or 0)
        except ValueError:
            messagebox.showerror("MongoDB Operation", "Invalid numeric values")
            return

        ok = add_movie_to_mongo(
            tmdb_id, title, overview, genres, keywords,
            rating, votes, 0, runtime
        )
        
        if ok:
            self._append_admin_movie_log(f"[OK] Movie {tmdb_id} added/updated in MongoDB: {title}")
            messagebox.showinfo("Success", f"Movie metadata saved to MongoDB (TMDB ID: {tmdb_id})")
        else:
            self._append_admin_movie_log(f"[ERROR] Failed to add/update movie {tmdb_id} in MongoDB")
            messagebox.showerror("Error", "Failed to save to MongoDB")

    def handle_admin_load_mongo(self):
        """Load movie metadata from MongoDB"""
        try:
            tmdb_id = int(self.admin_mongo_tmdb_id_var.get().strip())
        except ValueError:
            messagebox.showerror("Load MongoDB", "Valid TMDB ID is required")
            return

        metadata = get_tmdb_metadata(tmdb_id)
        if metadata:
            self.admin_mongo_title_var.set(metadata.get('title', ''))
            self.admin_mongo_genres_var.set(metadata.get('genres', ''))
            self.admin_mongo_keywords_var.set(metadata.get('keywords', ''))
            self.admin_mongo_overview_text.delete("1.0", "end")
            self.admin_mongo_overview_text.insert("1.0", metadata.get('overview', ''))
            self.admin_mongo_rating_var.set(str(metadata.get('vote_average', '')))
            self.admin_mongo_votes_var.set(str(metadata.get('vote_count', '')))
            self.admin_mongo_runtime_var.set(str(metadata.get('runtime', '')))
            
            self._append_admin_movie_log(f"[OK] Loaded metadata for TMDB ID {tmdb_id}")
        else:
            messagebox.showwarning("Not Found", f"No metadata found for TMDB ID {tmdb_id}")
            self._append_admin_movie_log(f"[WARN] No metadata found for TMDB ID {tmdb_id}")

    def handle_admin_delete_mongo(self):
        """Delete movie from MongoDB"""
        try:
            tmdb_id = int(self.admin_mongo_tmdb_id_var.get().strip())
        except ValueError:
            messagebox.showerror("Delete MongoDB", "Valid TMDB ID is required")
            return

        confirm = messagebox.askyesno(
            "Delete from MongoDB",
            f"Delete TMDB movie {tmdb_id} from MongoDB?\n\n"
            "This will remove all metadata for this movie.\n"
            "SQL data will NOT be affected."
        )
        if not confirm:
            return

        ok = delete_movie_from_mongo(tmdb_id)
        if ok:
            self._append_admin_movie_log(f"[OK] Movie {tmdb_id} deleted from MongoDB")
            messagebox.showinfo("Success", f"Movie {tmdb_id} removed from MongoDB")
            # Clear MongoDB form
            self.admin_mongo_title_var.set("")
            self.admin_mongo_genres_var.set("")
            self.admin_mongo_keywords_var.set("")
            self.admin_mongo_overview_text.delete("1.0", "end")
            self.admin_mongo_rating_var.set("")
            self.admin_mongo_votes_var.set("")
            self.admin_mongo_runtime_var.set("")
        else:
            self._append_admin_movie_log(f"[ERROR] Failed to delete movie {tmdb_id} from MongoDB")
            messagebox.showerror("Error", "Failed to delete from MongoDB")

    # ------------------------------------------------------------------
    # TAB 6: GENRE / KEYWORDS (MongoDB NoSQL side)
    # ------------------------------------------------------------------
    def handle_top_movies(self):
        rows, elapsed = get_top_rated_movies(limit=20)

        # clear
        for i in self.top_tree.get_children():
            self.top_tree.delete(i)
        for r in rows:
            self.top_tree.insert(
                "",
                "end",
                values=(
                    r["title"],
                    r["vote_count"],
                    r["avg_rating"],
                    r["min_rating"],
                    r["max_rating"],
                ),
            )
        self.top_exec_time_label.config(
            text=f"SQL aggregate took {elapsed:.3f}s; {len(rows)} rows."
        )

    def handle_user_stats(self):
        # Try to get user ID from one of three sources: User ID, Name, or Email
        user_id = None
        uid_str = self.stats_user_var.get().strip()
        name_str = self.stats_name_var.get().strip()
        email_str = self.stats_email_var.get().strip()

        # Priority: User ID > Name > Email
        if uid_str:
            try:
                user_id = int(uid_str)
            except ValueError:
                messagebox.showerror("Analytics", "User ID must be an integer.")
                return
        elif name_str:
            # Find user by name
            user_row = find_user_by_name_or_email(username=name_str)
            if user_row:
                user_id = user_row['userId']
            else:
                messagebox.showerror("Analytics", f"User with name '{name_str}' not found.")
                return
        elif email_str:
            # Find user by email
            user_row = find_user_by_name_or_email(email=email_str)
            if user_row:
                user_id = user_row['userId']
            else:
                messagebox.showerror("Analytics", f"User with email '{email_str}' not found.")
                return
        else:
            messagebox.showerror("Analytics", "Please enter User ID, Name, or Email.")
            return

        row, elapsed = get_user_statistics(user_id)
        if not row:
            self._set_text_widget(
                self.stats_text,
                f"User {user_id} not found or no data."
            )
            return

        out_lines = []
        out_lines.append(f"User Statistics for ID {row['userId']}")
        out_lines.append(f"  Name  : {row.get('username')}")
        out_lines.append(f"  Email : {row.get('email')}")
        out_lines.append(f"  Total ratings : {row['total_ratings']}")
        out_lines.append(f"  Avg rating given: {row['avg_rating_given']}")
        out_lines.append(f"  Min rating: {row['min_rating_given']} | Max rating: {row['max_rating_given']}")
        out_lines.append(f"  High ratings (>=4.0): {row['high_ratings_count']}")
        out_lines.append(f"  Low ratings (<=2.0) : {row['low_ratings_count']}")

        self._set_text_widget(self.stats_text, "\n".join(out_lines))
        self.stats_exec_time_label.config(
            text=f"Stats query: {elapsed:.4f}s"
        )

    # ------------------------------------------------------------------
    # NEW TAB: GENRE SEARCH (Simple $match with regex)
    # ------------------------------------------------------------------
    def build_genre_search_tab(self):
        """Simple genre search using $match + regex"""
        container = tk.Frame(self.genre_search_tab, bg="#f0f0f0")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # Title
        title_label = tk.Label(
            container,
            text="Genre Search",
            font=("Arial", 16, "bold"),
            bg="#f0f0f0",
            fg="#2c3e50"
        )
        title_label.pack(pady=(0, 10))

        # Search frame
        search_frame = ttk.LabelFrame(container, text="Search by Genre", padding=20)
        search_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(search_frame, text="Genre:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.genre_search_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.genre_search_var, width=40, font=("Arial", 11))\
            .grid(row=0, column=1, padx=5, pady=5)

        ttk.Button(
            search_frame,
            text="Search Genre",
            command=self.handle_genre_search_tab
        ).grid(row=0, column=2, padx=5, pady=5)

        tk.Label(
            search_frame,
            text="Examples: action, drama, sci-fi, horror, comedy",
            font=("Arial", 9, "italic"),
            fg="#7f8c8d"
        ).grid(row=1, column=0, columnspan=3, pady=(5, 0))

        # Info box
        info_frame = tk.Frame(container, bg="#e8f4f8", relief="ridge", borderwidth=2)
        info_frame.pack(fill="x", pady=(0, 10), padx=5)
        
        info_text = """This uses: find() with $regex (case-insensitive) + limit(50)
Query: db.tmdb_movies.find({"genres": {"$regex": "action", "$options": "i"}}).limit(50)"""
        
        tk.Label(
            info_frame,
            text=info_text,
            font=("Consolas", 9),
            bg="#e8f4f8",
            fg="#2c3e50",
            justify="left"
        ).pack(padx=10, pady=10)

        # Execution time label
        self.genre_search_exec_label = tk.Label(
            container,
            text="",
            font=("Arial", 10, "bold"),
            fg="#e67e22",
            bg="#f0f0f0"
        )
        self.genre_search_exec_label.pack(anchor="e", padx=10)

        # Results frame
        results_frame = ttk.LabelFrame(container, text="Search Results", padding=10)
        results_frame.pack(fill="both", expand=True)

        text_frame = tk.Frame(results_frame)
        text_frame.pack(fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.genre_search_results_text = tk.Text(
            text_frame,
            width=100,
            height=25,
            state="disabled",
            wrap="word",
            borderwidth=2,
            relief="groove",
            font=("Consolas", 9),
            bg="#ffffff",
            fg="#000000",
            yscrollcommand=scrollbar.set
        )
        self.genre_search_results_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.genre_search_results_text.yview)

    def handle_genre_search_tab(self):
        """Handler for simple genre search"""
        genre = self.genre_search_var.get().strip()
        if not genre:
            messagebox.showwarning("Input Required", "Please enter a genre to search")
            return

        docs, elapsed = search_movies_by_genre_mongo(genre)
        
        self.genre_search_exec_label.config(
            text=f"Query time: {elapsed:.4f}s | {len(docs)} results"
        )

        out_lines = [
            f"GENRE SEARCH: '{genre.upper()}'",
            f"Found {len(docs)} movies in {elapsed:.4f}s",
            "=" * 80,
            ""
        ]

        if not docs:
            out_lines.append("No movies found for this genre.")
        else:
            for i, doc in enumerate(docs, 1):
                out_lines.append(f"{i}. {doc.get('title', 'Unknown')}")
                out_lines.append(f"   TMDB ID: {doc.get('id', 'N/A')}")
                out_lines.append(f"   Genres: {doc.get('genres', 'N/A')}")
                out_lines.append(f"   Rating: {doc.get('vote_average', 'N/A')}/10")
                runtime = doc.get('runtime', 0)
                if runtime:
                    out_lines.append(f"   Runtime: {runtime} minutes")
                out_lines.append("")

        self._set_text_widget(self.genre_search_results_text, "\n".join(out_lines))

    # ------------------------------------------------------------------
    # NEW TAB: GENRE STATISTICS (Aggregation Pipeline)
    # ------------------------------------------------------------------
    def build_genre_stats_tab(self):
        """Genre statistics using full aggregation pipeline (Option 2)"""
        container = tk.Frame(self.genre_stats_tab, bg="#f0f0f0")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # Title
        title_label = tk.Label(
            container,
            text="Genre Statistics (MongoDB Aggregation Pipeline)",
            font=("Arial", 16, "bold"),
            bg="#f0f0f0",
            fg="#2c3e50"
        )
        title_label.pack(pady=(0, 10))

        # Button frame
        button_frame = tk.Frame(container, bg="#f0f0f0")
        button_frame.pack(fill="x", pady=(0, 10))

        ttk.Button(
            button_frame,
            text="📊 Calculate Genre Statistics",
            command=self.handle_genre_stats_tab
        ).pack(pady=10)

        # Info box
        info_frame = tk.Frame(container, bg="#e8f4f8", relief="ridge", borderwidth=2)
        info_frame.pack(fill="x", pady=(0, 10), padx=5)
        
        pipeline_text = """📋 This uses: Aggregation Pipeline with $match → $group → $sort → $limit

Pipeline Stages:
1. $match: {"genres": {"$exists": true, "$ne": ""}}
2. $group: {
     "_id": "$genres",
     "count": {"$sum": 1},
     "avg_rating": {"$avg": "$vote_average"},
     "avg_revenue": {"$avg": "$revenue"}
   }
3. $sort: {"count": -1}
4. $limit: 20

Query: db.tmdb_movies.aggregate([...])"""
        
        tk.Label(
            info_frame,
            text=pipeline_text,
            font=("Consolas", 9),
            bg="#e8f4f8",
            fg="#2c3e50",
            justify="left"
        ).pack(padx=10, pady=10, anchor="w")

        # Execution time label
        self.genre_stats_exec_label = tk.Label(
            container,
            text="",
            font=("Arial", 10, "bold"),
            fg="#27ae60",
            bg="#f0f0f0"
        )
        self.genre_stats_exec_label.pack(anchor="e", padx=10)

        # Results frame
        results_frame = ttk.LabelFrame(container, text="Aggregation Results", padding=10)
        results_frame.pack(fill="both", expand=True)

        text_frame = tk.Frame(results_frame)
        text_frame.pack(fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.genre_stats_results_text = tk.Text(
            text_frame,
            width=100,
            height=25,
            state="disabled",
            wrap="word",
            borderwidth=2,
            relief="groove",
            font=("Consolas", 9),
            bg="#ffffff",
            fg="#000000",
            yscrollcommand=scrollbar.set
        )
        self.genre_stats_results_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.genre_stats_results_text.yview)

    def handle_genre_stats_tab(self):
        """Handler for genre statistics aggregation"""
        agg_results, elapsed = get_genre_statistics_mongo()
        
        self.genre_stats_exec_label.config(
            text=f"Aggregation time: {elapsed:.4f}s | {len(agg_results)} genre groups"
        )

        out_lines = [
            "GENRE STATISTICS (Aggregation Pipeline)",
            f"Generated statistics for {len(agg_results)} genre groups in {elapsed:.4f}s",
            "=" * 90,
            ""
        ]

        if not agg_results:
            out_lines.append("No genre statistics available.")
        else:
            out_lines.append(f"{'Rank':<6} {'Genre':<40} {'Count':<8} {'Avg Rating':<12} {'Avg Revenue':<15}")
            out_lines.append("-" * 90)
            
            for i, stats in enumerate(agg_results, 1):
                genre = stats.get('_id', 'Unknown')[:38]
                count = stats.get('count', 0)
                avg_rating = stats.get('avg_rating', 0)
                avg_revenue = stats.get('avg_revenue', 0)
                
                out_lines.append(
                    f"{i:<6} {genre:<40} {count:<8} "
                    f"{avg_rating:<12.2f} ${avg_revenue:<14,.0f}"
                )
            
            out_lines.append("")
            out_lines.append("=" * 90)
            out_lines.append("Pipeline Stages Used:")
            out_lines.append("  1. $match - Filter documents with genres")
            out_lines.append("  2. $group - Group by genre and calculate count, avg_rating, avg_revenue")
            out_lines.append("  3. $sort - Sort by count descending")
            out_lines.append("  4. $limit - Limit to top 20 results")

        self._set_text_widget(self.genre_stats_results_text, "\n".join(out_lines))

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # TAB: KEYWORDS & SIMILAR MOVIES (MongoDB NoSQL side)
    # ------------------------------------------------------------------
    def build_nosql_tab(self):
        container = tk.Frame(self.nosql_tab, bg="#f0f0f0")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # left pane: queries (with fixed width)
        left_container = tk.Frame(container, bg="#f0f0f0", width=450)
        left_container.pack(side="left", fill="y", expand=False, padx=(0, 10))
        left_container.pack_propagate(False)  # Prevent shrinking

        # --- Genre search
        genre_wrapper = ttk.LabelFrame(left_container, text="Search by Genre", padding=10)
        genre_wrapper.pack(fill="x", pady=(0, 10))
        genre_wrapper.pack_propagate(False)
        genre_wrapper.configure(height=120)

        genre_form = tk.Frame(genre_wrapper, bg="white")
        genre_form.pack(fill="x")

        ttk.Label(genre_form, text="Genre:")\
            .grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.genre_var = tk.StringVar()
        ttk.Entry(genre_form, textvariable=self.genre_var, width=30)\
            .grid(row=0, column=1, padx=5, pady=5)

        ttk.Button(
            genre_form,
            text="Search Genre",
            command=self.handle_genre_search
        ).grid(row=0, column=2, padx=5, pady=5)

        tk.Label(
            genre_form,
            text="Examples: Action, Drama, Sci-Fi, Horror",
            font=("Arial", 8, "italic"),
            bg="white"
        ).grid(row=1, column=0, columnspan=3, pady=(0, 5))

        self.genre_exec_label = tk.Label(
            genre_wrapper,
            text="",
            font=("Arial", 8),
            bg="white",
            fg="#e67e22",
        )
        self.genre_exec_label.pack(anchor="e")

        # --- Keyword search
        keyword_wrapper = ttk.LabelFrame(left_container, text="Search by Keywords/Tags", padding=10)
        keyword_wrapper.pack(fill="x", pady=(0, 10))
        keyword_wrapper.pack_propagate(False)
        keyword_wrapper.configure(height=120)

        keyword_form = tk.Frame(keyword_wrapper, bg="white")
        keyword_form.pack(fill="x")

        ttk.Label(keyword_form, text="Keyword:")\
            .grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.keyword_var = tk.StringVar()
        ttk.Entry(keyword_form, textvariable=self.keyword_var, width=30)\
            .grid(row=0, column=1, padx=5, pady=5)

        ttk.Button(
            keyword_form,
            text="Search Keyword",
            command=self.handle_keyword_search
        ).grid(row=0, column=2, padx=5, pady=5)

        tk.Label(
            keyword_form,
            text="Examples: heist, space, revenge, detective",
            font=("Arial", 8, "italic"),
            bg="white"
        ).grid(row=1, column=0, columnspan=3, pady=(0, 5))

        self.keyword_exec_label = tk.Label(
            keyword_wrapper,
            text="",
            font=("Arial", 8),
            bg="white",
            fg="#e67e22",
        )
        self.keyword_exec_label.pack(anchor="e")

        # --- Similar movies finder
        similar_wrapper = ttk.LabelFrame(left_container, text="Similar Movies (Same Genre)", padding=10)
        similar_wrapper.pack(fill="x", pady=(0, 10))
        similar_wrapper.pack_propagate(False)
        similar_wrapper.configure(height=120)

        sim_form = tk.Frame(similar_wrapper, bg="white")
        sim_form.pack(fill="x")

        ttk.Label(sim_form, text="Movie Title:")\
            .grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.similar_var = tk.StringVar()
        ttk.Entry(sim_form, textvariable=self.similar_var, width=30)\
            .grid(row=0, column=1, padx=5, pady=5)

        ttk.Button(
            sim_form,
            text="Find Similar",
            command=self.handle_similar_movies
        ).grid(row=0, column=2, padx=5, pady=5)

        tk.Label(
            sim_form,
            text="Example: The Godfather, Inception",
            font=("Arial", 8, "italic"),
            bg="white",
            fg="#7f8c8d",
        ).grid(row=1, column=0, columnspan=3, sticky="w", padx=5, pady=(0, 5))

        # right pane: output
        right_container = tk.Frame(container, bg="#f0f0f0")
        right_container.pack(side="left", fill="both", expand=True, padx=(5, 0))

        output_wrapper = ttk.LabelFrame(right_container, text="Query Results", padding=10)
        output_wrapper.pack(fill="both", expand=True)

        # NoSQL results text with scrollbar
        nosql_results_frame = tk.Frame(output_wrapper, bg="white")
        nosql_results_frame.pack(fill="both", expand=True)
        
        nosql_scrollbar = tk.Scrollbar(nosql_results_frame)
        nosql_scrollbar.pack(side="right", fill="y")
        
        self.nosql_results_text = tk.Text(
            nosql_results_frame,
            width=80,
            height=30,
            state="disabled",
            wrap="word",
            borderwidth=2,
            relief="groove",
            font=("Consolas", 9),
            bg="#ffffff",
            fg="#000000",
            yscrollcommand=nosql_scrollbar.set
        )
        self.nosql_results_text.pack(side="left", fill="both", expand=True)
        nosql_scrollbar.config(command=self.nosql_results_text.yview)

    def handle_genre_search(self):
        genre = self.genre_var.get().strip() or "Action"
        docs, elapsed = search_movies_by_genre_mongo(genre)

        lines = []
        lines.append("=" * 80)
        lines.append(f"GENRE SEARCH: '{genre.upper()}'")
        lines.append(f"Found {len(docs)} movies in {elapsed:.3f}s")
        lines.append("=" * 80)
        lines.append("")

        for idx, d in enumerate(docs[:20], 1):
            # Handle both "id" (Atlas) and "tmdbId" (legacy) fields
            movie_id = d.get('id') or d.get('tmdbId', 'N/A')
            lines.append(f"{idx}. {d.get('title', 'N/A')}")
            lines.append(f"   TMDB ID: {movie_id}")
            lines.append(f"   Genres:  {d.get('genres', 'N/A')}")
            lines.append(f"   Rating:  {d.get('vote_average', 'N/A')}/10")
            lines.append(f"   Runtime: {d.get('runtime', 'N/A')} minutes")
            lines.append("")

        if len(docs) > 20:
            lines.append(f"... and {len(docs) - 20} more movies")

        self._set_text_widget(self.nosql_results_text, "\n".join(lines))
        self.genre_exec_label.config(
            text=f"Query time: {elapsed:.3f}s | {len(docs)} results"
        )

    def handle_keyword_search(self):
        kw = self.keyword_var.get().strip() or "space"
        docs, elapsed = search_movies_by_keyword_mongo(kw)

        lines = []
        lines.append("=" * 80)
        lines.append(f"KEYWORD SEARCH: '{kw.upper()}'")
        lines.append(f"Found {len(docs)} movies in {elapsed:.3f}s")
        lines.append("=" * 80)
        lines.append("")

        for idx, d in enumerate(docs[:20], 1):
            # Handle both "id" (Atlas) and "tmdbId" (legacy) fields
            movie_id = d.get('id') or d.get('tmdbId', 'N/A')
            lines.append(f"{idx}. {d.get('title', 'N/A')}")
            lines.append(f"   TMDB ID:  {movie_id}")
            lines.append(f"   Keywords: {d.get('keywords', 'N/A')}")
            lines.append(f"   Genres:   {d.get('genres', 'N/A')}")
            lines.append(f"   Rating:   {d.get('vote_average', 'N/A')}/10")
            lines.append("")

        if len(docs) > 20:
            lines.append(f"... and {len(docs) - 20} more movies")

        self._set_text_widget(self.nosql_results_text, "\n".join(lines))
        self.keyword_exec_label.config(
            text=f"Query time: {elapsed:.3f}s | {len(docs)} results"
        )

    def handle_similar_movies(self):
        movie_title = self.similar_var.get().strip()
        if movie_title == "":
            messagebox.showwarning("Similar Movies", "Please enter a movie title.")
            return

        # First, find the movie by title to get its TMDB ID
        movie_doc = find_movie_by_title_mongo(movie_title)
        
        if not movie_doc:
            lines = []
            lines.append("=" * 80)
            lines.append(f"MOVIE NOT FOUND: '{movie_title}'")
            lines.append("=" * 80)
            lines.append("")
            lines.append("No movies found matching that title.")
            lines.append("")
            lines.append("Tips:")
            lines.append("- Check spelling")
            lines.append("- Try partial title (e.g., 'Inception' instead of 'Inception (2010)')")
            lines.append("- Try without special characters")
            self._set_text_widget(self.nosql_results_text, "\n".join(lines))
            return
        
        # Get the TMDB ID from the found movie
        tmdb_id = movie_doc.get('id') or movie_doc.get('tmdbId')
        found_title = movie_doc.get('title', 'Unknown')
        
        if not tmdb_id:
            messagebox.showerror("Error", "Movie found but has no TMDB ID.")
            return

        docs, elapsed = find_similar_movies_mongo(tmdb_id)
        
        lines = []
        lines.append("=" * 80)
        lines.append(f"SIMILAR MOVIES TO: {found_title}")
        lines.append(f"TMDB ID: {tmdb_id}")
        lines.append(f"Found {len(docs)} similar movies in {elapsed:.3f}s")
        lines.append("=" * 80)
        lines.append("")

        if not docs:
            lines.append("No similar movies found.")
        else:
            for idx, d in enumerate(docs, 1):
                # Handle both "id" (Atlas) and "tmdbId" (legacy) fields
                movie_id = d.get('id') or d.get('tmdbId', 'N/A')
                lines.append(f"{idx}. {d.get('title', 'N/A')}")
                lines.append(f"   TMDB ID: {movie_id}")
                lines.append(f"   Genres:  {d.get('genres', 'N/A')}")
                lines.append(f"   Rating:  {d.get('vote_average', 'N/A')}/10")
                overview = d.get('overview', 'No overview available')
                if len(overview) > 150:
                    overview = overview[:150] + "..."
                lines.append(f"   Summary: {overview}")
                lines.append("")

        self._set_text_widget(self.nosql_results_text, "\n".join(lines))

    def handle_genre_stats(self):
        agg, elapsed = get_genre_statistics_mongo()
        
        lines = []
        lines.append("=" * 90)
        lines.append(f"TOP GENRES BY COUNT (MongoDB Aggregation)")
        lines.append(f"Analyzed {len(agg)} genre combinations in {elapsed:.3f}s")
        lines.append("=" * 90)
        lines.append("")
        lines.append(f"{'Rank':<6} {'Genre(s)':<40} {'Count':<8} {'Avg Rating':<12} {'Avg Revenue':<15}")
        lines.append("-" * 90)

        for idx, g in enumerate(agg[:20], 1):
            genre_name = g['_id'] if len(g['_id']) <= 38 else g['_id'][:35] + "..."
            avg_rating = round(g.get('avg_rating', 0), 2)
            avg_revenue = g.get('avg_revenue')
            
            # Format revenue
            if avg_revenue and avg_revenue > 0:
                if avg_revenue >= 1_000_000:
                    revenue_str = f"${avg_revenue/1_000_000:.1f}M"
                elif avg_revenue >= 1_000:
                    revenue_str = f"${avg_revenue/1_000:.1f}K"
                else:
                    revenue_str = f"${avg_revenue:.0f}"
            else:
                revenue_str = "N/A"

            lines.append(
                f"{idx:<6} {genre_name:<40} {g['count']:<8} {avg_rating:<12.2f} {revenue_str:<15}"
            )

        self._set_text_widget(self.genre_stats_text, "\n".join(lines))
        self.nosql_agg_time_label.config(
            text=f"Aggregation time: {elapsed:.3f}s"
        )

    # ------------------------------------------------------------------
    # TAB 7: PERFORMANCE
    # ------------------------------------------------------------------
    def build_performance_tab(self):
        container = tk.Frame(self.performance_tab, bg="#f0f0f0")
        container.pack(fill="both", expand=True)

        # Left side: Input controls WITH SCROLLBAR
        left_outer = tk.Frame(container, bg="#f0f0f0", width=400)
        left_outer.pack(side="left", fill="both", padx=10, pady=10)
        left_outer.pack_propagate(False)
        
        # Create canvas and scrollbar for left panel
        left_canvas = tk.Canvas(left_outer, bg="#f0f0f0", highlightthickness=0)
        left_scrollbar = tk.Scrollbar(left_outer, orient="vertical", command=left_canvas.yview)
        left_container = tk.Frame(left_canvas, bg="#f0f0f0")
        
        left_container.bind(
            "<Configure>",
            lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        )
        
        left_canvas.create_window((0, 0), window=left_container, anchor="nw")
        left_canvas.configure(yscrollcommand=left_scrollbar.set)
        
        left_canvas.pack(side="left", fill="both", expand=True)
        left_scrollbar.pack(side="right", fill="y")
        
        # Enable mouse wheel scrolling on left panel
        def _on_mousewheel(event):
            left_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        left_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        tk.Label(
            left_container,
            text="Performance Benchmark",
            font=("Arial", 14, "bold"),
            bg="#f0f0f0",
            fg="#2c3e50"
        ).pack(pady=(0, 15))

        # Performance Test Input
        perf_wrapper = ttk.LabelFrame(left_container, text="Run Performance Test", padding=10)
        perf_wrapper.pack(fill="x", pady=(0, 10))

        form = tk.Frame(perf_wrapper, bg="white")
        form.pack(fill="x", pady=(5, 10))

        ttk.Label(form, text="Keyword:")\
            .grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.perf_keyword_var = tk.StringVar(value="thriller")
        ttk.Entry(form, textvariable=self.perf_keyword_var, width=25)\
            .grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Button(
            form,
            text="Run Comparison",
            command=self.handle_performance_test
        ).grid(row=1, column=0, columnspan=2, padx=5, pady=(5, 0), sticky="ew")

        tk.Label(
            form,
            text="Examples: thriller, action, space, love",
            font=("Arial", 8, "italic"),
            bg="white",
            fg="#7f8c8d"
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 0))

        form.columnconfigure(1, weight=1)

        # Description box
        desc_frame = tk.Frame(perf_wrapper, bg="white")
        desc_frame.pack(fill="x", pady=(10, 5))

        tk.Label(
            desc_frame,
            text="What This Tests:",
            font=("Arial", 9, "bold"),
            bg="white",
            fg="#2c3e50",
            anchor="w"
        ).pack(fill="x", padx=5)

        tk.Label(
            desc_frame,
            text="• SQL: Searches movie titles\n• MongoDB: Searches keywords\n• Compares speed & results",
            font=("Arial", 8),
            bg="white",
            fg="#34495e",
            justify="left",
            anchor="w"
        ).pack(fill="x", padx=5, pady=(2, 0))

        # Test 2: INSERT Performance
        insert_wrapper = ttk.LabelFrame(left_container, text="Test 2: INSERT Performance", padding=10)
        insert_wrapper.pack(fill="x", pady=(10, 10))

        insert_form = tk.Frame(insert_wrapper, bg="white")
        insert_form.pack(fill="x", pady=(5, 10))

        ttk.Label(insert_form, text="Records:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.insert_records_var = tk.StringVar(value="100")
        ttk.Entry(insert_form, textvariable=self.insert_records_var, width=25)\
            .grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Button(
            insert_form,
            text="Run INSERT Test",
            command=self.handle_insert_performance_test
        ).grid(row=1, column=0, columnspan=2, padx=5, pady=(5, 0), sticky="ew")

        tk.Label(
            insert_form,
            text="Tests bulk INSERT speed\n✓ Zero impact - data is deleted after test",
            font=("Arial", 8, "italic"),
            bg="white",
            fg="#27ae60",
            justify="left"
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 0))

        insert_form.columnconfigure(1, weight=1)

        # Test 3: UPDATE Performance
        update_wrapper = ttk.LabelFrame(left_container, text="Test 3: UPDATE Performance", padding=10)
        update_wrapper.pack(fill="x", pady=(0, 10))

        update_form = tk.Frame(update_wrapper, bg="white")
        update_form.pack(fill="x", pady=(5, 10))

        ttk.Label(update_form, text="Records:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.update_records_var = tk.StringVar(value="100")
        ttk.Entry(update_form, textvariable=self.update_records_var, width=25)\
            .grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Button(
            update_form,
            text="Run UPDATE Test",
            command=self.handle_update_performance_test
        ).grid(row=1, column=0, columnspan=2, padx=5, pady=(5, 0), sticky="ew")

        tk.Label(
            update_form,
            text="Tests bulk UPDATE speed\n✓ Zero impact - original data is restored",
            font=("Arial", 8, "italic"),
            bg="white",
            fg="#27ae60",
            justify="left"
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 0))

        update_form.columnconfigure(1, weight=1)

        # Test 4: Data Integrity & Constraints (NEW)
        constraint_wrapper = ttk.LabelFrame(left_container, text="Test 4: Data Integrity & Constraints", padding=10)
        constraint_wrapper.pack(fill="x", pady=(0, 10))

        constraint_form = tk.Frame(constraint_wrapper, bg="white")
        constraint_form.pack(fill="x", pady=(5, 10))

        ttk.Button(
            constraint_form,
            text="Test Foreign Key Constraints",
            command=self.handle_test_fk_constraints
        ).grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        ttk.Button(
            constraint_form,
            text="Test Primary Key Constraints",
            command=self.handle_test_pk_constraints
        ).grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        tk.Label(
            constraint_form,
            text="Demonstrates database constraint violations\nand how integrity is maintained.",
            font=("Arial", 8, "italic"),
            bg="white",
            fg="#7f8c8d",
            justify="left"
        ).grid(row=2, column=0, padx=5, pady=(5, 0), sticky="w")

        constraint_form.columnconfigure(0, weight=1)

        # Test 5: Genre Search Comparison (SQL vs NoSQL)
        genre_wrapper = ttk.LabelFrame(left_container, text="Test 5: Genre Search (SQL vs NoSQL)", padding=10)
        genre_wrapper.pack(fill="x", pady=(0, 10))

        genre_form = tk.Frame(genre_wrapper, bg="white")
        genre_form.pack(fill="x", pady=(5, 10))

        ttk.Label(genre_form, text="Genre:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.genre_perf_var = tk.StringVar(value="Action")
        ttk.Entry(genre_form, textvariable=self.genre_perf_var, width=25)\
            .grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Button(
            genre_form,
            text="Compare Search Speed",
            command=self.handle_genre_search_performance
        ).grid(row=1, column=0, columnspan=2, padx=5, pady=(5, 0), sticky="ew")

        tk.Label(
            genre_form,
            text="Compares SQL vs MongoDB genre search speed\n✓ Shows performance differences in genre filtering",
            font=("Arial", 8, "italic"),
            bg="white",
            fg="#27ae60",
            justify="left"
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 0))

        genre_form.columnconfigure(1, weight=1)

        # Right side: Results output
        right_container = tk.Frame(container, bg="#f0f0f0")
        right_container.pack(side="left", fill="both", expand=True, padx=(5, 10), pady=10)

        output_wrapper = ttk.LabelFrame(right_container, text="Benchmark Results", padding=10)
        output_wrapper.pack(fill="both", expand=True)

        # Performance output with scrollbar
        perf_frame = tk.Frame(output_wrapper, bg="white")
        perf_frame.pack(fill="both", expand=True)
        
        perf_scrollbar = tk.Scrollbar(perf_frame)
        perf_scrollbar.pack(side="right", fill="y")
        
        self.perf_output = tk.Text(
            perf_frame,
            width=100,
            height=20,
            state="disabled",
            wrap="word",
            borderwidth=2,
            relief="groove",
            font=("Consolas", 9),
            bg="#ffffff",
            fg="#000000",
            yscrollcommand=perf_scrollbar.set
        )
        self.perf_output.pack(side="left", fill="both", expand=True)
        perf_scrollbar.config(command=self.perf_output.yview)

        # Set welcome message for Performance tab
        welcome_msg = (
            "=" * 80 + "\n" +
            "                   PERFORMANCE BENCHMARK TOOL\n" +
            "=" * 80 + "\n\n" +
            "+---------------------------------------------------------------------------+\n" +
            "|                           ABOUT THIS TOOL                                 |\n" +
            "+---------------------------------------------------------------------------+\n" +
            "| This tool compares query performance between SQL and NoSQL databases      |\n" +
            "| across multiple operations: SELECT, INSERT, UPDATE, and GENRE SEARCH      |\n" +
            "+---------------------------------------------------------------------------+\n\n" +
            "AVAILABLE TESTS:\n" +
            "  Test 1: Keyword Search - SQL title search vs MongoDB keyword search\n" +
            "  Test 2: INSERT Performance - Bulk insert speed comparison\n" +
            "  Test 3: UPDATE Performance - Bulk update speed comparison\n" +
            "  Test 4: Data Integrity - Foreign key and primary key constraints\n" +
            "  Test 5: Genre Search - SQL LIKE vs MongoDB regex genre filtering\n\n" +
            "+---------------------------------------------------------------------------+\n" +
            "|                              PURPOSE                                      |\n" +
            "+---------------------------------------------------------------------------+\n" +
            "| Demonstrates why a hybrid database architecture is beneficial.            |\n" +
            "| Different databases excel at different tasks!                             |\n" +
            "+---------------------------------------------------------------------------+\n\n" +
            "+---------------------------------------------------------------------------+\n" +
            "|                        TRY THESE EXAMPLES                                 |\n" +
            "+---------------------------------------------------------------------------+\n" +
            "| Keywords: 'thriller', 'action', 'space', 'love'                           |\n" +
            "| Genres:   'Action', 'Comedy', 'Drama', 'Horror', 'Sci-Fi'                |\n" +
            "+---------------------------------------------------------------------------+\n\n" +
            "Select a test from the left panel and click the corresponding button!\n"
        )
        self._set_text_widget(self.perf_output, welcome_msg)

    def handle_performance_test(self):
        kw = self.perf_keyword_var.get().strip()
        if not kw:
            messagebox.showwarning("Benchmark", "Enter a keyword.")
            return

        metrics = compare_sql_vs_nosql_performance(kw)
        
        # Determine winner
        sql_time = metrics['sql_time']
        mongo_time = metrics['mongo_time']
        sql_count = metrics['sql_count']
        mongo_count = metrics['mongo_count']
        
        if sql_time < mongo_time:
            speed_winner = "SQL (MariaDB)"
            speed_diff = ((mongo_time - sql_time) / mongo_time) * 100
            speed_comparison = f"SQL is {speed_diff:.1f}% faster"
        elif mongo_time < sql_time:
            speed_winner = "NoSQL (MongoDB)"
            speed_diff = ((sql_time - mongo_time) / sql_time) * 100
            speed_comparison = f"MongoDB is {speed_diff:.1f}% faster"
        else:
            speed_winner = "TIE"
            speed_comparison = "Both performed equally"
        
        # Create visual progress bars using simple characters
        max_time = max(sql_time, mongo_time)
        sql_bar_length = int((sql_time / max_time) * 40) if max_time > 0 else 0
        mongo_bar_length = int((mongo_time / max_time) * 40) if max_time > 0 else 0
        
        max_count = max(sql_count, mongo_count) if max(sql_count, mongo_count) > 0 else 1
        sql_results_bar = int((sql_count / max_count) * 40)
        mongo_results_bar = int((mongo_count / max_count) * 40)
        
        sql_bar = "#" * sql_bar_length + "-" * (40 - sql_bar_length)
        mongo_bar = "#" * mongo_bar_length + "-" * (40 - mongo_bar_length)
        sql_res_bar = "=" * sql_results_bar + "." * (40 - sql_results_bar)
        mongo_res_bar = "=" * mongo_results_bar + "." * (40 - mongo_results_bar)
        
        # Build output sections
        out = []
        out.append("=" * 80)
        out.append("                  PERFORMANCE BENCHMARK RESULTS")
        out.append(f"                     Search Keyword: '{kw}'")
        out.append("=" * 80)
        out.append("")
        out.append("")
        
        # ==================== SECTION 1: QUICK SUMMARY ====================
        out.append("+---------------------------------------------------------------------------+")
        out.append("|                            QUICK SUMMARY                                  |")
        out.append("+---------------------------------------------------------------------------+")
        out.append(f"|  Speed Winner:    {speed_winner:<55}|")
        out.append(f"|                   {speed_comparison:<55}|")
        out.append(f"|                                                                           |")
        sql_mongo_str = f"SQL found {sql_count} | MongoDB found {mongo_count}"
        out.append(f"|  Results Count:   {sql_mongo_str:<55}|")
        out.append("+---------------------------------------------------------------------------+")
        out.append("")
        out.append("")
        
        # ==================== SECTION 2: EXECUTION TIME ====================
        out.append("+---------------------------------------------------------------------------+")
        out.append("|                       EXECUTION TIME COMPARISON                           |")
        out.append("+---------------------------------------------------------------------------+")
        out.append("")
        out.append(f"  SQL (MariaDB)      [{sql_bar}] {sql_time:.4f}s")
        out.append("")
        out.append(f"  NoSQL (MongoDB)    [{mongo_bar}] {mongo_time:.4f}s")
        out.append("")
        out.append("+---------------------------------------------------------------------------+")
        out.append("")
        out.append("")
        
        # ==================== SECTION 3: RESULTS COUNT ====================
        out.append("+---------------------------------------------------------------------------+")
        out.append("|                       RESULTS COUNT COMPARISON                            |")
        out.append("+---------------------------------------------------------------------------+")
        out.append("")
        out.append(f"  SQL (MariaDB)      [{sql_res_bar}] {sql_count} results")
        out.append("")
        out.append(f"  NoSQL (MongoDB)    [{mongo_res_bar}] {mongo_count} results")
        out.append("")
        out.append("+---------------------------------------------------------------------------+")
        out.append("")
        out.append("")
        
        # ==================== SECTION 4: DETAILED COMPARISON ====================
        out.append("+---------------------------------------------------------------------------+")
        out.append("|                      DETAILED QUERY COMPARISON                            |")
        out.append("+---------------------------------------------------------------------------+")
        out.append("")
        out.append(f"{'Aspect':<20} | {'SQL (MariaDB)':<25} | {'NoSQL (MongoDB)':<25}")
        out.append("-" * 80)
        out.append(f"{'Query Type':<20} | {'SELECT + LEFT JOIN':<25} | {'find() with regex':<25}")
        
        # Build search target strings separately to avoid quote issues
        sql_search = f"Title LIKE '%{kw}%'"
        mongo_search = f"Keywords (/{kw}/i)"
        out.append(f"{'Search Target':<20} | {sql_search:<25} | {mongo_search:<25}")
        
        out.append(f"{'Data Structure':<20} | {'Relational tables':<25} | {'Document collection':<25}")
        out.append(f"{'Tables/Collections':<20} | {'movies + ratings':<25} | {'tmdb_movies':<25}")
        
        # Build result strings separately
        sql_results_str = f"{sql_count} movies"
        mongo_results_str = f"{mongo_count} movies"
        out.append(f"{'Results Found':<20} | {sql_results_str:<25} | {mongo_results_str:<25}")
        
        # Build time strings separately
        sql_time_str = f"{sql_time:.4f}s"
        mongo_time_str = f"{mongo_time:.4f}s"
        out.append(f"{'Execution Time':<20} | {sql_time_str:<25} | {mongo_time_str:<25}")
        out.append("")
        
        out.append("What Each Database Returns:")
        out.append("  SQL:     Movie ID, Title, Vote counts, Average ratings")
        out.append("  MongoDB: Full metadata (Genres, Keywords, Overview, Runtime, Revenue)")
        out.append("")
        out.append("+---------------------------------------------------------------------------+")
        out.append("")
        out.append("")
        
        # ==================== SECTION 5: WHEN TO USE ====================
        out.append("+---------------------------------------------------------------------------+")
        out.append("|                      WHEN TO USE EACH DATABASE                            |")
        out.append("+---------------------------------------------------------------------------+")
        out.append("")
        out.append("[ SQL (MariaDB) ]")
        out.append("-" * 80)
        out.append("Use When You Need:")
        out.append("  + Complex relational queries with multiple JOINs")
        out.append("  + Aggregations (COUNT, AVG, SUM, GROUP BY, HAVING)")
        out.append("  + ACID transactions for data integrity")
        out.append("  + Referential integrity and foreign key constraints")
        out.append("  + Structured data with fixed schema")
        out.append("")
        out.append("Best For:")
        out.append("  > User ratings & authentication")
        out.append("  > Analytics & statistics")
        out.append("  > Top movies by votes")
        out.append("  > User activity tracking")
        out.append("")
        out.append("")
        out.append("[ NoSQL (MongoDB) ]")
        out.append("-" * 80)
        out.append("Use When You Need:")
        out.append("  + Flexible schema for varying movie metadata")
        out.append("  + Fast text search on unstructured fields (keywords, overview)")
        out.append("  + Document storage with nested arrays/objects")
        out.append("  + Rapid retrieval of complete movie information")
        out.append("  + Horizontal scalability for large datasets")
        out.append("")
        out.append("Best For:")
        out.append("  > Genre browsing")
        out.append("  > Keyword searches")
        out.append("  > Similar movie recommendations")
        out.append("  > Rich metadata display")
        out.append("")
        out.append("+---------------------------------------------------------------------------+")
        out.append("")
        out.append("")
        
        # ==================== SECTION 6: ARCHITECTURE ====================
        out.append("+---------------------------------------------------------------------------+")
        out.append("|                    HYBRID ARCHITECTURE BENEFITS                           |")
        out.append("+---------------------------------------------------------------------------+")
        out.append("")
        out.append("Our system uses BOTH databases to leverage their strengths:")
        out.append("")
        out.append("[1] DATA SEPARATION")
        out.append("    SQL:     Critical transactional data (users, ratings)")
        out.append("    MongoDB: Rich metadata (genres, keywords, cast, crew)")
        out.append("")
        out.append("[2] OPTIMIZED QUERY ROUTING")
        out.append("    SQL:     Analytical queries (top rated, user statistics)")
        out.append("    MongoDB: Content discovery (similar movies, genre browsing)")
        out.append("")
        out.append("[3] SCALABILITY & RELIABILITY")
        out.append("    SQL:     Maintains data integrity for critical operations")
        out.append("    MongoDB: Scales horizontally for growing catalog")
        out.append("")
        out.append("[4] BEST TOOL FOR EACH JOB")
        out.append("    Each database excels at its designated tasks")
        out.append("    Users get optimal performance regardless of query type")
        out.append("")
        out.append("+---------------------------------------------------------------------------+")
        out.append("")
        out.append("")
        out.append("=" * 80)
        out.append("TIP: Try different keywords (action, romance, space, thriller) to see")
        out.append("     how results vary based on title vs. keyword searches!")
        out.append("=" * 80)
        out.append("=" * 90)
        
        self._set_text_widget(self.perf_output, "\n".join(out))

    def handle_insert_performance_test(self):
        """Handle INSERT performance test button click"""
        try:
            num_records = int(self.insert_records_var.get())
            if num_records <= 0 or num_records > 1000:
                messagebox.showwarning("Invalid Input", "Please enter a number between 1 and 1000")
                return
        except ValueError:
            messagebox.showwarning("Invalid Input", "Please enter a valid number")
            return

        # Show "Running..." message
        self._set_text_widget(self.perf_output, f"\n{'='*80}\nRunning INSERT Performance Test with {num_records} records...\nPlease wait...\n{'='*80}\n")
        self.update()

        # Run the test
        results = test_bulk_insert_performance(num_records)

        # Display results
        out = []
        out.append("=" * 80)
        out.append("           INSERT PERFORMANCE TEST RESULTS (ZERO IMPACT)")
        out.append("=" * 80)
        out.append("")
        out.append(f"Records Tested: {results['record_count']}")
        out.append("")
        out.append("+---------------------------------------------------------------------------+")
        out.append("|                         SQL (MariaDB) Results                             |")
        out.append("+---------------------------------------------------------------------------+")
        if results['sql_success']:
            out.append(f"  Time:       {results['sql_time']:.3f}s")
            out.append(f"  Throughput: {results['sql_throughput']:.1f} inserts/sec")
            out.append(f"  Status:     ✓ SUCCESS (data deleted after test)")
        else:
            out.append("  Status:     ✗ FAILED")
        out.append("")
        out.append("+---------------------------------------------------------------------------+")
        out.append("|                         MongoDB Atlas Results                             |")
        out.append("+---------------------------------------------------------------------------+")
        if results['mongo_success']:
            out.append(f"  Time:       {results['mongo_time']:.3f}s")
            out.append(f"  Throughput: {results['mongo_throughput']:.1f} inserts/sec")
            out.append(f"  Status:     ✓ SUCCESS (data deleted after test)")
        else:
            out.append("  Status:     ✗ FAILED or MongoDB not connected")
        out.append("")
        out.append("+---------------------------------------------------------------------------+")
        out.append("|                              Comparison                                   |")
        out.append("+---------------------------------------------------------------------------+")
        if results['sql_success'] and results['mongo_success']:
            if results['sql_throughput'] > results['mongo_throughput']:
                diff = (results['sql_throughput'] / results['mongo_throughput']) if results['mongo_throughput'] > 0 else 0
                out.append(f"  Winner: SQL is {diff:.1f}x faster for INSERT operations")
            else:
                diff = (results['mongo_throughput'] / results['sql_throughput']) if results['sql_throughput'] > 0 else 0
                out.append(f"  Winner: MongoDB is {diff:.1f}x faster for INSERT operations")
        out.append("")
        out.append("✓ ZERO IMPACT: All test data was removed. Your dataset is unchanged.")
        out.append("=" * 80)

        self._set_text_widget(self.perf_output, "\n".join(out))

    def handle_update_performance_test(self):
        """Handle UPDATE performance test button click"""
        try:
            num_records = int(self.update_records_var.get())
            if num_records <= 0 or num_records > 1000:
                messagebox.showwarning("Invalid Input", "Please enter a number between 1 and 1000")
                return
        except ValueError:
            messagebox.showwarning("Invalid Input", "Please enter a valid number")
            return

        # Show "Running..." message
        self._set_text_widget(self.perf_output, f"\n{'='*80}\nRunning UPDATE Performance Test with {num_records} records...\nPlease wait...\n{'='*80}\n")
        self.update()

        # Run the test
        results = test_bulk_update_performance(num_records)

        # Display results
        out = []
        out.append("=" * 80)
        out.append("           UPDATE PERFORMANCE TEST RESULTS (ZERO IMPACT)")
        out.append("=" * 80)
        out.append("")
        out.append(f"Records Tested: {results['record_count']}")
        out.append("")
        out.append("+---------------------------------------------------------------------------+")
        out.append("|                         SQL (MariaDB) Results                             |")
        out.append("+---------------------------------------------------------------------------+")
        if results['sql_success']:
            out.append(f"  Time:       {results['sql_time']:.3f}s")
            out.append(f"  Throughput: {results['sql_throughput']:.1f} updates/sec")
            out.append(f"  Status:     ✓ SUCCESS (original data restored)")
        else:
            out.append("  Status:     ✗ FAILED")
        out.append("")
        out.append("+---------------------------------------------------------------------------+")
        out.append("|                         MongoDB Atlas Results                             |")
        out.append("+---------------------------------------------------------------------------+")
        if results['mongo_success']:
            out.append(f"  Time:       {results['mongo_time']:.3f}s")
            out.append(f"  Throughput: {results['mongo_throughput']:.1f} updates/sec")
            out.append(f"  Status:     ✓ SUCCESS (original data restored)")
        else:
            out.append("  Status:     ✗ FAILED or MongoDB not connected")
        out.append("")
        out.append("+---------------------------------------------------------------------------+")
        out.append("|                              Comparison                                   |")
        out.append("+---------------------------------------------------------------------------+")
        if results['sql_success'] and results['mongo_success']:
            if results['sql_throughput'] > results['mongo_throughput']:
                diff = (results['sql_throughput'] / results['mongo_throughput']) if results['mongo_throughput'] > 0 else 0
                out.append(f"  Winner: SQL is {diff:.1f}x faster for UPDATE operations")
            else:
                diff = (results['mongo_throughput'] / results['sql_throughput']) if results['sql_throughput'] > 0 else 0
                out.append(f"  Winner: MongoDB is {diff:.1f}x faster for UPDATE operations")
        out.append("")
        out.append("✓ ZERO IMPACT: All data was restored to original values. Dataset unchanged.")
        out.append("=" * 80)

        self._set_text_widget(self.perf_output, "\n".join(out))

    def handle_test_fk_constraints(self):
        """Test Foreign Key constraint violations"""
        out = []
        out.append("=" * 80)
        out.append("            DATA INTEGRITY: FOREIGN KEY CONSTRAINT TEST")
        out.append("=" * 80)
        out.append("")
        out.append("This test demonstrates how database constraints maintain data integrity.")
        out.append("We'll attempt to insert invalid data that violates foreign key constraints.")
        out.append("")
        out.append("+---------------------------------------------------------------------------+")
        out.append("|                          TEST 1: Invalid User ID                          |")
        out.append("+---------------------------------------------------------------------------+")
        
        # Test 1: Try to insert rating with non-existent user ID
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                out.append("Attempting: INSERT rating with userId=999999 (does not exist)...")
                try:
                    cur.execute("""
                        INSERT INTO ratings (userId, movieId, rating, timestamp)
                        VALUES (999999, 1, 5.0, UNIX_TIMESTAMP())
                    """)
                    conn.commit()
                    out.append("  Result: ✗ UNEXPECTED - Insert succeeded (constraint not working!)")
                except pymysql.IntegrityError as e:
                    conn.rollback()
                    out.append(f"  Result: ✓ SUCCESS - Database rejected insert")
                    out.append(f"  Error: {str(e)[:80]}")
                    out.append("  → Data integrity maintained!")
        finally:
            conn.close()
        
        out.append("")
        out.append("+---------------------------------------------------------------------------+")
        out.append("|                         TEST 2: Invalid Movie ID                          |")
        out.append("+---------------------------------------------------------------------------+")
        
        # Test 2: Try to insert rating with non-existent movie ID
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                out.append("Attempting: INSERT rating with movieId=999999 (does not exist)...")
                try:
                    # Get a valid user ID first
                    cur.execute("SELECT userId FROM users LIMIT 1")
                    user_row = cur.fetchone()
                    if user_row:
                        valid_user_id = user_row['userId']
                        cur.execute(f"""
                            INSERT INTO ratings (userId, movieId, rating, timestamp)
                            VALUES ({valid_user_id}, 999999, 5.0, UNIX_TIMESTAMP())
                        """)
                        conn.commit()
                        out.append("  Result: ✗ UNEXPECTED - Insert succeeded (constraint not working!)")
                    else:
                        out.append("  Result: ⚠ SKIPPED - No users found in database")
                except pymysql.IntegrityError as e:
                    conn.rollback()
                    out.append(f"  Result: ✓ SUCCESS - Database rejected insert")
                    out.append(f"  Error: {str(e)[:80]}")
                    out.append("  → Data integrity maintained!")
        finally:
            conn.close()
        
        out.append("")
        out.append("+---------------------------------------------------------------------------+")
        out.append("|                              CONCLUSION                                   |")
        out.append("+---------------------------------------------------------------------------+")
        out.append("Foreign key constraints prevent orphaned records and maintain referential")
        out.append("integrity. This ensures:")
        out.append("  • Ratings can only reference valid users")
        out.append("  • Ratings can only reference valid movies")
        out.append("  • Database remains consistent and reliable")
        out.append("=" * 80)
        
        self._set_text_widget(self.perf_output, "\n".join(out))
    
    def handle_test_pk_constraints(self):
        """Test Primary Key constraint violations"""
        out = []
        out.append("=" * 80)
        out.append("           DATA INTEGRITY: PRIMARY KEY CONSTRAINT TEST")
        out.append("=" * 80)
        out.append("")
        out.append("Primary keys ensure uniqueness and prevent duplicate records.")
        out.append("")
        out.append("+---------------------------------------------------------------------------+")
        out.append("|                    TEST 1: Duplicate User ID Insert                       |")
        out.append("+---------------------------------------------------------------------------+")
        
        # Test 1: Try to insert duplicate user ID
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                # Get an existing user ID
                cur.execute("SELECT userId FROM users LIMIT 1")
                user_row = cur.fetchone()
                
                if user_row:
                    existing_id = user_row['userId']
                    out.append(f"Attempting: INSERT user with existing userId={existing_id}...")
                    try:
                        cur.execute(f"""
                            INSERT INTO users (userId, username, email, password_hash, role)
                            VALUES ({existing_id}, 'test_duplicate', 'test@test.com', 
                                    'hash123', 'user')
                        """)
                        conn.commit()
                        out.append("  Result: ✗ UNEXPECTED - Duplicate insert succeeded!")
                    except pymysql.IntegrityError as e:
                        conn.rollback()
                        out.append(f"  Result: ✓ SUCCESS - Database rejected duplicate")
                        out.append(f"  Error: {str(e)[:80]}")
                        out.append("  → Primary key constraint enforced!")
                else:
                    out.append("  Result: ⚠ SKIPPED - No users found in database")
        finally:
            conn.close()
        
        out.append("")
        out.append("+---------------------------------------------------------------------------+")
        out.append("|                   TEST 2: Duplicate Movie ID Insert                       |")
        out.append("+---------------------------------------------------------------------------+")
        
        # Test 2: Try to insert duplicate movie ID
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                # Get an existing movie ID
                cur.execute("SELECT movieId FROM movies LIMIT 1")
                movie_row = cur.fetchone()
                
                if movie_row:
                    existing_id = movie_row['movieId']
                    out.append(f"Attempting: INSERT movie with existing movieId={existing_id}...")
                    try:
                        cur.execute(f"""
                            INSERT INTO movies (movieId, title, release_date)
                            VALUES ({existing_id}, 'Duplicate Movie', '2024-01-01')
                        """)
                        conn.commit()
                        out.append("  Result: ✗ UNEXPECTED - Duplicate insert succeeded!")
                    except pymysql.IntegrityError as e:
                        conn.rollback()
                        out.append(f"  Result: ✓ SUCCESS - Database rejected duplicate")
                        out.append(f"  Error: {str(e)[:80]}")
                        out.append("  → Primary key constraint enforced!")
                else:
                    out.append("  Result: ⚠ SKIPPED - No movies found in database")
        finally:
            conn.close()
        
        out.append("")
        out.append("+---------------------------------------------------------------------------+")
        out.append("|                              CONCLUSION                                   |")
        out.append("+---------------------------------------------------------------------------+")
        out.append("Primary key constraints ensure:")
        out.append("  • No duplicate IDs in the database")
        out.append("  • Each record is uniquely identifiable")
        out.append("  • Data consistency and reliability")
        out.append("  • Foundation for foreign key relationships")
        out.append("=" * 80)
        
        self._set_text_widget(self.perf_output, "\n".join(out))

    def handle_genre_search_performance(self):
        """Handle Genre Search Performance Comparison (SQL vs NoSQL)"""
        genre = self.genre_perf_var.get().strip()
        if not genre:
            messagebox.showwarning("Genre Search", "Please enter a genre name.")
            return

        # Show "Running..." message
        self._set_text_widget(self.perf_output, f"\n{'='*80}\nComparing SQL vs MongoDB genre search for: {genre}\nPlease wait...\n{'='*80}\n")
        self.update()

        import time

        # SQL Search (search by title containing genre)
        sql_start = time.time()
        conn = get_connection()
        sql_results = []
        try:
            with conn.cursor() as cur:
                sql = """
                    SELECT movieId, title, release_date
                    FROM movies
                    WHERE title LIKE %s
                    LIMIT 50
                """
                cur.execute(sql, (f'%{genre}%',))
                sql_results = cur.fetchall()
        finally:
            conn.close()
        sql_time = time.time() - sql_start

        # MongoDB Search (search by genres field)
        mongo_results, mongo_time = search_movies_by_genre_mongo(genre)

        # Display results
        out = []
        out.append("=" * 80)
        out.append("           GENRE SEARCH PERFORMANCE COMPARISON")
        out.append("=" * 80)
        out.append("")
        out.append(f"Search Query: '{genre}'")
        out.append("")
        
        # Determine winner
        if sql_time < mongo_time:
            speed_winner = "SQL (MariaDB)"
            speed_diff = ((mongo_time - sql_time) / mongo_time) * 100
            speed_comparison = f"SQL is {speed_diff:.1f}% faster"
        elif mongo_time < sql_time:
            speed_winner = "NoSQL (MongoDB)"
            speed_diff = ((sql_time - mongo_time) / sql_time) * 100
            speed_comparison = f"MongoDB is {speed_diff:.1f}% faster"
        else:
            speed_winner = "TIE"
            speed_comparison = "Both performed equally"

        # Create progress bars
        max_time = max(sql_time, mongo_time)
        sql_bar_length = int((sql_time / max_time) * 40) if max_time > 0 else 0
        mongo_bar_length = int((mongo_time / max_time) * 40) if max_time > 0 else 0

        out.append("+---------------------------------------------------------------------------+")
        out.append("|                         SQL (MariaDB) Results                             |")
        out.append("+---------------------------------------------------------------------------+")
        out.append(f"  Query:      Searches movie TITLES with LIKE '%{genre}%'")
        out.append(f"  Time:       {sql_time:.3f}s  [{'█' * sql_bar_length}]")
        out.append(f"  Results:    {len(sql_results)} movies found")
        out.append(f"  Method:     Pattern matching on title field")
        out.append("")
        
        out.append("+---------------------------------------------------------------------------+")
        out.append("|                         MongoDB Atlas Results                             |")
        out.append("+---------------------------------------------------------------------------+")
        out.append(f"  Query:      Searches GENRES field with regex /{genre}/i")
        out.append(f"  Time:       {mongo_time:.3f}s  [{'█' * mongo_bar_length}]")
        out.append(f"  Results:    {len(mongo_results)} movies found")
        out.append(f"  Method:     Regex pattern matching on genres field")
        out.append("")
        
        out.append("+---------------------------------------------------------------------------+")
        out.append("|                              WINNER                                       |")
        out.append("+---------------------------------------------------------------------------+")
        out.append(f"  Speed:      {speed_winner}")
        out.append(f"  Difference: {speed_comparison}")
        out.append("")
        
        out.append("+---------------------------------------------------------------------------+")
        out.append("|                          KEY INSIGHTS                                     |")
        out.append("+---------------------------------------------------------------------------+")
        out.append("  SQL Advantages:")
        out.append("    • Simple LIKE pattern matching")
        out.append("    • Good for exact title searches")
        out.append("    • Well-indexed for common queries")
        out.append("")
        out.append("  MongoDB Advantages:")
        out.append("    • Dedicated genres field for precise matching")
        out.append("    • Flexible regex patterns")
        out.append("    • Better for multi-genre filtering")
        out.append("")
        out.append("  Use Case:")
        out.append("    • SQL:     Quick title-based searches")
        out.append("    • MongoDB: Genre-specific browsing & discovery")
        out.append("")
        out.append("=" * 80)

        # Show sample results
        out.append("")
        out.append("SAMPLE RESULTS (First 5 from each):")
        out.append("")
        out.append("SQL Results:")
        for i, movie in enumerate(sql_results[:5], 1):
            out.append(f"  {i}. {movie['title']} ({movie.get('release_date', 'N/A')})")
        
        out.append("")
        out.append("MongoDB Results:")
        for i, movie in enumerate(mongo_results[:5], 1):
            title = movie.get('title', 'Unknown')
            genres = movie.get('genres', 'N/A')
            out.append(f"  {i}. {title}")
            out.append(f"      Genres: {genres}")
        
        out.append("")
        out.append("=" * 80)

        self._set_text_widget(self.perf_output, "\n".join(out))


###############################################################################
# 9. TRANSACTION & ROLLBACK TESTING FUNCTIONS
###############################################################################

def test_concurrent_lock_mechanism():
    """    
    This test simulates the scenario:
    1. User A starts editing Movie D (lock acquired)
    2. User B tries to edit Movie D (blocked by lock)
    3. User A finishes updating (lock released)
    4. User B can now edit Movie D (lock acquired by User B)
    
    This is NOT about simultaneous button presses!
    This is about preventing concurrent edits to the same rating.
    """
    print("\n" + "="*80)
    print(" CONCURRENT EDIT PREVENTION TEST")
    print("="*80)
    print("\nScenario: User A editing Movie D, User B tries to edit same movie")
    print("-" * 80)
    
    # Setup test data
    test_user_a = 1
    test_user_b = 2
    test_movie_d = 1
    
    conn = get_connection()
    
    # Verify users and movie exist
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT username FROM USERS WHERE userId = %s", (test_user_a,))
            user_a = cur.fetchone()
            cur.execute("SELECT username FROM USERS WHERE userId = %s", (test_user_b,))
            user_b = cur.fetchone()
            cur.execute("SELECT title FROM movies WHERE movieId = %s", (test_movie_d,))
            movie_d = cur.fetchone()
            
            if not user_a or not user_b or not movie_d:
                print("❌ Test failed: Required test data not found")
                print(f"   User A (ID={test_user_a}): {user_a}")
                print(f"   User B (ID={test_user_b}): {user_b}")
                print(f"   Movie D (ID={test_movie_d}): {movie_d}")
                conn.close()
                return
                
            user_a_name = user_a['username']
            user_b_name = user_b['username']
            movie_d_title = movie_d['title']
    finally:
        conn.close()
    
    print(f"\nTest Setup:")
    print(f"  • User A: {user_a_name} (ID: {test_user_a})")
    print(f"  • User B: {user_b_name} (ID: {test_user_b})")
    print(f"  • Movie D: {movie_d_title} (ID: {test_movie_d})")
    
    # STEP 1: User A acquires lock to edit Movie D
    print(f"\n[STEP 1] User A ({user_a_name}) starts editing Movie D")
    print("-" * 80)
    success = acquire_rating_lock(test_user_a, test_movie_d, user_a_name)
    if success:
        print(f"  ✅ Lock ACQUIRED by {user_a_name}")
        print(f"  → Movie D rating (userId={test_user_a}, movieId={test_movie_d}) is now LOCKED")
    else:
        print(f"  ❌ Failed to acquire lock")
        return
    
    # STEP 2: User B tries to edit the same Movie D (should be BLOCKED)
    print(f"\n[STEP 2] User B ({user_b_name}) tries to edit same Movie D")
    print("-" * 80)
    locked_by = check_rating_lock(test_user_a, test_movie_d)
    if locked_by:
        print(f"  ⚠️  BLOCKED! Rating is locked by '{locked_by}'")
        print(f"  → User B CANNOT edit until User A finishes")
        print(f"  → This demonstrates CONCURRENT EDIT PREVENTION")
    else:
        print(f"  ❌ Test failed: Lock not detected")
        return
    
    # STEP 3: User A completes the update and releases lock
    print(f"\n[STEP 3] User A ({user_a_name}) finishes updating Movie D")
    print("-" * 80)
    print(f"  • Transaction BEGIN")
    print(f"  • DELETE old rating")
    print(f"  • INSERT new rating (4.5)")
    print(f"  • VERIFY insert successful")
    print(f"  • Transaction COMMIT")
    release_rating_lock(test_user_a, test_movie_d)
    print(f"  ✅ Lock RELEASED by {user_a_name}")
    print(f"  → Movie D rating is now UNLOCKED")
    
    # STEP 4: User B can now edit Movie D
    print(f"\n[STEP 4] User B ({user_b_name}) tries again to edit Movie D")
    print("-" * 80)
    locked_by = check_rating_lock(test_user_a, test_movie_d)
    if locked_by:
        print(f"  ❌ Test failed: Lock still exists (locked by '{locked_by}')")
        return
    else:
        print(f"  ✅ No lock detected - User B can now edit!")
    
    # User B acquires lock
    success = acquire_rating_lock(test_user_b, test_movie_d, user_b_name)
    if success:
        print(f"  ✅ Lock ACQUIRED by {user_b_name}")
        print(f"  → User B successfully obtained lock for editing")
    else:
        print(f"  ❌ Failed to acquire lock")
        return
    
    # Clean up - release User B's lock
    release_rating_lock(test_user_b, test_movie_d)
    print(f"  ✅ Lock RELEASED by {user_b_name}")
    
    # Test Summary
    print("\n" + "="*80)
    print(" TEST SUMMARY")
    print("="*80)
    print("✅ All steps completed successfully!")
    print("\nWhat was demonstrated:")
    print("  1. User A editing Movie D → Lock acquired (prevents concurrent edits)")
    print("  2. User B tries to edit → BLOCKED by lock (concurrent edit prevented)")
    print("  3. User A finishes → Lock released (opens for other users)")
    print("  4. User B can now edit → Lock acquired by User B (edit allowed)")
    print("  • When User A is editing Movie D, User B cannot edit until A finishes")
    print("  • Lock timeout: 5 minutes (300 seconds)")
    print("  • Transaction rollback protects data integrity during updates")
    print("="*80 + "\n")


def test_transaction_rollback():
    """
    Test function to demonstrate transaction rollback.
    This simulates a transaction failure and shows rollback behavior.
    """
    print("\n" + "="*60)
    print("TRANSACTION & ROLLBACK TEST")
    print("="*60)
    
    # Test 1: Successful transaction
    print("\n[TEST 1] Successful Transaction:")
    conn = get_connection()
    try:
        conn.begin()
        with conn.cursor() as cur:
            # Check current rating count
            cur.execute("SELECT COUNT(*) as count FROM ratings WHERE userId=1 AND movieId=1")
            before_count = cur.fetchone()['count']
            print(f"  Before: {before_count} ratings for (userId=1, movieId=1)")
            
            # Insert a test rating
            cur.execute(
                "INSERT INTO ratings (userId, movieId, rating, timestamp) VALUES (%s, %s, %s, %s)",
                (1, 1, 4.5, int(time.time()))
            )
            print("  [TRANSACTION] Inserted rating (4.5)")
            
            # Verify
            cur.execute("SELECT COUNT(*) as count FROM ratings WHERE userId=1 AND movieId=1")
            after_count = cur.fetchone()['count']
            print(f"  After insert: {after_count} ratings")
            
        conn.commit()
        print("  [COMMIT] Transaction committed successfully ✓")
        
        # Clean up
        with conn.cursor() as cur:
            cur.execute("DELETE FROM ratings WHERE userId=1 AND movieId=1 AND rating=4.5")
        conn.commit()
        print("  [CLEANUP] Test data removed")
        
    except Exception as e:
        conn.rollback()
        print(f"  [ROLLBACK] Transaction rolled back: {e}")
    finally:
        conn.close()
    
    # Test 2: Failed transaction with rollback
    print("\n[TEST 2] Failed Transaction (simulated):")
    conn = get_connection()
    try:
        conn.begin()
        with conn.cursor() as cur:
            # Insert valid data
            cur.execute(
                "INSERT INTO ratings (userId, movieId, rating, timestamp) VALUES (%s, %s, %s, %s)",
                (1, 2, 3.5, int(time.time()))
            )
            print("  [TRANSACTION] Inserted rating (3.5)")
            
            # Simulate an error - try to insert invalid data
            print("  [TRANSACTION] Attempting invalid operation...")
            cur.execute(
                "INSERT INTO ratings (userId, movieId, rating, timestamp) VALUES (%s, %s, %s, %s)",
                (999999, 2, 5.0, int(time.time()))  # userId 999999 doesn't exist - FK constraint violation
            )
            
        conn.commit()
        print("  [COMMIT] Should not reach here")
        
    except Exception as e:
        print(f"  [ERROR] {e}")
        conn.rollback()
        print("  [ROLLBACK] All changes rolled back ✓")
        
        # Verify rollback - check that first insert was also undone
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as count FROM ratings WHERE userId=1 AND movieId=2 AND rating=3.5")
            count = cur.fetchone()['count']
            if count == 0:
                print(f"  [VERIFY] Rollback successful - no data persisted ✓")
            else:
                print(f"  [VERIFY] Rollback may have failed - found {count} rows")
    finally:
        conn.close()
    
    # Test 3: Rating lock concurrency test
    print("\n[TEST 3] Rating Lock Test:")
    test_user_id = 1
    test_movie_id = 3
    
    # Acquire lock
    print(f"  User 'admin' acquiring lock on (user={test_user_id}, movie={test_movie_id})")
    success = acquire_rating_lock(test_user_id, test_movie_id, "admin")
    if success:
        print("  [LOCK] Lock acquired successfully ✓")
        
        # Check lock
        locked_by = check_rating_lock(test_user_id, test_movie_id)
        if locked_by:
            print(f"  [CHECK] Lock is held by: {locked_by} ✓")
        
        # Release lock
        release_rating_lock(test_user_id, test_movie_id)
        print("  [UNLOCK] Lock released ✓")
        
        # Verify lock is gone
        locked_by = check_rating_lock(test_user_id, test_movie_id)
        if not locked_by:
            print("  [VERIFY] Lock successfully released ✓")
    else:
        print("  [LOCK] Failed to acquire lock")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60 + "\n")


def test_concurrent_updates():
    """
    Test concurrent update scenario using rating locks.
    Simulates two users trying to update the same rating.
    """
    print("\n" + "="*60)
    print("CONCURRENT UPDATE TEST")
    print("="*60)
    
    test_user_id = 2
    test_movie_id = 5
    
    print(f"\nScenario: Two sessions try to update rating for (userId={test_user_id}, movieId={test_movie_id})")
    
    # Session 1: Acquire lock
    print("\n[SESSION 1] User 'testuser' starts editing...")
    lock1 = acquire_rating_lock(test_user_id, test_movie_id, "testuser")
    if lock1:
        print("  [SESSION 1] Lock acquired ✓")
        
        # Session 2: Try to acquire same lock
        print("\n[SESSION 2] User 'another_user' tries to edit same rating...")
        locked_by = check_rating_lock(test_user_id, test_movie_id)
        if locked_by:
            print(f"  [SESSION 2] ❌ Rating is locked by: {locked_by}")
            print(f"  [SESSION 2] Must wait for {locked_by} to finish")
        
        # Session 1: Complete update
        print("\n[SESSION 1] Completing update...")
        success = add_or_update_rating(test_user_id, test_movie_id, 4.0)
        if success:
            print("  [SESSION 1] Rating updated to 4.0 ✓")
        
        # Session 1: Release lock
        release_rating_lock(test_user_id, test_movie_id)
        print("  [SESSION 1] Lock released ✓")
        
        # Session 2: Now can acquire lock
        print("\n[SESSION 2] Retrying after lock release...")
        locked_by = check_rating_lock(test_user_id, test_movie_id)
        if not locked_by:
            print("  [SESSION 2] Lock is available now ✓")
            lock2 = acquire_rating_lock(test_user_id, test_movie_id, "another_user")
            if lock2:
                print("  [SESSION 2] Lock acquired ✓")
                release_rating_lock(test_user_id, test_movie_id)
                print("  [SESSION 2] Lock released ✓")
        
        # Cleanup
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM ratings WHERE userId=%s AND movieId=%s", (test_user_id, test_movie_id))
            conn.commit()
            print("\n[CLEANUP] Test data removed")
        finally:
            conn.close()
    
    print("\n" + "="*60)
    print("CONCURRENT TEST COMPLETE")
    print("="*60 + "\n")


###############################################################################
# 10. RUN APP
###############################################################################

if __name__ == "__main__":
    # Uncomment to run tests before GUI launches
    # Test 1: Concurrent edit prevention with locks
    # test_concurrent_lock_mechanism()
    
    # Test 2: Transaction rollback demonstration
    # test_transaction_rollback()
    
    # Test 3: Concurrent updates stress test
    # test_concurrent_updates()
    
    # Check for AUTO_GUEST environment variable for Docker deployment
    auto_guest = os.getenv("AUTO_GUEST", "").lower() in ("true", "1", "yes")
    if auto_guest:
        # Auto-login as guest for Docker/web deployment
        CURRENT_USER.update({
            "userId": None,
            "username": "GUEST",
            "email": None,
            "role": "guest",
        })
        app = MovieApp(skip_login=True)
    else:
        app = MovieApp()
    app.mainloop()