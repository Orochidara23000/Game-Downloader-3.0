import logging
import threading
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from config import settings
from steam_cmd import steam_cmd
import os
from queue import Queue
from models import DownloadStatus, DownloadProgress, GameInfo
from utils import format_size, format_speed, format_time

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
        self.download_queue = Queue()
        self.active_downloads: Dict[int, DownloadProgress] = {}
        self.download_thread = None
        self.running = False
        
        # Start queue processor
        self.queue_processor = threading.Thread(
            target=self._process_queue,
            daemon=True
        )
        self.queue_processor.start()
    
    def start(self):
        """Start the download manager."""
        if not self.running:
            self.running = True
            self.download_thread = threading.Thread(target=self._process_queue)
            self.download_thread.daemon = True
            self.download_thread.start()
    
    def stop(self):
        """Stop the download manager."""
        self.running = False
        if self.download_thread:
            self.download_thread.join()
    
    def add_to_queue(self, game_info: GameInfo, credentials: Optional[Dict] = None):
        """Add a game to the download queue."""
        self.download_queue.put((game_info, credentials))
        logger.info(f"Added game {game_info.app_id} to download queue")
    
    def _process_queue(self):
        """Process the download queue."""
        while self.running:
            try:
                if not self.download_queue.empty():
                    game_info, credentials = self.download_queue.get()
                    self._handle_download(game_info, credentials)
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error processing download queue: {e}")
    
    def _handle_download(self, game_info: GameInfo, credentials: Optional[Dict]):
        """Handle the download of a single game."""
        try:
            # Login to Steam
            if credentials:
                steam_cmd.login(**credentials)
            else:
                steam_cmd.login()

            # Prepare download directory
            install_dir = settings.DOWNLOAD_DIR / str(game_info.app_id)
            install_dir.mkdir(parents=True, exist_ok=True)

            # Start download
            if steam_cmd.download_game(game_info.app_id, install_dir):
                self._monitor_download(game_info.app_id)
            else:
                logger.error(f"Failed to start download for game {game_info.app_id}")

        except Exception as e:
            logger.error(f"Error downloading game {game_info.app_id}: {e}")
            self.active_downloads[game_info.app_id] = DownloadProgress(
                status=DownloadStatus.FAILED,
                progress=0,
                speed="0 B/s",
                eta="Unknown",
                current_file="",
                total_size="Unknown"
            )
    
    def _monitor_download(self, app_id: int):
        """Monitor download progress for a game."""
        while True:
            progress, message = steam_cmd.get_download_progress()
            
            self.active_downloads[app_id] = DownloadProgress(
                status=DownloadStatus.DOWNLOADING if progress < 100 else DownloadStatus.COMPLETED,
                progress=progress,
                speed=self._extract_speed(message),
                eta=self._extract_eta(message),
                current_file=self._extract_filename(message),
                total_size=self._extract_size(message)
            )

            if progress >= 100 or "Failed" in message:
                break
            time.sleep(1)
    
    def get_status(self) -> Dict:
        """Get current download status."""
        return {
            "queue_size": self.download_queue.qsize(),
            "active_downloads": self.active_downloads
        }
    
    def cancel_download(self, app_id: int):
        """Cancel a specific download."""
        steam_cmd.cancel_download()
        if app_id in self.active_downloads:
            self.active_downloads[app_id].status = DownloadStatus.CANCELLED
    
    # Helper methods for parsing SteamCMD output
    def _extract_speed(self, message: str) -> str:
        # Implementation for extracting speed from message
        return "0 B/s"  # Placeholder
    
    def _extract_eta(self, message: str) -> str:
        # Implementation for extracting ETA from message
        return "Unknown"  # Placeholder
    
    def _extract_filename(self, message: str) -> str:
        # Implementation for extracting filename from message
        return ""  # Placeholder
    
    def _extract_size(self, message: str) -> str:
        # Implementation for extracting size from message
        return "Unknown"  # Placeholder

# Create global instance
download_manager = DownloadManager() 
