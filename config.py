from pathlib import Path
import os
from typing import Dict, Any, Optional

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings  # Fallback for older versions

class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "Steam Games Downloader"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Paths
    BASE_DIR: Path = Path.cwd()
    STEAMCMD_DIR: Path = BASE_DIR / "steamcmd"
    LOG_DIR: Path = BASE_DIR / "logs"
    DOWNLOAD_DIR: Path = Path(os.environ.get("STEAM_DOWNLOAD_PATH", BASE_DIR / "downloads"))
    
    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 7860
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Download Settings
    MAX_CONCURRENT_DOWNLOADS: int = 1
    MAX_HISTORY_SIZE: int = 50
    DOWNLOAD_TIMEOUT: int = 3600  # 1 hour
    
    # Steam API
    STEAM_API_URL: str = "https://store.steampowered.com/api"
    
    # Steam settings
    STEAM_GUARD_REQUIRED: bool = False
    STEAM_USERNAME: Optional[str] = None
    
    class Config:
        env_file = ".env"
        
    def create_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        for directory in [self.STEAMCMD_DIR, self.LOG_DIR, self.DOWNLOAD_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
            
    def get_steamcmd_path(self) -> Path:
        """Get the path to SteamCMD executable based on platform."""
        if os.name == 'nt':  # Windows
            return self.STEAMCMD_DIR / "steamcmd.exe"
        return self.STEAMCMD_DIR / "steamcmd.sh"

# Create global settings instance
settings = Settings() 