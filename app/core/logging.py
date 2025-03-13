import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from .config import settings

def setup_logging() -> None:
    """Configure logging for the application."""
    # Create logs directory if it doesn't exist
    Path(settings.LOG_DIR).mkdir(parents=True, exist_ok=True)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set up file handler with rotation
    file_handler = RotatingFileHandler(
        settings.LOG_DIR / "steam_downloader.log",
        maxBytes=10_000_000,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    
    # Set up console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Create application logger
    logger = logging.getLogger("steam_downloader")
    logger.setLevel(settings.LOG_LEVEL)
    
    # Log startup information
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")
    logger.info(f"Log level: {settings.LOG_LEVEL}")
    logger.info(f"Download path: {settings.STEAM_DOWNLOAD_PATH}") 
