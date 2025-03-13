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
import zipfile
import tarfile
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
    STEAM_DOWNLOAD_PATH = os.getenv("STEAM_DOWNLOAD_PATH", "/data/downloads")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    MAX_CONCURRENT_DOWNLOADS = 1
    MAX_HISTORY_SIZE = 50
    
    @classmethod
    def create_directories(cls):
        """Create necessary directories."""
        directories = [
            cls.STEAM_DOWNLOAD_PATH,
            "logs",
            "steamcmd",
            "cache"
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/steam_downloader.log"),
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
        
    def _get_steamcmd_path(self):
        if platform.system() == "Windows":
            return Path("steamcmd/steamcmd.exe")
        return Path("steamcmd/steamcmd.sh")
    
    def install(self):
        """Install SteamCMD."""
        try:
            if platform.system() == "Windows":
                url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
                self._download_and_extract_zip(url)
            else:
                url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz"
                self._download_and_extract_tar(url)
            
            logger.info("SteamCMD installed successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to install SteamCMD: {e}")
            return False
    
    def _download_and_extract_zip(self, url):
        response = requests.get(url)
        zip_path = "steamcmd/steamcmd.zip"
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall("steamcmd")
        os.remove(zip_path)
    
    def _download_and_extract_tar(self, url):
        response = requests.get(url)
        tar_path = "steamcmd/steamcmd.tar.gz"
        with open(tar_path, 'wb') as f:
            f.write(response.content)
        with tarfile.open(tar_path, 'r:gz') as tar:
            tar.extractall("steamcmd")
        os.remove(tar_path)
        os.chmod("steamcmd/steamcmd.sh", 0o755)

    def download_game(self, appid: str, download_dir: str, 
                     username: Optional[str] = None,
                     password: Optional[str] = None,
                     guard_code: Optional[str] = None) -> Tuple[bool, str]:
        """Download a game using SteamCMD."""
        try:
            cmd = [str(self.path)]
            
            if username and password:
                cmd.extend(["+login", username, password])
                if guard_code:
                    cmd.append(guard_code)
            else:
                cmd.extend(["+login", "anonymous"])
            
            cmd.extend([
                "+force_install_dir", download_dir,
                "+app_update", appid,
                "validate",
                "+quit"
            ])
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            if process.returncode == 0:
                return True, "Download completed successfully"
            return False, f"Download failed: {process.stderr}"
            
        except Exception as e:
            return False, f"Error: {str(e)}"

# Game Information Service
class GameInfoService:
    def __init__(self):
        self.api_url = "https://store.steampowered.com/api"
        self.cache_dir = "cache"
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def get_game_info(self, game_input: str) -> Dict[str, Any]:
        """Get game information from Steam API."""
        try:
            appid = self.parse_game_input(game_input)
            if not appid:
                return {"error": "Invalid game input"}
            
            # Check cache
            cache_file = os.path.join(self.cache_dir, f"game_{appid}.json")
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    return json.load(f)
            
            # Fetch from API
            url = f"{self.api_url}/appdetails"
            params = {"appids": appid}
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data[appid]["success"]:
                game_info = data[appid]["data"]
                # Cache the result
                with open(cache_file, 'w') as f:
                    json.dump(game_info, f)
                return game_info
            
            return {"error": "Game not found"}
            
        except Exception as e:
            return {"error": str(e)}
    
    def parse_game_input(self, game_input: str) -> Optional[str]:
        """Extract AppID from game input."""
        if game_input.isdigit():
            return game_input
        
        match = re.search(r'app/(\d+)', game_input)
        if match:
            return match.group(1)
        
        return None

# Download Manager
class DownloadManager:
    def __init__(self):
        self.active_downloads: Dict[str, Dict] = {}
        self.download_queue: List[Dict] = []
        self.download_history: List[Dict] = []
        self.steam_cmd = SteamCMD()
        self.game_info = GameInfoService()
    
    def start_download(self, game_input: str, anonymous: bool = True,
                      username: Optional[str] = None, 
                      password: Optional[str] = None,
                      guard_code: Optional[str] = None) -> Dict[str, Any]:
        """Start a game download."""
        try:
            # Get game info
            game_info = self.game_info.get_game_info(game_input)
            if "error" in game_info:
                return {"success": False, "message": game_info["error"]}
            
            appid = str(game_info["steam_appid"])
            game_name = game_info["name"]
            
            # Create download directory
            download_dir = os.path.join(Settings.STEAM_DOWNLOAD_PATH, f"app_{appid}")
            os.makedirs(download_dir, exist_ok=True)
            
            # Create download entry
            download_id = f"dl_{int(datetime.now().timestamp())}_{appid}"
            
            # Start download in a separate thread
            thread = threading.Thread(
                target=self._download_thread,
                args=(download_id, appid, download_dir, username, password, guard_code, game_name)
            )
            thread.daemon = True
            
            self.active_downloads[download_id] = {
                "appid": appid,
                "name": game_name,
                "status": "Starting",
                "progress": 0,
                "start_time": datetime.now()
            }
            
            thread.start()
            
            return {
                "success": True,
                "download_id": download_id,
                "message": f"Download started for {game_name}"
            }
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            return {"success": False, "message": str(e)}
    
    def _download_thread(self, download_id: str, appid: str, download_dir: str,
                        username: Optional[str], password: Optional[str],
                        guard_code: Optional[str], game_name: str):
        """Handle the download process in a separate thread."""
        try:
            success, message = self.steam_cmd.download_game(
                appid, download_dir, username, password, guard_code
            )
            
            if success:
                self.active_downloads[download_id]["status"] = "Completed"
                self.active_downloads[download_id]["progress"] = 100
            else:
                self.active_downloads[download_id]["status"] = "Failed"
                self.active_downloads[download_id]["error"] = message
            
            # Add to history
            self.download_history.append({
                "id": download_id,
                "name": game_name,
                "status": "Completed" if success else "Failed",
                "completed_at": datetime.now().isoformat()
            })
            
            # Trim history if needed
            if len(self.download_history) > Settings.MAX_HISTORY_SIZE:
                self.download_history.pop(0)
                
        except Exception as e:
            logger.error(f"Download thread error: {e}")
            self.active_downloads[download_id]["status"] = "Failed"
            self.active_downloads[download_id]["error"] = str(e)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current download status."""
        return {
            "active_downloads": [
                {
                    "id": dl_id,
                    **info
                }
                for dl_id, info in self.active_downloads.items()
            ],
            "queue": self.download_queue,
            "history": self.download_history
        }
    
    def cancel_download(self, download_id: str) -> bool:
        """Cancel a download."""
        if download_id in self.active_downloads:
            self.active_downloads[download_id]["status"] = "Cancelled"
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

# Create global instances
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
            
            game_info = gr.JSON(label="Game Information")
            
            check_button = gr.Button("Check Game")
            
            def check_game(input_text):
                return download_manager.game_info.get_game_info(input_text)
            
            check_button.click(
                fn=check_game,
                inputs=game_input,
                outputs=game_info
            )
            
            anonymous = gr.Checkbox(
                label="Anonymous Login (Free Games Only)",
                value=True
            )
            
            with gr.Group() as login_group:
                username = gr.Textbox(label="Steam Username")
                password = gr.Textbox(
                    label="Steam Password",
                    type="password"
                )
                guard_code = gr.Textbox(label="Steam Guard Code (if needed)")
            
            download_btn = gr.Button("Download Game")
            status = gr.JSON(label="Download Status")
            
            def start_download(game_input, anonymous, username, password, guard_code):
                return download_manager.start_download(
                    game_input,
                    anonymous,
                    username if not anonymous else None,
                    password if not anonymous else None,
                    guard_code if not anonymous else None
                )
            
            download_btn.click(
                fn=start_download,
                inputs=[game_input, anonymous, username, password, guard_code],
                outputs=status
            )
        
        with gr.Tab("Downloads"):
            status_output = gr.JSON(label="Current Downloads")
            refresh_btn = gr.Button("Refresh Status")
            
            def update_status():
                return download_manager.get_status()
            
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
        # Create directories
        Settings.create_directories()
        
        # Install SteamCMD if needed
        if not download_manager.steam_cmd.path.exists():
            download_manager.steam_cmd.install()
        
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