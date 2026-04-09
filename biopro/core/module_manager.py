"""Dynamic Plugin/Module Loader for BioPro."""

import importlib
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Type

from PyQt6.QtWidgets import QWidget

# HACK: Import the base plugins namespace so we can expand it
import biopro.plugins

logger = logging.getLogger(__name__)

class ModuleManager:
    """Discovers, manages, and loads BioPro analysis modules dynamically."""

    def __init__(self):
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
        self._discover_modules()

    def _discover_modules(self) -> None:
        """Scan both internal and user plugin directories for valid manifests."""
        directories_to_scan = [self.internal_plugins_dir, self.user_plugins_dir]
        
        for directory in directories_to_scan:
            if not directory.exists():
                continue
                
            for plugin_path in directory.iterdir():
                if plugin_path.is_dir():
                    manifest_file = plugin_path / "manifest.json"
                    if manifest_file.exists():
                        try:
                            with open(manifest_file, "r") as f:
                                manifest = json.load(f)
                            
                            module_id = manifest.get("id")
                            if module_id:
                                self.modules[module_id] = {
                                    "package_name": plugin_path.name,
                                    "path": plugin_path,
                                    "manifest": manifest,
                                    "loaded": False,
                                    "plugin_ref": None
                                }
                        except Exception as e:
                            logger.error(f"Failed to read manifest in {plugin_path.name}: {e}")

    def get_available_modules(self) -> list[dict]:
        """Return a list of manifests so the UI can build the 'Home Screen' grid."""
        return [m["manifest"] for m in self.modules.values()]

    def load_module_ui(self, module_id: str) -> Type[QWidget]:
        """Dynamically import the Python package and extract the main UI class."""
        if module_id not in self.modules:
            raise ValueError(f"Module {module_id} is not installed.")
        
        mod_info = self.modules[module_id]
        if mod_info["loaded"]:
            return mod_info["plugin_ref"].get_panel_class()

        package_name = f"biopro.plugins.{mod_info['package_name']}"
        try:
            plugin_module = importlib.import_module(package_name)
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