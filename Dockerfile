FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
    lib32gcc-s1 \
    curl \
    libcurl4 \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY *.py .
COPY entrypoint.sh .

# Create necessary directories
RUN mkdir -p /data/downloads /app/steamcmd /app/logs

# Set environment variables
ENV STEAM_DOWNLOAD_PATH=/data/downloads \
    LOG_LEVEL=INFO \
    PORT=7860 \
    HOST=0.0.0.0

# Make the entrypoint script executable
RUN chmod +x entrypoint.sh

# Expose port
EXPOSE 7860

# Set entrypoint
ENTRYPOINT ["./entrypoint.sh"]