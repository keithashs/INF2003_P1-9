"""
Quick setup and test script for Streamlit deployment
Run this before deploying to verify everything works locally.
"""

import subprocess
import sys
import os

def check_python_version():
    """Check if Python version is 3.8 or higher."""
    version = sys.version_info
    print(f"✓ Python version: {version.major}.{version.minor}.{version.micro}")
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher required!")
        return False
    return True

def install_requirements():
    """Install required packages."""
    print("\n📦 Installing requirements...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install requirements")
        return False

def check_env_file():
    """Check if .env file exists."""
    if os.path.exists(".env"):
        print("✓ .env file found")
        return True
    else:
        print("⚠️  .env file not found")
        print("   Create a .env file with your database credentials")
        print("   See .env.example for template")
        return False

def check_database_files():
    """Check if required files exist."""
    required_files = [
        "streamlit_app.py",
        "gui.py",
        "requirements.txt",
        ".streamlit/config.toml"
    ]
    
    all_exist = True
    for file in required_files:
        if os.path.exists(file):
            print(f"✓ {file} found")
        else:
            print(f"❌ {file} not found")
            all_exist = False
    
    return all_exist

def run_streamlit():
    """Launch Streamlit app."""
    print("\n🚀 Launching Streamlit app...")
    print("   Press Ctrl+C to stop\n")
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "streamlit_app.py"])
    except KeyboardInterrupt:
        print("\n✓ Streamlit app stopped")

def main():
    """Main setup function."""
    print("=" * 60)
    print("Movie Database - Streamlit Setup & Test")
    print("=" * 60)
    
    # Check Python version
    if not check_python_version():
        return
    
    # Install requirements
    if not install_requirements():
        return
    
    print("\n" + "=" * 60)
    print("Checking required files...")
    print("=" * 60)
    
    # Check files
    if not check_database_files():
        print("\n❌ Some required files are missing!")
        return
    
    # Check .env
    check_env_file()
    
    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    
    # Ask to run
    response = input("\nDo you want to run the Streamlit app now? (y/n): ")
    if response.lower() in ['y', 'yes']:
        run_streamlit()
    else:
        print("\nTo run the app later, use:")
        print("  streamlit run streamlit_app.py")
        print("\nFor deployment instructions, see STREAMLIT_DEPLOYMENT.md")

if __name__ == "__main__":
    main()
