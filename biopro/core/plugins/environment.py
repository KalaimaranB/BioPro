"""Plugin environment path injection service."""

import importlib.metadata as metadata
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class PluginEnvironmentInjector:
    """Manages the injection of isolated .venv paths into the global sys.path."""

    @staticmethod
    def inject_path(plugin_path: Path, internal_plugins_dir: Path) -> None:  # noqa: C901
        """Prepend plugin's local .venv site-packages to sys.path if it exists."""
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        candidate_paths = [
            # Unix/macOS layout: lib/pythonX.Y/site-packages
            plugin_path / ".venv" / "lib" / py_ver / "site-packages",
            plugin_path / ".venv" / "lib" / py_ver / "site-packages",
            # Windows layout: Lib/site-packages (no version subdirectory)
            plugin_path / ".venv" / "Lib" / "site-packages",
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
                "This usually happens if the plugin was sideloaded locally without running the Store installer.",  # noqa: E501
                plugin_path,
                ", ".join(str(p) for p in candidate_paths),
            )
            return

        # Insert the plugin site-packages before any application-bundle paths
        insert_index = 0
        try:
            app_root = str(internal_plugins_dir).split("biopro/plugins")[0]
            for idx, p in enumerate(sys.path):
                if p and str(p).startswith(app_root):
                    insert_index = idx
                    break
        except Exception as e:
            logger.debug(f"Failed to find insert index in sys.path: {e}")
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
            sys.path.insert(insert_index, str(selected_path))

        # V3 Architecture: Also inject the plugin's src directory if it exists
        src_dir = plugin_path / "src"
        if src_dir.exists() and src_dir.is_dir() and str(src_dir) not in sys.path:
            sys.path.insert(insert_index, str(src_dir))
            logger.info(
                "Dynamically injected plugin src path to sys.path at index %d: %s",
                insert_index,
                src_dir,
            )

        if selected_path:
            logger.info(
                "Dynamically injected plugin path to sys.path at index %d: %s",
                insert_index,
                selected_path,
            )
            PluginEnvironmentInjector._log_plugin_environment(plugin_path, selected_path)

    @staticmethod
    def _log_plugin_environment(plugin_path: Path, site_packages: Path) -> None:
        """Log the plugin virtual environment package list and summary."""
        try:
            distributions = list(metadata.distributions(path=[str(site_packages)]))
            packages = sorted(
                [(dist.metadata.get("Name", dist.name), dist.version) for dist in distributions],
                key=lambda item: item[0].lower() if item[0] else "",
            )
            if packages:
                package_list = ", ".join(f"{name}=={version}" for name, version in packages)
                logger.info(
                    "Plugin environment packages for %s: %s", plugin_path.name, package_list
                )  # noqa: E501
        except Exception as exc:
            logger.warning(
                "Failed to enumerate plugin environment packages for %s: %s",
                site_packages,
                exc,
            )

    @staticmethod
    def cleanup_paths() -> None:
        """Remove any plugin .venv paths from sys.path."""
        target_marker = str(Path(".biopro") / "plugins")
        for path in list(sys.path):
            norm_path = str(Path(path))
            if (
                target_marker in norm_path
                and (".venv" in norm_path or ".venv" in norm_path)
                and ("site-packages" in norm_path)
            ):
                sys.path.remove(path)
                logger.info(f"Cleaned up dynamic plugin path from sys.path: {path}")
