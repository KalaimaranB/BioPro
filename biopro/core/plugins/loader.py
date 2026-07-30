"""Dynamic plugin instantiation and architecture routing."""

import contextlib
import importlib
import logging
import sys
from pathlib import Path
from typing import Any

from biopro_sdk.plugin import BioProPlugin
from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def isolate_frozen_environment() -> Any:
    """Temporarily suspends the PyInstaller 'frozen' state during dynamic imports.

    This is a fundamental fix for scientific libraries (Bokeh, Matplotlib, SciPy, etc.)
    that explicitly look inside the PyInstaller `sys._MEIPASS` bundle for their static
    assets (templates, DLLs, CSS) when `sys.frozen` is True.

    Because our plugins live in external, isolated `.venv` directories, those libraries
    crash when looking in the wrong place. By temporarily setting `sys.frozen = False`,
    we force all imported libraries to use standard `__file__` relative paths, correctly
    locating their assets inside the plugin's `.venv`.
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
        """Dynamically imports the package and returns the UI class."""
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
                    from biopro_sdk.plugin.context import PluginContext
                    from biopro_sdk.plugin.manifest import PluginManifest

                    from biopro.core.task_scheduler import task_scheduler

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
                    package_name = f"biopro.plugins.{mod_info['package_name']}"
                    plugin_module = importlib.import_module(package_name)

                    # Perform strict contract validation
                    if not isinstance(plugin_module, BioProPlugin):  # type: ignore
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
    def verify_dependencies(plugin_path: Path, manifest: dict) -> None:
        """Verifies if the virtual environment exists before attempting to load."""
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
