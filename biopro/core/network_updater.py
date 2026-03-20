"""Background network fetcher and plugin installer for BioPro."""

import io
import json
import logging
import zipfile
from pathlib import Path
import requests
from biopro.core.config import AppConfig

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


import json
import os
import urllib.request
from pathlib import Path

class NetworkUpdater:
    def __init__(self): 
        # Grab the values directly from the config!
        self.core_version = AppConfig.CORE_VERSION
        self.registry_url = AppConfig.REGISTRY_URL
        
        self.plugin_dir = Path.home() / ".biopro" / "plugins"
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        
        # This is our local tracker file
        self.local_registry_path = self.plugin_dir / "installed.json"
        
        # Create an empty local tracker if they are a first-time user
        if not self.local_registry_path.exists():
            with open(self.local_registry_path, 'w') as f:
                json.dump({}, f)

    def get_local_state(self):
        """Reads the local tracker to see what the user already has."""
        with open(self.local_registry_path, 'r') as f:
            return json.load(f)

    def fetch_remote_registry(self, registry_url):
        """Pulls the master JSON from your GitHub repository."""
        try:
            # Using urllib to avoid needing third-party libraries in PyInstaller
            req = urllib.request.Request(registry_url, headers={'User-Agent': 'BioPro-App'})
            with urllib.request.urlopen(req, timeout=5) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            print(f"Network error fetching registry: {e}")
            return {}

    # REMOVE registry_url from the arguments here too!
    def evaluate_store_state(self): 
        # USE self.registry_url instead
        remote_data = self.fetch_remote_registry(self.registry_url) 
        local_data = self.get_local_state()
        
        store_inventory = {}
        
        plugins_data = remote_data.get("plugins", {})
        
        for plugin_id, remote_info in plugins_data.items():
            state = "INSTALL" 
            
            # 1. The Safety Lock
            if self.core_version < remote_info.get("min_core_version", "0.0.0"):
                state = "INCOMPATIBLE"
                
            # 2. Local check
            elif plugin_id in local_data:
                local_version = local_data[plugin_id].get("version", "0.0.0")
                if local_version < remote_info["version"]:
                    state = "UPDATE"
                else:
                    state = "UP_TO_DATE"
                    
            store_inventory[plugin_id] = {
                "info": remote_info,
                "state": state,
                "local_version": local_data.get(plugin_id, {}).get("version", None)
            }
            
        return store_inventory
    
    def check_for_core_updates(self): 
        """Checks if the PyInstaller Core App needs an update."""
        # USE self.registry_url instead
        remote_data = self.fetch_remote_registry(self.registry_url) 
        
        # Extract the core app data safely
        core_info = remote_data.get("core_app", {})
        remote_version = core_info.get("version", "0.0.0")
        
        if self.core_version < remote_version:
            return True, core_info
        return False, None
    
    def install_plugin(self, plugin_id, remote_info):
        """Downloads a .zip plugin package, extracts it, and updates the registry."""
        import urllib.request
        import zipfile
        import io
        import json
        import shutil

        try:
            # 1. Fetch the zip file from GitHub
            req = urllib.request.Request(remote_info['download_url'], headers={'User-Agent': 'BioPro-App'})
            with urllib.request.urlopen(req, timeout=15) as response:
                zip_bytes = response.read()
                
            # 2. Prepare the destination folder
            plugin_folder = self.plugin_dir / plugin_id
            if plugin_folder.exists():
                shutil.rmtree(plugin_folder) # Wipe the old version if updating
                
            # 3. Extract the zip into memory, then to the hard drive
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                # Note: This assumes the zip file itself contains a folder named `plugin_id`
                z.extractall(self.plugin_dir) 
                
            # 4. Update the local tracker
            local_data = self.get_local_state()
            local_data[plugin_id] = {
                "version": remote_info["version"],
                "name": remote_info["name"]
            }
            
            with open(self.local_registry_path, 'w') as f:
                json.dump(local_data, f, indent=4)
                
            return True, "Installation successful."
        except Exception as e:
            return False, f"Failed to install: {e}"

    def remove_plugin(self, plugin_id):
        """Deletes the plugin folder and removes it from the registry."""
        import json
        import shutil
        try:
            # 1. Delete the entire physical folder
            plugin_folder = self.plugin_dir / plugin_id
            if plugin_folder.exists():
                shutil.rmtree(plugin_folder)
                
            # 2. Erase the record
            local_data = self.get_local_state()
            if plugin_id in local_data:
                del local_data[plugin_id]
                
            with open(self.local_registry_path, 'w') as f:
                json.dump(local_data, f, indent=4)
                
            return True, "Plugin removed successfully."
        except Exception as e:
            return False, f"Failed to remove: {e}"