import pymysql
from pymongo import MongoClient
import tkinter as tk
from tkinter import ttk, messagebox
import time
import re
from datetime import datetime

def is_valid_email(email):
    """Validate email format using regex pattern."""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None


###############################################################################
# 1. DB CONNECTION SETTINGS
###############################################################################

DB_HOST = "localhost"
DB_USER = "root"
DB_PASS = "12345"
DB_NAME = "movies_db"

MONGO_HOST = "localhost"
MONGO_PORT = 27017
MONGO_DB = "movies_nosql"

# MongoDB Connection
mongo_client = MongoClient(f"mongodb://{MONGO_HOST}:{MONGO_PORT}/")
mongo_db = mongo_client[MONGO_DB]
tmdb_collection = mongo_db["tmdb_movies"]


def get_connection():
    """Open a DB connection."""
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )


###############################################################################
# 2. SQL HELPER FUNCTIONS - MOVIES
###############################################################################

def search_movies_by_title(keyword):
    """Search movies by title with average rating."""
    start_time = time.time()
    sql = """
        SELECT
            m.movieId,
            m.title,
            COUNT(r.rating) AS vote_count,
            ROUND(AVG(r.rating), 2) AS avg_rating
        FROM movies m
        LEFT JOIN ratings r ON m.movieId = r.movieId
        WHERE m.title LIKE %s AND m.title NOT LIKE 'Movie_%%'
        GROUP BY m.movieId, m.title
        ORDER BY ROUND(AVG(r.rating), 2) IS NULL ASC, ROUND(AVG(r.rating), 2) DESC, m.title ASC
        LIMIT 50;
    """
    like_param = f"%{keyword}%"

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (like_param,))
            rows = cur.fetchall()
            execution_time = time.time() - start_time
            return rows, execution_time
    finally:
        conn.close()


def get_movie_details(movie_id):
    """Get full info for one movie."""
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
        GROUP BY m.movieId, m.title, m.release_date, l.imdbId, l.tmdbId;
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (movie_id,))
            row = cur.fetchone()
            return row
    finally:
        conn.close()


def get_tmdb_metadata(tmdb_id):
    """Get TMDB metadata from MongoDB by tmdbId."""
    if not tmdb_id:
        return None
    
    try:
        # Convert to int if it's a string
        if isinstance(tmdb_id, str):
            tmdb_id = int(tmdb_id)
        
        doc = tmdb_collection.find_one({"tmdbId": tmdb_id})
        
        if not doc:
            return None
        
        return {
            "tmdbId": doc.get("tmdbId"),
            "title": doc.get("title"),
            "overview": doc.get("overview"),
            "genres": doc.get("genres"),
            "vote_average": doc.get("vote_average"),
            "vote_count": doc.get("vote_count"),
            "revenue": doc.get("revenue"),
            "runtime": doc.get("runtime"),
            "original_language": doc.get("original_language"),
            "release_date": doc.get("release_date"),
            "tagline": doc.get("tagline"),
            "popularity": doc.get("popularity")
        }
    except Exception as e:
        print(f"MongoDB error: {e}")
        return None


###############################################################################
# 3. MONGODB HELPER FUNCTIONS - NoSQL Operations
###############################################################################

def search_movies_by_genre_mongo(genre):
    """Search MongoDB by genre - demonstrates NoSQL flexible querying."""
    try:
        start_time = time.time()
        results = tmdb_collection.find(
            {"genres": {"$regex": genre, "$options": "i"}},
            {"tmdbId": 1, "title": 1, "genres": 1, "vote_average": 1, "overview": 1, "runtime": 1}
        ).limit(50)
        results_list = list(results)
        exec_time = time.time() - start_time
        return results_list, exec_time
    except Exception as e:
        print(f"MongoDB genre search error: {e}")
        return [], 0


def search_movies_by_keyword_mongo(keyword):
    """Search by movie keywords/tags - NoSQL advantage."""
    try:
        start_time = time.time()
        results = tmdb_collection.find(
            {"keywords": {"$regex": keyword, "$options": "i"}},
            {"tmdbId": 1, "title": 1, "keywords": 1, "genres": 1, "vote_average": 1}
        ).limit(50)
        results_list = list(results)
        exec_time = time.time() - start_time
        return results_list, exec_time
    except Exception as e:
        print(f"MongoDB keyword search error: {e}")
        return [], 0


