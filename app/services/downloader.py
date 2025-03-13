import logging
import threading
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from ..core.config import settings
from ..core.exceptions import DownloadError
from .steam_cmd import steam_cmd

logger = logging.getLogger(__name__)

@dataclass
class DownloadStatus:
    id: str
    appid: str
    name: str
    progress: float
    status: str
    start_time: datetime
    speed: str = "0 B/s"
    eta: str = "Unknown"
    size: str = "Unknown"
    error: Optional[str] = None

class DownloadManager:
    def __init__(self):
        self.active_downloads: Dict[str, DownloadStatus] = {}
        self.download_queue: List[Dict] = []
        self.download_history: List[Dict] = []
        self.lock = threading.Lock()
        
        # Start queue processor
        self.queue_processor = threading.Thread(
            target=self._process_queue,
            daemon=True
        )
        self.queue_processor.start()
    
    def start_download(
        self,
        appid: str,
        name: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        guard_code: Optional[str] = None,
        validate: bool = True
    ) -> str:
        """
        Start or queue a new download.
        
        Returns:
            Download ID
        """
        download_id = f"dl_{int(time.time())}_{appid}"
        
        download_info = {
            "id": download_id,
            "appid": appid,
            "name": name,
            "username": username,
            "password": password,
            "guard_code": guard_code,
            "validate": validate
        }
        
        with self.lock:
            if len(self.active_downloads) >= settings.MAX_CONCURRENT_DOWNLOADS:
                self.download_queue.append(download_info)
                logger.info("Download queued: %s", name)
                return download_id
            
            self._start_download_thread(download_info)
            return download_id
    
    def _start_download_thread(self, download_info: Dict) -> None:
        """Start a new download thread."""
        status = DownloadStatus(
            id=download_info["id"],
            appid=download_info["appid"],
            name=download_info["name"],
            progress=0.0,
            status="Starting",
            start_time=datetime.now()
        )
        
        self.active_downloads[download_info["id"]] = status
        
        thread = threading.Thread(
            target=self._download_worker,
            args=(download_info,),
            daemon=True
        )
        thread.start()
    
    def _download_worker(self, download_info: Dict) -> None:
        """Worker function for download thread."""
        try:
            success, message = steam_cmd.download_game(
                appid=download_info["appid"],
                username=download_info["username"],
                password=download_info["password"],
                guard_code=download_info["guard_code"],
                validate=download_info["validate"]
            )
            
            with self.lock:
                if success:
                    self.active_downloads[download_info["id"]].status = "Completed"
                    self.active_downloads[download_info["id"]].progress = 100.0
                else:
                    self.active_downloads[download_info["id"]].status = "Failed"
                    self.active_downloads[download_info["id"]].error = message
                
                # Add to history
                self._add_to_history(download_info["id"])
                
        except Exception as e:
            logger.error("Download error: %s", str(e))
            with self.lock:
                self.active_downloads[download_info["id"]].status = "Failed"
                self.active_downloads[download_info["id"]].error = str(e)
                self._add_to_history(download_info["id"])
    
    def _process_queue(self) -> None:
        """Process the download queue."""
        while True:
            time.sleep(5)  # Check every 5 seconds
            
            with self.lock:
                # Remove completed downloads
                self._cleanup_completed()
                
                # Start new downloads if possible
                while (len(self.active_downloads) < settings.MAX_CONCURRENT_DOWNLOADS
                       and self.download_queue):
                    next_download = self.download_queue.pop(0)
                    self._start_download_thread(next_download)
    
    def _cleanup_completed(self) -> None:
        """Remove completed downloads that are older than 1 minute."""
        current_time = datetime.now()
        completed_ids = [
            dl_id for dl_id, status in self.active_downloads.items()
            if status.status in ["Completed", "Failed"]
            and (current_time - status.start_time).total_seconds() > 60
        ]
        
        for dl_id in completed_ids:
            self._add_to_history(dl_id)
            del self.active_downloads[dl_id]
    
    def _add_to_history(self, download_id: str) -> None:
        """Add a download to history."""
        status = self.active_downloads[download_id]
        history_entry = {
            "id": status.id,
            "appid": status.appid,
            "name": status.name,
            "status": status.status,
            "error": status.error,
            "completed_at": datetime.now().isoformat()
        }
        
        self.download_history.append(history_entry)
        
        # Trim history if needed
        if len(self.download_history) > settings.MAX_HISTORY_SIZE:
            self.download_history.pop(0)
    
    def get_status(self) -> Dict:
        """Get current download status."""
        with self.lock:
            return {
                "active": [vars(status) for status in self.active_downloads.values()],
                "queue": [
                    {"name": d["name"], "appid": d["appid"]}
                    for d in self.download_queue
                ],
                "history": self.download_history
            }
    
    def cancel_download(self, download_id: str) -> bool:
        """Cancel a download."""
        with self.lock:
            if download_id in self.active_downloads:
                self.active_downloads[download_id].status = "Cancelled"
                self._add_to_history(download_id)
                return True
            
            # Check queue
            for i, download in enumerate(self.download_queue):
                if download["id"] == download_id:
                    self.download_queue.pop(i)
                    return True
            
            return False

# Create global instance
download_manager = DownloadManager() 