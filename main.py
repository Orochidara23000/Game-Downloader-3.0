#!/usr/bin/env python3
import os
import sys
import signal
import logging
import uvicorn
import threading
import gradio as gr
import requests
import subprocess
import platform
import psutil
import json
import re
import tarfile
import zipfile
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Basic Configuration
class Settings:
    APP_NAME = "Steam Games Downloader"
    VERSION = "2.0.0"
    HOST = "0.0.0.0"
    PORT = int(os.getenv("PORT", 7860))
    DEBUG = bool(os.getenv("DEBUG", False))
    BASE_DIR = Path(__file__).parent
    STEAM_DOWNLOAD_PATH = os.getenv("STEAM_DOWNLOAD_PATH", str(BASE_DIR / "downloads"))
    STEAMCMD_DIR = BASE_DIR / "steamcmd"
    LOG_DIR = BASE_DIR / "logs"
    CACHE_DIR = BASE_DIR / "cache"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    MAX_CONCURRENT_DOWNLOADS = 1
    MAX_HISTORY_SIZE = 50

    @classmethod
    def create_directories(cls):
        """Create necessary directories."""
        for directory in [cls.STEAM_DOWNLOAD_PATH, cls.LOG_DIR, cls.STEAMCMD_DIR, cls.CACHE_DIR]:
            Path(directory).mkdir(parents=True, exist_ok=True)

