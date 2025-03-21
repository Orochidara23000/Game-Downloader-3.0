# Steam Games Downloader

A web-based application to download Steam games using SteamCMD.

## Features

- Download games using SteamCMD
- Support for both anonymous (free games) and account-based downloads
- Queue system for multiple downloads
- Monitoring of download progress
- Easy-to-use web interface

## Deployment Options

### Local Development

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the application:
   ```
   python main.py
   ```

### Cloud Deployment

The application is designed to work in cloud environments that support Python web applications:

#### Environment Variables

- `PORT`: Port to run the application (default: 8080)
- `LOG_LEVEL`: Logging level (default: INFO)
- `STEAM_DOWNLOAD_PATH`: Path to store downloaded games (default: /data/downloads)
- `ENABLE_SHARE`: Enable Gradio sharing feature (default: True)
- `DEBUG`: Enable debug mode (default: False)

#### Hugging Face Spaces

1. Create a new Space on Hugging Face
2. Choose Gradio as the SDK
3. Upload this repository
4. The application will automatically start using app.py as the entry point

#### Other Cloud Platforms

1. Deploy to your preferred platform that supports Python
2. Make sure to set the appropriate environment variables
3. The application can be started with:
   ```
   python app.py
   ```
   or
   ```
   python main.py
   ```

## File Structure

- `main.py`: Main application code
- `app.py`: Entry point for cloud deployments
- `requirements.txt`: Required Python dependencies

## Requirements

- Python 3.10+
- SteamCMD (required for actual game downloads)
- At least 1GB of RAM
- Sufficient disk space for game downloads