#!/bin/bash
set -euo pipefail

echo "Starting Steam Downloader..."

# Remove any conflicting logging.py if it exists
rm -f /app/logging.py

# Create and set permissions for directories
mkdir -p /data/downloads /app/steamcmd /app/logs
chmod 755 /data/downloads /app/steamcmd /app/logs

# Run initialization checks
echo "Running system checks..."
python3 init_check.py
if [ $? -ne 0 ]; then
    echo "System checks failed. Please check the logs."
    exit 1
fi

# Start the application
echo "Starting main application..."
exec python3 main.py