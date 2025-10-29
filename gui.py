import pymysql
import tkinter as tk
from tkinter import ttk, messagebox
import time
import re

def is_valid_email(email):
    """Validate email format using regex pattern."""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None


###############################################################################
# 1. DB CONNECTION SETTINGS  >>>>>>  CHANGE THESE <<<<<<
###############################################################################

DB_HOST = "localhost"        # e.g. "127.0.0.1" or container IP
DB_USER = "root"             # your MySQL/MariaDB username
DB_PASS = "12345"         # your password
DB_NAME = "movies_db"        # the schema/database name from Workbench


def get_connection():
    """
    Open a DB connection. We connect per-operation to keep it simple.
    """
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )


###############################################################################
# 2. SQL HELPER FUNCTIONS
###############################################################################

def search_movies_by_title(keyword):
    """
    Returns a list of movies matching the keyword in title,
    plus their average rating if available.
    """
    sql = """
        SELECT
            m.movieId,
            m.title,
            ROUND(AVG(r.rating), 2) AS avg_rating
        FROM movies m
        LEFT JOIN ratings r ON m.movieId = r.movieId
        WHERE m.title LIKE %s
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
            return rows
    finally:
        conn.close()


def get_movie_details(movie_id):
    """
    Get full info for one movie:
    - title
    - release_date
    - avg rating
    - imdbId / tmdbId
    """
    sql = """
        SELECT
            m.movieId,
            m.title,
            m.release_date,
            ROUND(AVG(r.rating), 2) AS avg_rating,
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


def add_user(user_id, username, email):
    """
    Insert a new user row.
    created_at we'll just set to NOW() from the DB.
    """
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


def get_user(user_id):
    """
    Fetch a user for confirmation / debugging.
    """
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


