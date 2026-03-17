"""Dynamic Plugin/Module Loader for BioPro."""

import importlib
import json
import logging
from pathlib import Path
from typing import Dict, Any, Type

from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)

class ModuleManager:
    """Discovers, manages, and loads BioPro analysis modules dynamically."""

    def __init__(self):
        # Resolve the absolute path to the plugins directory
        self.plugins_dir = Path(__file__).parent.parent / "plugins"
        self.modules: Dict[str, Any] = {}
        self._discover_modules()

    def _discover_modules(self) -> None:
        """Scan the plugins directory for valid manifests."""
        if not self.plugins_dir.exists():
            return

        for plugin_path in self.plugins_dir.iterdir():
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