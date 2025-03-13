from pydantic import BaseModel
from typing import Optional, List, Dict
from enum import Enum
from datetime import datetime

class DownloadStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class GameInfo(BaseModel):
    app_id: int
    name: str
    size: Optional[int] = None
    installed: bool = False
    install_dir: Optional[str] = None

class DownloadProgress(BaseModel):
    progress: float
    speed: str
    eta: str
    current_file: str
    total_size: str

class DownloadRequest(BaseModel):
    app_id: int
    username: Optional[str] = None
    password: Optional[str] = None
    steam_guard_code: Optional[str] = None
    anonymous: bool = True

class SystemStatus(BaseModel):
    cpu_usage: float
    memory_usage: float
    disk_usage: Dict[str, float]
    download_queue: List[int]
    active_downloads: Dict[int, DownloadProgress] 