def add_or_update_rating(user_id, movie_id, rating_val):
    """
    Add or update rating for (user,movie).
    We assume: if a row already exists for that user/movie pair, update the rating.
    We'll set timestamp to current UNIX time.
    """
    current_ts = int(time.time())

    # Try insert first
    insert_sql = """
        INSERT INTO ratings (userId, movieId, rating, timestamp)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
           rating = VALUES(rating),
           timestamp = VALUES(timestamp);
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(insert_sql, (user_id, movie_id, rating_val, current_ts))
        conn.commit()
        return True
    except pymysql.MySQLError as e:
        messagebox.showerror("DB Error (Add/Update Rating)", str(e))
        return False
    finally:
        conn.close()


def delete_rating(user_id, movie_id):
    """
    Delete a rating row for that (user,movie).
    This assumes your ratings table can uniquely identify a user's rating
    for a movie. If your real PK needs timestamp too, then you'll need to
    include timestamp in the WHERE.
    """
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
# 3. GUI APP
###############################################################################

class MovieApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # --- Window config ---
        self.title("Movie DB Demo App")
        self.geometry("1000x600")
        self.resizable(False, False)

        # ---------------------------
        # TOP AREA: SEARCH + RESULTS
        # ---------------------------
        top_wrapper = ttk.LabelFrame(self, text="Search Movies", padding=10)
        top_wrapper.place(x=10, y=10, width=600, height=340)

        # --- Search bar + button ---
        ttk.Label(top_wrapper, text="Enter movie title:").grid(row=0, column=0, sticky="w")

        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(top_wrapper, textvariable=self.search_var, width=40)
        self.search_entry.grid(row=0, column=1, padx=8)

        self.search_button = ttk.Button(top_wrapper, text="Search", command=self.handle_search)
        self.search_button.grid(row=0, column=2)

        # --- Results Treeview ---
        columns = ("movieId", "title", "avg_rating")
        self.tree = ttk.Treeview(
            top_wrapper,
            columns=columns,
            show="headings",
            height=12
        )

        self.tree.heading("movieId", text="Movie ID")
        self.tree.heading("title", text="Title")
        self.tree.heading("avg_rating", text="Avg Rating")

        self.tree.column("movieId", width=70, anchor="center")
        self.tree.column("title", width=350, anchor="w")
        self.tree.column("avg_rating", width=80, anchor="center")

        self.tree.grid(row=1, column=0, columnspan=3, pady=10, sticky="nsew")

        # Scrollbar for tree
        scrollbar = ttk.Scrollbar(top_wrapper, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=1, column=3, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        # --- Details button + box ---
        self.details_button = ttk.Button(top_wrapper, text="View Details", command=self.handle_view_details)
        self.details_button.grid(row=2, column=0, sticky="w")

        self.details_text = tk.Text(
            top_wrapper,
            width=60,
            height=5,
            state="disabled",
            wrap="word",
            borderwidth=1,
            relief="solid"
        )
        self.details_text.grid(row=3, column=0, columnspan=4, pady=(8,0), sticky="w")

        # ---------------------------
        # RIGHT AREA: USER CRUD
        # ---------------------------
        user_wrapper = ttk.LabelFrame(self, text="User Management", padding=10)
        user_wrapper.place(x=620, y=10, width=360, height=200)

        # Add User section
        ttk.Label(user_wrapper, text="User ID:").grid(row=0, column=0, sticky="e")
        ttk.Label(user_wrapper, text="Username:").grid(row=1, column=0, sticky="e")
        ttk.Label(user_wrapper, text="Email:").grid(row=2, column=0, sticky="e")

        self.user_id_var = tk.StringVar()
        self.username_var = tk.StringVar()
        self.email_var = tk.StringVar()

        ttk.Entry(user_wrapper, textvariable=self.user_id_var, width=25).grid(row=0, column=1, padx=5, pady=2)
        ttk.Entry(user_wrapper, textvariable=self.username_var, width=25).grid(row=1, column=1, padx=5, pady=2)
        ttk.Entry(user_wrapper, textvariable=self.email_var, width=25).grid(row=2, column=1, padx=5, pady=2)

        self.add_user_button = ttk.Button(user_wrapper, text="Add User", command=self.handle_add_user)
        self.add_user_button.grid(row=3, column=1, sticky="e", pady=5)

        # Get User section
        ttk.Label(user_wrapper, text="Lookup User ID:").grid(row=4, column=0, sticky="e", pady=(10,2))
        self.lookup_user_id_var = tk.StringVar()
        ttk.Entry(user_wrapper, textvariable=self.lookup_user_id_var, width=25).grid(row=4, column=1, padx=5, pady=(10,2))

        self.get_user_button = ttk.Button(user_wrapper, text="Get User Info", command=self.handle_get_user)
        self.get_user_button.grid(row=5, column=1, sticky="e", pady=5)

        # Output box for user info
        self.user_info_text = tk.Text(
            user_wrapper,
            width=40,
            height=3,
            state="disabled",
            wrap="word",
            borderwidth=1,
            relief="solid"
        )
        self.user_info_text.grid(row=6, column=0, columnspan=2, pady=(5,0))

        # ---------------------------
        # BOTTOM AREA: RATINGS CRUD
        # ---------------------------
        rating_wrapper = ttk.LabelFrame(self, text="Ratings Management", padding=10)
        rating_wrapper.place(x=10, y=360, width=970, height=220)

        # Add/Update Rating
        ttk.Label(rating_wrapper, text="User ID:").grid(row=0, column=0, sticky="e")
        ttk.Label(rating_wrapper, text="Movie ID:").grid(row=1, column=0, sticky="e")
        ttk.Label(rating_wrapper, text="Rating (0.5 - 5.0):").grid(row=2, column=0, sticky="e")

        self.rate_user_id_var = tk.StringVar()
        self.rate_movie_id_var = tk.StringVar()
        self.rate_value_var = tk.StringVar()

        ttk.Entry(rating_wrapper, textvariable=self.rate_user_id_var, width=20).grid(row=0, column=1, padx=5, pady=2)
        ttk.Entry(rating_wrapper, textvariable=self.rate_movie_id_var, width=20).grid(row=1, column=1, padx=5, pady=2)
        ttk.Entry(rating_wrapper, textvariable=self.rate_value_var, width=20).grid(row=2, column=1, padx=5, pady=2)

        self.add_update_rating_button = ttk.Button(
            rating_wrapper,
            text="Add / Update Rating",
            command=self.handle_add_update_rating
        )
        self.add_update_rating_button.grid(row=3, column=1, sticky="e", pady=5)

        # Delete Rating
        ttk.Label(rating_wrapper, text="Delete Rating -> User ID:").grid(row=0, column=2, sticky="e", padx=(40,5))
        ttk.Label(rating_wrapper, text="Movie ID:").grid(row=1, column=2, sticky="e", padx=(40,5))

        self.del_user_id_var = tk.StringVar()
        self.del_movie_id_var = tk.StringVar()

        ttk.Entry(rating_wrapper, textvariable=self.del_user_id_var, width=20).grid(row=0, column=3, padx=5, pady=2)
        ttk.Entry(rating_wrapper, textvariable=self.del_movie_id_var, width=20).grid(row=1, column=3, padx=5, pady=2)

        self.delete_rating_button = ttk.Button(
            rating_wrapper,
            text="Delete Rating",
            command=self.handle_delete_rating
        )
        self.delete_rating_button.grid(row=3, column=3, sticky="e", pady=5)

        # Status / feedback box for ratings ops
        self.rating_status_text = tk.Text(
            rating_wrapper,
            width=90,
            height=5,
            state="disabled",
            wrap="word",
            borderwidth=1,
            relief="solid"
        )
        self.rating_status_text.grid(row=4, column=0, columnspan=4, pady=(10,0))

    ############################################################################
    # GUI EVENT HANDLERS
    ############################################################################

    def handle_search(self):
        keyword = self.search_var.get().strip()

        # Clear old rows
        for item in self.tree.get_children():
            self.tree.delete(item)

        if keyword == "":
            messagebox.showinfo("Info", "Please type part of a movie title first.")
            return

        rows = search_movies_by_title(keyword)
        if not rows:
            messagebox.showinfo("Nothing found", "No movies matched that search.")
            return

        for row in rows:
            self.tree.insert(
                "",
                tk.END,
                values=(
                    row["movieId"],
                    row["title"],
                    row["avg_rating"] if row["avg_rating"] is not None else "N/A"
                )
            )

    def handle_view_details(self):
        # Get selected row in the Treeview
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("Select a movie", "Click a movie row first.")
            return

        values = self.tree.item(selected, "values")
        movie_id = values[0]

        info = get_movie_details(movie_id)
        if not info:
            messagebox.showerror("Error", "Movie not found in DB?")
            return

        details_str = (
            f"Movie ID: {info['movieId']}\n"
            f"Title: {info['title']}\n"
            f"Release Date: {info['release_date']}\n"
            f"Average Rating: {info['avg_rating']}\n"
            f"IMDb ID: {info['imdbId']}\n"
            f"TMDB ID: {info['tmdbId']}\n"
        )

        self.details_text.config(state="normal")
        self.details_text.delete("1.0", tk.END)
        self.details_text.insert(tk.END, details_str)
        self.details_text.config(state="disabled")

    def handle_add_user(self):
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
            messagebox.showinfo("Success", f"User {user_id} added.")
            # Clear input fields after successful addition
            self.user_id_var.set("")
            self.username_var.set("")
            self.email_var.set("")
            # optional: clear inputs
            # self.user_id_var.set("")
            # self.username_var.set("")
            # self.email_var.set("")

    def handle_get_user(self):
        # fetch user by userId and display in user_info_text
        try:
            lookup_id = int(self.lookup_user_id_var.get().strip())
        except ValueError:
            messagebox.showerror("Input Error", "Lookup User ID must be an integer.")
            return

        row = get_user(lookup_id)

        self.user_info_text.config(state="normal")
        self.user_info_text.delete("1.0", tk.END)

        if not row:
            self.user_info_text.insert(tk.END, f"No user found with ID {lookup_id}")
        else:
            txt = (
                f"userId: {row['userId']}\n"
                f"username: {row['username']}\n"
                f"email: {row['email']}\n"
                f"created_at: {row['created_at']}\n"
            )
            self.user_info_text.insert(tk.END, txt)

        self.user_info_text.config(state="disabled")

    def handle_add_update_rating(self):
        # Read rating form
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

        if r_val < 0.5 or r_val > 5.0:
            messagebox.showerror("Input Error", "Rating must be between 0.5 and 5.0.")
            return

        ok = add_or_update_rating(uid, mid, r_val)

        self.rating_status_text.config(state="normal")
        if ok:
            self.rating_status_text.insert(
                tk.END,
                f"[OK] Rating set -> user {uid}, movie {mid}, rating {r_val}\n"
            )
            # Clear input fields after successful rating
            self.rate_user_id_var.set("")
            self.rate_movie_id_var.set("")
            self.rate_value_var.set("")
        else:
            self.rating_status_text.insert(
                tk.END,
                f"[ERR] Could not set rating for user {uid}, movie {mid}\n"
            )
        self.rating_status_text.see(tk.END)  # Auto-scroll to bottom
        self.rating_status_text.config(state="disabled")

    def handle_delete_rating(self):
        try:
            uid = int(self.del_user_id_var.get().strip())
            mid = int(self.del_movie_id_var.get().strip())
        except ValueError:
            messagebox.showerror("Input Error", "User ID and Movie ID must be integers.")
            return

        ok = delete_rating(uid, mid)

        self.rating_status_text.config(state="normal")
        if ok:
            self.rating_status_text.insert(
                tk.END,
                f"[OK] Deleted rating for user {uid}, movie {mid}\n"
            )
            # Clear input fields after successful deletion
            self.del_user_id_var.set("")
            self.del_movie_id_var.set("")
        else:
            self.rating_status_text.insert(
                tk.END,
                f"[ERR] Failed to delete rating for user {uid}, movie {mid}\n"
            )
        self.rating_status_text.see(tk.END)  # Auto-scroll to bottom
        self.rating_status_text.config(state="disabled")


###############################################################################
# 4. MAIN
###############################################################################

if __name__ == "__main__":
    app = MovieApp()
    app.mainloop()
