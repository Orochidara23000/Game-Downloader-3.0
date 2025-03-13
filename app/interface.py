import gradio as gr
from typing import Dict, Optional
from models import DownloadRequest, GameInfo
from downloader import download_manager
from steam_handler import steam_cmd
from utils import is_valid_game_id, extract_game_id

def create_interface() -> gr.Blocks:
    """Create the Gradio interface."""
    with gr.Blocks(title="Steam Games Downloader") as interface:
        gr.Markdown("# Steam Games Downloader")
        
        with gr.Tabs():
            with gr.Tab("Download Games"):
                with gr.Row():
                    game_input = gr.Textbox(label="Game ID or Steam Store URL")
                    anonymous_login = gr.Checkbox(label="Anonymous Login", value=True)
                
                with gr.Group(visible=False) as login_group:
                    username = gr.Textbox(label="Steam Username")
                    password = gr.Textbox(label="Steam Password", type="password")
                    steam_guard = gr.Textbox(label="Steam Guard Code (if required)")
                
                with gr.Row():
                    download_btn = gr.Button("Download Now")
                    queue_btn = gr.Button("Add to Queue")
                
                progress = gr.Progress(label="Download Progress")
                status = gr.JSON(label="Download Status")
            
            with gr.Tab("Library"):
                refresh_btn = gr.Button("Refresh Library")
                library = gr.JSON(label="Installed Games")
            
            with gr.Tab("Settings"):
                download_path = gr.Textbox(label="Download Path")
                clear_cache = gr.Button("Clear Cache")
                check_steam = gr.Button("Check SteamCMD Installation")

        # Event handlers
        def toggle_login(anonymous: bool) -> Dict:
            return {"visible": not anonymous}
        
        def validate_input(input_text: str) -> str:
            if is_valid_game_id(input_text):
                return ""
            game_id = extract_game_id(input_text)
            if game_id:
                return ""
            return "Invalid game ID or Steam store URL"

        def start_download(
            input_text: str,
            anonymous: bool,
            username: Optional[str],
            password: Optional[str],
            steam_guard: Optional[str]
        ):
            game_id = extract_game_id(input_text) if not is_valid_game_id(input_text) else int(input_text)
            
            request = DownloadRequest(
                app_id=game_id,
                anonymous=anonymous,
                username=username if not anonymous else None,
                password=password if not anonymous else None,
                steam_guard_code=steam_guard if not anonymous else None
            )
            
            game_info = GameInfo(app_id=game_id, name=f"Game {game_id}")
            download_manager.add_to_queue(game_info, None if anonymous else {
                "username": username,
                "password": password,
                "steam_guard_code": steam_guard
            })
            
            return "Download started"

        # Connect events
        anonymous_login.change(toggle_login, anonymous_login, login_group)
        game_input.change(validate_input, game_input, game_input)
        download_btn.click(
            start_download,
            [game_input, anonymous_login, username, password, steam_guard],
            status
        )

    return interface 
