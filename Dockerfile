# ============================================================
# Python Application Dockerfile
# ============================================================
# For running the Movie Database GUI application
# ============================================================

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # For MariaDB/MySQL client
    default-mysql-client \
    default-libmysqlclient-dev \
    # For tkinter GUI
    python3-tk \
    tk-dev \
    # For building Python packages
    build-essential \
    gcc \
    # X11 for GUI display
    x11-apps \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create logs directory
RUN mkdir -p logs

# Default command (override in docker-compose)
CMD ["python", "gui.py"]