def get_genre_statistics_mongo():
    """Use MongoDB aggregation pipeline for genre analysis."""
    try:
        start_time = time.time()
        pipeline = [
            {"$match": {"genres": {"$exists": True, "$ne": ""}}},
            {"$group": {
                "_id": "$genres",
                "count": {"$sum": 1},
                "avg_rating": {"$avg": "$vote_average"},
                "avg_revenue": {"$avg": "$revenue"}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 20}
        ]
        results = list(tmdb_collection.aggregate(pipeline))
        exec_time = time.time() - start_time
        return results, exec_time
    except Exception as e:
        print(f"MongoDB aggregation error: {e}")
        return [], 0


def find_similar_movies_mongo(tmdb_id):
    """Find similar movies by genre - NoSQL flexible matching."""
    try:
        start_time = time.time()
        current = tmdb_collection.find_one({"tmdbId": tmdb_id})
        if not current or not current.get('genres'):
            return [], 0
        
        # Get first genre as main category
        first_genre = current['genres'].split(',')[0].strip() if ',' in current['genres'] else current['genres']
        
        similar = tmdb_collection.find(
            {
                "tmdbId": {"$ne": tmdb_id},
                "genres": {"$regex": first_genre, "$options": "i"}
            },
            {"tmdbId": 1, "title": 1, "genres": 1, "vote_average": 1, "overview": 1}
        ).limit(10)
        results_list = list(similar)
        exec_time = time.time() - start_time
        return results_list, exec_time
    except Exception as e:
        print(f"MongoDB similar movies error: {e}")
        return [], 0


def compare_sql_vs_nosql_performance(keyword):
    """Compare query performance between MariaDB and MongoDB."""
    # SQL: Search in titles (structured data)
    sql_start = time.time()
    sql_results, _ = search_movies_by_title(keyword)
    sql_time = time.time() - sql_start
    
    # NoSQL: Search in overview/genres (unstructured data)
    mongo_start = time.time()
    mongo_results, _ = search_movies_by_keyword_mongo(keyword)
    mongo_time = time.time() - mongo_start
    
    return {
        'sql_time': sql_time,
        'sql_count': len(sql_results),
        'mongo_time': mongo_time,
        'mongo_count': len(mongo_results)
    }


def search_movies_advanced(title=None, min_rating=None, max_rating=None, min_votes=None):
    """Advanced search with multiple filters."""
    start_time = time.time()
    base_sql = """
        SELECT 
            m.movieId,
            m.title,
            m.release_date,
            COUNT(r.rating) as vote_count,
            ROUND(AVG(r.rating), 2) as avg_rating
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
    
    having_conditions = []
    if min_rating is not None:
        having_conditions.append("ROUND(AVG(r.rating), 2) >= %s")
        params.append(min_rating)
    
    if max_rating is not None:
        having_conditions.append("ROUND(AVG(r.rating), 2) <= %s")
        params.append(max_rating)
    
    if min_votes is not None:
        having_conditions.append("COUNT(r.rating) >= %s")
        params.append(min_votes)
    
    if having_conditions:
        base_sql += " HAVING " + " AND ".join(having_conditions)
    
    base_sql += " ORDER BY avg_rating DESC, vote_count DESC LIMIT 50;"
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(base_sql, params)
            rows = cur.fetchall()
            execution_time = time.time() - start_time
            return rows, execution_time
    finally:
        conn.close()


###############################################################################
# 3. SQL HELPER FUNCTIONS - USERS
###############################################################################

def get_user(user_id):
    """READ operation: Fetch a user by ID."""
    sql = """
        SELECT userId, username, email, created_at
        FROM users
        WHERE userId = %s;
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            row = cur.fetchone()
            return row
    finally:
        conn.close()


def search_users(keyword=""):
    """READ operation: Search all users."""
    if keyword:
        sql = """
            SELECT userId, username, email, created_at
            FROM users
            WHERE (username LIKE %s OR email LIKE %s)
              AND username IS NOT NULL
              AND email IS NOT NULL
            ORDER BY userId ASC
            LIMIT 50;
        """
        like_param = f"%{keyword}%"
        params = (like_param, like_param)
    else:
        sql = """
            SELECT userId, username, email, created_at
            FROM users
            WHERE username IS NOT NULL AND email IS NOT NULL
            ORDER BY userId ASC
            LIMIT 50;
        """
        params = ()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            return rows
    finally:
        conn.close()


def add_user(user_id, username, email):
    """CREATE operation: Insert a new user."""
    sql = """
        INSERT INTO users (userId, username, email, created_at)
        VALUES (%s, %s, %s, NOW());
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, username, email))
        conn.commit()
        return True
    except pymysql.MySQLError as e:
        messagebox.showerror("DB Error (Add User)", str(e))
        return False
    finally:
        conn.close()


def update_user(user_id, username, email):
    """UPDATE operation: Modify existing user."""
    sql = """
        UPDATE users
        SET username = %s, email = %s
        WHERE userId = %s;
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (username, email, user_id))
        conn.commit()
        return True
    except pymysql.MySQLError as e:
        messagebox.showerror("DB Error (Update User)", str(e))
        return False
    finally:
        conn.close()


def delete_user(user_id):
    """DELETE operation: Remove a user."""
    sql = """
        DELETE FROM users
        WHERE userId = %s;
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
        conn.commit()
        return True
    except pymysql.MySQLError as e:
        messagebox.showerror("DB Error (Delete User)", str(e))
        return False
    finally:
        conn.close()


###############################################################################
# 4. SQL HELPER FUNCTIONS - RATINGS
###############################################################################

def add_or_update_rating(user_id, movie_id, rating_val):
    """Add or update rating for (user,movie)."""
    current_ts = int(time.time())

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            delete_sql = "DELETE FROM ratings WHERE userId = %s AND movieId = %s;"
            cur.execute(delete_sql, (user_id, movie_id))
            
            insert_sql = """
                INSERT INTO ratings (userId, movieId, rating, timestamp)
                VALUES (%s, %s, %s, %s);
            """
            cur.execute(insert_sql, (user_id, movie_id, rating_val, current_ts))
        conn.commit()
        return True
    except pymysql.MySQLError as e:
        messagebox.showerror("DB Error (Add/Update Rating)", str(e))
        return False
    finally:
        conn.close()


def get_user_rating(user_id, movie_id):
    """Get the current rating for a user-movie pair."""
    sql = """
        SELECT rating, timestamp
        FROM ratings
        WHERE userId = %s AND movieId = %s
        ORDER BY timestamp DESC
        LIMIT 1;
    """
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, movie_id))
            row = cur.fetchone()
            return row
    finally:
        conn.close()


def delete_rating(user_id, movie_id):
    """Delete a rating."""
    sql = """
        DELETE FROM ratings
        WHERE userId = %s AND movieId = %s;
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, movie_id))
        conn.commit()
        return True
    except pymysql.MySQLError as e:
        messagebox.showerror("DB Error (Delete Rating)", str(e))
        return False
    finally:
        conn.close()


###############################################################################
# 5. ANALYTICS FUNCTIONS
###############################################################################

def get_top_rated_movies(limit=10):
    """Aggregate query with GROUP BY, HAVING, ORDER BY."""
    start_time = time.time()
    sql = """
        SELECT 
            m.movieId,
            m.title,
            m.release_date,
            COUNT(r.rating) as vote_count,
            ROUND(AVG(r.rating), 2) as avg_rating,
            MIN(r.rating) as min_rating,
            MAX(r.rating) as max_rating
        FROM movies m
        INNER JOIN ratings r ON m.movieId = r.movieId
        WHERE m.title NOT LIKE 'Movie_%%'
        GROUP BY m.movieId, m.title, m.release_date
        HAVING COUNT(r.rating) >= 10
        ORDER BY avg_rating DESC, vote_count DESC
        LIMIT %s;
    """
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            rows = cur.fetchall()
            execution_time = time.time() - start_time
            return rows, execution_time
    finally:
        conn.close()


def get_user_statistics(user_id):
    """Nested query with correlated subqueries."""
    start_time = time.time()
    sql = """
        SELECT 
            u.userId,
            u.username,
            u.email,
            COUNT(r.movieId) as total_ratings,
            ROUND(AVG(r.rating), 2) as avg_rating_given,
            MIN(r.rating) as min_rating_given,
            MAX(r.rating) as max_rating_given,
            (SELECT COUNT(*) FROM ratings WHERE rating >= 4.0 AND userId = u.userId) as high_ratings_count,
            (SELECT COUNT(*) FROM ratings WHERE rating <= 2.0 AND userId = u.userId) as low_ratings_count
        FROM users u
        LEFT JOIN ratings r ON u.userId = r.userId
        WHERE u.userId = %s
        GROUP BY u.userId, u.username, u.email;
    """
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            row = cur.fetchone()
            execution_time = time.time() - start_time
            return row, execution_time
    finally:
        conn.close()


