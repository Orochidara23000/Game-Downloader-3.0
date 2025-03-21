import os
import sys
import logging
import gradio as gr
import time
import threading
from main import create_download_games_tab, create_library_tab, create_setup_tab, create_settings_tab
from main import setup_refresh_interval, process_download_queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)
logger.info("Starting Steam Games Downloader via app.py entry point")

# Set environment variables
os.environ["ENABLE_SHARE"] = "True"
os.environ["PORT"] = os.environ.get("PORT", "8080")

# Create and launch the application
if __name__ == "__main__":
    print("="*50)
    print("Starting Steam Games Downloader via app.py")
    print("="*50)
    
    # Initialize background threads
    try:
        download_queue_thread = threading.Thread(target=process_download_queue, daemon=True)
        download_queue_thread.start()
        logger.info("Download queue thread started")
    except Exception as e:
        logger.error(f"Error starting download queue thread: {str(e)}")
    
    # Create the interface directly instead of importing main.py
    with gr.Blocks(title="Steam Games Downloader") as app:
        gr.Markdown("# Steam Games Downloader")
        
        with gr.Tabs():
            download_tab = create_download_games_tab()
            library_tab = create_library_tab()
            setup_tab = create_setup_tab()
            settings_tab = create_settings_tab()
        
        # Set up periodic refresh for downloads
        refresh_interval = setup_refresh_interval()
        
        logger.info("Interface created, starting application...")
    
    # Launch with settings optimized for containers
    app.queue().launch(
        server_port=int(os.environ.get("PORT", 8080)),
        server_name="0.0.0.0",
        share=True,
        show_error=True,
        prevent_thread_lock=True
    )
    
    # We shouldn't reach here if prevent_thread_lock is True,
    # but just in case, add an infinite loop to keep the container alive
    logger.info("Application started. Container will stay running.")
    try:
        while True:
            time.sleep(60)
            logger.info("Application heartbeat - still running")
    except KeyboardInterrupt:
        logger.info("Application shutdown requested, exiting...") 