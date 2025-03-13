import psutil
import humanize
from pathlib import Path
from typing import Dict, Optional

def get_system_metrics() -> Dict:
    """Get system resource usage metrics."""
    return {
        "cpu_usage": psutil.cpu_percent(),
        "memory_usage": psutil.virtual_memory().percent,
        "disk_usage": {
            str(disk.mountpoint): disk.percent 
            for disk in psutil.disk_partitions(all=False)
        }
    }

def format_size(size_bytes: int) -> str:
    """Convert bytes to human readable format."""
    return humanize.naturalsize(size_bytes)

def format_speed(speed_bytes: float) -> str:
    """Format download speed in human readable format."""
    return f"{humanize.naturalsize(speed_bytes)}/s"

def format_time(seconds: int) -> str:
    """Format seconds into human readable time."""
    return humanize.naturaltime(seconds)

def is_valid_game_id(game_id: str) -> bool:
    """Validate if the input is a valid Steam game ID."""
    try:
        return bool(int(game_id))
    except ValueError:
        return False

def extract_game_id(url: str) -> Optional[int]:
    """Extract game ID from Steam store URL."""
    import re
    pattern = r'store.steampowered.com/app/(\d+)'
    match = re.search(pattern, url)
    return int(match.group(1)) if match else None 