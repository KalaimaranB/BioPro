"""Background network fetcher and plugin installer for BioPro."""

import io
import json
import logging
import zipfile
import os
import shutil
from pathlib import Path
import requests
import certifi
from biopro.core.config import AppConfig
from biopro.core.event_bus import event_bus, BioProEvent

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)

def _safe_extract(zip_ref: zipfile.ZipFile, dest_dir: Path):
    """
    Safely extract zip files preventing Zip Slip (path traversal) vulnerabilities.
    """
    dest_dir_str = os.path.abspath(dest_dir)
    for member in zip_ref.infolist():
        # Get absolute path of extracted file
        member_target_path = os.path.abspath(os.path.join(dest_dir_str, member.filename))
        
        # Ensure that the resolved path is within the intended destination directory
        if not member_target_path.startswith(dest_dir_str + os.sep):
            logger.warning(f"Prevented directory traversal attack! Skipping file: {member.filename}")
            continue
            
        zip_ref.extract(member, dest_dir)


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
            # Use certifi.where() for PyInstaller compatibility
            response = requests.get(self.download_url, stream=True, timeout=15, verify=certifi.where())
            response.raise_for_status()
            
            # 3. Extract the Zip (Safely!)
            self.progress.emit(60, "Extracting plugin files...")
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                _safe_extract(z, self.plugins_dir)
                
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
    def __init__(self): 
        self.core_version = AppConfig.CORE_VERSION
        self.registry_url = AppConfig.REGISTRY_URL
        self.authority_url = AppConfig.AUTHORITY_REGISTRY_URL
        
        self.plugin_dir = Path.home() / ".biopro" / "plugins"
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        
        self.local_registry_path = self.plugin_dir / "installed.json"
        
        if not self.local_registry_path.exists():
            with open(self.local_registry_path, 'w') as f:
                json.dump({}, f)
                
        self.setup_developer_tools()

    def setup_developer_tools(self):
        """Ensures a copy of the signing utility is available in the plugins folder for developers."""
        try:
            signer_source = Path(__file__).parent / "sign_plugin.py"
            signer_dest = self.plugin_dir / "biopro-sign.py"
            
            if signer_source.exists():
                # Only copy if it doesn't exist or we have a newer version
                if not signer_dest.exists() or os.path.getmtime(signer_source) > os.path.getmtime(signer_dest):
                    import shutil
                    shutil.copy(signer_source, signer_dest)
                    logger.info(f"Deployed biopro-sign tool to {signer_dest}")
        except Exception as e:
            logger.warning(f"Could not deploy signing tool: {e}")

    def get_local_state(self):
        """
        Scans the plugin directory for actual manifest files to determine current state.
        This ensures that manually updated or locally developed plugins are correctly identified.
        """
        local_state = {}
        
        # 1. Scan the plugin directory for subfolders
        if not self.plugin_dir.exists():
            return local_state
            
        for item in self.plugin_dir.iterdir():
            if item.is_dir():
                manifest_path = item / "manifest.json"
                if manifest_path.exists():
                    try:
                        with open(manifest_path, 'r') as f:
                            manifest = json.load(f)
                            plugin_id = manifest.get("id") or item.name
                            local_state[plugin_id] = {
                                "version": manifest.get("version", "0.0.0"),
                                "name": manifest.get("name", item.name)
                            }
                    except Exception as e:
                        logger.warning(f"Could not read manifest for {item.name}: {e}")
        
        # 2. Sync back to installed.json for consistency (legacy support)
        try:
            with open(self.local_registry_path, 'w') as f:
                json.dump(local_state, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to sync local registry: {e}")
            
        return local_state

    def fetch_remote_registry(self, registry_url):
        """Pulls the master JSON from your GitHub repository using requests with certifi."""
        try:
            import time
            # Cache-busting: force GitHub to bypass their CDN cache
            registry_url = f"{registry_url}?t={int(time.time())}"
            
            headers = {'User-Agent': 'BioPro-App', 'Cache-Control': 'no-cache'}
            response = requests.get(registry_url, timeout=5, headers=headers, verify=certifi.where())
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Network error fetching registry: {e}")
            return {}

    def _parse_version(self, v_str: str) -> tuple:
        """Converts a version string like '1.0.4' into a comparable tuple (1, 0, 4)."""
        try:
            # Handle empty or non-string inputs
            if not v_str or not isinstance(v_str, str):
                return (0, 0, 0)
            # Remove any non-numeric suffixes (like -alpha, -beta) for comparison
            clean_v = v_str.split('-')[0]
            return tuple(map(int, clean_v.split('.')))
        except (ValueError, AttributeError):
            return (0, 0, 0)

    def evaluate_store_state(self): 
        remote_data = self.fetch_remote_registry(self.registry_url) 
        local_data = self.get_local_state()
        store_inventory = {}
        plugins_data = remote_data.get("plugins", {})
        app_v = self._parse_version(self.core_version)
        
        logger.info(f"Checking Store State. App Version: {self.core_version} (Parsed: {app_v})")
        
        for plugin_id, remote_info in plugins_data.items():
            state = "INSTALL" 
            min_core_str = remote_info.get("min_core_version", "0.0.0")
            min_core_v = self._parse_version(min_core_str)
            
            logger.info(f"Plugin {plugin_id}: MinCoreReq={min_core_str} ({min_core_v}), AppVersion={self.core_version} ({app_v})")
            
            if app_v < min_core_v:
                state = "INCOMPATIBLE"
                logger.warning(f"MARKING {plugin_id} AS INCOMPATIBLE: {app_v} < {min_core_v}")
            elif plugin_id in local_data:
                local_v = self._parse_version(local_data[plugin_id].get("version", "0.0.0"))
                remote_v = self._parse_version(remote_info.get("version", "0.0.0"))
                
                if local_v < remote_v:
                    state = "UPDATE"
                else:
                    state = "UP_TO_DATE"
                    
            # 4. Check if the developer is Verified
            is_verified = False
            author_id = remote_info.get("author_id", remote_info.get("author"))
            if author_id:
                roots_dir = Path.home() / ".biopro" / "trusted_roots"
                if (roots_dir / f"network_{author_id}.pub").exists():
                    is_verified = True

            store_inventory[plugin_id] = {
                "info": remote_info,
                "state": state,
                "local_version": local_data.get(plugin_id, {}).get("version", None),
                "is_verified": is_verified
            }
            
        self.sync_trusted_developers(remote_data.get("trusted_developers", []))
        self.fetch_and_sync_authorities() 
        return store_inventory
    
    def fetch_and_sync_authorities(self):
        """Pulls the separate authorities JSON and syncs them to local storage."""
        if not self.authority_url:
            return
            
        try:
            headers = {'User-Agent': 'BioPro-App'}
            response = requests.get(self.authority_url, timeout=5, headers=headers, verify=certifi.where())
            
            # If the authority registry is missing (404), just skip it silently.
            # This prevents noisy logs in environments where the authority repo hasn't been set up yet.
            if response.status_code == 404:
                return
                
            response.raise_for_status()
            remote_data = response.json()
            authorities = remote_data.get("authorities", [])
            
            if authorities:
                self._sync_keys(authorities, prefix="auth_")
        except Exception as e:
            # Only log actual network failures, not 404s
            logger.debug(f"Optional authority registry not available: {e}")

    def _sync_keys(self, trusted_list: list, prefix: str = "network_"):
        """Generic key syncing logic used by both plugins and authority registries."""
        roots_dir = Path.home() / ".biopro" / "trusted_roots"
        roots_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Identify current network keys for this prefix
        existing_keys = list(roots_dir.glob(f"{prefix}*.pub"))
        new_filenames = []
        
        for entity in trusted_list:
            entity_id = entity.get("id") or entity.get("developer_id")
            pub_hex = entity.get("public_key")
            
            if not entity_id or not pub_hex:
                continue
                
            filename = roots_dir / f"{prefix}{entity_id}.pub"
            new_filenames.append(filename)
            
            try:
                # Save raw bytes
                with open(filename, "wb") as f:
                    f.write(bytes.fromhex(pub_hex))
            except Exception as e:
                logger.error(f"Failed to sync key for {entity_id}: {e}")
        
        # 2. Cleanup
        for old_key in existing_keys:
            if old_key not in new_filenames:
                try:
                    old_key.unlink()
                except Exception:
                    pass

    def sync_trusted_developers(self, trusted_list: list):
        """Maintained for backward compatibility but routes to generic sync."""
        self._sync_keys(trusted_list, prefix="network_")
    
    def check_for_core_updates(self): 
        remote_data = self.fetch_remote_registry(self.registry_url) 
        core_info = remote_data.get("core_app", {})
        remote_version = core_info.get("version", "0.0.0")
        
        if self.core_version < remote_version:
            return True, core_info
        return False, None
        
    def launch_core_update_page(self) -> bool:
        import webbrowser
        remote_data = self.fetch_remote_registry(self.registry_url) 
        core_info = remote_data.get("core_app", {})
        download_url = core_info.get("download_url")
        
        if download_url:
            webbrowser.open_new_tab(download_url)
            return True
        return False
    
    def install_plugin(self, plugin_id, remote_info):
        """Downloads a .zip plugin package, extracts it securely, and updates the registry."""
        try:
            headers = {'User-Agent': 'BioPro-App'}
            response = requests.get(remote_info['download_url'], timeout=15, headers=headers, verify=certifi.where())
            response.raise_for_status()
            zip_bytes = response.content
                
            plugin_folder = self.plugin_dir / plugin_id
            if plugin_folder.exists():
                shutil.rmtree(plugin_folder)
                
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                _safe_extract(z, self.plugin_dir)
                
            local_data = self.get_local_state()
            local_data[plugin_id] = {
                "version": remote_info["version"],
                "name": remote_info["name"]
            }
            
            with open(self.local_registry_path, 'w') as f:
                json.dump(local_data, f, indent=4)
            
            # Broadcast the installation success (The Nervous System sends a pulse)
            event_bus.emit(BioProEvent.PLUGIN_INSTALLED, plugin_id)
                
            return True, "Installation successful."
        except Exception as e:
            logger.error(f"Failed to install {plugin_id}: {e}")
            return False, f"Failed to install: {e}"

    def remove_plugin(self, plugin_id):
        try:
            plugin_folder = self.plugin_dir / plugin_id
            if plugin_folder.exists():
                shutil.rmtree(plugin_folder)
                
            local_data = self.get_local_state()
            if plugin_id in local_data:
                del local_data[plugin_id]
                
            with open(self.local_registry_path, 'w') as f:
                json.dump(local_data, f, indent=4)
            
            # Broadcast the removal
            event_bus.emit(BioProEvent.PLUGIN_REMOVED, plugin_id)
                
            return True, "Plugin removed successfully."
        except Exception as e:
            return False, f"Failed to remove: {e}"