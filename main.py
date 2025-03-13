#!/usr/bin/env python3
import os
import sys
import signal
import logging
import uvicorn
import threading
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import gradio as gr
import requests
import subprocess
import platform
import psutil
import json
from typing import Dict, Optional, Any
from datetime import datetime

# Basic Configuration
class Settings:
    APP_NAME = "Steam Games Downloader"
    VERSION = "2.0.0"
    HOST = "0.0.0.0"
    PORT = int(os.getenv("PORT", 7860))
    DEBUG = bool(os.getenv("DEBUG", False))
    STEAM_DOWNLOAD_PATH = os.getenv("STEAM_DOWNLOAD_PATH", "/data/downloads")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
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

# Initialize FastAPI
app = FastAPI(title=Settings.APP_NAME, version=Settings.VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        import zipfile
        response = requests.get(url)
        zip_path = "steamcmd/steamcmd.zip"
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall("steamcmd")
        os.remove(zip_path)
    
    def _download_and_extract_tar(self, url):
        import tarfile
        response = requests.get(url)
        tar_path = "steamcmd/steamcmd.tar.gz"
        with open(tar_path, 'wb') as f:
            f.write(response.content)
        with tarfile.open(tar_path, 'r:gz') as tar:
            tar.extractall("steamcmd")
        os.remove(tar_path)
        os.chmod("steamcmd/steamcmd.sh", 0o755)

# Download Manager
class DownloadManager:
    def __init__(self):
        self.active_downloads = {}
        self.download_queue = []
        self.download_history = []
        self.steam_cmd = SteamCMD()
    
    def start_download(self, game_input: str, anonymous: bool = True,
                      username: Optional[str] = None, 
                      password: Optional[str] = None) -> Dict[str, Any]:
        """Start a game download."""
        try:
            # Extract AppID
            appid = self._parse_game_input(game_input)
            if not appid:
                return {"success": False, "message": "Invalid game input"}
            
            # Create download directory
            download_dir = os.path.join(Settings.STEAM_DOWNLOAD_PATH, f"app_{appid}")
            os.makedirs(download_dir, exist_ok=True)
            
            # Prepare command
            cmd = [str(self.steam_cmd.path)]
            if anonymous:
                cmd.extend(["+login", "anonymous"])
            else:
                if not username or not password:
                    return {"success": False, "message": "Username and password required"}
                cmd.extend(["+login", username, password])
            
            cmd.extend([
                "+force_install_dir", download_dir,
                "+app_update", appid,
                "validate",
                "+quit"
            ])
            
            # Start download process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            download_id = f"dl_{datetime.now().timestamp()}_{appid}"
            self.active_downloads[download_id] = {
                "process": process,
                "appid": appid,
                "status": "Downloading",
                "start_time": datetime.now()
            }
            
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
        
        import re
        match = re.search(r'app/(\d+)', game_input)
        if match:
            return match.group(1)
        
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current download status."""
        return {
            "active_downloads": [
                {
                    "id": dl_id,
                    "appid": info["appid"],
                    "status": info["status"],
                    "start_time": info["start_time"].isoformat()
                }
                for dl_id, info in self.active_downloads.items()
            ],
            "queue": self.download_queue,
            "history": self.download_history
        }

# Create global instances
download_manager = DownloadManager()

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
                username = gr.Textbox(label="Steam Username")
                password = gr.Textbox(
                    label="Steam Password",
                    type="password"
                )
            
            download_btn = gr.Button("Download Game")
            status = gr.JSON(label="Download Status")
            
            def start_download(game_input, anonymous, username, password):
                result = download_manager.start_download(
                    game_input,
                    anonymous,
                    username,
                    password
                )
                return json.dumps(result, indent=2)
            
            download_btn.click(
                fn=start_download,
                inputs=[game_input, anonymous, username, password],
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
    
    return interface

# API Routes
@app.get("/api/status")
async def get_status():
    return download_manager.get_status()

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

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