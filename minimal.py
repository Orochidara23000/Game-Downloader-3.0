import os
import sys
import logging
import gradio as gr
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)
logger.info("Starting Steam Games Downloader - MINIMAL VERSION")

# Create a very simple interface for testing container deployment
def create_minimal_interface():
    with gr.Blocks(title="Steam Games Downloader - Minimal") as app:
        gr.Markdown("# Steam Games Downloader")
        gr.Markdown("## Container Deployment Test")
        
        with gr.Tabs():
            with gr.Tab("Download Games"):
                gr.Markdown("### This is a minimal test interface")
                gr.Markdown("If you can see this, the container is working correctly!")
                
                test_input = gr.Textbox(
                    label="Game ID",
                    placeholder="Enter a game ID (e.g., 570)",
                    info="This is just for testing"
                )
                test_button = gr.Button("Test Button")
                status = gr.Textbox(label="Status", value="Ready")
                
                # Simple test function
                def test_function(input_text):
                    logger.info(f"Test button clicked with input: {input_text}")
                    return f"Button clicked with input: {input_text}"
                
                test_button.click(
                    fn=test_function,
                    inputs=[test_input],
                    outputs=[status]
                )
        
        return app

# Main entry point
if __name__ == "__main__":
    print("="*50)
    print("Starting Steam Games Downloader - MINIMAL TEST VERSION")
    print("="*50)
    
    # Create and launch the application
    app = create_minimal_interface()
    
    # Launch with settings optimized for containers
    app.launch(
        server_port=int(os.environ.get("PORT", 8080)),
        server_name="0.0.0.0",
        share=True,
        prevent_thread_lock=True
    )
    
    # This should not be reached due to prevent_thread_lock=True
    # But adding it as a fallback to keep the container alive
    print("Application launched. Container should stay running.")
    try:
        while True:
            print(".", end="", flush=True)
            time.sleep(30)
    except KeyboardInterrupt:
        print("\nShutting down...") 