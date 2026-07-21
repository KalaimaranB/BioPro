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
        """Batch install all dependencies natively using uv into a standalone plugin venv."""
        if not dependencies:
            if progress_callback:
                progress_callback(100)
            return

        venv_dir = plugin_dir / ".plugin_venv"

        reqs = []
        for name, ver in dependencies.items():
            if ver and not ver.startswith(("=", ">", "<")):
                reqs.append(f"{name}=={ver}")
            else:
                reqs.append(f"{name}{ver}")

        uv_path = None
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            uv_name = "uv.exe" if sys.platform == "win32" else "uv"
            bundled_uv = Path(sys._MEIPASS) / "bin" / uv_name
            if bundled_uv.exists():
                uv_path = str(bundled_uv)
        if not uv_path:
            uv_path = shutil.which("uv")

        if not uv_path:
            raise RuntimeError(
                "uv is required to install plugin dependencies but was not found "
                "(bundled uv missing and not on PATH)."
            )

        logger.info(
            "Preparing plugin dependency install: venv=%s uv_path=%s req_count=%d",
            venv_dir,
            uv_path,
            len(reqs),
        )
        logger.debug("Plugin dependency requirement list: %s", reqs)

        if progress_callback:
            progress_callback(5)

        # 1. Create a real, standalone interpreter for the plugin (idempotent)
        venv_cmd = [uv_path, "venv", str(venv_dir), "--python", "3.12"]
        logger.info("Creating plugin venv: %s", " ".join(venv_cmd))
        result = subprocess.run(venv_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to create plugin venv: {result.stderr}\nCommand: {' '.join(venv_cmd)}"
            )

        # Resolve the interpreter path cross-platform.
        # Windows: <venv>/Scripts/python.exe
        # Unix/macOS: <venv>/bin/python3.12
        if sys.platform == "win32":
            venv_python = venv_dir / "Scripts" / "python.exe"
        else:
            venv_python = venv_dir / "bin" / "python3.12"

        if not venv_python.exists():
            raise RuntimeError(f"uv venv did not produce expected interpreter at {venv_python}")

        if progress_callback:
            progress_callback(15)

        # 2. Install packages into that interpreter, not into a bare directory
        install_cmd = [uv_path, "pip", "install", "--python", str(venv_python)] + reqs
        logger.info("Installing plugin dependencies: %s", " ".join(install_cmd))
        result = subprocess.run(install_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to install dependencies: {result.stderr}\nCommand: {' '.join(install_cmd)}"
            )

        # 3. Boot self-test — fail loudly here, not three steps later at file-load time
        worker_script = plugin_dir / "analysis" / "fcs_worker.py"
        if not worker_script.exists():
            raise RuntimeError(
                f"Cannot run plugin self-test — worker script not found at {worker_script}"
            )

        selftest_cmd = [str(venv_python), str(worker_script), "--selftest"]
        result = subprocess.run(selftest_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"Plugin venv self-test failed — interpreter or packages are broken: "
                f"{result.stderr.strip()}"
            )
        logger.info("Plugin venv self-test passed: %s", result.stdout.strip())

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
        import logging

        logging.getLogger(__name__).info(
            "PluginInstallerWorker initialized for %s", self.plugin_dir
        )

    def run(self):
        try:
            import logging

            logging.getLogger(__name__).info(
                "PluginInstallerWorker.run() started for %s", self.plugin_dir
            )
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
