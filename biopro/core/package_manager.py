import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class PackageManager:
    """Manages the global pre-compiled package cache and user-space symlinking."""

    def __init__(self, cache_dir: Path | None = None):
        """Initialize PackageManager with a global package cache folder."""
        if cache_dir is None:
            self.cache_dir = Path.home() / ".biopro" / "cache" / "packages"
        else:
            self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def resolve_and_install_all(
        self, dependencies: dict[str, str], plugin_dir: Path, progress_callback=None
    ):
        """Batch install all dependencies natively using uv or pip into the plugin venv."""
        if not dependencies:
            if progress_callback:
                progress_callback(100)
            return

        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = plugin_dir / ".plugin_venv" / "lib" / py_ver / "site-packages"
        site_packages.mkdir(parents=True, exist_ok=True)

        reqs = []
        for name, ver in dependencies.items():
            if (
                ver
                and not ver.startswith("=")
                and not ver.startswith(">")
                and not ver.startswith("<")
            ):
                reqs.append(f"{name}=={ver}")
            else:
                reqs.append(f"{name}{ver}")

        uv_path = None
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            bundled_uv = Path(sys._MEIPASS) / "bin" / "uv"
            if bundled_uv.exists():
                uv_path = str(bundled_uv)

        if not uv_path:
            uv_path = shutil.which("uv")

        logger.info(
            "Preparing plugin dependency install: target=%s uv_path=%s req_count=%d",
            site_packages,
            uv_path or "<none>",
            len(reqs),
        )
        logger.debug("Plugin dependency requirement list: %s", reqs)

        if uv_path:
            cmd = [
                uv_path,
                "pip",
                "install",
                "--target",
                str(site_packages),
                "--python",
                sys.executable
                if not getattr(sys, "frozen", False)
                else f"{sys.version_info.major}.{sys.version_info.minor}",
            ] + reqs
        else:
            cmd = [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--target",
                str(site_packages),
            ] + reqs

        if progress_callback:
            progress_callback(10)

        logger.info("Installing plugin dependencies natively: %s", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to install dependencies: {result.stderr}\nCommand: {' '.join(cmd)}"
            )

        if progress_callback:
            progress_callback(100)


class PluginInstallerWorker(QThread):
    """Background thread to download, cache, and link dependencies for a plugin."""

    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, plugin_dir: Path | str, cache_dir: Path | None = None):
        super().__init__()
        self.plugin_dir = Path(plugin_dir)
        self.pm = PackageManager(cache_dir=cache_dir)

    def run(self):
        try:
            manifest_path = self.plugin_dir / "manifest.json"
            if not manifest_path.exists():
                self.finished.emit(False, "manifest.json missing from plugin directory.")
                return

            with open(manifest_path) as f:
                manifest = json.load(f)

            # Use python_dependencies, fallback to core_dependencies for legacy
            dependencies = manifest.get("python_dependencies")
            if dependencies is None:
                deps_list = manifest.get("core_dependencies", [])
                dependencies = {dep: "" for dep in deps_list}

            if not dependencies:
                self.progress.emit(100)
                self.finished.emit(True, "")
                return

            self.pm.resolve_and_install_all(
                dependencies, self.plugin_dir, lambda p: self.progress.emit(p)
            )
            self.finished.emit(True, "")

        except Exception as e:
            logger.error(f"Plugin dependency installation failed: {e}", exc_info=True)
            self.finished.emit(False, str(e))
