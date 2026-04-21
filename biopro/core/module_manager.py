"""Dynamic Plugin/Module Loader for BioPro."""

import importlib
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Type, Optional
from PyQt6.QtWidgets import QWidget
from biopro.sdk.core.interfaces import BioProPlugin
from biopro.core.event_bus import event_bus, BioProEvent
from biopro.core.trust_manager import TrustManager

# HACK: Import the base plugins namespace so we can expand it
import biopro.plugins

logger = logging.getLogger(__name__)

class ModuleManager:
    """Discovers, manages, and loads BioPro analysis modules dynamically."""

    def __init__(self, trust_manager: Optional[TrustManager] = None):
        # 1. The built-in plugins (baked into the PyInstaller .app)
        self.internal_plugins_dir = Path(__file__).parent.parent / "plugins"
        
        # 2. The dynamic downloaded plugins (safe from macOS code-signing blocks)
        self.user_plugins_dir = Path.home() / ".biopro" / "plugins"
        self.user_plugins_dir.mkdir(parents=True, exist_ok=True)

        # 3. THE MAGIC BULLET: Bind the user folder to the internal plugin namespace!
        if str(self.user_plugins_dir) not in biopro.plugins.__path__:
            biopro.plugins.__path__.append(str(self.user_plugins_dir))
            logger.info(f"Appended user directory to plugin namespace: {self.user_plugins_dir}")

        self.modules: Dict[str, Any] = {}
        self.trust_manager = trust_manager or TrustManager()
        self._discover_modules()
        
        # Subscribe to plugin lifecycle events (The Nervous System listening for pulses)
        event_bus.subscribe(BioProEvent.PLUGIN_INSTALLED, lambda _: self.reload_modules())
        event_bus.subscribe(BioProEvent.PLUGIN_REMOVED, lambda _: self.reload_modules())

    def _discover_modules(self) -> None:
        """Scan both internal and user plugin directories for valid manifests."""
        directories_to_scan = [self.internal_plugins_dir, self.user_plugins_dir]
        
        for directory in directories_to_scan:
            if not directory.exists():
                continue
                
            for plugin_path in directory.iterdir():
                if plugin_path.is_dir():
                    # SECURITY: Check trust but DON'T skip if failed (unless critical infrastructure fail)
                    # We want to show "Untrusted/Modified" modules so the user can 'Lock' them.
                    trust_result = self.trust_manager.verify_plugin(plugin_path)
                    
                    manifest_file = plugin_path / "manifest.json"
                    if not manifest_file.exists():
                        continue

                    try:
                        with open(manifest_file, "r") as f:
                            manifest = json.load(f)
                            
                        mod_id = manifest.get("id")
                        if not mod_id: continue
                        
                        self.modules[mod_id] = {
                            "manifest": manifest,
                            "path": plugin_path,
                            "package_name": plugin_path.name,
                            "loaded": False,
                            "plugin_ref": None,
                            "trust_level": trust_result.trust_level,
                            "trust_error": trust_result.error_message,
                            "trust_path": trust_result.trust_path,
                            "calculated_hashes": trust_result.calculated_hashes  # For snapshotting
                        }
                        
                        # Add trust level and developer metadata for UI logic
                        manifest["trust_level"] = trust_result.trust_level
                        manifest["trust_path"] = trust_result.trust_path
                        manifest["developer_name"] = trust_result.developer_name
                        manifest["developer_key"] = trust_result.developer_key
                        if not trust_result.success:
                            logger.warning(f"Plugin {mod_id} discovered in UNTRUSTED state: {trust_result.error_message}")
                            
                    except Exception as e:
                        logger.error(f"Failed to read manifest for {plugin_path.name}: {e}")

    def get_available_modules(self) -> list[dict]:
        """Return a list of manifests so the UI can build the 'Home Screen' grid."""
        return [m["manifest"] for m in self.modules.values()]

    def load_module_ui(self, module_id: str) -> Type[QWidget]:
        """Dynamically import the Python package and extract the main UI class."""
        if module_id not in self.modules:
            raise ValueError(f"Module {module_id} is not installed.")
        
        mod_info = self.modules[module_id]
        
        # Hard check: Prevent execution of untrusted code
        if mod_info["trust_level"] == "untrusted":
            raise PermissionError(f"Security Block: Cannot load untrusted module '{module_id}'. Please verify and lock changes first.")

        if mod_info["loaded"]:
            return mod_info["plugin_ref"].get_panel_class()

        package_name = f"biopro.plugins.{mod_info['package_name']}"
        try:
            plugin_module = importlib.import_module(package_name)
            
            # Perform strict contract validation (Track 1 solidification)
            if not isinstance(plugin_module, BioProPlugin):
                logger.error(f"Module {module_id} failed interface validation. Missing required hooks.")
                raise TypeError(f"Module {module_id} does not satisfy BioProPlugin protocol.")
                
            mod_info["plugin_ref"] = plugin_module
            mod_info["loaded"] = True
            return plugin_module.get_panel_class()
        except Exception as e:
            logger.exception(f"Fatal error loading module {module_id}")
            raise

    def reload_modules(self) -> None:
        """Clears the registry and rescans the disk for new/removed plugins (Hot-Reload)."""
        for mod_info in self.modules.values():
            if mod_info["loaded"]:
                prefix = f"biopro.plugins.{mod_info['package_name']}"
                # Purge Python's aggressively cached module data
                keys_to_remove = [k for k in sys.modules if k == prefix or k.startswith(f"{prefix}.")]
                for k in keys_to_remove:
                    del sys.modules[k]
                    
        self.modules.clear()
        self._discover_modules()
        logger.info(f"Hot-reloaded plugins. Currently loaded: {list(self.modules.keys())}")

    def trust_module(self, module_id: str) -> bool:
        """Manually trust the current state of a module (Verified Lock)."""
        if module_id not in self.modules:
            return False
            
        mod_info = self.modules[module_id]
        hashes = mod_info.get("calculated_hashes")
        
        if not hashes:
            # Re-verify to get fresh hashes if missing
            res = self.trust_manager.verify_plugin(mod_info["path"])
            hashes = res.calculated_hashes
            
        if hashes:
            self.trust_manager.overrides.trust_current_state(module_id, hashes)
            
            # Clear cache for this module so fresh verification runs next time
            cache = self.trust_manager._get_cache()
            if cache and module_id in cache.data:
                del cache.data[module_id]
                cache._save()
                
            logger.info(f"User manually trusted module: {module_id}")
            self.reload_modules() # Refresh everything
            return True
        return False