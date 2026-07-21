"""Dynamic Plugin/Module Loader for BioPro."""

import contextlib
import importlib
import importlib.metadata as metadata
import logging
import sys
from pathlib import Path
from typing import Any

from biopro_sdk.host import TrustManager
from biopro_sdk.plugin import BioProPlugin
from biopro_sdk.plugin.manifest_parser import ManifestParser, ManifestValidationError
from PyQt6.QtWidgets import QWidget

# HACK: Import the base plugins namespace so we can expand it
import biopro.plugins
from biopro.core.event_bus import BioProEvent, event_bus
from biopro.core.resource_manager import resource_path
from biopro.core.trust.strategies import TrustStrategyFactory

logger = logging.getLogger(__name__)


class ModuleManager:
    """Discovers, manages, and loads BioPro analysis modules dynamically."""

    def __init__(self, trust_manager: TrustManager | None = None):
        # 1. The built-in plugins (baked into the PyInstaller .app)
        self.internal_plugins_dir = resource_path("biopro/plugins")

        # 2. The dynamic downloaded plugins (safe from macOS code-signing blocks)
        self.user_plugins_dir = Path.home() / ".biopro" / "plugins"
        self.user_plugins_dir.mkdir(parents=True, exist_ok=True)

        # 3. THE MAGIC BULLET: Bind the user folder to the internal plugin namespace!
        if str(self.user_plugins_dir) not in biopro.plugins.__path__:
            biopro.plugins.__path__.append(str(self.user_plugins_dir))
            logger.info(f"Appended user directory to plugin namespace: {self.user_plugins_dir}")

        self.modules: dict[str, Any] = {}
        self.trust_manager = trust_manager or TrustManager()
        self._discover_modules()

        # Subscribe to plugin lifecycle events (The Nervous System listening for pulses)
        event_bus.subscribe(BioProEvent.PLUGIN_INSTALLED, lambda _: self.reload_modules())
        event_bus.subscribe(BioProEvent.PLUGIN_REMOVED, lambda _: self.reload_modules())

    def _discover_modules(self) -> None:
        """Scan both internal and user plugin directories for valid manifests.

        This method performs security verification for each discovered directory.
        Modules that fail verification are still registered but marked as untrusted,
        allowing the UI to prompt the user for action.
        """
        directories_to_scan = [self.internal_plugins_dir, self.user_plugins_dir]

        for directory in directories_to_scan:
            if not directory.exists():
                continue

            for plugin_path in directory.iterdir():
                if plugin_path.is_dir():
                    manifest_file = plugin_path / "manifest.json"
                    if not manifest_file.exists():
                        continue

                    try:
                        parser = ManifestParser()
                        try:
                            manifest = parser.parse_file(str(manifest_file))
                        except ManifestValidationError as e:
                            error_str = str(e)
                            if "Legacy 'author' field" in error_str:
                                try:
                                    import json

                                    with open(manifest_file, encoding="utf-8") as f:
                                        raw_manifest = json.load(f)
                                    mod_id = raw_manifest.get("id", plugin_path.name)

                                    manifest = {
                                        "id": mod_id,
                                        "name": raw_manifest.get("name", plugin_path.name),
                                        "description": "This module is outdated and must be updated.",
                                        "version": raw_manifest.get("version", "Unknown"),
                                        "trust_level": "outdated",
                                        "trust_path": None,
                                        "developer_name": "Unknown",
                                        "developer_key": "Unknown",
                                    }

                                    self.modules[mod_id] = {
                                        "manifest": manifest,
                                        "path": plugin_path,
                                        "package_name": plugin_path.name,
                                        "loaded": False,
                                        "plugin_ref": None,
                                        "trust_level": "outdated",
                                        "trust_error": error_str,
                                        "trust_path": None,
                                        "calculated_hashes": None,
                                    }
                                    continue
                                except Exception as inner_e:
                                    logger.error(f"Failed to parse outdated manifest: {inner_e}")
                                    # Fall through to normal error reporting

                            msg = f"Plugin {plugin_path.name} failed manifest validation: {e}"
                            logger.error(msg)
                            try:
                                from biopro.core.diagnostics import diagnostics

                                diagnostics.report_error(msg, exception=e)
                            except Exception:
                                pass
                            continue

                        mod_id = manifest.get("id")
                        if not mod_id:
                            continue

                        # SOLID: Dispatch to the correct trust strategy based on the manifest entity type
                        strategy = TrustStrategyFactory.get_strategy(manifest, str(plugin_path))
                        trust_result = strategy.verify(manifest, str(plugin_path))

                        self.modules[mod_id] = {
                            "manifest": manifest,
                            "path": plugin_path,
                            "package_name": plugin_path.name,
                            "loaded": False,
                            "plugin_ref": None,
                            "trust_level": trust_result.trust_level,
                            "trust_error": trust_result.error_message,
                            "trust_path": trust_result.trust_path,
                            "calculated_hashes": trust_result.calculated_hashes,
                        }

                        # Add trust level and entity metadata for UI logic
                        manifest["trust_level"] = trust_result.trust_level
                        manifest["trust_path"] = trust_result.trust_path
                        manifest["developer_name"] = trust_result.developer_name
                        manifest["developer_key"] = trust_result.developer_key
                        if not trust_result.success:
                            logger.warning(
                                f"Plugin {mod_id} discovered in UNTRUSTED state: {trust_result.error_message}"
                            )

                    except Exception as e:
                        logger.error(f"Failed to read manifest for {plugin_path.name}: {e}")
                        try:
                            from biopro.core.diagnostics import diagnostics

                            diagnostics.report_error(
                                f"Failed to read manifest for {plugin_path.name}", exception=e
                            )
                        except Exception:
                            pass

    def get_available_modules(self) -> list[dict]:
        """Return a list of manifests so the UI can build the 'Home Screen' grid."""
        return [m["manifest"] for m in self.modules.values()]

    def load_module_ui(self, module_id: str) -> type[QWidget]:
        """Dynamically import the Python package and extract the main UI class.

        Args:
            module_id (str): The unique identifier for the module from its manifest.

        Returns:
            Type[QWidget]: The class object for the module's main UI panel.

        Raises:
            ValueError: If the module is not found.
            PermissionError: If the module is untrusted and blocked by security policy.
            TypeError: If the module does not implement the required BioProPlugin interface.
        """
        if module_id not in self.modules:
            raise ValueError(f"Module {module_id} is not installed.")

        mod_info = self.modules[module_id]

        # Hard check: Prevent execution of untrusted code
        if mod_info["trust_level"] == "untrusted":
            raise PermissionError(
                f"Security Block: Cannot load untrusted module '{module_id}'. Please verify and lock changes first."
            )

        if mod_info["trust_level"] == "outdated":
            raise RuntimeError(
                f"OutdatedModuleError: The module '{mod_info['manifest'].get('name', mod_info['package_name'])}' is outdated and must be updated to work with this version of BioPro."
            )

        if mod_info["loaded"]:
            return mod_info["plugin_ref"].get_panel_class()

        logger.info(
            "Loading plugin UI: module_id=%s package=%s path=%s trust_level=%s",
            module_id,
            mod_info["package_name"],
            mod_info["path"],
            mod_info["trust_level"],
        )
        self._inject_plugin_path(mod_info["path"])

        package_name = f"biopro.plugins.{mod_info['package_name']}"
        try:
            plugin_module = importlib.import_module(package_name)

            # Perform strict contract validation (Track 1 solidification)
            # Use type: ignore because some IDEs squiggle when checking protocols against modules
            if not isinstance(plugin_module, BioProPlugin):  # type: ignore
                msg = f"Module {module_id} failed interface validation. Missing required hooks."
                logger.error(msg)
                try:
                    from biopro.core.diagnostics import diagnostics

                    diagnostics.report_error(msg)
                except Exception:
                    pass
                raise TypeError(f"Module {module_id} does not satisfy BioProPlugin protocol.")

            mod_info["plugin_ref"] = plugin_module
            mod_info["loaded"] = True
            return plugin_module.get_panel_class()
        except Exception as e:
            logger.exception(f"Fatal error loading module {module_id}")
            try:
                from biopro.core.diagnostics import diagnostics

                diagnostics.report_error(
                    f"Fatal error loading module {module_id}", exception=e, fatal=True
                )
            except Exception:
                pass
            raise

    def reload_modules(self) -> None:
        """Clears the registry and rescans the disk for new/removed plugins (Hot-Reload)."""
        for mod_info in self.modules.values():
            if mod_info["loaded"]:
                prefix = f"biopro.plugins.{mod_info['package_name']}"
                # Purge Python's aggressively cached module data
                keys_to_remove = [
                    k for k in sys.modules if k == prefix or k.startswith(f"{prefix}.")
                ]
                for k in keys_to_remove:
                    del sys.modules[k]

        self._cleanup_plugin_paths()
        self.modules.clear()
        self._discover_modules()
        logger.info(f"Hot-reloaded plugins. Currently loaded: {list(self.modules.keys())}")

    def trust_module(self, module_id: str) -> bool:
        """Manually trust the current state of a module (Verified Lock).

        Saves the current file hashes to the local trust store. This is used
        when a user wants to approve local modifications to a plugin or
        install an unverified plugin from source.

        Args:
            module_id (str): The ID of the module to trust.

        Returns:
            bool: True if the module was successfully trusted, False otherwise.
        """
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
            self.reload_modules()  # Refresh everything
            return True
        return False

    def _inject_plugin_path(self, plugin_path: Path):
        """Prepend plugin's local .plugin_venv site-packages to sys.path if it exists."""
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        candidate_paths = [
            # Unix/macOS layout: lib/pythonX.Y/site-packages
            plugin_path / ".plugin_venv" / "lib" / py_ver / "site-packages",
            plugin_path / ".venv" / "lib" / py_ver / "site-packages",
            # Windows layout: Lib/site-packages (no version subdirectory)
            plugin_path / ".plugin_venv" / "Lib" / "site-packages",
            plugin_path / ".venv" / "Lib" / "site-packages",
        ]

        selected_path = None
        for candidate in candidate_paths:
            logger.debug(
                "Checking plugin site-packages candidate: %s exists=%s",
                candidate,
                candidate.exists(),
            )
            if candidate.exists():
                selected_path = candidate
                break

        if not selected_path:
            logger.warning(
                "No plugin Python environment found for %s. Checked: %s. "
                "This usually happens if the plugin was sideloaded locally without running the Store installer, "
                "or if 'uv venv' & 'uv pip install' were never run manually by the developer.",
                plugin_path,
                ", ".join(str(p) for p in candidate_paths),
            )
            return

        # Insert the plugin site-packages before any application-bundle paths
        # so that module imports and package data resolve to the plugin's
        # environment rather than the PyInstaller app bundle.
        insert_index = 0
        try:
            app_root = str(self.internal_plugins_dir).split("biopro/plugins")[0]
            for idx, p in enumerate(sys.path):
                if p and str(p).startswith(app_root):
                    insert_index = idx
                    break
        except Exception:
            insert_index = 0

        if str(selected_path) in sys.path:
            current_idx = sys.path.index(str(selected_path))
            if current_idx > insert_index:
                # Move existing entry earlier to take precedence
                sys.path.pop(current_idx)
                sys.path.insert(insert_index, str(selected_path))
                logger.info(
                    "Moved existing plugin path earlier in sys.path: %s (to index %d)",
                    selected_path,
                    insert_index,
                )
            else:
                logger.debug(
                    "Plugin path already present on sys.path at index %d: %s",
                    current_idx,
                    selected_path,
                )
            self._log_plugin_environment(plugin_path, selected_path)
        else:
            sys.path.insert(insert_index, str(selected_path))
            logger.info(
                "Dynamically injected plugin path to sys.path at index %d: %s",
                insert_index,
                selected_path,
            )
            logger.debug("sys.path head after injection: %s", sys.path[:12])
            self._log_plugin_environment(plugin_path, selected_path)

        # --- Anti-Tamper for Scientific Libraries in PyInstaller ---
        # Bokeh explicitly looks inside sys._MEIPASS for templates if sys.frozen is True.
        # Because our plugin environment is separate from the PyInstaller bundle, we
        # temporarily lie to Python and preload bokeh templates so it binds to the
        # .plugin_venv correctly!
        was_frozen = getattr(sys, "frozen", False)
        if was_frozen:
            try:
                sys.frozen = False  # type: ignore[attr-defined]
                with contextlib.suppress(ImportError):
                    importlib.import_module("bokeh.core.templates")
            finally:
                sys.frozen = True  # type: ignore[attr-defined]

    def _log_plugin_environment(self, plugin_path: Path, site_packages: Path) -> None:
        """Log the plugin virtual environment package list and summary."""
        try:
            distributions = list(metadata.distributions(path=[str(site_packages)]))
            packages = sorted(
                [
                    (
                        dist.metadata.get("Name", dist.name),
                        dist.version,
                    )
                    for dist in distributions
                ],
                key=lambda item: item[0].lower() if item[0] else "",
            )
            logger.info(
                "Plugin environment summary: plugin=%s site_packages=%s package_count=%d",
                plugin_path.name,
                site_packages,
                len(packages),
            )
            if packages:
                package_list = ", ".join(f"{name}=={version}" for name, version in packages)
                logger.info("Plugin environment packages: %s", package_list)
            else:
                logger.warning(
                    "No installed distributions found in plugin environment: %s",
                    site_packages,
                )
        except Exception as exc:
            logger.warning(
                "Failed to enumerate plugin environment packages for %s: %s",
                site_packages,
                exc,
            )

    def _cleanup_plugin_paths(self):
        """Remove any plugin .plugin_venv paths from sys.path."""
        target_marker = str(Path(".biopro") / "plugins")
        for path in list(sys.path):
            norm_path = str(Path(path))
            if (
                target_marker in norm_path
                and (".plugin_venv" in norm_path or ".venv" in norm_path)
                and ("site-packages" in norm_path)
            ):
                sys.path.remove(path)
                logger.info(f"Cleaned up dynamic plugin path from sys.path: {path}")
