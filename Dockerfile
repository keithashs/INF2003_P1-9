FROM python:3.11-slim

# Install system dependencies for Tkinter and VNC
RUN apt-get update && apt-get install -y \
    python3-tk \
    x11vnc \
    xvfb \
    fluxbox \
    novnc \
    websockify \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install MariaDB client for running SQL scripts
RUN apt-get update && apt-get install -y mariadb-client default-mysql-client && rm -rf /var/lib/apt/lists/*

# Copy application files and startup script
COPY gui.py .
COPY 2_import_data.py .
COPY *.csv ./
COPY *.sql ./
COPY start.sh .
RUN chmod +x /app/start.sh

EXPOSE 6080

CMD ["/bin/bash", "/app/start.sh"]
