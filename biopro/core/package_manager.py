"""Core module."""

import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from biopro_sdk.plugin.manifest_parser import ManifestParser
from PyQt6.QtCore import QThread, pyqtSignal

from biopro.core.config import AppConfig

logger = logging.getLogger(__name__)


class PackageManager:
    """Manages the global pre-compiled package cache and user-space symlinking."""

    def __init__(self, cache_dir: Path | None = None):
        """Initialize the package manager with the specified or default cache directory.
        
        Parameters:
            cache_dir (Path | None): Directory used to cache packages. Defaults to the application package cache directory.
        """
        if cache_dir is None:
            self.cache_dir = AppConfig.APP_DATA_DIR / "cache" / "packages"
        else:
            self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def resolve_and_install_all(  # noqa: C901, PLR0915
        self, dependencies: dict[str, str], plugin_dir: Path, progress_callback=None
    ):
        """
        Install the plugin's dependencies into its standalone virtual environment.
        
        Parameters:
            dependencies (dict[str, str]): Dependency names mapped to versions or version
                constraints.
            plugin_dir (Path): Directory containing the plugin.
            progress_callback (callable, optional): Callback receiving installation progress
                percentages.
        
        Raises:
            RuntimeError: If `uv` is unavailable or environment creation, dependency
                installation, interpreter discovery, or the plugin self-test fails.
        """
        if not dependencies:
            if progress_callback:
                progress_callback(100)
            return

        venv_dir = plugin_dir / ".venv"

        reqs = []
        for name, ver in dependencies.items():
            if ver and not ver.startswith(("=", ">", "<")):
                reqs.append(f"{name}=={ver}")
            else:
                reqs.append(f"{name}{ver}")

        # Ensure setuptools is always available since modern uv --seed omits it, breaking packages like FlowKit  # noqa: E501
        if not any(r.startswith("setuptools") for r in reqs):
            reqs.append("setuptools<71.0.0")

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

        # Hide subprocess window on Windows
        sp_kwargs: dict[str, Any] = {}
        if sys.platform == "win32":
            # subprocess.CREATE_NO_WINDOW = 0x08000000
            sp_kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

        # 1. Create a real, standalone interpreter for the plugin (idempotent)
        venv_cmd = [uv_path, "venv", str(venv_dir), "--python", "3.12", "--seed"]
        logger.info("Creating plugin venv: %s", " ".join(venv_cmd))
        result = subprocess.run(venv_cmd, capture_output=True, text=True, **sp_kwargs)
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
        result = subprocess.run(install_cmd, capture_output=True, text=True, **sp_kwargs)
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to install dependencies: {result.stderr}\nCommand: {' '.join(install_cmd)}"
            )

        # 3. Boot self-test — fail loudly here, not three steps later at file-load time
        worker_script = plugin_dir / "analysis" / "fcs_worker.py"
        if worker_script.exists():
            selftest_cmd = [str(venv_python), str(worker_script), "--selftest"]
            result = subprocess.run(selftest_cmd, capture_output=True, text=True, **sp_kwargs)
            if result.returncode != 0:
                raise RuntimeError(
                    f"Plugin venv self-test failed — interpreter or packages are broken: "
                    f"{result.stderr.strip()}"
                )
            logger.info("Plugin venv self-test passed: %s", result.stdout.strip())
        else:
            logger.info(f"No self-test script found at {worker_script}, skipping self-test.")

        if progress_callback:
            progress_callback(100)


class PluginInstallerWorker(QThread):
    """Background thread to download, cache, and link dependencies for a plugin."""

    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, plugin_dir: Path | str, cache_dir: Path | None = None):
        """
        Initialize the worker for installing dependencies in a plugin directory.
        
        Parameters:
            plugin_dir (Path | str): Directory containing the plugin.
            cache_dir (Path | None): Optional directory for the package cache.
        """
        super().__init__()
        self.plugin_dir = Path(plugin_dir)
        self.pm = PackageManager(cache_dir=cache_dir)
        import logging

        logging.getLogger(__name__).info(
            "PluginInstallerWorker initialized for %s", self.plugin_dir
        )

    def run(self) -> Any:
        """
        Parse the plugin manifest and install its declared Python dependencies.
        
        Emits progress updates during installation and signals completion with success
        or failure status. Missing or invalid manifests and installation errors are
        reported through the completion signal.
        """
        try:
            import logging

            logging.getLogger(__name__).info(
                "PluginInstallerWorker.run() started for %s", self.plugin_dir
            )
            manifest_path = self.plugin_dir / "pyproject.toml"
            if not manifest_path.exists():
                self.finished.emit(False, "pyproject.toml missing from plugin directory.")
                return

            try:
                parser = ManifestParser()
                manifest = parser.parse_file(manifest_path)
            except Exception as e:
                self.finished.emit(False, f"Failed to parse pyproject.toml: {e}")
                return

            # Use python_dependencies, fallback to core_dependencies for legacy
            dependencies = manifest.get("python_dependencies")
            if dependencies is None:
                deps_list = manifest.get("core_dependencies", [])
                dependencies = dict.fromkeys(deps_list, "")

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
