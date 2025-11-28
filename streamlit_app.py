"""
Streamlit Movie Database Application
A web-based interface for the hybrid SQL-NoSQL movie database system.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import sys

# Import database functions from gui.py
from gui import (
    # Authentication
    authenticate_user, register_new_user, is_valid_email,
    # Movie operations
    search_movies_by_title, search_movies_advanced, get_movie_details,
    find_movie_by_title_sql, add_movie_to_sql, update_movie_in_sql, delete_movie_from_sql,
    # MongoDB operations
    get_tmdb_metadata, search_movies_by_genre_mongo, search_movies_by_keyword_mongo,
    find_similar_movies_mongo, get_genre_statistics_mongo,
    # Rating operations
    add_or_update_rating, get_user_rating, get_all_user_ratings, delete_rating,
    check_rating_lock, acquire_rating_lock, release_rating_lock,
    # Watchlist operations
    add_to_watchlist, remove_from_watchlist, get_user_watchlist, is_in_watchlist,
    # Analytics
    get_top_rated_movies, get_user_statistics, get_popular_movies_from_view,
    find_users_who_never_rated_popular_movies, find_movies_rated_by_all_active_users,
    find_movies_with_rating_variance, get_movies_with_above_average_ratings,
    # User management
    get_user, search_users, add_user, update_user, delete_user
)

###############################################################################
# PAGE CONFIGURATION
###############################################################################

st.set_page_config(
    page_title="Movie Database System",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #ff7f0e;
        padding: 0.5rem 0;
    }
    .info-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        border-left: 5px solid #28a745;
    }
    .error-box {
        background-color: #f8d7da;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        border-left: 5px solid #dc3545;
    }
    .movie-card {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
    }
    </style>
""", unsafe_allow_html=True)

###############################################################################
# SESSION STATE INITIALIZATION
###############################################################################

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = "guest"
if 'email' not in st.session_state:
    st.session_state.email = None
if 'role' not in st.session_state:
    st.session_state.role = "guest"
if 'page' not in st.session_state:
    st.session_state.page = "home"

###############################################################################
# AUTHENTICATION FUNCTIONS
###############################################################################

