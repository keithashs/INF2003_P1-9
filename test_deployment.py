"""
Test script to verify Streamlit app can import all required functions
Run this before deploying to catch any import errors.
"""

import sys
import traceback

def test_imports():
    """Test all imports from gui.py."""
    print("Testing imports from gui.py...\n")
    
    tests = {
        "Authentication": [
            "authenticate_user",
            "register_new_user",
            "is_valid_email"
        ],
        "Movie Operations": [
            "search_movies_by_title",
            "search_movies_advanced",
            "get_movie_details",
            "find_movie_by_title_sql"
        ],
        "MongoDB Operations": [
            "get_tmdb_metadata",
            "search_movies_by_genre_mongo",
            "search_movies_by_keyword_mongo",
            "find_similar_movies_mongo",
            "get_genre_statistics_mongo"
        ],
        "Rating Operations": [
            "add_or_update_rating",
            "get_user_rating",
            "get_all_user_ratings",
            "delete_rating",
            "check_rating_lock",
            "acquire_rating_lock",
            "release_rating_lock"
        ],
        "Watchlist Operations": [
            "add_to_watchlist",
            "remove_from_watchlist",
            "get_user_watchlist",
            "is_in_watchlist"
        ],
        "Analytics": [
            "get_top_rated_movies",
            "get_user_statistics",
            "get_popular_movies_from_view",
            "find_movies_with_rating_variance",
            "get_movies_with_above_average_ratings"
        ],
        "User Management": [
            "get_user",
            "search_users",
            "add_user",
            "update_user",
            "delete_user"
        ]
    }
    
    all_passed = True
    
    for category, functions in tests.items():
        print(f"📦 {category}")
        for func_name in functions:
            try:
                exec(f"from gui import {func_name}")
                print(f"  ✓ {func_name}")
            except ImportError as e:
                print(f"  ❌ {func_name} - {e}")
                all_passed = False
            except Exception as e:
                print(f"  ⚠️  {func_name} - {e}")
        print()
    
    return all_passed

def test_streamlit_app():
    """Test if streamlit_app.py can be imported."""
    print("Testing streamlit_app.py...\n")
    
    try:
        import streamlit_app
        print("✓ streamlit_app.py imported successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to import streamlit_app.py")
        print(f"Error: {e}")
        traceback.print_exc()
        return False

def test_dependencies():
    """Test if all required packages are installed."""
    print("\nTesting dependencies...\n")
    
    required_packages = [
        ("streamlit", "streamlit"),
        ("pandas", "pandas"),
        ("plotly", "plotly.express"),
        ("pymysql", "pymysql"),
        ("pymongo", "pymongo"),
        ("bcrypt", "bcrypt")
    ]
    
    all_installed = True
    
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
            print(f"✓ {package_name}")
        except ImportError:
            print(f"❌ {package_name} - Not installed")
            all_installed = False
    
    return all_installed

def main():
    """Run all tests."""
    print("=" * 60)
    print("Streamlit Deployment - Pre-flight Check")
    print("=" * 60)
    print()
    
    # Test dependencies
    deps_ok = test_dependencies()
    print()
    
    if not deps_ok:
        print("❌ Some dependencies are missing!")
        print("Run: pip install -r requirements.txt")
        return
    
    # Test imports from gui.py
    imports_ok = test_imports()
    
    # Test streamlit_app.py
    app_ok = test_streamlit_app()
    
    print()
    print("=" * 60)
    
    if imports_ok and app_ok:
        print("✅ All tests passed!")
        print("=" * 60)
        print()
        print("You're ready to deploy! Next steps:")
        print("1. Test locally: streamlit run streamlit_app.py")
        print("2. Push to GitHub: git push origin main")
        print("3. Deploy on Streamlit Cloud: share.streamlit.io")
        print()
        print("See STREAMLIT_DEPLOYMENT.md for detailed instructions.")
    else:
        print("❌ Some tests failed!")
        print("=" * 60)
        print()
        print("Please fix the errors above before deploying.")
    
    print()

if __name__ == "__main__":
    main()
