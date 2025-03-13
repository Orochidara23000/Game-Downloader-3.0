from pathlib import Path
import os
from typing import Dict, Any
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "Steam Games Downloader"
    VERSION: str = "2.0.0"
    DEBUG: bool = False
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    STEAM_DOWNLOAD_PATH: str = os.environ.get(
        'STEAM_DOWNLOAD_PATH', 
        str(BASE_DIR / "downloads")
    )
    LOG_DIR: Path = BASE_DIR / "logs"
    STEAMCMD_DIR: Path = BASE_DIR / "steamcmd"
    CACHE_DIR: Path = BASE_DIR / "cache"
    
    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 7860
    
    # Logging
    LOG_LEVEL: str = os.environ.get('LOG_LEVEL', 'INFO')
    
    # Download Settings
    MAX_CONCURRENT_DOWNLOADS: int = 1
    MAX_HISTORY_SIZE: int = 50
    DOWNLOAD_TIMEOUT: int = 3600  # 1 hour
    
    # Steam API
    STEAM_API_URL: str = "https://store.steampowered.com/api"
    
    class Config:
        env_file = ".env"
        
    def create_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        directories = [
            self.STEAM_DOWNLOAD_PATH,
            self.LOG_DIR,
            self.STEAMCMD_DIR,
            self.CACHE_DIR
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            
    def get_steamcmd_path(self) -> Path:
        """Get the path to SteamCMD executable based on platform."""
        if os.name == 'nt':  # Windows
            return self.STEAMCMD_DIR / "steamcmd.exe"
        return self.STEAMCMD_DIR / "steamcmd.sh"

# Create global settings instance
settings = Settings() 