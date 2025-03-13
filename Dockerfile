FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
    lib32gcc-s1 \
    curl \
    libcurl4 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create necessary directories
RUN mkdir -p /data/downloads /app/steamcmd /app/logs /app/cache

# Set environment variables
ENV STEAM_DOWNLOAD_PATH=/data/downloads
ENV LOG_LEVEL=INFO
ENV PORT=7860

# Make the application files executable
RUN chmod +x main.py

# Run the application
CMD ["python", "main.py"]