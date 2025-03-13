from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any
import psutil
from datetime import datetime
from ..services.downloader import download_manager
from ..services.game_info import game_info_service
from ..core.exceptions import SteamDownloaderError
from . import schemas

router = APIRouter()

@router.post("/downloads", response_model=Dict[str, str])
async def start_download(request: schemas.DownloadRequest) -> Dict[str, str]:
    """Start a new download."""
    try:
        # Get game info first
        game_info = game_info_service.get_game_info(request.game_input)
        
        # Start download
        download_id = download_manager.start_download(
            appid=game_info["steam_appid"],
            name=game_info["name"],
            username=None if request.anonymous else request.username,
            password=None if request.anonymous else request.password,
            guard_code=request.guard_code,
            validate=request.validate
        )
        
        return {"download_id": download_id, "message": "Download started successfully"}
        
    except SteamDownloaderError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/downloads", response_model=schemas.DownloadStatusResponse)
async def get_downloads() -> schemas.DownloadStatusResponse:
    """Get status of all downloads."""
    try:
        return download_manager.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/downloads/{download_id}")
async def cancel_download(download_id: str) -> Dict[str, str]:
    """Cancel a download."""
    if download_manager.cancel_download(download_id):
        return {"message": f"Download {download_id} cancelled successfully"}
    raise HTTPException(status_code=404, detail="Download not found")

@router.get("/games/{game_input}", response_model=schemas.GameInfo)
async def get_game_info(game_input: str) -> schemas.GameInfo:
    """Get information about a game."""
    try:
        game_info = game_info_service.get_game_info(game_input)
        return schemas.GameInfo(**game_info)
    except SteamDownloaderError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/system", response_model=schemas.SystemStatus)
async def get_system_status() -> schemas.SystemStatus:
    """Get system status information."""
    try:
        status = download_manager.get_status()
        return schemas.SystemStatus(
            cpu_usage=psutil.cpu_percent(),
            memory_usage=psutil.virtual_memory().percent,
            disk_usage=psutil.disk_usage('/').percent,
            download_speed="N/A",  # TODO: Implement network speed monitoring
            uptime=str(datetime.now() - datetime.fromtimestamp(psutil.boot_time())),
            active_downloads=len(status["active"]),
            queued_downloads=len(status["queue"])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
