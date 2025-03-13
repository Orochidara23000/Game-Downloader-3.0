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

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent))

# Import application components
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.exceptions import SteamDownloaderError
from app.api.routes import router as api_router
from app.ui.interface import create_interface
from app.services.steam_cmd import steam_cmd
from app.services.downloader import download_manager

# Initialize FastAPI application
fastapi_app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Steam Games Downloader API"
)

# Add CORS middleware
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
fastapi_app.include_router(api_router, prefix="/api")

def initialize_application():
    """Initialize the application components."""
    try:
        # Set up logging
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("Initializing Steam Games Downloader")
        
        # Create necessary directories
        settings.create_directories()
        logger.info("Application directories created")
        
        # Ensure SteamCMD is installed
        if not steam_cmd.path.exists():
            logger.info("Installing SteamCMD...")
            steam_cmd.install()
        logger.info("SteamCMD is ready")
        
        return True
    except Exception as e:
        print(f"Error initializing application: {str(e)}", file=sys.stderr)
        return False

def start_api_server(host: str, port: int):
    """Start the FastAPI server in a separate thread."""
    uvicorn.run(
        fastapi_app,
        host=host,
        port=port,
        log_level=settings.LOG_LEVEL.lower()
    )

def setup_signal_handlers():
    """Set up signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger = logging.getLogger(__name__)
        logger.info("Received shutdown signal, cleaning up...")
        
        # Cancel all active downloads
        for download_id in list(download_manager.active_downloads.keys()):
            download_manager.cancel_download(download_id)
        
        logger.info("Shutdown complete")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def create_app():
    """Create and configure the Gradio interface."""
    # Create the interface
    app = create_interface()
    
    # Add custom JavaScript for auto-refresh
    app.load(js="""
        function setupAutoRefresh() {
            setInterval(() => {
                // Find and click the refresh button
                const refreshBtn = document.querySelector('button:contains("Refresh Status")');
                if (refreshBtn) refreshBtn.click();
            }, 5000);
        }
        
        // Run setup when the page loads
        window.addEventListener('load', setupAutoRefresh);
    """)
    
    return app

def main():
    """Main application entry point."""
    # Initialize application
    if not initialize_application():
        sys.exit(1)
    
    logger = logging.getLogger(__name__)
    
    # Set up signal handlers
    setup_signal_handlers()
    
    try:
        # Start FastAPI server in a separate thread
        api_thread = threading.Thread(
            target=start_api_server,
            args=(settings.HOST, settings.PORT + 1),  # Use different port for API
            daemon=True
        )
        api_thread.start()
        logger.info(f"API server starting on port {settings.PORT + 1}")
        
        # Create and launch Gradio interface
        app = create_app()
        logger.info(f"Starting Gradio interface on port {settings.PORT}")
        
        # Launch the interface
        app.launch(
            server_name=settings.HOST,
            server_port=settings.PORT,
            share=True,
            debug=settings.DEBUG,
            auth=None,  # Add authentication if needed
            ssl_verify=False if settings.DEBUG else True
        )
        
    except Exception as e:
        logger.error(f"Application startup failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()