###############################################################################
# 6. GUI APP - TABBED INTERFACE
###############################################################################

class MovieApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # Window config
        self.title("Movie Database Management System")
        self.geometry("1400x850")
        self.resizable(True, True)
        self.configure(bg='#f0f0f0')
        
        # Configure styles
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TLabelframe', background='#f0f0f0', borderwidth=2)
        style.configure('TLabelframe.Label', font=('Arial', 11, 'bold'), 
                       background='#f0f0f0', foreground='#2c3e50')
        style.configure('TLabel', background='#f0f0f0', font=('Arial', 10))
        style.configure('TButton', font=('Arial', 9, 'bold'))
        style.configure('TEntry', fieldbackground='white', font=('Arial', 10))
        style.configure("Treeview", background="white", foreground="black",
                       rowheight=25, fieldbackground="white", font=('Arial', 9))
        style.map('Treeview', background=[('selected', '#3498db')])
        
        # Header
        header = tk.Frame(self, bg='#2c3e50', height=70)
        header.pack(fill='x', side='top')
        header.pack_propagate(False)
        
        title_label = tk.Label(header, text="TMDB Movie Database", 
                              font=('Arial', 18, 'bold'), bg='#2c3e50', fg='white')
        title_label.pack(pady=8)
        
        # Create tabbed notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create tabs
        self.movies_tab = ttk.Frame(self.notebook)
        self.users_tab = ttk.Frame(self.notebook)
        self.analytics_tab = ttk.Frame(self.notebook)
        self.nosql_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.movies_tab, text='  Movies & Search  ')
        self.notebook.add(self.users_tab, text='  Users & Ratings  ')
        self.notebook.add(self.analytics_tab, text='  Analytics & Stats  ')
        self.notebook.add(self.nosql_tab, text='  Genre & Keywords  ')
        
        # Build each tab
        self.build_movies_tab()
        self.build_users_tab()
        self.build_analytics_tab()
        self.build_nosql_tab()

    ###########################################################################
    # TAB 1: MOVIES & SEARCH
    ###########################################################################
    
    def build_movies_tab(self):
        """Build the Movies & Search tab."""
        # Container with fixed structure
        container = tk.Frame(self.movies_tab, bg='#f0f0f0')
        container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Search Section - FIXED HEIGHT
        search_wrapper = ttk.LabelFrame(container, text="Movie Search", padding=10)
        search_wrapper.pack(fill='x', pady=(0, 10))
        search_wrapper.pack_propagate(False)  # Prevent resizing
        search_wrapper.configure(height=160)  # Fixed height - more space for advanced search
        
        # Basic search
        basic_frame = tk.Frame(search_wrapper, bg='white')
        basic_frame.pack(fill='x', pady=(0, 5))
        
        ttk.Label(basic_frame, text="Title:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(basic_frame, textvariable=self.search_var, width=40)
        self.search_entry.grid(row=0, column=1, padx=5, pady=5)
        self.search_entry.bind('<Return>', lambda e: self.handle_search())
        
        ttk.Button(basic_frame, text="Search", command=self.handle_search).grid(row=0, column=2, padx=5, pady=5)
        
        self.exec_time_label = tk.Label(search_wrapper, text="", font=('Arial', 8), 
                                       bg='white', fg='#27ae60')
        self.exec_time_label.pack(anchor='e')
        
        # Advanced search
        adv_frame = tk.Frame(search_wrapper, bg='white')
        adv_frame.pack(fill='x')
        
        ttk.Label(adv_frame, text="Min Rating:").grid(row=0, column=0, sticky="w", padx=5, pady=3)
        self.min_rating_var = tk.StringVar()
        ttk.Entry(adv_frame, textvariable=self.min_rating_var, width=10).grid(row=0, column=1, padx=5, pady=3)
        
        ttk.Label(adv_frame, text="Max Rating:").grid(row=0, column=2, sticky="w", padx=5, pady=3)
        self.max_rating_var = tk.StringVar()
        ttk.Entry(adv_frame, textvariable=self.max_rating_var, width=10).grid(row=0, column=3, padx=5, pady=3)
        
        ttk.Label(adv_frame, text="Min Votes:").grid(row=0, column=4, sticky="w", padx=5, pady=3)
        self.min_votes_var = tk.StringVar()
        ttk.Entry(adv_frame, textvariable=self.min_votes_var, width=10).grid(row=0, column=5, padx=5, pady=3)
        
        ttk.Button(adv_frame, text="Advanced Search", 
                  command=self.handle_advanced_search).grid(row=0, column=6, padx=5, pady=3)
        
        self.adv_exec_time_label = tk.Label(search_wrapper, text="", font=('Arial', 8), 
                                            bg='white', fg='#e67e22')
        self.adv_exec_time_label.pack(anchor='e')
        
        # Results Section - Can shrink to show details below
        results_wrapper = ttk.LabelFrame(container, text="Search Results", padding=10)
        results_wrapper.pack(fill='both', expand=True)
        
        tree_frame = tk.Frame(results_wrapper, bg='white')
        tree_frame.pack(fill='both', expand=True)
        
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
        
        self.tree.pack(side='left', fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Movie details - Increased height for MongoDB data
        ttk.Button(results_wrapper, text="View Details", 
                  command=self.handle_view_details).pack(anchor='w', pady=(5, 3))
        
        self.details_text = tk.Text(results_wrapper, width=100, height=12, state="disabled",
                                   wrap="word", borderwidth=2, relief="groove",
                                   font=('Arial', 9), bg='#ecf0f1', fg='#2c3e50')
        self.details_text.pack(fill='both', expand=True)

    ###########################################################################
    # TAB 2: USERS & RATINGS
    ###########################################################################
    
    def build_users_tab(self):
        """Build the Users & Ratings tab."""
        container = tk.Frame(self.users_tab, bg='#f0f0f0')
        container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # User Management Section - FIXED HEIGHT
        user_wrapper = ttk.LabelFrame(container, text="User Management", padding=10)
        user_wrapper.pack(fill='x', pady=(0, 10))
        user_wrapper.pack_propagate(False)  # Prevent resizing
        user_wrapper.configure(height=200)  # Fixed height
        
        user_form = tk.Frame(user_wrapper, bg='white')
        user_form.pack(fill='x')
        
        ttk.Label(user_form, text="User ID:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.user_id_var = tk.StringVar()
        ttk.Entry(user_form, textvariable=self.user_id_var, width=15).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(user_form, text="Name:").grid(row=0, column=2, sticky="e", padx=5, pady=5)
        self.username_var = tk.StringVar()
        ttk.Entry(user_form, textvariable=self.username_var, width=20).grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(user_form, text="Email:").grid(row=0, column=4, sticky="e", padx=5, pady=5)
        self.email_var = tk.StringVar()
        ttk.Entry(user_form, textvariable=self.email_var, width=30).grid(row=0, column=5, padx=5, pady=5)
        
        # CRUD Buttons
        button_frame = tk.Frame(user_form, bg='white')
        button_frame.grid(row=1, column=0, columnspan=6, pady=10)
        
        ttk.Button(button_frame, text="Create", command=self.handle_add_user, width=12).pack(side='left', padx=3)
        ttk.Button(button_frame, text="Read", command=self.handle_read_user, width=12).pack(side='left', padx=3)
        ttk.Button(button_frame, text="Update", command=self.handle_update_user, width=12).pack(side='left', padx=3)
        ttk.Button(button_frame, text="Delete", command=self.handle_delete_user, width=12).pack(side='left', padx=3)
        ttk.Button(button_frame, text="Search All", command=self.handle_search_users, width=12).pack(side='left', padx=3)
        
        # User status display
        self.user_status_text = tk.Text(user_wrapper, width=100, height=8, state="disabled",
                                       wrap="word", borderwidth=2, relief="groove",
                                       font=('Consolas', 9), bg='#ffffff', fg='#000000')
        self.user_status_text.pack(fill='x', pady=(5, 0))
        
        # Ratings Management Section
        rating_wrapper = ttk.LabelFrame(container, text="Ratings Management", padding=10)
        rating_wrapper.pack(fill='both', expand=True)
        
        rating_form = tk.Frame(rating_wrapper, bg='white')
        rating_form.pack(fill='x')
        
        ttk.Label(rating_form, text="User ID:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.rate_user_id_var = tk.StringVar()
        ttk.Entry(rating_form, textvariable=self.rate_user_id_var, width=15).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(rating_form, text="Movie ID:").grid(row=0, column=2, sticky="e", padx=5, pady=5)
        self.rate_movie_id_var = tk.StringVar()
        ttk.Entry(rating_form, textvariable=self.rate_movie_id_var, width=15).grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(rating_form, text="Rating (0.5-5.0):").grid(row=0, column=4, sticky="e", padx=5, pady=5)
        self.rate_value_var = tk.StringVar()
        ttk.Entry(rating_form, textvariable=self.rate_value_var, width=10).grid(row=0, column=5, padx=5, pady=5)
        
        ttk.Button(rating_form, text="Add/Update Rating", 
                  command=self.handle_add_update_rating).grid(row=0, column=6, padx=5, pady=5)
        ttk.Button(rating_form, text="Delete Rating", 
                  command=self.handle_delete_rating).grid(row=0, column=7, padx=5, pady=5)
        
        tk.Label(rating_wrapper, text="Activity Log:", font=('Arial', 9, 'bold'), 
                bg='white', anchor='w').pack(fill='x', pady=(10, 2))
        
        self.rating_status_text = tk.Text(rating_wrapper, width=100, height=12, state="disabled",
                                         wrap="word", borderwidth=2, relief="groove",
                                         font=('Consolas', 8), bg='#2c3e50', fg='#ecf0f1')
        self.rating_status_text.pack(fill='both', expand=True)

    ###########################################################################
    # TAB 3: ANALYTICS & STATS
    ###########################################################################
    
    def build_analytics_tab(self):
        """Build the Analytics & Stats tab."""
        container = tk.Frame(self.analytics_tab, bg='#f0f0f0')
        container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Top Rated Movies
        top_wrapper = ttk.LabelFrame(container, text="Top Rated Movies", padding=10)
        top_wrapper.pack(fill='both', expand=True, pady=(0, 10))
        
        ttk.Button(top_wrapper, text="Show Top 20 Movies", 
                  command=self.handle_top_movies).pack(anchor='w', pady=(0, 5))
        
        self.top_exec_time_label = tk.Label(top_wrapper, text="", font=('Arial', 8), 
                                            bg='white', fg='#8e44ad')
        self.top_exec_time_label.pack(anchor='e')
        
        top_tree_frame = tk.Frame(top_wrapper, bg='white')
        top_tree_frame.pack(fill='both', expand=True)
        
        top_columns = ("title", "votes", "avg", "min", "max")
        self.top_tree = ttk.Treeview(top_tree_frame, columns=top_columns, show="headings", height=8)
        
        self.top_tree.heading("title", text="Movie Title")
        self.top_tree.heading("votes", text="Votes")
        self.top_tree.heading("avg", text="Avg")
        self.top_tree.heading("min", text="Min")
        self.top_tree.heading("max", text="Max")
        
        self.top_tree.column("title", width=500, anchor="w")
        self.top_tree.column("votes", width=80, anchor="center")
        self.top_tree.column("avg", width=80, anchor="center")
        self.top_tree.column("min", width=80, anchor="center")
        self.top_tree.column("max", width=80, anchor="center")
        
        self.top_tree.pack(side='left', fill='both', expand=True)
        
        top_scrollbar = ttk.Scrollbar(top_tree_frame, orient=tk.VERTICAL, command=self.top_tree.yview)
        top_scrollbar.pack(side='right', fill='y')
        self.top_tree.configure(yscrollcommand=top_scrollbar.set)
        
        # User Statistics - FIXED HEIGHT
        stats_wrapper = ttk.LabelFrame(container, text="User Statistics", padding=10)
        stats_wrapper.pack(fill='x')
        stats_wrapper.pack_propagate(False)  # Prevent resizing
        stats_wrapper.configure(height=180)  # Fixed height
        
        stats_form = tk.Frame(stats_wrapper, bg='white')
        stats_form.pack(fill='x')
        
        ttk.Label(stats_form, text="User ID:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.stats_user_var = tk.StringVar()
        ttk.Entry(stats_form, textvariable=self.stats_user_var, width=15).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(stats_form, text="Get Stats", 
                  command=self.handle_user_stats).grid(row=0, column=2, padx=5, pady=5)
        
        self.stats_exec_time_label = tk.Label(stats_wrapper, text="", font=('Arial', 8), 
                                              bg='white', fg='#16a085')
        self.stats_exec_time_label.pack(anchor='e')
        
        self.stats_text = tk.Text(stats_wrapper, width=100, height=6, state="disabled",
                                 wrap="word", borderwidth=2, relief="groove",
                                 font=('Consolas', 9), bg='#ecf0f1', fg='#2c3e50')
        self.stats_text.pack(fill='x', pady=(5, 0))

    ###########################################################################
    # TAB 4: NoSQL FEATURES
    ###########################################################################
    
    def build_nosql_tab(self):
        """Build the NoSQL Features tab - MongoDB operations."""
        container = tk.Frame(self.nosql_tab, bg='#f0f0f0')
        container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Left side: Search & Operations
        left_container = tk.Frame(container, bg='#f0f0f0')
        left_container.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        # Genre Search Section - FIXED HEIGHT
        genre_wrapper = ttk.LabelFrame(left_container, text="Search by Genre", padding=10)
        genre_wrapper.pack(fill='x', pady=(0, 10))
        genre_wrapper.pack_propagate(False)
        genre_wrapper.configure(height=120)
        
        genre_form = tk.Frame(genre_wrapper, bg='white')
        genre_form.pack(fill='x')
        
        ttk.Label(genre_form, text="Genre:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.genre_var = tk.StringVar()
        genre_entry = ttk.Entry(genre_form, textvariable=self.genre_var, width=30)
        genre_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(genre_form, text="Search Genre", 
                  command=self.handle_genre_search).grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(genre_form, text="Examples: Action, Drama, Sci-Fi, Horror", 
                 font=('Arial', 8, 'italic')).grid(row=1, column=0, columnspan=3, pady=(0, 5))
        
        self.genre_exec_label = tk.Label(genre_wrapper, text="", font=('Arial', 8), 
                                         bg='white', fg='#e67e22')
        self.genre_exec_label.pack(anchor='e')
        
        # Keyword Search Section - FIXED HEIGHT
        keyword_wrapper = ttk.LabelFrame(left_container, text="Search by Keywords/Tags", padding=10)
        keyword_wrapper.pack(fill='x', pady=(0, 10))
        keyword_wrapper.pack_propagate(False)
        keyword_wrapper.configure(height=120)
        
        keyword_form = tk.Frame(keyword_wrapper, bg='white')
        keyword_form.pack(fill='x')
        
        ttk.Label(keyword_form, text="Keyword:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.keyword_var = tk.StringVar()
        keyword_entry = ttk.Entry(keyword_form, textvariable=self.keyword_var, width=30)
        keyword_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(keyword_form, text="Search Keyword", 
                  command=self.handle_keyword_search).grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(keyword_form, text="Examples: heist, space, revenge, detective", 
                 font=('Arial', 8, 'italic')).grid(row=1, column=0, columnspan=3, pady=(0, 5))
        
        self.keyword_exec_label = tk.Label(keyword_wrapper, text="", font=('Arial', 8), 
                                           bg='white', fg='#e67e22')
        self.keyword_exec_label.pack(anchor='e')
        
        # Results Section - Expandable
        results_wrapper = ttk.LabelFrame(left_container, text="Query Results", padding=10)
        results_wrapper.pack(fill='both', expand=True)
        
        tree_frame = tk.Frame(results_wrapper, bg='white')
        tree_frame.pack(fill='both', expand=True)
        
        columns = ("tmdbId", "title", "genres", "rating")
        self.nosql_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=10)
        
        self.nosql_tree.heading("tmdbId", text="TMDB ID")
        self.nosql_tree.heading("title", text="Title")
        self.nosql_tree.heading("genres", text="Genres")
        self.nosql_tree.heading("rating", text="Rating")
        
        self.nosql_tree.column("tmdbId", width=80, anchor="center")
        self.nosql_tree.column("title", width=300, anchor="w")
        self.nosql_tree.column("genres", width=200, anchor="w")
        self.nosql_tree.column("rating", width=80, anchor="center")
        
        self.nosql_tree.pack(side='left', fill='both', expand=True)
        
        nosql_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.nosql_tree.yview)
        nosql_scrollbar.pack(side='right', fill='y')
        self.nosql_tree.configure(yscrollcommand=nosql_scrollbar.set)
        
        # Right side: Analytics
        right_container = tk.Frame(container, bg='#f0f0f0')
        right_container.pack(side='right', fill='both', expand=True, padx=(5, 0))
        
        # Genre Statistics - FIXED HEIGHT
        genre_stats_wrapper = ttk.LabelFrame(right_container, text="Genre Statistics", padding=10)
        genre_stats_wrapper.pack(fill='x', pady=(0, 10))
        genre_stats_wrapper.pack_propagate(False)
        genre_stats_wrapper.configure(height=100)
        
        ttk.Button(genre_stats_wrapper, text="Get Genre Statistics", 
                  command=self.handle_genre_stats).pack(anchor='w', pady=(0, 5))
        
        self.genre_stats_exec_label = tk.Label(genre_stats_wrapper, text="", font=('Arial', 8), 
                                               bg='white', fg='#9b59b6')
        self.genre_stats_exec_label.pack(anchor='e')
        
        # Genre Stats Results - Expandable
        genre_stats_results = ttk.LabelFrame(right_container, text="Top Genres by Count", padding=10)
        genre_stats_results.pack(fill='both', expand=True)
        
        stats_tree_frame = tk.Frame(genre_stats_results, bg='white')
        stats_tree_frame.pack(fill='both', expand=True)
        
        stats_columns = ("genre", "count", "avg_rating", "avg_revenue")
        self.genre_stats_tree = ttk.Treeview(stats_tree_frame, columns=stats_columns, 
                                             show="headings", height=10)
        
        self.genre_stats_tree.heading("genre", text="Genre(s)")
        self.genre_stats_tree.heading("count", text="Count")
        self.genre_stats_tree.heading("avg_rating", text="Avg Rating")
        self.genre_stats_tree.heading("avg_revenue", text="Avg Revenue")
        
        self.genre_stats_tree.column("genre", width=200, anchor="w")
        self.genre_stats_tree.column("count", width=80, anchor="center")
        self.genre_stats_tree.column("avg_rating", width=100, anchor="center")
        self.genre_stats_tree.column("avg_revenue", width=120, anchor="e")
        
        self.genre_stats_tree.pack(side='left', fill='both', expand=True)
        
        stats_scrollbar = ttk.Scrollbar(stats_tree_frame, orient=tk.VERTICAL, 
                                        command=self.genre_stats_tree.yview)
        stats_scrollbar.pack(side='right', fill='y')
        self.genre_stats_tree.configure(yscrollcommand=stats_scrollbar.set)

    ###########################################################################
    # EVENT HANDLERS - MOVIES
    ###########################################################################
    
    def handle_search(self):
        """Basic movie search."""
        keyword = self.search_var.get().strip()
        
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if keyword == "":
            messagebox.showinfo("Info", "Please enter a movie title to search.")
            return
        
        rows, exec_time = search_movies_by_title(keyword)
        self.exec_time_label.config(text=f"⏱️ Query: {exec_time:.4f}s")
        
        if not rows:
            messagebox.showinfo("Nothing found", "No movies matched your search.")
            return
        
        for row in rows:
            self.tree.insert("", tk.END, values=(
                row["movieId"],
                row["title"],
                row["vote_count"] if row["vote_count"] else 0,
                row["avg_rating"] if row["avg_rating"] is not None else "N/A"
            ))
    
    def handle_advanced_search(self):
        """Advanced movie search with filters."""
        title = self.search_var.get().strip() or None
        
        try:
            min_rating = float(self.min_rating_var.get()) if self.min_rating_var.get() else None
            max_rating = float(self.max_rating_var.get()) if self.max_rating_var.get() else None
            min_votes = int(self.min_votes_var.get()) if self.min_votes_var.get() else None
        except ValueError:
            messagebox.showerror("Input Error", "Rating must be a number, votes must be an integer.")
            return
        
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        rows, exec_time = search_movies_advanced(title, min_rating, max_rating, min_votes)
        self.adv_exec_time_label.config(text=f"⏱️ Advanced query: {exec_time:.4f}s")
        
        if not rows:
            messagebox.showinfo("Nothing found", "No movies matched the filters.")
            return
        
        for row in rows:
            self.tree.insert("", tk.END, values=(
                row["movieId"],
                row["title"],
                row["vote_count"] if row["vote_count"] else 0,
                row["avg_rating"] if row["avg_rating"] is not None else "N/A"
            ))
    
    def handle_view_details(self):
        """View selected movie details - combines MariaDB + MongoDB data."""
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("Select a movie", "Click a movie row first.")
            return
        
        values = self.tree.item(selected, "values")
        movie_id = values[0]
        
        # Get MariaDB data (SQL)
        info = get_movie_details(movie_id)
        if not info:
            messagebox.showerror("Error", "Movie not found in database.")
            return
        
        # Build SQL portion
        details_str = (
            f"=== MariaDB (SQL) Data ===\n"
            f"Movie ID: {info['movieId']} | Title: {info['title']}\n"
            f"Release Date: {info['release_date']} | User Votes: {info['vote_count']}\n"
            f"Average User Rating: {info['avg_rating']}\n"
            f"IMDb ID: {info['imdbId']} | TMDB ID: {info['tmdbId']}\n"
        )
        
        # Get MongoDB data (NoSQL) if tmdbId exists
        tmdb_meta = None
        if info.get('tmdbId'):
            tmdb_meta = get_tmdb_metadata(info['tmdbId'])
        
        if tmdb_meta:
            # Format genres properly (handle both string and list)
            genres = tmdb_meta.get('genres', 'N/A')
            if isinstance(genres, list):
                genres_str = ', '.join(genres)
            elif isinstance(genres, str):
                genres_str = genres  # Already a string, don't split it
            else:
                genres_str = 'N/A'
            
            details_str += (
                f"\n=== MongoDB (NoSQL) Data ===\n"
                f"TMDB Title: {tmdb_meta.get('title', 'N/A')}\n"
                f"Genres: {genres_str}\n"
                f"TMDB Vote Average: {tmdb_meta.get('vote_average', 'N/A')} "
                f"(Count: {tmdb_meta.get('vote_count', 'N/A')})\n"
                f"Runtime: {tmdb_meta.get('runtime', 'N/A')} min | "
                f"Revenue: ${tmdb_meta.get('revenue', 0):,}\n"
                f"Language: {tmdb_meta.get('original_language', 'N/A')} | "
                f"Popularity: {tmdb_meta.get('popularity', 'N/A')}\n"
                f"Tagline: {tmdb_meta.get('tagline', 'N/A')}\n"
                f"\nOverview: {tmdb_meta.get('overview', 'N/A')}\n"
            )
            
            # Add Similar Movies section
            similar_movies, sim_time = find_similar_movies_mongo(info['tmdbId'])
            if similar_movies:
                details_str += f"\n=== Similar Movies (MongoDB Query: {sim_time:.4f}s) ===\n"
                for i, movie in enumerate(similar_movies[:5], 1):
                    details_str += f"{i}. {movie.get('title', 'N/A')} (Rating: {movie.get('vote_average', 'N/A')})\n"
        else:
            details_str += f"\n=== MongoDB (NoSQL) Data ===\n(No TMDB metadata found for this movie)\n"
        
        self.details_text.config(state="normal")
        self.details_text.delete("1.0", tk.END)
        self.details_text.insert(tk.END, details_str)
        self.details_text.config(state="disabled")

    ###########################################################################
    # EVENT HANDLERS - USERS
    ###########################################################################
    
    def handle_add_user(self):
        """CREATE operation for users."""
        try:
            user_id = int(self.user_id_var.get().strip())
        except ValueError:
            messagebox.showerror("Input Error", "User ID must be an integer.")
            return
        
        username = self.username_var.get().strip()
        email = self.email_var.get().strip()
        
        if username == "" or email == "":
            messagebox.showerror("Input Error", "Username and Email cannot be empty.")
            return
        
        if not is_valid_email(email):
            messagebox.showerror("Input Error", "Please enter a valid email address.")
            return
        
        ok = add_user(user_id, username, email)
        if ok:
            messagebox.showinfo("Success", f"User {user_id} created successfully!")
            self.log_user_activity(f"[CREATE] User {user_id} ({username}) added")
            self.user_id_var.set("")
            self.username_var.set("")
            self.email_var.set("")
    
    def handle_read_user(self):
        """READ operation - View single user."""
        try:
            user_id = int(self.user_id_var.get().strip())
        except ValueError:
            messagebox.showerror("Input Error", "User ID must be an integer.")
            return
        
        user = get_user(user_id)
        
        self.user_status_text.config(state="normal")
        self.user_status_text.delete("1.0", tk.END)
        
        if user:
            info = (
                f"[READ] User Found:\n"
                f"ID: {user['userId']} | Name: {user['username']}\n"
                f"Email: {user['email']} | Created: {user['created_at']}\n"
            )
            self.user_status_text.insert(tk.END, info)
            self.username_var.set(user['username'])
            self.email_var.set(user['email'])
        else:
            self.user_status_text.insert(tk.END, f"[READ] User ID {user_id} not found")
        
        self.user_status_text.config(state="disabled")
    
    def handle_search_users(self):
        """READ operation - Search all users."""
        keyword = self.username_var.get().strip()
        users = search_users(keyword)
        
        self.user_status_text.config(state="normal")
        self.user_status_text.delete("1.0", tk.END)
        
        if users:
            self.user_status_text.insert(tk.END, f"[READ] Found {len(users)} user(s):\n")
            for user in users[:15]:
                username = user['username'] if user['username'] else "(no name)"
                email = user['email'] if user['email'] else "(no email)"
                self.user_status_text.insert(
                    tk.END,
                    f"ID:{user['userId']} {username} ({email})\n"
                )
            if len(users) > 15:
                self.user_status_text.insert(tk.END, f"... and {len(users)-15} more\n")
        else:
            self.user_status_text.insert(tk.END, "[READ] No users found")
        
        self.user_status_text.config(state="disabled")
    
    def handle_update_user(self):
        """UPDATE operation for users."""
        try:
            user_id = int(self.user_id_var.get().strip())
        except ValueError:
            messagebox.showerror("Input Error", "User ID must be an integer.")
            return
        
        username = self.username_var.get().strip()
        email = self.email_var.get().strip()
        
        if username == "" or email == "":
            messagebox.showerror("Input Error", "Username and Email cannot be empty.")
            return
        
        if not is_valid_email(email):
            messagebox.showerror("Input Error", "Please enter a valid email address.")
            return
        
        existing = get_user(user_id)
        if not existing:
            messagebox.showerror("Error", f"User ID {user_id} does not exist. Use Create instead.")
            return
        
        ok = update_user(user_id, username, email)
        if ok:
            messagebox.showinfo("Success", f"User {user_id} updated successfully!")
            self.log_user_activity(f"[UPDATE] User {user_id} updated to {username}")
    
    def handle_delete_user(self):
        """DELETE operation for users."""
        try:
            user_id = int(self.user_id_var.get().strip())
        except ValueError:
            messagebox.showerror("Input Error", "User ID must be an integer.")
            return
        
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Delete user {user_id}? This will also delete all their ratings!"
        )
        
        if not confirm:
            return
        
        ok = delete_user(user_id)
        if ok:
            messagebox.showinfo("Success", f"User {user_id} deleted successfully!")
            self.log_user_activity(f"[DELETE] User {user_id} removed")
            self.user_id_var.set("")
            self.username_var.set("")
            self.email_var.set("")
    
    def log_user_activity(self, message):
        """Log user CRUD activities."""
        self.user_status_text.config(state="normal")
        self.user_status_text.insert(tk.END, message + "\n")
        self.user_status_text.see(tk.END)
        self.user_status_text.config(state="disabled")

    ###########################################################################
    # EVENT HANDLERS - RATINGS
    ###########################################################################
    
    def handle_add_update_rating(self):
        """Add or update rating with referential integrity validation."""
        # Validate input types
        try:
            uid = int(self.rate_user_id_var.get().strip())
            mid = int(self.rate_movie_id_var.get().strip())
        except ValueError:
            messagebox.showerror("Input Error", "User ID and Movie ID must be integers.")
            return
        
        try:
            r_val = float(self.rate_value_var.get().strip())
        except ValueError:
            messagebox.showerror("Input Error", "Rating must be a number like 3.5.")
            return
        
        # Validate rating range
        if r_val < 0.5 or r_val > 5.0:
            messagebox.showerror("Input Error", "Rating must be between 0.5 and 5.0.")
            return
        
        # ✅ VALIDATION: Check if user exists
        user_info = get_user(uid)
        if not user_info:
            messagebox.showerror("Validation Error", 
                               f"User ID {uid} does not exist in database.\n"
                               f"Please create the user first in the Users tab.")
            self.rating_status_text.config(state="normal")
            self.rating_status_text.insert(
                tk.END,
                f"[VALIDATION ERROR] User {uid} not found - rating rejected\n"
            )
            self.rating_status_text.see(tk.END)
            self.rating_status_text.config(state="disabled")
            return
        
        # ✅ VALIDATION: Check if movie exists
        movie_info = get_movie_details(mid)
        if not movie_info:
            messagebox.showerror("Validation Error", 
                               f"Movie ID {mid} does not exist in database.\n"
                               f"Cannot rate a non-existent movie.")
            self.rating_status_text.config(state="normal")
            self.rating_status_text.insert(
                tk.END,
                f"[VALIDATION ERROR] Movie {mid} not found - rating rejected\n"
            )
            self.rating_status_text.see(tk.END)
            self.rating_status_text.config(state="disabled")
            return
        
        # Validation passed - proceed with rating
        ok = add_or_update_rating(uid, mid, r_val)
        
        self.rating_status_text.config(state="normal")
        if ok:
            saved_rating = get_user_rating(uid, mid)
            if saved_rating:
                self.rating_status_text.insert(
                    tk.END,
                    f"[OK] Rating saved -> user {uid} ({user_info['username']}), "
                    f"movie {mid} ({movie_info['title']}), rating {saved_rating['rating']} (verified)\n"
                )
            else:
                self.rating_status_text.insert(
                    tk.END,
                    f"[OK] Rating set -> user {uid}, movie {mid}, rating {r_val}\n"
                )
            self.rate_user_id_var.set("")
            self.rate_movie_id_var.set("")
            self.rate_value_var.set("")
        else:
            self.rating_status_text.insert(
                tk.END,
                f"[ERR] Could not set rating for user {uid}, movie {mid}\n"
            )
        self.rating_status_text.see(tk.END)
        self.rating_status_text.config(state="disabled")
    
    def handle_delete_rating(self):
        """Delete rating with validation."""
        try:
            uid = int(self.rate_user_id_var.get().strip())
            mid = int(self.rate_movie_id_var.get().strip())
        except ValueError:
            messagebox.showerror("Input Error", "User ID and Movie ID must be integers.")
            return
        
        # ✅ VALIDATION: Check if rating exists before deleting
        existing_rating = get_user_rating(uid, mid)
        if not existing_rating:
            messagebox.showwarning("Not Found", 
                                  f"No rating found for User {uid} and Movie {mid}.\n"
                                  f"Nothing to delete.")
            self.rating_status_text.config(state="normal")
            self.rating_status_text.insert(
                tk.END,
                f"[WARNING] No rating to delete for user {uid}, movie {mid}\n"
            )
            self.rating_status_text.see(tk.END)
            self.rating_status_text.config(state="disabled")
            return
        
        # Confirm deletion
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Delete rating {existing_rating['rating']} from User {uid} for Movie {mid}?"
        )
        
        if not confirm:
            return
        
        ok = delete_rating(uid, mid)
        
        self.rating_status_text.config(state="normal")
        if ok:
            self.rating_status_text.insert(
                tk.END,
                f"[OK] Deleted rating {existing_rating['rating']} for user {uid}, movie {mid}\n"
            )
            self.rate_user_id_var.set("")
            self.rate_movie_id_var.set("")
        else:
            self.rating_status_text.insert(
                tk.END,
                f"[ERR] Failed to delete rating for user {uid}, movie {mid}\n"
            )
        self.rating_status_text.see(tk.END)
        self.rating_status_text.config(state="disabled")

    ###########################################################################
    # EVENT HANDLERS - ANALYTICS
    ###########################################################################
    
    def handle_top_movies(self):
        """Show top rated movies."""
        for item in self.top_tree.get_children():
            self.top_tree.delete(item)
        
        rows, exec_time = get_top_rated_movies(20)
        self.top_exec_time_label.config(text=f"⏱️ Aggregate query: {exec_time:.4f}s")
        
        for row in rows:
            self.top_tree.insert("", tk.END, values=(
                row["title"][:60] + "..." if len(row["title"]) > 60 else row["title"],
                row["vote_count"],
                row["avg_rating"],
                row["min_rating"],
                row["max_rating"]
            ))
    
    def handle_user_stats(self):
        """Show user statistics."""
        try:
            user_id = int(self.stats_user_var.get().strip())
        except ValueError:
            messagebox.showerror("Input Error", "User ID must be an integer.")
            return
        
        result, exec_time = get_user_statistics(user_id)
        self.stats_exec_time_label.config(text=f"⏱️ Nested query: {exec_time:.4f}s")
        
        self.stats_text.config(state="normal")
        self.stats_text.delete("1.0", tk.END)
        
        if not result:
            self.stats_text.insert(tk.END, f"No user found with ID {user_id}")
        else:
            stats = (
                f"User: {result['username']} ({result['email']})\n"
                f"Total Ratings: {result['total_ratings']}\n"
                f"Avg Rating Given: {result['avg_rating_given']}\n"
                f"Range: {result['min_rating_given']} - {result['max_rating_given']}\n"
                f"High Ratings (≥4): {result['high_ratings_count']} | "
                f"Low Ratings (≤2): {result['low_ratings_count']}"
            )
            self.stats_text.insert(tk.END, stats)
        
        self.stats_text.config(state="disabled")

    ###########################################################################
    # EVENT HANDLERS - NoSQL
    ###########################################################################
    
    def handle_genre_search(self):
        """Search movies by genre in MongoDB."""
        genre = self.genre_var.get().strip()
        
        # Clear previous results
        for item in self.nosql_tree.get_children():
            self.nosql_tree.delete(item)
        
        if not genre:
            messagebox.showinfo("Info", "Please enter a genre to search.")
            return
        
        results, exec_time = search_movies_by_genre_mongo(genre)
        self.genre_exec_label.config(text=f"⚡ MongoDB query: {exec_time:.4f}s | Results: {len(results)}")
        
        if not results:
            messagebox.showinfo("No Results", f"No movies found with genre '{genre}'")
            return
        
        for movie in results:
            self.nosql_tree.insert('', 'end', values=(
                movie.get('tmdbId', 'N/A'),
                movie.get('title', 'N/A'),
                movie.get('genres', 'N/A'),
                movie.get('vote_average', 'N/A')
            ))
    
    def handle_keyword_search(self):
        """Search movies by keyword in overview."""
        keyword = self.keyword_var.get().strip()
        
        # Clear previous results
        for item in self.nosql_tree.get_children():
            self.nosql_tree.delete(item)
        
        if not keyword:
            messagebox.showinfo("Info", "Please enter a keyword to search.")
            return
        
        results, exec_time = search_movies_by_keyword_mongo(keyword)
        self.keyword_exec_label.config(text=f"⚡ MongoDB query: {exec_time:.4f}s | Results: {len(results)}")
        
        if not results:
            messagebox.showinfo("No Results", f"No movies found with keyword '{keyword}'")
            return
        
        for movie in results:
            self.nosql_tree.insert('', 'end', values=(
                movie.get('tmdbId', 'N/A'),
                movie.get('title', 'N/A'),
                movie.get('genres', 'N/A'),
                movie.get('vote_average', 'N/A')
            ))
    
    def handle_genre_stats(self):
        """Get genre statistics using MongoDB aggregation."""
        # Clear previous results
        for item in self.genre_stats_tree.get_children():
            self.genre_stats_tree.delete(item)
        
        results, exec_time = get_genre_statistics_mongo()
        self.genre_stats_exec_label.config(text=f"⚡ Aggregation pipeline: {exec_time:.4f}s")
        
        if not results:
            messagebox.showinfo("No Results", "No genre statistics available")
            return
        
        for stat in results:
            self.genre_stats_tree.insert('', 'end', values=(
                stat.get('_id', 'N/A'),
                stat.get('count', 0),
                f"{stat.get('avg_rating', 0):.2f}" if stat.get('avg_rating') else 'N/A',
                f"${stat.get('avg_revenue', 0):,.0f}" if stat.get('avg_revenue') else '$0'
            ))


###############################################################################
# MAIN
###############################################################################

if __name__ == "__main__":
    app = MovieApp()
    app.mainloop()
