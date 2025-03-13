import os
import subprocess
import logging
import requests
from pathlib import Path
from typing import Optional, Tuple, Dict
from config import settings
from models import GameInfo

logger = logging.getLogger(__name__)

class SteamCMD:
    def __init__(self):
        self.path = settings.STEAMCMD_DIR / ("steamcmd.exe" if os.name == "nt" else "steamcmd.sh")
        self._process = None
        self._logged_in = False

    def install(self) -> bool:
        """Install SteamCMD."""
        try:
            if os.name == "nt":
                return self._install_windows()
            return self._install_unix()
        except Exception as e:
            logger.error(f"Failed to install SteamCMD: {e}")
            return False

    def _install_windows(self) -> bool:
        url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
        return self._download_and_extract(url)

    def _install_unix(self) -> bool:
        url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz"
        return self._download_and_extract(url)

    def _download_and_extract(self, url: str) -> bool:
        import tarfile
        import zipfile
        
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            archive_path = settings.STEAMCMD_DIR / "steamcmd_temp"
            with open(archive_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            if url.endswith('.zip'):
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(settings.STEAMCMD_DIR)
            else:
                with tarfile.open(archive_path, 'r:gz') as tar_ref:
                    tar_ref.extractall(settings.STEAMCMD_DIR)

            os.remove(archive_path)
            self.path.chmod(0o755)
            return True

        except Exception as e:
            logger.error(f"Failed to download/extract SteamCMD: {e}")
            return False

    def login(self, username: Optional[str] = None, password: Optional[str] = None, 
              steam_guard_code: Optional[str] = None) -> bool:
        """Login to Steam."""
        try:
            cmd = [str(self.path)]
            
            if username and password:
                cmd.extend(["+login", username, password])
                if steam_guard_code:
                    cmd.append(steam_guard_code)
            else:
                cmd.append("+login anonymous")

            cmd.append("+quit")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            self._logged_in = "Login Failure" not in result.stdout
            return self._logged_in

        except Exception as e:
            logger.error(f"Steam login failed: {e}")
            return False

    def download_game(self, app_id: int, install_dir: Path) -> bool:
        """Download a Steam game."""
        try:
            cmd = [
                str(self.path),
                "+force_install_dir", str(install_dir),
                "+app_update", str(app_id),
                "validate",
                "+quit"
            ]

            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            return True

        except Exception as e:
            logger.error(f"Failed to start game download: {e}")
            return False

    def get_download_progress(self) -> Tuple[float, str]:
        """Get current download progress."""
        if not self._process:
            return 0.0, ""

        if self._process.poll() is not None:
            return 100.0, "Complete" if self._process.returncode == 0 else "Failed"

        return self._parse_progress(self._process.stdout.readline() if self._process.stdout else "")

    def _parse_progress(self, line: str) -> Tuple[float, str]:
        """Parse progress from SteamCMD output."""
        if "Progress:" in line:
            try:
                progress = float(line.split("Progress:")[1].strip().rstrip("%"))
                return progress, line.strip()
            except:
                pass
        return 0.0, line.strip()

    def cancel_download(self):
        """Cancel current download."""
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()

steam_cmd = SteamCMD() 
