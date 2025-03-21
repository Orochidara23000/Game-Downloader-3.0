#!/usr/bin/env python3
"""
SteamCMD Manager Module

This module handles all SteamCMD-related functionality including:
- Installation and verification
- Binary fixes for different environments
- Execution and command building
- Error handling and recovery
"""

import os
import sys
import platform
import logging
import subprocess
import urllib.request
import tarfile
import zipfile
import shutil
import tempfile
import stat
import time
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

class SteamCMDManager:
    """Class to manage SteamCMD installation, verification and execution"""
    
    def __init__(self, steamcmd_path=None):
        """Initialize the SteamCMD manager"""
        self.steamcmd_path = steamcmd_path or self._get_default_steamcmd_path()
        self.is_windows = platform.system() == "Windows"
        self.is_container = self._check_if_container()
        self.settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
        
        # Load settings if available
        self._load_settings()
        
        logging.info(f"SteamCMD Manager initialized with path: {self.steamcmd_path}")
        logging.info(f"Running on: {platform.system()} (Container: {self.is_container})")
    
    def _check_if_container(self):
        """Check if we're running in a container environment"""
        return os.path.exists("/.dockerenv") or os.path.exists("/var/run/docker.sock")
    
    def _get_default_steamcmd_path(self):
        """Get the default path for SteamCMD based on platform"""
        # Check common paths in containerized environments first
        container_paths = [
            "/app/steamcmd/steamcmd.sh",
            "/steamcmd/steamcmd.sh",
            "/root/steamcmd/steamcmd.sh"
        ]
        
        for path in container_paths:
            if os.path.exists(path):
                return path
        
        # Default paths based on OS
        if platform.system() == "Windows":
            return os.path.join(os.path.expanduser("~"), "steamcmd", "steamcmd.exe")
        else:  # Linux or macOS
            return os.path.join(os.path.expanduser("~"), "steamcmd", "steamcmd.sh")
    
    def _load_settings(self):
        """Load settings from settings file if it exists"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    if "steamcmd_path" in settings and settings["steamcmd_path"]:
                        self.steamcmd_path = settings["steamcmd_path"]
                        logging.info(f"Loaded SteamCMD path from settings: {self.steamcmd_path}")
            except Exception as e:
                logging.error(f"Error reading settings file: {str(e)}")
    
    def is_installed(self):
        """Check if SteamCMD is installed"""
        if not os.path.exists(self.steamcmd_path):
            logging.warning(f"SteamCMD not found at {self.steamcmd_path}")
            return False
            
        # On Linux/macOS, also check if the binary exists
        if not self.is_windows:
            steamcmd_dir = os.path.dirname(self.steamcmd_path)
            linux32_dir = os.path.join(steamcmd_dir, "linux32")
            steamcmd_binary = os.path.join(linux32_dir, "steamcmd")
            
            if not os.path.exists(steamcmd_binary):
                logging.warning(f"SteamCMD binary not found at {steamcmd_binary}")
                return False
        
        logging.info(f"SteamCMD is installed at {self.steamcmd_path}")
        return True
    
    def verify_installation(self):
        """Verify SteamCMD installation by running a simple command"""
        if not self.is_installed():
            logging.warning("SteamCMD not installed, cannot verify")
            return False
        
        try:
            logging.info("Verifying SteamCMD installation...")
            cmd = [self.steamcmd_path, "+quit"]
            
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30
            )
            
            if process.returncode == 0:
                logging.info("SteamCMD verification successful")
                return True
            else:
                logging.error(f"SteamCMD verification failed with code: {process.returncode}")
                logging.error(f"STDOUT: {process.stdout}")
                logging.error(f"STDERR: {process.stderr}")
                return False
                
        except Exception as e:
            logging.error(f"Error verifying SteamCMD: {str(e)}")
            return False
    
    def install(self):
        """Install SteamCMD based on the current platform"""
        logging.info(f"Installing SteamCMD for {platform.system()}")
        
        # Create steamcmd directory
        steamcmd_dir = os.path.dirname(self.steamcmd_path)
        os.makedirs(steamcmd_dir, exist_ok=True)
        
        try:
            if self.is_windows:
                return self._install_windows()
            else:  # Linux or macOS
                return self._install_linux()
        except Exception as e:
            logging.error(f"Failed to install SteamCMD: {str(e)}", exc_info=True)
            return False
    
    def _install_windows(self):
        """Install SteamCMD on Windows"""
        try:
            steamcmd_dir = os.path.dirname(self.steamcmd_path)
            zip_path = os.path.join(steamcmd_dir, "steamcmd.zip")
            
            # Download SteamCMD zip
            logging.info("Downloading SteamCMD for Windows...")
            urllib.request.urlretrieve(
                "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip",
                zip_path
            )
            
            # Extract the zip
            logging.info(f"Extracting SteamCMD to {steamcmd_dir}")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(steamcmd_dir)
            
            # Clean up
            os.remove(zip_path)
            
            # Verify installation
            if os.path.exists(self.steamcmd_path):
                logging.info("SteamCMD installed successfully on Windows")
                return True
            else:
                logging.error(f"SteamCMD executable not found at {self.steamcmd_path} after installation")
                return False
                
        except Exception as e:
            logging.error(f"Error installing SteamCMD on Windows: {str(e)}", exc_info=True)
            return False
    
    def _install_linux(self):
        """Install SteamCMD on Linux/macOS"""
        try:
            steamcmd_dir = os.path.dirname(self.steamcmd_path)
            os.makedirs(steamcmd_dir, exist_ok=True)
            
            # Try to install dependencies first (might fail in restricted environments)
            if not self.is_container:
                try:
                    logging.info("Installing dependencies")
                    subprocess.run("apt-get update && apt-get install -y lib32gcc-s1 lib32stdc++6 libcurl4", 
                                shell=True, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                except Exception as e:
                    logging.warning(f"Failed to install dependencies, but continuing anyway: {str(e)}")
            
            # Download SteamCMD
            tar_path = os.path.join(steamcmd_dir, "steamcmd_linux.tar.gz")
            logging.info(f"Downloading SteamCMD archive to {tar_path}")
            urllib.request.urlretrieve(
                "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz", 
                tar_path
            )
            
            # Extract the archive
            logging.info(f"Extracting SteamCMD to {steamcmd_dir}")
            with tarfile.open(tar_path, 'r:gz') as tar_ref:
                tar_ref.extractall(steamcmd_dir)
            
            # Make steamcmd.sh executable
            os.chmod(self.steamcmd_path, 0o755)
            
            # Create simplified script for containers
            if self.is_container:
                self._create_simplified_script(steamcmd_dir)
            
            # Check for the binary and fix if needed
            linux32_dir = os.path.join(steamcmd_dir, "linux32")
            if not os.path.exists(os.path.join(linux32_dir, "steamcmd")):
                logging.warning("SteamCMD binary not found in linux32 directory, attempting fix...")
                if not self._fix_missing_binary():
                    logging.error("Failed to fix SteamCMD binary")
                    return False
            
            # Clean up
            if os.path.exists(tar_path):
                os.remove(tar_path)
            
            logging.info("SteamCMD installed successfully on Linux")
            return True
            
        except Exception as e:
            logging.error(f"Error installing SteamCMD on Linux: {str(e)}", exc_info=True)
            # Try backup approach
            return self._backup_install_approach()
    
    def _create_simplified_script(self, steamcmd_dir):
        """Create a simplified steamcmd.sh script that works in restricted environments"""
        try:
            script_path = os.path.join(steamcmd_dir, "steamcmd.sh")
            logging.info(f"Creating simplified steamcmd.sh script at {script_path}")
            
            # Create the linux32 directory if it doesn't exist
            linux32_dir = os.path.join(steamcmd_dir, "linux32")
            os.makedirs(linux32_dir, exist_ok=True)
            
            # Create a simple script that just executes the binary with all arguments
            with open(script_path, 'w') as f:
                f.write('''#!/bin/bash
# Simple SteamCMD wrapper script created by SteamGames Downloader

# Directory where this script is located
STEAMCMD_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BINARY="$STEAMCMD_DIR/linux32/steamcmd"

if [ ! -f "$BINARY" ]; then
    echo "ERROR: SteamCMD binary not found at $BINARY"
    echo "Please run the application again to reinstall SteamCMD"
    exit 1
fi

# Make sure it's executable
chmod +x "$BINARY"

# Run SteamCMD with all arguments
"$BINARY" "$@"
''')
            
            # Make the script executable
            os.chmod(script_path, 0o755)
            logging.info("Successfully created simplified steamcmd.sh script")
            return True
            
        except Exception as e:
            logging.error(f"Failed to create simplified steamcmd.sh script: {str(e)}")
            return False
    
    def _fix_missing_binary(self):
        """Fix the missing steamcmd binary issue by manually extracting to the right location"""
        try:
            logging.info("Attempting to fix missing SteamCMD binary...")
            
            # Determine the SteamCMD directory
            steamcmd_dir = os.path.dirname(self.steamcmd_path)
            
            # Create linux32 directory
            linux32_dir = os.path.join(steamcmd_dir, "linux32")
            os.makedirs(linux32_dir, exist_ok=True)
            
            # Download SteamCMD archive
            tar_path = os.path.join(steamcmd_dir, "steamcmd_linux.tar.gz")
            urllib.request.urlretrieve(
                "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz", 
                tar_path
            )
            
            # Extract directly into the linux32 directory
            with tarfile.open(tar_path, 'r:gz') as tar_ref:
                for member in tar_ref.getmembers():
                    # Extract only the steamcmd file
                    if member.name == "steamcmd":
                        member.name = "steamcmd"  # Ensure correct filename
                        tar_ref.extract(member, linux32_dir)
                        # Make it executable
                        bin_path = os.path.join(linux32_dir, "steamcmd")
                        os.chmod(bin_path, 0o755)
                        logging.info(f"Extracted steamcmd binary to {bin_path}")
            
            # Clean up
            os.remove(tar_path)
            
            # Verify the binary exists
            if os.path.exists(os.path.join(linux32_dir, "steamcmd")):
                logging.info("Successfully fixed SteamCMD binary issue")
                return True
            else:
                logging.error("Failed to create SteamCMD binary")
                return False
            
        except Exception as e:
            logging.error(f"Error fixing SteamCMD binary: {str(e)}")
            return False
    
    def _backup_install_approach(self):
        """Use a different approach to get SteamCMD working when normal installation fails"""
        try:
            logging.info("Trying backup SteamCMD installation method...")
            
            # Create a temporary directory
            temp_dir = tempfile.mkdtemp()
            logging.info(f"Created temporary directory: {temp_dir}")
            
            # Download the SteamCMD archive
            steam_archive = os.path.join(temp_dir, "steamcmd.tar.gz")
            urllib.request.urlretrieve(
                "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz", 
                steam_archive
            )
            logging.info(f"Downloaded SteamCMD archive to {steam_archive}")
            
            # Extract the archive
            with tarfile.open(steam_archive, 'r:gz') as tar:
                tar.extractall(temp_dir)
            logging.info(f"Extracted SteamCMD files to {temp_dir}")
            
            # Get the actual steamcmd script path
            steamcmd_sh = os.path.join(temp_dir, "steamcmd.sh")
            
            if not os.path.exists(steamcmd_sh):
                logging.error(f"steamcmd.sh not found in {temp_dir}")
                return False
            
            # Make it executable
            os.chmod(steamcmd_sh, 0o755)
            
            # Test running it
            try:
                cmd = [steamcmd_sh, "+quit"]
                logging.info(f"Testing SteamCMD with command: {' '.join(cmd)}")
                process = subprocess.run(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=30
                )
                
                if process.returncode == 0:
                    logging.info("Backup SteamCMD installation successful")
                    
                    # Create steamcmd directory if needed
                    steamcmd_dir = os.path.dirname(self.steamcmd_path)
                    os.makedirs(steamcmd_dir, exist_ok=True)
                    
                    # Copy the working files to the steamcmd directory
                    for file in os.listdir(temp_dir):
                        src = os.path.join(temp_dir, file)
                        dst = os.path.join(steamcmd_dir, file)
                        if os.path.isfile(src):
                            shutil.copy2(src, dst)
                            # Ensure executable permissions are preserved
                            if os.access(src, os.X_OK):
                                os.chmod(dst, os.stat(dst).st_mode | stat.S_IEXEC)
                    
                    # Clean up
                    shutil.rmtree(temp_dir)
                    return True
                else:
                    logging.error(f"Backup SteamCMD test failed with code: {process.returncode}")
                    logging.error(f"STDOUT: {process.stdout}")
                    logging.error(f"STDERR: {process.stderr}")
            except Exception as e:
                logging.error(f"Error testing backup SteamCMD: {str(e)}")
            
            # Clean up
            shutil.rmtree(temp_dir)
            return False
        except Exception as e:
            logging.error(f"Error in backup SteamCMD approach: {str(e)}", exc_info=True)
            return False
    
    def run_command(self, args, target_dir=None, timeout=None):
        """Run a SteamCMD command with the given arguments"""
        if not self.is_installed():
            logging.error("SteamCMD not installed, cannot run command")
            if not self.install():
                return False, "Failed to install SteamCMD"
        
        try:
            cmd = [self.steamcmd_path]
            cmd.extend(args)
            
            logging.info(f"Running SteamCMD command: {' '.join(cmd)}")
            
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=target_dir,
                timeout=timeout
            )
            
            if process.returncode == 0:
                logging.info("SteamCMD command executed successfully")
                return True, process.stdout
            else:
                logging.error(f"SteamCMD command failed with code: {process.returncode}")
                logging.error(f"STDERR: {process.stderr}")
                return False, process.stderr
                
        except subprocess.TimeoutExpired:
            logging.error(f"SteamCMD command timed out after {timeout} seconds")
            return False, "Command timed out"
        except Exception as e:
            logging.error(f"Error running SteamCMD command: {str(e)}")
            return False, str(e)
    
    def download_game(self, appid, target_dir, validate=False, login_anonymous=True, username=None, password=None, guard_code=None):
        """Download a game using SteamCMD"""
        if not self.is_installed():
            logging.error("SteamCMD not installed, cannot download game")
            if not self.install():
                return False, "Failed to install SteamCMD"
        
        try:
            # Create target directory if it doesn't exist
            os.makedirs(target_dir, exist_ok=True)
            
            # Build command arguments
            args = []
            
            # Login information
            if login_anonymous:
                args.extend(["+login", "anonymous"])
            elif username and password:
                args.extend(["+login", username, password])
                if guard_code:
                    args.append(guard_code)
            else:
                return False, "Invalid login information"
            
            # Set installation directory
            args.extend(["+force_install_dir", target_dir])
            
            # App update command
            args.extend(["+app_update", str(appid)])
            
            # Add validate if requested
            if validate:
                args.append("validate")
            
            # Add quit command
            args.append("+quit")
            
            # Run the command
            success, output = self.run_command(args)
            
            if success:
                logging.info(f"Successfully downloaded game {appid} to {target_dir}")
                return True, "Download completed successfully"
            else:
                logging.error(f"Failed to download game {appid}: {output}")
                return False, f"Download failed: {output}"
                
        except Exception as e:
            logging.error(f"Error downloading game {appid}: {str(e)}")
            return False, str(e)

# Singleton instance for easy access
_instance = None

def get_instance(steamcmd_path=None):
    """Get the singleton instance of SteamCMDManager"""
    global _instance
    if _instance is None:
        _instance = SteamCMDManager(steamcmd_path)
    return _instance

# For direct script execution
if __name__ == "__main__":
    # Simple test
    manager = SteamCMDManager()
    if not manager.is_installed():
        print("SteamCMD not installed, installing...")
        if manager.install():
            print("SteamCMD installed successfully")
        else:
            print("Failed to install SteamCMD")
    else:
        print(f"SteamCMD already installed at {manager.steamcmd_path}")
        
    # Verify installation
    if manager.verify_installation():
        print("SteamCMD installation verified successfully")
    else:
        print("SteamCMD installation verification failed")