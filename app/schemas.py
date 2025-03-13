from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime

class DownloadRequest(BaseModel):
    game_input: str = Field(..., description="Game ID, URL, or name")
    username: Optional[str] = Field(None, description="Steam username")
    password: Optional[str] = Field(None, description="Steam password")
    guard_code: Optional[str] = Field(None, description="Steam Guard code")
    validate: bool = Field(True, description="Validate game files after download")
    anonymous: bool = Field(False, description="Use anonymous login")

class DownloadStatus(BaseModel):
    id: str
    appid: str
    name: str
    progress: float
    status: str
    start_time: datetime
    speed: str
    eta: str
    size: str
    error: Optional[str] = None

class QueuedDownload(BaseModel):
    name: str
    appid: str

class HistoryEntry(BaseModel):
    id: str
    appid: str
    name: str
    status: str
    error: Optional[str]
    completed_at: datetime

class DownloadStatusResponse(BaseModel):
    active: List[DownloadStatus]
    queue: List[QueuedDownload]
    history: List[HistoryEntry]

class GameInfo(BaseModel):
    appid: str
    name: str
    is_free: bool
    description: str
    header_image: Optional[str]
    developers: List[str]
    publishers: List[str]
    release_date: str
    metacritic_score: Optional[int]
    categories: List[str]
    genres: List[str]
    platforms: Dict[str, bool]
    price_info: Optional[Dict[str, str]]

class SystemStatus(BaseModel):
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    download_speed: str
    uptime: str
    active_downloads: int
    queued_downloads: int 