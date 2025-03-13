#!/usr/bin/env python3
"""
Diagnostic script to check environment before starting the main application.
"""

import os
import sys
import platform
import psutil
import requests
from pathlib import Path
from log_config import setup_logging

# Set up logging
logger = setup_logging(name="init_check")

def check_python_version():
    """Check if Python version is compatible."""
    required_version = (3, 9)
    current_version = sys.version_info[:2]
    
    if current_version < required_version:
        logger.error(f"Python {required_version[0]}.{required_version[1]} or higher is required")
        return False
        
    logger.info(f"Python version {platform.python_version()} OK")
    return True

def check_system_resources():
    """Check if system has sufficient resources."""
    min_memory_gb = 2
    min_disk_gb = 10
    
    memory_gb = psutil.virtual_memory().total / (1024**3)
    disk_gb = psutil.disk_usage('/').free / (1024**3)
    
    if memory_gb < min_memory_gb:
        logger.error(f"Insufficient memory: {memory_gb:.1f}GB (minimum {min_memory_gb}GB required)")
        return False
        
    if disk_gb < min_disk_gb:
        logger.error(f"Insufficient disk space: {disk_gb:.1f}GB (minimum {min_disk_gb}GB required)")
        return False
    
    logger.info(f"System resources OK (Memory: {memory_gb:.1f}GB, Free disk space: {disk_gb:.1f}GB)")
    return True

def check_internet_connection():
    """Check internet connectivity."""
    test_urls = [
        "https://store.steampowered.com",
        "https://steamcdn-a.akamaihd.net"
    ]
    
    for url in test_urls:
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to connect to {url}: {str(e)}")
            return False
    
    logger.info("Internet connectivity OK")
    return True

def check_permissions():
    """Check if the application has necessary permissions."""
    paths_to_check = [
        Path.cwd(),
        Path.cwd() / "downloads",
        Path.cwd() / "logs",
        Path.cwd() / "steamcmd"
    ]
    
    for path in paths_to_check:
        try:
            path.mkdir(exist_ok=True)
            test_file = path / ".permission_test"
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            logger.error(f"Permission error for {path}: {str(e)}")
            return False
    
    logger.info("File system permissions OK")
    return True

def main():
    """Run all initialization checks."""
    checks = [
        ("Python version", check_python_version),
        ("System resources", check_system_resources),
        ("Internet connection", check_internet_connection),
        ("File permissions", check_permissions)
    ]
    
    results = []
    for check_name, check_func in checks:
        logger.info(f"\nRunning {check_name} check...")
        results.append(check_func())
    
    if all(results):
        logger.info("\nAll checks passed successfully!")
        return 0
    else:
        logger.error("\nOne or more checks failed. Please fix the issues before running the application.")
        return 1

if __name__ == "__main__":
    sys.exit(main())