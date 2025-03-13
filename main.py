#!/usr/bin/env python3
import os
import sys
import signal
import logging
import uvicorn
import threading
import gradio as gr
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Local imports
from config import settings
from interface import create_interface
from downloader import download_manager
from steam_cmd import steam_cmd
from schemas import (
    DownloadRequest,
    DownloadStatusResponse,
    GameInfo,
    SystemStatus
)

# Set up logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_DIR / "steam_downloader.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        settings.create_directories()
        
        # Install SteamCMD if needed
        if not steam_cmd.path.exists():
            logger.info("Installing SteamCMD...")
            if not steam_cmd.install():
                raise Exception("Failed to install SteamCMD")
        
        # Create and launch interface
        interface = create_interface()
        interface.launch(
            server_name=settings.HOST,
            server_port=settings.PORT,
            share=True
        )
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()