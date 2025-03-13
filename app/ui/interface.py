import gradio as gr
from .components import (
    create_game_info_component,
    create_download_form,
    create_downloads_tab
)
from ..core.config import settings

def create_interface() -> gr.Blocks:
    """Create the main Gradio interface."""
    with gr.Blocks(title=settings.APP_NAME) as app:
        gr.Markdown(f"# {settings.APP_NAME}")
        
        with gr.Tabs():
            with gr.Tab("Download Games"):
                # Game info section
                game_input, game_info, game_preview = create_game_info_component()
                
                # Download form
                (anonymous_login, username, password, guard_code,
                 validate, download_button, download_status) = create_download_form()
                
                def handle_download(
                    game_input: str,
                    anonymous: bool,
                    username: str,
                    password: str,
                    guard_code: str,
                    validate: bool,
                    game_info: dict
                ) -> str:
                    if not game_info:
                        return "❌ Please check game information first"
                    
                    if not anonymous and (not username or not password):
                        return "❌ Username and password required for non-anonymous downloads"
                    
                    try:
                        download_id = download_manager.start_download(
                            appid=game_info["steam_appid"],
                            name=game_info["name"],
                            username=None if anonymous else username,
                            password=None if anonymous else password,
                            guard_code=guard_code,
                            validate=validate
                        )
                        
                        return f"✅ Download started with ID: {download_id}"
                    except Exception as e:
                        return f"❌ Error: {str(e)}"
                
                download_button.click(
                    fn=handle_download,
                    inputs=[
                        game_input,
                        anonymous_login,
                        username,
                        password,
                        guard_code,
                        validate,
                        game_info
                    ],
                    outputs=download_status
                )
            
            # Downloads status tab
            create_downloads_tab()
            
            with gr.Tab("Settings"):
                gr.Markdown("## Application Settings")
                
                with gr.Row():
                    with gr.Column():
                        download_path = gr.Textbox(
                            label="Download Path",
                            value=settings.STEAM_DOWNLOAD_PATH,
                            interactive=False
                        )
                        max_downloads = gr.Slider(
                            label="Maximum Concurrent Downloads",
                            minimum=1,
                            maximum=5,
                            value=settings.MAX_CONCURRENT_DOWNLOADS,
                            step=1
                        )
                    
                    with gr.Column():
                        log_level = gr.Dropdown(
                            label="Log Level",
                            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                            value=settings.LOG_LEVEL
                        )
                        keep_history = gr.Checkbox(
                            label="Keep Download History",
                            value=True
                        )
    
    return app 
