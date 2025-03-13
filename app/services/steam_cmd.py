import os
import platform
import subprocess
import requests
import tarfile
import zipfile
import logging
from pathlib import Path
from typing import Tuple, Optional
from ..core.config import settings
from ..core.exceptions import SteamCMDError

logger = logging.getLogger(__name__)

class SteamCMD:
    def __init__(self):
        self.path = settings.get_steamcmd_path()
        self._ensure_installed()
    
    def _ensure_installed(self) -> None:
        """Ensure SteamCMD is installed and up to date."""
        if not self.path.exists():
            logger.info("SteamCMD not found. Installing...")
            self.install()
        else:
            logger.info("SteamCMD found at: %s", self.path)
    
    def install(self) -> None:
        """Install SteamCMD based on platform."""
        try:
            if platform.system() == "Windows":
                self._install_windows()
            else:
                self._install_unix()
            
            # Verify installation
            self._verify_installation()
            
        except Exception as e:
            raise SteamCMDError(f"Failed to install SteamCMD: {str(e)}") from e
    
    def _install_windows(self) -> None:
        """Install SteamCMD on Windows."""
        url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
        zip_path = settings.STEAMCMD_DIR / "steamcmd.zip"
        
        # Download SteamCMD
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Save and extract
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(settings.STEAMCMD_DIR)
        
        # Cleanup
        zip_path.unlink()
    
    def _install_unix(self) -> None:
        """Install SteamCMD on Unix-like systems."""
        url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz"
        tar_path = settings.STEAMCMD_DIR / "steamcmd_linux.tar.gz"
        
        # Download SteamCMD
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Save and extract
        with open(tar_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        with tarfile.open(tar_path, 'r:gz') as tar:
            tar.extractall(path=settings.STEAMCMD_DIR)
        
        # Make executable
        self.path.chmod(0o755)
        
        # Cleanup
        tar_path.unlink()
    
    def _verify_installation(self) -> None:
        """Verify SteamCMD installation by running a simple command."""
        try:
            result = subprocess.run(
                [str(self.path), "+quit"],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info("SteamCMD installation verified successfully")
        except subprocess.CalledProcessError as e:
            raise SteamCMDError(f"SteamCMD verification failed: {e.stderr}")
    
    def download_game(
        self,
        appid: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        guard_code: Optional[str] = None,
        validate: bool = True
    ) -> Tuple[bool, str]:
        """
        Download a game using SteamCMD.
        
        Args:
            appid: The Steam AppID of the game
            username: Steam username (optional for free games)
            password: Steam password (optional for free games)
            guard_code: Steam Guard code (if required)
            validate: Whether to validate game files after download
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Prepare download directory
            download_dir = Path(settings.STEAM_DOWNLOAD_PATH) / f"app_{appid}"
            download_dir.mkdir(parents=True, exist_ok=True)
            
            # Build command
            cmd = [str(self.path)]
            
            if username and password:
                cmd.extend(["+login", username, password])
                if guard_code:
                    cmd.append(guard_code)
            else:
                cmd.extend(["+login", "anonymous"])
            
            cmd.extend([
                "+force_install_dir", str(download_dir),
                "+app_update", appid
            ])
            
            if validate:
                cmd.append("validate")
            
            cmd.append("+quit")
            
            # Execute command
            logger.info("Starting download for AppID: %s", appid)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            # Check for success
            if result.returncode == 0 and "Success! App '" in result.stdout:
                return True, "Download completed successfully"
            else:
                error_msg = self._parse_error(result.stdout)
                return False, f"Download failed: {error_msg}"
                
        except Exception as e:
            logger.error("Download error for AppID %s: %s", appid, str(e))
            return False, f"Download error: {str(e)}"
    
    def _parse_error(self, output: str) -> str:
        """Parse SteamCMD output for common errors."""
        error_patterns = {
            "Invalid Password": "Invalid password provided",
            "Invalid Username": "Invalid username provided",
            "No subscription": "You don't own this game or it requires purchase",
            "Need two-factor code": "Steam Guard code required",
            "rate limited": "Too many attempts, please wait and try again"
        }
        
        for pattern, message in error_patterns.items():
            if pattern in output:
                return message
        
        return "Unknown error occurred"

# Create global instance
steam_cmd = SteamCMD() 