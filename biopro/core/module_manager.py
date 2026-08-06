"""Dynamic Plugin/Module Loader for BioPro (Facade)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from biopro_sdk.host import TrustManager

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget

# HACK: Import the base plugins namespace so we can expand it
import biopro.plugins
from biopro.core.event_bus import BioProEvent, event_bus
from biopro.core.plugins.discovery import PluginDiscoveryService
from biopro.core.plugins.environment import PluginEnvironmentInjector
from biopro.core.plugins.loader import PluginLoaderFactory
from biopro.core.resource_manager import resource_path

logger = logging.getLogger(__name__)


class ModuleManager:
    """Discovers, manages, and loads BioPro analysis modules dynamically."""

    def __init__(self, trust_manager: TrustManager | None = None):
        """Initialize module manager with plugin directories and lifecycle subscriptions.

        Parameters:
            trust_manager (TrustManager | None): Trust manager to use, or None to create a default
            manager.
        """
        # 1. The built-in plugins (baked into the PyInstaller .app)
        self.internal_plugins_dir = resource_path("biopro/plugins")

        # 2. The dynamic downloaded plugins (safe from macOS code-signing blocks)
        self.user_plugins_dir = Path.home() / ".biopro" / "plugins"
        self.user_plugins_dir.mkdir(parents=True, exist_ok=True)

        # 3. Bind the user folder to the internal plugin namespace
        if str(self.user_plugins_dir) not in biopro.plugins.__path__:
            biopro.plugins.__path__.append(str(self.user_plugins_dir))
            logger.info(f"Appended user directory to plugin namespace: {self.user_plugins_dir}")

        self.modules: dict[str, Any] = {}
        self.trust_manager = trust_manager or TrustManager()
        self._discover_modules()

        # Subscribe to plugin lifecycle events
        event_bus.subscribe(BioProEvent.PLUGIN_INSTALLED, lambda _: self.reload_modules())
        event_bus.subscribe(BioProEvent.PLUGIN_REMOVED, lambda _: self.reload_modules())

    def _discover_modules(self) -> None:
        """Discover available modules from the internal and user plugin directories."""
        discovered = PluginDiscoveryService.discover_modules(
            self.internal_plugins_dir, self.user_plugins_dir
        )
        self.modules.update(discovered)

    def get_available_modules(self) -> list[dict]:
        """Return the manifests for all discovered modules.

        Returns:
                list[dict]: The available module manifests.
        """
        return [m["manifest"] for m in self.modules.values()]

    def load_module_ui(self, module_id: str) -> type[QWidget] | None:
        """Load the user interface class for an installed and trusted module.

        Parameters:
            module_id (str): Identifier of the module to load.

        Returns:
            type[QWidget] | None: The module's UI class, or `None` when no UI class is available.

        Raises:
            ValueError: If the module is not installed.
            PermissionError: If the module is untrusted.
            RuntimeError: If the module is outdated.
        """
        if module_id not in self.modules:
            raise ValueError(f"Module {module_id} is not installed.")

        mod_info = self.modules[module_id]

        # Hard check: Prevent execution of untrusted code
        if mod_info["trust_level"] == "untrusted":
            raise PermissionError(
                f"Security Block: Cannot load untrusted module '{module_id}'. Please verify and lock changes first."  # noqa: E501
            )

        if mod_info["trust_level"] == "outdated":
            raise RuntimeError(
                f"OutdatedModuleError: The module '{mod_info['manifest'].get('name', mod_info['package_name'])}' is outdated and must be updated to work with this version of BioPro."  # noqa: E501
            )

        # Verify Environment Exists
        PluginLoaderFactory.verify_dependencies(Path(mod_info["path"]), mod_info["manifest"])

        # Inject path dynamically before loading
        site_packages = PluginEnvironmentInjector.inject_path(
            Path(mod_info["path"]), self.internal_plugins_dir
        )

        # Force any of this plugin's dependencies already shadowed by a stale
        # sys.modules entry (e.g. a partial copy claimed by the frozen core
        # bundle) to re-resolve from the plugin's own environment.
        purged: list[str] = []
        if site_packages is not None:
            purged = PluginEnvironmentInjector.enforce_priority(
                Path(mod_info["path"]), site_packages
            )

        # Load the UI safely
        result = PluginLoaderFactory.load_ui(module_id, mod_info)

        # If a collision was found and purged above, confirm the plugin's own import
        # actually landed correctly. If it's still shadowed, purging sys.modules alone
        # couldn't fix it (most likely a frozen sys.meta_path importer reclaiming the
        # name) — that's an environment problem the plugin cannot self-correct, so it
        # must be surfaced loudly rather than left to silently degrade.
        if purged and site_packages is not None:
            still_shadowed = PluginEnvironmentInjector.verify_isolation(purged, site_packages)
            if still_shadowed:
                logger.error(
                    "Plugin '%s' dependencies %s still resolve outside its own "
                    "environment after isolation was enforced — likely bundled into the "
                    "application itself. Affected features may misbehave.",
                    module_id,
                    still_shadowed,
                )
                try:
                    from biopro.core.diagnostics import diagnostics

                    diagnostics.report_error(
                        f"Plugin '{module_id}' could not fully isolate its dependencies "
                        f"({', '.join(still_shadowed)}) from the application. Some features "
                        f"in this plugin may not work correctly.",
                        fatal=True,
                    )
                except ImportError:
                    pass

        return result

    def reload_modules(self) -> None:
        """Refreshes the plugin registry to reflect installed, removed, or updated plugins."""
        for mod_info in self.modules.values():
            if mod_info["loaded"]:
                prefix = f"biopro.plugins.{mod_info['package_name']}"
                keys_to_remove = [
                    k for k in sys.modules if k == prefix or k.startswith(f"{prefix}.")
                ]
                for k in keys_to_remove:
                    del sys.modules[k]

        PluginEnvironmentInjector.cleanup_paths()
        self.modules.clear()
        self._discover_modules()
        logger.info(f"Hot-reloaded plugins. Currently loaded: {list(self.modules.keys())}")

    def trust_module(self, module_id: str) -> bool:
        """Manually trusts the module's current state.

        Parameters:
                module_id (str): Identifier of the module to trust.

        Returns:
                bool: `True` if the module is trusted, `False` if it is unavailable or its state
                cannot be verified.
        """
        if module_id not in self.modules:
            return False

        mod_info = self.modules[module_id]
        hashes = mod_info.get("calculated_hashes")

        if not hashes:
            res = self.trust_manager.verify_plugin(mod_info["path"])
            hashes = res.calculated_hashes

        if hashes:
            self.trust_manager.overrides.trust_current_state(module_id, hashes)
            cache = self.trust_manager._get_cache()
            if cache and module_id in cache.data:
                del cache.data[module_id]
                cache._save()

            logger.info(f"User manually trusted module: {module_id}")
            self.reload_modules()
            return True
        return False