# Set up logging
def setup_logging():
    Settings.create_directories()
    logging.basicConfig(
        level=Settings.LOG_LEVEL,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(Settings.LOG_DIR / "steam_downloader.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )

logger = logging.getLogger(__name__)

# Custom Exceptions
class SteamDownloaderError(Exception):
    """Base exception for Steam Downloader application."""
    pass

class SteamCMDError(SteamDownloaderError):
    """Raised when there's an error with SteamCMD."""
    pass

# SteamCMD Management
class SteamCMD:
    def __init__(self):
        self.path = self._get_steamcmd_path()
        
    def _get_steamcmd_path(self) -> Path:
        """Get the path to SteamCMD executable."""
        if platform.system() == "Windows":
            return Settings.STEAMCMD_DIR / "steamcmd.exe"
        return Settings.STEAMCMD_DIR / "steamcmd.sh"
    
    def install(self) -> bool:
        """Install SteamCMD."""
        try:
            if platform.system() == "Windows":
                url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
                self._download_and_extract_zip(url)
            else:
                url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz"
                self._download_and_extract_tar(url)
            
            # Verify installation
            self._verify_installation()
            logger.info("SteamCMD installed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to install SteamCMD: {e}")
            return False
    
    def _download_and_extract_zip(self, url: str):
        response = requests.get(url)
        zip_path = Settings.STEAMCMD_DIR / "steamcmd.zip"
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(Settings.STEAMCMD_DIR)
        zip_path.unlink()
    
    def _download_and_extract_tar(self, url: str):
        response = requests.get(url)
        tar_path = Settings.STEAMCMD_DIR / "steamcmd.tar.gz"
        with open(tar_path, 'wb') as f:
            f.write(response.content)
        with tarfile.open(tar_path, 'r:gz') as tar:
            tar.extractall(Settings.STEAMCMD_DIR)
        tar_path.unlink()
        self.path.chmod(0o755)
    
    def _verify_installation(self):
        """Verify SteamCMD installation."""
        try:
            result = subprocess.run(
                [str(self.path), "+quit"],
                capture_output=True,
                text=True,
                check=True
            )
            if result.returncode != 0:
                raise SteamCMDError("SteamCMD verification failed")
        except Exception as e:
            raise SteamCMDError(f"SteamCMD verification failed: {e}")

# Download Manager
class DownloadManager:
    def __init__(self):
        self.active_downloads: Dict[str, Dict[str, Any]] = {}
        self.download_queue: List[Dict[str, Any]] = []
        self.download_history: List[Dict[str, Any]] = []
        self.steam_cmd = SteamCMD()
        self.lock = threading.Lock()
    
    def start_download(
        self,
        game_input: str,
        anonymous: bool = True,
        username: Optional[str] = None,
        password: Optional[str] = None,
        validate: bool = True
    ) -> Dict[str, Any]:
        """Start a game download."""
        try:
            # Extract AppID
            appid = self._parse_game_input(game_input)
            if not appid:
                return {"success": False, "message": "Invalid game input"}
            
            # Create download directory
            download_dir = Path(Settings.STEAM_DOWNLOAD_PATH) / f"app_{appid}"
            download_dir.mkdir(parents=True, exist_ok=True)
            
            # Prepare command
            cmd = [str(self.steam_cmd.path)]
            if anonymous:
                cmd.extend(["+login", "anonymous"])
            else:
                if not username or not password:
                    return {"success": False, "message": "Username and password required"}
                cmd.extend(["+login", username, password])
            
            cmd.extend([
                "+force_install_dir", str(download_dir),
                "+app_update", appid
            ])
            
            if validate:
                cmd.append("validate")
            
            cmd.append("+quit")
            
            # Start download process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            download_id = f"dl_{int(datetime.now().timestamp())}_{appid}"
            
            with self.lock:
                self.active_downloads[download_id] = {
                    "process": process,
                    "appid": appid,
                    "status": "Downloading",
                    "progress": 0,
                    "start_time": datetime.now()
                }
            
            # Start monitoring thread
            threading.Thread(
                target=self._monitor_download,
                args=(download_id,),
                daemon=True
            ).start()
            
            return {
                "success": True,
                "download_id": download_id,
                "message": "Download started"
            }
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            return {"success": False, "message": str(e)}
    
    def _parse_game_input(self, game_input: str) -> Optional[str]:
        """Extract AppID from game input."""
        if game_input.isdigit():
            return game_input
        
        match = re.search(r'app/(\d+)', game_input)
        if match:
            return match.group(1)
        
        return None
    
    def _monitor_download(self, download_id: str):
        """Monitor download progress."""
        try:
            download = self.active_downloads[download_id]
            process = download["process"]
            
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                
                if "Progress:" in line:
                    progress = re.search(r'Progress:\s*(\d+\.?\d*)%', line)
                    if progress:
                        with self.lock:
                            download["progress"] = float(progress.group(1))
                
                if "Success!" in line:
                    with self.lock:
                        download["status"] = "Completed"
                        download["progress"] = 100
            
            # Process completed
            with self.lock:
                if process.returncode == 0:
                    download["status"] = "Completed"
                else:
                    download["status"] = "Failed"
                self._add_to_history(download_id)
                
        except Exception as e:
            logger.error(f"Error monitoring download {download_id}: {e}")
            with self.lock:
                download["status"] = "Failed"
                download["error"] = str(e)
                self._add_to_history(download_id)
    
    def _add_to_history(self, download_id: str):
        """Add download to history."""
        download = self.active_downloads[download_id]
        self.download_history.append({
            "id": download_id,
            "appid": download["appid"],
            "status": download["status"],
            "completed_at": datetime.now()
        })
        
        if len(self.download_history) > Settings.MAX_HISTORY_SIZE:
            self.download_history.pop(0)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current download status."""
        with self.lock:
            return {
                "active_downloads": [
                    {
                        "id": dl_id,
                        "appid": info["appid"],
                        "status": info["status"],
                        "progress": info.get("progress", 0),
                        "start_time": info["start_time"].isoformat()
                    }
                    for dl_id, info in self.active_downloads.items()
                ],
                "queue": self.download_queue,
                "history": self.download_history
            }
    
    def cancel_download(self, download_id: str) -> bool:
        """Cancel a download."""
        with self.lock:
            if download_id in self.active_downloads:
                download = self.active_downloads[download_id]
                if "process" in download:
                    download["process"].terminate()
                download["status"] = "Cancelled"
                self._add_to_history(download_id)
                return True
            return False

# Initialize FastAPI
app = FastAPI(title=Settings.APP_NAME, version=Settings.VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create global download manager
download_manager = DownloadManager()

# API Routes
@app.get("/api/status")
async def get_status():
    return download_manager.get_status()

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

# Gradio Interface
def create_interface():
    """Create the Gradio interface."""
    with gr.Blocks(title=Settings.APP_NAME) as interface:
        gr.Markdown(f"# {Settings.APP_NAME}")
        
        with gr.Tab("Download Games"):
            game_input = gr.Textbox(
                label="Game URL or ID",
                placeholder="Enter Steam game URL or ID"
            )
            
            anonymous = gr.Checkbox(
                label="Anonymous Login (Free Games Only)",
                value=True
            )
            
            with gr.Group() as login_group:
                username = gr.Textbox(
                    label="Steam Username",
                    placeholder="Enter your Steam username"
                )
                password = gr.Textbox(
                    label="Steam Password",
                    type="password",
                    placeholder="Enter your Steam password"
                )
            
            validate = gr.Checkbox(
                label="Validate Files",
                value=True
            )
            
            download_btn = gr.Button("Download Game")
            status = gr.JSON(label="Download Status")
            
            def start_download(game_input, anonymous, username, password, validate):
                result = download_manager.start_download(
                    game_input,
                    anonymous,
                    username,
                    password,
                    validate
                )
                return json.dumps(result, indent=2)
            
            download_btn.click(
                fn=start_download,
                inputs=[game_input, anonymous, username, password, validate],
                outputs=status
            )
        
        with gr.Tab("Downloads"):
            status_output = gr.JSON(label="Current Downloads")
            refresh_btn = gr.Button("Refresh Status")
            
            def update_status():
                return json.dumps(download_manager.get_status(), indent=2)
            
            refresh_btn.click(
                fn=update_status,
                outputs=status_output
            )
            
            # Auto-refresh every 5 seconds
            gr.update(every=5)(
                fn=update_status,
                outputs=status_output
            )
    
    return interface

def main():
    """Main application entry point."""
    try:
        # Set up logging
        setup_logging()
        logger.info(f"Starting {Settings.APP_NAME}")
        
        # Create directories
        Settings.create_directories()
        
        # Install SteamCMD if needed
        if not download_manager.steam_cmd.path.exists():
            logger.info("Installing SteamCMD...")
            if not download_manager.steam_cmd.install():
                raise SteamCMDError("Failed to install SteamCMD")
        
        # Create and launch interface
        interface = create_interface()
        interface.launch(
            server_name=Settings.HOST,
            server_port=Settings.PORT,
            share=True
        )
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()