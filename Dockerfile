# ============================================================
# Dockerfile for TMDB Movie Database Python Application
# ============================================================
# This builds a containerized environment for the hybrid
# SQL-NoSQL movie database GUI application.
# ============================================================

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# - tk: Required for Tkinter GUI
# - gcc, build-essential: Needed for compiling Python packages
RUN apt-get update && apt-get install -y \
    python3-tk \
    tk-dev \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY . .

# Create logs directory
RUN mkdir -p logs

# Environment variables (can be overridden in docker-compose.yml)
ENV DB_HOST=mariadb
ENV DB_USER=root
ENV DB_PASS=root_password
ENV DB_NAME=movies_db
ENV MONGO_USERNAME=nkt12385_db_user
ENV MONGO_PASSWORD=Keetian12345
ENV MONGO_CLUSTER=cluster0.qrc4kkf.mongodb.net
ENV MONGO_DB=movies_nosql
ENV MONGO_COLL=tmdb_movies

# Display environment for X11 forwarding (for GUI)
ENV DISPLAY=:0

# Expose port (for future web interface)
EXPOSE 5000

# Default command: Keep container running
# (GUI requires X11 - on Windows, run GUI on host instead)
CMD ["tail", "-f", "/dev/null"]
