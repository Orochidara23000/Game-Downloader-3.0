import gradio as gr
from typing import Tuple, List, Dict, Any
from ..services.game_info import game_info_service
from ..services.downloader import download_manager
from ..core.exceptions import SteamDownloaderError

def create_game_info_component() -> Tuple[gr.components.Component, ...]:
    """Create the game information input and display components."""
    with gr.Row():
        with gr.Column():
            game_input = gr.Textbox(
                label="Game URL or ID",
                placeholder="Enter Steam game URL or ID"
            )
            check_button = gr.Button("Check Game")
        
        with gr.Column():
            game_info = gr.JSON(label="Game Information", visible=False)
            game_preview = gr.HTML(label="Game Preview")
    
    def check_game(input_text: str) -> Tuple[Dict[str, Any], str]:
        try:
            info = game_info_service.get_game_info(input_text)
            
            # Create preview HTML
            preview = f"""
            <div style="padding: 1rem; border-radius: 8px; background: #f5f5f5;">
                <h3>{info['name']}</h3>
                <img src="{info.get('header_image', '')}" style="max-width: 100%; border-radius: 4px;">
                <p>{info.get('short_description', 'No description available')}</p>
                <div style="margin-top: 1rem;">
                    <strong>Price:</strong> {'Free to Play' if info.get('is_free') else info.get('price_overview', {}).get('final_formatted', 'N/A')}
                    <br>
                    <strong>Developers:</strong> {', '.join(info.get('developers', ['Unknown']))}
                    <br>
                    <strong>Release Date:</strong> {info.get('release_date', {}).get('date', 'Unknown')}
                </div>
            </div>
            """
            
            return info, preview
            
        except SteamDownloaderError as e:
            return None, f"<div style='color: red;'>Error: {str(e)}</div>"
        except Exception as e:
            return None, f"<div style='color: red;'>Unexpected error: {str(e)}</div>"
    
    check_button.click(
        fn=check_game,
        inputs=game_input,
        outputs=[game_info, game_preview]
    )
    
    return game_input, game_info, game_preview

def create_download_form() -> Tuple[gr.components.Component, ...]:
    """Create the download form components."""
    with gr.Group():
        anonymous_login = gr.Checkbox(
            label="Use Anonymous Login (Free Games Only)",
            value=True
        )
        
        with gr.Group() as login_group:
            username = gr.Textbox(
                label="Steam Username",
                placeholder="Enter your Steam username"
            )
            password = gr.Textbox(
                label="Steam Password",
                placeholder="Enter your Steam password",
                type="password"
            )
            guard_code = gr.Textbox(
                label="Steam Guard Code (if enabled)",
                placeholder="Enter code from Steam Guard"
            )
        
        validate = gr.Checkbox(
            label="Validate Files After Download",
            value=True
        )
        
        download_button = gr.Button("Start Download")
        status = gr.Markdown()
        
        def toggle_login_fields(anonymous: bool) -> Dict[str, Any]:
            return {
                login_group: gr.update(visible=not anonymous)
            }
        
        anonymous_login.change(
            fn=toggle_login_fields,
            inputs=anonymous_login,
            outputs=login_group
        )
        
        return (anonymous_login, username, password, guard_code, 
                validate, download_button, status)

def create_downloads_tab() -> gr.components.Tab:
    """Create the downloads status tab."""
    with gr.Tab("Downloads"):
        with gr.Row():
            with gr.Column():
                active_downloads = gr.DataFrame(
                    headers=["ID", "Name", "Progress", "Status", "Speed", "ETA"],
                    label="Active Downloads"
                )
                
                queued_downloads = gr.DataFrame(
                    headers=["Position", "Name", "AppID"],
                    label="Download Queue"
                )
                
                download_history = gr.DataFrame(
                    headers=["Time", "Name", "Status"],
                    label="Download History"
                )
            
            with gr.Column():
                cancel_input = gr.Textbox(
                    label="Download ID to Cancel",
                    placeholder="Enter download ID"
                )
                cancel_button = gr.Button("Cancel Download")
                cancel_status = gr.Markdown()
                
                refresh_button = gr.Button("Refresh Status")
        
        def update_status() -> Tuple[List[List[Any]], List[List[Any]], List[List[Any]]]:
            status = download_manager.get_status()
            
            active = [
                [d.id, d.name, f"{d.progress:.1f}%", d.status, d.speed, d.eta]
                for d in status["active"]
            ]
            
            queue = [
                [i+1, d["name"], d["appid"]]
                for i, d in enumerate(status["queue"])
            ]
            
            history = [
                [h["completed_at"], h["name"], h["status"]]
                for h in status["history"]
            ]
            
            return active, queue, history
        
        def cancel_download(download_id: str) -> str:
            if download_manager.cancel_download(download_id):
                return "✅ Download cancelled successfully"
            return "❌ Download not found"
        
        refresh_button.click(
            fn=update_status,
            outputs=[active_downloads, queued_downloads, download_history]
        )
        
        cancel_button.click(
            fn=cancel_download,
            inputs=cancel_input,
            outputs=cancel_status
        )
        
        # Auto-refresh every 5 seconds
        gr.update(every=5)(
            fn=update_status,
            outputs=[active_downloads, queued_downloads, download_history]
        ) 
