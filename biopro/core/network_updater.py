"""Background network fetcher and plugin installer for BioPro."""

import io
import json
import logging
import zipfile
from pathlib import Path
import requests

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)
REGISTRY_URL = "https://kalaimaranb.github.io/BioPro-Plugins/registry.json"

class PluginInstallerWorker(QThread):
    """Downloads, extracts, and installs a plugin into the user directory."""
    
    progress = pyqtSignal(int, str)  
    finished = pyqtSignal(bool, str) 
    
    def __init__(self, plugin_id: str, download_url: str, plugins_dir: Path):
        super().__init__()
        self.plugin_id = plugin_id
        self.download_url = download_url
        
        # Override plugins_dir to strictly use the safe user folder, ignoring the source code folder
        self.plugins_dir = Path.home() / ".biopro" / "plugins"

    def run(self):
        try:
            # 1. Ensure the user plugin directory exists
            self.plugins_dir.mkdir(parents=True, exist_ok=True)

            # 2. Download the Zip File
            self.progress.emit(10, f"Downloading {self.plugin_id}...")
            response = requests.get(self.download_url, stream=True, timeout=15)
            response.raise_for_status()
            
            # 3. Extract the Zip
            self.progress.emit(60, "Extracting plugin files...")
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                # This assumes your zip file contains a root folder named exactly like the plugin
                # e.g., western_blot.zip unzips to ~/.biopro/plugins/western_blot/
                z.extractall(self.plugins_dir)
                
            self.progress.emit(100, "Installation complete!")
            self.finished.emit(True, f"Successfully installed {self.plugin_id}")
            
        except requests.RequestException as e:
            logger.error(f"Network error downloading plugin: {e}")
            self.finished.emit(False, "Download failed: Check your internet connection.")
        except zipfile.BadZipFile:
            logger.error("Downloaded file is not a valid zip archive.")
            self.finished.emit(False, "Installation failed: Corrupted zip file.")
        except Exception as e:
            logger.exception(f"Unexpected error installing plugin {self.plugin_id}")
            self.finished.emit(False, f"Installation error: {str(e)}")


class NetworkUpdater:
    """Manager class to fetch the registry and handle core/plugin updates."""
    
    CURRENT_CORE_VERSION = "0.1.0"
    
    @staticmethod
    def fetch_registry() -> dict:
        """Fetches the master list of available updates from GitHub."""
        try:
            response = requests.get(REGISTRY_URL, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to fetch live registry. ({e})")
            return {"core": {}, "modules": []}

    @classmethod
    def check_for_core_update(cls) -> dict | None:
        """Compares live core version with cloud core version."""
        registry = cls.fetch_registry()
        core_info = registry.get("core", {})
        latest_version = core_info.get("latest_version", "0.0.0")
        
        if latest_version > cls.CURRENT_CORE_VERSION:
            return core_info
        return None