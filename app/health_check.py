#!/usr/bin/env python3
import requests
import sys
from typing import Tuple

def check_health() -> Tuple[bool, str]:
    """Check if the application is running and healthy."""
    # Check Gradio interface
    try:
        response = requests.get("http://localhost:7860/")
        if response.status_code != 200:
            return False, f"Gradio interface returned status code {response.status_code}"
    except requests.RequestException as e:
        return False, f"Could not connect to Gradio interface: {str(e)}"
    
    # Check API
    try:
        response = requests.get("http://localhost:7861/api/system")
        if response.status_code != 200:
            return False, f"API returned status code {response.status_code}"
        
        # Check system status
        status = response.json()
        if status["cpu_usage"] > 95:
            return False, "CPU usage is too high"
        if status["memory_usage"] > 95:
            return False, "Memory usage is too high"
        if status["disk_usage"] > 95:
            return False, "Disk usage is too high"
    except requests.RequestException as e:
        return False, f"Could not connect to API: {str(e)}"
    
    return True, "Application is healthy"

if __name__ == "__main__":
    healthy, message = check_health()
    print(message)
    sys.exit(0 if healthy else 1) 