def login_page():
    """Display login page."""
    st.markdown('<div class="main-header">🎬 Movie Database System</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        tab1, tab2, tab3 = st.tabs(["Login", "Register", "Guest Access"])
        
        with tab1:
            st.subheader("Login to Your Account")
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Login", use_container_width=True):
                    if username and password:
                        result = authenticate_user(username, password)
                        if result["success"]:
                            st.session_state.authenticated = True
                            st.session_state.user_id = result["userId"]
                            st.session_state.username = result["username"]
                            st.session_state.email = result["email"]
                            st.session_state.role = result["role"]
                            st.success(f"Welcome back, {username}!")
                            st.rerun()
                        else:
                            st.error(result["message"])
                    else:
                        st.warning("Please enter both username and password")
        
        with tab2:
            st.subheader("Create New Account")
            new_username = st.text_input("Username", key="reg_username")
            new_email = st.text_input("Email", key="reg_email")
            new_password = st.text_input("Password", type="password", key="reg_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
            
            if st.button("Register", use_container_width=True):
                if not all([new_username, new_email, new_password, confirm_password]):
                    st.warning("Please fill in all fields")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                elif not is_valid_email(new_email):
                    st.error("Invalid email format")
                else:
                    result = register_new_user(new_username, new_email, new_password)
                    if result["success"]:
                        st.success(result["message"])
                        st.info("Please login with your new credentials")
                    else:
                        st.error(result["message"])
        
        with tab3:
            st.subheader("Continue as Guest")
            st.info("Guest users can browse movies but cannot rate or add to watchlist")
            if st.button("Continue as Guest", use_container_width=True):
                st.session_state.authenticated = True
                st.session_state.user_id = None
                st.session_state.username = "guest"
                st.session_state.role = "guest"
                st.rerun()

def logout():
    """Logout user."""
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.username = "guest"
    st.session_state.email = None
    st.session_state.role = "guest"
    st.rerun()

###############################################################################
# SIDEBAR NAVIGATION
###############################################################################

def sidebar_navigation():
    """Display sidebar navigation."""
    with st.sidebar:
        st.markdown('<div class="sub-header">Navigation</div>', unsafe_allow_html=True)
        
        # User info
        st.markdown(f"**Logged in as:** {st.session_state.username}")
        st.markdown(f"**Role:** {st.session_state.role}")
        
        if st.button("🚪 Logout", use_container_width=True):
            logout()
        
        st.markdown("---")
        
        # Navigation menu
        st.markdown("### Menu")
        
        if st.button("🏠 Home", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()
        
        if st.button("🔍 Search Movies", use_container_width=True):
            st.session_state.page = "search"
            st.rerun()
        
        if st.button("🎭 Browse by Genre", use_container_width=True):
            st.session_state.page = "genre"
            st.rerun()
        
        if st.session_state.role != "guest":
            if st.button("⭐ My Ratings", use_container_width=True):
                st.session_state.page = "ratings"
                st.rerun()
            
            if st.button("📋 My Watchlist", use_container_width=True):
                st.session_state.page = "watchlist"
                st.rerun()
        
        if st.button("📊 Analytics", use_container_width=True):
            st.session_state.page = "analytics"
            st.rerun()
        
        if st.session_state.role == "admin":
            st.markdown("---")
            st.markdown("### Admin")
            if st.button("👥 User Management", use_container_width=True):
                st.session_state.page = "users"
                st.rerun()
            
            if st.button("🎬 Movie Management", use_container_width=True):
                st.session_state.page = "movies_admin"
                st.rerun()

###############################################################################
# HOME PAGE
###############################################################################

def home_page():
    """Display home page with top rated movies."""
    st.markdown('<div class="main-header">🎬 Welcome to Movie Database</div>', unsafe_allow_html=True)
    
    # Display user stats if logged in
    if st.session_state.role != "guest":
        stats = get_user_statistics(st.session_state.user_id)
        if stats["success"]:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Ratings", stats["total_ratings"])
            with col2:
                st.metric("Average Rating", f"{stats['average_rating']:.2f}" if stats['average_rating'] else "N/A")
            with col3:
                st.metric("Watchlist Items", stats["watchlist_count"])
            with col4:
                st.metric("Favorite Genre", stats["favorite_genre"] or "N/A")
    
    st.markdown("---")
    st.markdown('<div class="sub-header">🏆 Top Rated Movies</div>', unsafe_allow_html=True)
    
    # Display top rated movies
    top_movies = get_top_rated_movies(limit=20)
    if top_movies["success"]:
        for movie in top_movies["movies"]:
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.markdown(f"**{movie['title']}** ({movie.get('release_year', 'N/A')})")
                with col2:
                    st.markdown(f"⭐ {movie['avg_rating']:.2f}")
                with col3:
                    st.markdown(f"📊 {movie['rating_count']} ratings")
                
                # View details button
                if st.button(f"View Details", key=f"details_{movie['movieId']}"):
                    st.session_state.selected_movie = movie['movieId']
                    st.session_state.page = "movie_details"
                    st.rerun()
                
                st.markdown("---")

###############################################################################
# SEARCH PAGE
###############################################################################

def search_page():
    """Display movie search page."""
    st.markdown('<div class="main-header">🔍 Search Movies</div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Basic Search", "Advanced Search"])
    
    with tab1:
        search_query = st.text_input("Search by title", placeholder="Enter movie title...")
        
        if st.button("Search", key="basic_search"):
            if search_query:
                results = search_movies_by_title(search_query)
                if results["success"]:
                    st.success(f"Found {len(results['movies'])} movies")
                    display_movie_list(results['movies'])
                else:
                    st.error(results["message"])
            else:
                st.warning("Please enter a search term")
    
    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            adv_title = st.text_input("Title contains", key="adv_title")
            min_rating = st.number_input("Minimum rating", min_value=0.0, max_value=5.0, value=0.0, step=0.1)
        with col2:
            max_rating = st.number_input("Maximum rating", min_value=0.0, max_value=5.0, value=5.0, step=0.1)
            min_votes = st.number_input("Minimum votes", min_value=0, value=0, step=10)
        
        if st.button("Advanced Search", key="adv_search"):
            results = search_movies_advanced(
                title=adv_title if adv_title else None,
                min_rating=min_rating if min_rating > 0 else None,
                max_rating=max_rating if max_rating < 5.0 else None,
                min_votes=min_votes if min_votes > 0 else None
            )
            if results["success"]:
                st.success(f"Found {len(results['movies'])} movies")
                display_movie_list(results['movies'])
            else:
                st.error(results["message"])

def display_movie_list(movies):
    """Display a list of movies."""
    for movie in movies:
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"**{movie['title']}**")
            with col2:
                avg_rating = movie.get('avg_rating')
                if avg_rating:
                    st.markdown(f"⭐ {avg_rating:.2f}")
            with col3:
                if st.button("View", key=f"view_{movie['movieId']}"):
                    st.session_state.selected_movie = movie['movieId']
                    st.session_state.page = "movie_details"
                    st.rerun()
            st.markdown("---")

###############################################################################
# GENRE BROWSE PAGE
###############################################################################

def genre_page():
    """Display genre browsing page."""
    st.markdown('<div class="main-header">🎭 Browse by Genre</div>', unsafe_allow_html=True)
    
    # Get genre statistics
    genre_stats = get_genre_statistics_mongo()
    if genre_stats["success"]:
        # Display genre chart
        df = pd.DataFrame(genre_stats["genres"])
        fig = px.bar(df, x='genre', y='count', title='Movies by Genre',
                     labels={'genre': 'Genre', 'count': 'Number of Movies'})
        st.plotly_chart(fig, use_container_width=True)
        
        # Genre selection
        genres = [g['genre'] for g in genre_stats["genres"]]
        selected_genre = st.selectbox("Select a genre to browse", [""] + genres)
        
        if selected_genre:
            results = search_movies_by_genre_mongo(selected_genre)
            if results["success"]:
                st.success(f"Found {len(results['movies'])} movies in {selected_genre}")
                display_mongo_movie_list(results['movies'])
            else:
                st.error(results["message"])

def display_mongo_movie_list(movies):
    """Display a list of MongoDB movies."""
    for movie in movies:
        with st.container():
            col1, col2 = st.columns([4, 1])
            with col1:
                title = movie.get('title', 'Unknown')
                year = movie.get('release_date', '')[:4] if movie.get('release_date') else ''
                st.markdown(f"**{title}** ({year})")
                
                # Display genres
                genres = movie.get('genres', [])
                if genres:
                    genre_names = [g.get('name', '') for g in genres if isinstance(g, dict)]
                    st.markdown(f"*Genres: {', '.join(genre_names)}*")
            with col2:
                vote_avg = movie.get('vote_average')
                if vote_avg:
                    st.markdown(f"⭐ {vote_avg:.1f}/10")
            
            # Overview
            overview = movie.get('overview', '')
            if overview:
                st.markdown(f"> {overview[:200]}..." if len(overview) > 200 else f"> {overview}")
            
            st.markdown("---")

###############################################################################
# RATINGS PAGE
###############################################################################

def ratings_page():
    """Display user ratings page."""
    st.markdown('<div class="main-header">⭐ My Ratings</div>', unsafe_allow_html=True)
    
    if st.session_state.role == "guest":
        st.warning("Please login to view and manage your ratings")
        return
    
    # Get user ratings
    ratings = get_all_user_ratings(st.session_state.user_id)
    
    if not ratings:
        st.info("You haven't rated any movies yet")
        return
    
    st.success(f"You have rated {len(ratings)} movies")
    
    # Display ratings
    for rating in ratings:
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"**{rating['title']}**")
            with col2:
                st.markdown(f"⭐ Your rating: {rating['rating']:.1f}")
            with col3:
                if st.button("Delete", key=f"del_rating_{rating['movieId']}"):
                    result = delete_rating(st.session_state.user_id, rating['movieId'])
                    if result["success"]:
                        st.success("Rating deleted")
                        st.rerun()
                    else:
                        st.error(result["message"])
            st.markdown("---")

###############################################################################
# WATCHLIST PAGE
###############################################################################

def watchlist_page():
    """Display watchlist page."""
    st.markdown('<div class="main-header">📋 My Watchlist</div>', unsafe_allow_html=True)
    
    if st.session_state.role == "guest":
        st.warning("Please login to view and manage your watchlist")
        return
    
    # Get watchlist
    watchlist = get_user_watchlist(st.session_state.user_id)
    
    if not watchlist:
        st.info("Your watchlist is empty")
        return
    
    st.success(f"You have {len(watchlist)} movies in your watchlist")
    
    # Display watchlist items
    for item in watchlist:
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"**{item['title']}**")
                if item.get('notes'):
                    st.markdown(f"*Notes: {item['notes']}*")
            with col2:
                priority = item.get('priority', 'medium')
                st.markdown(f"Priority: {priority}")
            with col3:
                if st.button("Remove", key=f"remove_{item['movieId']}"):
                    result = remove_from_watchlist(st.session_state.user_id, item['movieId'])
                    if result["success"]:
                        st.success("Removed from watchlist")
                        st.rerun()
                    else:
                        st.error(result["message"])
            st.markdown("---")

###############################################################################
# ANALYTICS PAGE
###############################################################################

def analytics_page():
    """Display analytics page."""
    st.markdown('<div class="main-header">📊 Database Analytics</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Top Movies", "User Insights", "Rating Analysis"])
    
    with tab1:
        st.subheader("Top Rated Movies")
        top_movies = get_top_rated_movies(limit=50)
        if top_movies["success"]:
            df = pd.DataFrame(top_movies["movies"])
            fig = px.bar(df.head(20), x='title', y='avg_rating',
                        title='Top 20 Rated Movies',
                        labels={'title': 'Movie', 'avg_rating': 'Average Rating'})
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Popular Movies")
        popular = get_popular_movies_from_view(limit=20)
        if popular["success"]:
            df_pop = pd.DataFrame(popular["movies"])
            st.dataframe(df_pop[['title', 'rating_count', 'avg_rating']], use_container_width=True)
    
    with tab2:
        st.subheader("Movies with High Rating Variance")
        variance = find_movies_with_rating_variance()
        if variance["success"] and variance["movies"]:
            df_var = pd.DataFrame(variance["movies"])
            st.dataframe(df_var, use_container_width=True)
    
    with tab3:
        st.subheader("Movies Above Average Ratings")
        above_avg = get_movies_with_above_average_ratings()
        if above_avg["success"] and above_avg["movies"]:
            df_above = pd.DataFrame(above_avg["movies"])
            st.dataframe(df_above.head(20), use_container_width=True)

###############################################################################
# MOVIE DETAILS PAGE
###############################################################################

def movie_details_page():
    """Display detailed movie information."""
    movie_id = st.session_state.get('selected_movie')
    if not movie_id:
        st.error("No movie selected")
        return
    
    # Get movie details
    details = get_movie_details(movie_id)
    if not details["success"]:
        st.error(details["message"])
        return
    
    movie = details["movie"]
    
    st.markdown(f'<div class="main-header">{movie["title"]}</div>', unsafe_allow_html=True)
    
    # Basic info
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Average Rating", f"{movie.get('avg_rating', 0):.2f}")
    with col2:
        st.metric("Total Ratings", movie.get('rating_count', 0))
    with col3:
        st.metric("Release Date", movie.get('releaseDate', 'N/A'))
    
    # Get metadata from MongoDB
    tmdb_data = details.get('tmdb_metadata')
    if tmdb_data:
        st.markdown("### Overview")
        st.write(tmdb_data.get('overview', 'No overview available'))
        
        # Genres
        genres = tmdb_data.get('genres', [])
        if genres:
            genre_names = [g.get('name', '') for g in genres if isinstance(g, dict)]
            st.markdown(f"**Genres:** {', '.join(genre_names)}")
        
        # Additional info
        col1, col2 = st.columns(2)
        with col1:
            if tmdb_data.get('runtime'):
                st.markdown(f"**Runtime:** {tmdb_data['runtime']} minutes")
            if tmdb_data.get('budget'):
                st.markdown(f"**Budget:** ${tmdb_data['budget']:,}")
        with col2:
            if tmdb_data.get('revenue'):
                st.markdown(f"**Revenue:** ${tmdb_data['revenue']:,}")
            if tmdb_data.get('vote_average'):
                st.markdown(f"**TMDB Rating:** {tmdb_data['vote_average']:.1f}/10")
    
    st.markdown("---")
    
    # User actions
    if st.session_state.role != "guest":
        st.markdown("### Your Actions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Rate this movie")
            current_rating = get_user_rating(st.session_state.user_id, movie_id)
            
            if current_rating:
                st.info(f"Your current rating: {current_rating:.1f}")
            
            new_rating = st.slider("Rating", 0.5, 5.0, 
                                  current_rating if current_rating else 3.0, 
                                  0.5, key="movie_rating")
            
            if st.button("Submit Rating"):
                # Check lock
                lock_check = check_rating_lock(st.session_state.user_id, movie_id)
                if not lock_check["available"]:
                    st.error(f"This rating is currently locked by {lock_check['locked_by']}")
                else:
                    # Acquire lock
                    lock_result = acquire_rating_lock(st.session_state.user_id, movie_id, 
                                                     st.session_state.username)
                    if lock_result["success"]:
                        # Add/update rating
                        rating_result = add_or_update_rating(st.session_state.user_id, 
                                                            movie_id, new_rating)
                        # Release lock
                        release_rating_lock(st.session_state.user_id, movie_id)
                        
                        if rating_result["success"]:
                            st.success("Rating saved!")
                            st.rerun()
                        else:
                            st.error(rating_result["message"])
                    else:
                        st.error(lock_result["message"])
        
        with col2:
            st.subheader("Watchlist")
            in_watchlist = is_in_watchlist(st.session_state.user_id, movie_id)
            
            if in_watchlist:
                st.info("This movie is in your watchlist")
                if st.button("Remove from Watchlist"):
                    result = remove_from_watchlist(st.session_state.user_id, movie_id)
                    if result["success"]:
                        st.success("Removed from watchlist")
                        st.rerun()
                    else:
                        st.error(result["message"])
            else:
                notes = st.text_area("Notes (optional)", key="watchlist_notes")
                priority = st.selectbox("Priority", ["low", "medium", "high"])
                
                if st.button("Add to Watchlist"):
                    result = add_to_watchlist(st.session_state.user_id, movie_id, notes, priority)
                    if result["success"]:
                        st.success("Added to watchlist!")
                        st.rerun()
                    else:
                        st.error(result["message"])
    
    # Back button
    if st.button("← Back"):
        st.session_state.page = "home"
        st.rerun()

###############################################################################
# ADMIN PAGES
###############################################################################

def user_management_page():
    """Admin page for user management."""
    st.markdown('<div class="main-header">👥 User Management</div>', unsafe_allow_html=True)
    
    if st.session_state.role != "admin":
        st.error("Access denied. Admin privileges required.")
        return
    
    tab1, tab2 = st.tabs(["View Users", "Add User"])
    
    with tab1:
        search_term = st.text_input("Search users", key="user_search")
        users = search_users(search_term)
        
        if users:
            df = pd.DataFrame(users)
            st.dataframe(df[['userId', 'username', 'email']], use_container_width=True)
    
    with tab2:
        with st.form("add_user_form"):
            new_username = st.text_input("Username")
            new_email = st.text_input("Email")
            new_password = st.text_input("Password", type="password")
            
            if st.form_submit_button("Add User"):
                if all([new_username, new_email, new_password]):
                    result = add_user(new_username, new_email, new_password)
                    if result["success"]:
                        st.success("User added successfully")
                    else:
                        st.error(result["message"])
                else:
                    st.warning("Please fill in all fields")

###############################################################################
# MAIN APPLICATION
###############################################################################

def main():
    """Main application entry point."""
    
    # Check authentication
    if not st.session_state.authenticated:
        login_page()
        return
    
    # Display sidebar navigation
    sidebar_navigation()
    
    # Route to appropriate page
    page = st.session_state.page
    
    if page == "home":
        home_page()
    elif page == "search":
        search_page()
    elif page == "genre":
        genre_page()
    elif page == "ratings":
        ratings_page()
    elif page == "watchlist":
        watchlist_page()
    elif page == "analytics":
        analytics_page()
    elif page == "movie_details":
        movie_details_page()
    elif page == "users":
        user_management_page()
    else:
        home_page()

if __name__ == "__main__":
    main()
