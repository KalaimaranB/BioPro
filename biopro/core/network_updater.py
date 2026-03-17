"""Background network fetcher and plugin installer for BioPro."""

import io
import json
import logging
import subprocess
import sys
import zipfile
from pathlib import Path
import requests

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)

# biopro/core/network_updater.py
REGISTRY_URL = "https://raw.githubusercontent.com/KalaimaranB/BioPro/main/registry.json"

class PluginInstallerWorker(QThread):
    """Downloads, extracts, and installs a plugin and its dependencies in the background."""
    
    # Signals to talk back to the UI safely
    progress = pyqtSignal(int, str)  # Percentage, Status Message
    finished = pyqtSignal(bool, str) # Success boolean, Final Message
    
    def __init__(self, plugin_id: str, download_url: str, plugins_dir: Path):
        super().__init__()
        self.plugin_id = plugin_id
        self.download_url = download_url
        self.plugins_dir = plugins_dir

    def run(self):
        try:
            # 1. Download the Zip File
            self.progress.emit(10, f"Downloading {self.plugin_id}...")
            response = requests.get(self.download_url, stream=True, timeout=10)
            response.raise_for_status()
            
            # 2. Extract the Zip directly into the plugins directory
            self.progress.emit(50, "Extracting files...")
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                # GitHub zips usually have a root folder (e.g., western_blot-main/)
                # We extract it, but in the future we might need to strip that root folder name
                z.extractall(self.plugins_dir)
                
            self.progress.emit(75, "Checking dependencies...")
            
            # 3. Look for requirements.txt and run PIP silently!
            # (Assuming the extracted folder matches the plugin ID for now)
            plugin_folder = self.plugins_dir / self.plugin_id.split('.')[-1]
            req_file = plugin_folder / "requirements.txt"
            
            if req_file.exists():
                self.progress.emit(85, "Installing dependencies (this may take a minute)...")
                # Run pip install securely using the exact python executable running the app
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.STDOUT
                )
                
            self.progress.emit(100, "Installation complete!")
            self.finished.emit(True, f"Successfully installed {self.plugin_id}")
            
        except requests.RequestException as e:
            logger.error(f"Network error downloading plugin: {e}")
            self.finished.emit(False, f"Download failed: Check your internet connection.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Pip install failed: {e}")
            self.finished.emit(False, f"Failed to install Python dependencies.")
        except Exception as e:
            logger.exception(f"Unexpected error installing plugin {self.plugin_id}")
            self.finished.emit(False, f"Installation error: {str(e)}")


class NetworkUpdater:
    """Manager class to fetch the registry and handle core/plugin updates."""
    
    CURRENT_CORE_VERSION = "0.1.0" # Hardcode this here or read from biopro/__init__.py
    
    @staticmethod
    def fetch_registry() -> dict:
        """Fetches the master list of available updates from GitHub."""
        try:
            # 1. We actually make the call to your GitHub repo now!
            response = requests.get(REGISTRY_URL, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to fetch live registry. ({e})")
            # Return an empty store if offline
            return {"core": {}, "modules": []}

    @classmethod
    def check_for_core_update(cls) -> dict | None:
        """Compares live core version with cloud core version."""
        registry = cls.fetch_registry()
        core_info = registry.get("core", {})
        latest_version = core_info.get("latest_version", "0.0.0")
        
        # Simple string comparison (for complex versioning, use the 'packaging' library)
        if latest_version > cls.CURRENT_CORE_VERSION:
            return core_info
        return None