"""Dynamic plugin instantiation and architecture routing."""

import contextlib
import importlib
import logging
import sys
from pathlib import Path
from typing import Any

from karcytics_sdk.plugin import KarcyticsPlugin
from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def isolate_frozen_environment() -> Any:
    """Temporarily disables the PyInstaller frozen state while executing a context.

    The original state is restored when the context exits.

    Yields:
        None
    """
    was_frozen = getattr(sys, "frozen", False)
    if was_frozen:
        logger.debug("Temporarily suspending sys.frozen state to load external dependencies.")
        sys.frozen = False  # type: ignore[attr-defined]
    try:
        yield
    finally:
        if was_frozen:
            sys.frozen = True  # type: ignore[attr-defined]


class PluginLoaderFactory:
    """Instantiates plugin UI classes based on their architecture (V2 vs V3)."""

    @staticmethod
    def load_ui(module_id: str, mod_info: dict[str, Any]) -> type[QWidget] | None:
        """Load a plugin and obtain its UI panel class.

        Parameters:
            module_id (str): Identifier used to locate and report the plugin.
            mod_info (dict[str, Any]): Plugin metadata and mutable loading state.

        Returns:
            type[QWidget] | None: The plugin's UI panel class, or `None` when initialization
                fails with an exception that is contained by the loader.

        Raises:
            TypeError: If the plugin does not satisfy the required interface.
            ValueError: If plugin metadata or its entry point is invalid.
            PermissionError: If loading is denied.
        """
        if mod_info.get("manifest", {}).get("process_model") == "isolated":
            return PluginLoaderFactory._load_ui_isolated(module_id)

        if mod_info["loaded"]:
            return mod_info["plugin_ref"].get_panel_class()

        logger.info(
            "Loading plugin UI: module_id=%s package=%s path=%s trust_level=%s",
            module_id,
            mod_info["package_name"],
            mod_info["path"],
            mod_info["trust_level"],
        )

        try:
            manifest_dict = mod_info.get("manifest", {})

            with isolate_frozen_environment():
                if "entry_point" in manifest_dict:
                    # V3 Architecture with entry point and PluginContext
                    from karcytics_sdk.plugin.context import PluginContext
                    from karcytics_sdk.plugin.manifest import PluginManifest

                    from karcytics.core.task_scheduler import task_scheduler

                    services = {
                        "task_scheduler": task_scheduler,
                        "logger": logging.getLogger(f"plugin.{module_id}"),
                        "event_bus": None,
                    }

                    pm = PluginManifest(
                        name=manifest_dict.get("name", module_id),
                        entry_point=manifest_dict["entry_point"],
                        sdk_version=manifest_dict.get("sdk_version", "2.0"),
                        requires=manifest_dict.get("requires", []),
                    )
                    context = PluginContext(services=services, manifest=pm)

                    module_name, func_name = manifest_dict["entry_point"].split(":")
                    plugin_module = importlib.import_module(module_name)
                    init_func = getattr(plugin_module, func_name)
                    plugin_instance = init_func(context)
                    mod_info["plugin_ref"] = plugin_instance
                else:
                    # V2 Legacy Architecture
                    package_name = f"karcytics.plugins.{mod_info['package_name']}"
                    plugin_module = importlib.import_module(package_name)

                    # Perform strict contract validation
                    if not isinstance(plugin_module, KarcyticsPlugin):  # type: ignore
                        msg = f"Module {module_id} failed interface validation. Missing required hooks."  # noqa: E501
                        logger.error(msg)
                        raise TypeError(msg)

                    mod_info["plugin_ref"] = plugin_module

            mod_info["loaded"] = True
            mod_info["status"] = "OK"
            return mod_info["plugin_ref"].get_panel_class()

        except Exception as e:
            logger.error(f"Fatal error loading module {module_id}: {e}", exc_info=True)
            mod_info["loaded"] = False
            mod_info["status"] = "FAILED"
            if isinstance(e, (TypeError, ValueError, PermissionError)):
                raise

            # Exception Containment: Do not crash the application if a plugin fails to initialize
            return None

    @staticmethod
    def _load_ui_isolated(module_id: str) -> type[QWidget]:
        """Return a zero-arg factory for module_id's status widget.

        Deliberately does none of what the in-process path above does:
        no `importlib.import_module` of the plugin's package, no
        `PluginEnvironmentInjector` path injection, no `sys.modules`
        bookkeeping — an isolated module's own code never enters the Hub's
        interpreter at all. `PluginUIDaemon.get_instance(module_id)` is a
        singleton keyed by plugin_id, so calling this repeatedly (e.g. the
        user re-opens an already-running module) reconnects to the same
        daemon rather than spawning a second one.

        Returns a callable rather than a literal `type[QWidget]` — callers
        already invoke this value as `PanelClass()` with no arguments, which
        a zero-arg closure satisfies identically.
        """
        from karcytics_sdk.host.module_status_widget import ModuleStatusWidget
        from karcytics_sdk.plugin.daemon import PluginUIDaemon

        def _factory() -> QWidget:
            daemon = PluginUIDaemon.get_instance(module_id)
            return ModuleStatusWidget(daemon, module_name=module_id)

        return _factory  # type: ignore[return-value]

    @staticmethod
    def verify_dependencies(plugin_path: Path, manifest: dict) -> None:
        """Verify that the plugin's isolated Python environment is available.

        Parameters:
            plugin_path (Path): Path to the plugin directory.
            manifest (dict): Plugin manifest used to identify the plugin in error messages.

        Raises:
            RuntimeError: If the plugin's Python environment cannot be found.
        """
        venv = plugin_path / ".venv"
        deps_missing = True
        candidates = []
        if sys.platform == "win32":
            candidates.append(venv / "Scripts" / "python.exe")
        else:
            major, minor = sys.version_info.major, sys.version_info.minor
            candidates.append(venv / "bin" / f"python{major}.{minor}")
            candidates.append(venv / "bin" / "python3")

        for c in candidates:
            if c.exists():
                deps_missing = False
                break

        if deps_missing:
            raise RuntimeError(
                f"DependencyMissingError: The plugin '{manifest.get('name', 'Unknown')}' "
                f"is missing its Python environment. Please reinstall the plugin from the Store to repair it."  # noqa: E501
            )
