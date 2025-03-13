import re
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import requests
from ..core.config import settings
from ..core.exceptions import GameNotFoundError, NetworkError

logger = logging.getLogger(__name__)

class GameInfoService:
    def __init__(self):
        self.cache_dir = Path(settings.CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_game_info(self, game_input: str) -> Dict[str, Any]:
        """
        Get game information from Steam API or cache.
        
        Args:
            game_input: Game ID, URL, or name
            
        Returns:
            Dict containing game information
        """
        appid = self.parse_game_input(game_input)
        if not appid:
            raise GameNotFoundError(f"Could not extract AppID from: {game_input}")
        
        # Check cache first
        cached_info = self._get_cached_info(appid)
        if cached_info:
            return cached_info
        
        # Fetch from API
        try:
            url = f"{settings.STEAM_API_URL}/appdetails"
            params = {"appids": appid}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if not data[appid]["success"]:
                raise GameNotFoundError(f"Game with AppID {appid} not found")
            
            game_info = data[appid]["data"]
            
            # Cache the result
            self._cache_info(appid, game_info)
            
            return game_info
            
        except requests.RequestException as e:
            raise NetworkError(f"Failed to fetch game info: {str(e)}")
    
    def parse_game_input(self, game_input: str) -> Optional[str]:
        """Extract AppID from various input formats."""
        # Direct AppID
        if game_input.isdigit():
            return game_input
        
        # Steam URL
        url_patterns = [
            r'store\.steampowered\.com/app/(\d+)',
            r'steamcommunity\.com/app/(\d+)',
            r'/app/(\d+)'
        ]
        
        for pattern in url_patterns:
            match = re.search(pattern, game_input)
            if match:
                return match.group(1)
        
        return None
    
    def _get_cached_info(self, appid: str) -> Optional[Dict[str, Any]]:
        """Get cached game information if available."""
        cache_file = self.cache_dir / f"game_{appid}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Failed to read cache: %s", str(e))
                return None
        return None
    
    def _cache_info(self, appid: str, info: Dict[str, Any]) -> None:
        """Cache game information."""
        cache_file = self.cache_dir / f"game_{appid}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(info, f)
        except Exception as e:
            logger.warning("Failed to cache game info: %s", str(e))

# Create global instance
game_info_service = GameInfoService() 