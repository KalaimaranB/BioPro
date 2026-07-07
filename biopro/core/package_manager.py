import json
import logging
import os
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

    def find_installer_cmd(
        self, package_name: str, version_spec: str, target_dir: Path
    ) -> list[str]:
        """Returns the command list to install a package into target_dir."""
        # Try to find uv sidecar (bundled in PyInstaller MEIPASS, or in system PATH)
        uv_path = None
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            bundled_uv = Path(sys._MEIPASS) / "bin" / "uv"
            if bundled_uv.exists():
                uv_path = str(bundled_uv)

        if not uv_path:
            uv_path = shutil.which("uv")

        package_req = (
            f"{package_name}{version_spec}"
            if version_spec and not version_spec.startswith("=")
            else f"{package_name}=={version_spec}"
            if version_spec
            else package_name
        )

        if uv_path:
            # uv pip install
            # if frozen, sys.executable is not python. We can tell uv the python version.
            py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
            cmd = [
                uv_path,
                "pip",
                "install",
                package_req,
                "--target",
                str(target_dir),
                "--python",
                sys.executable if not getattr(sys, "frozen", False) else py_ver,
                "--no-deps",
            ]
            return cmd

        # Fallback to pip
        cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            package_req,
            "--target",
            str(target_dir),
            "--only-binary=:all:",
            "--no-deps",
        ]
        return cmd

    def install_package(self, package_name: str, version_spec: str) -> Path:
        """Securely install a package into the global cache using target isolation."""
        safe_spec = (
            version_spec.replace(">", "").replace("=", "").replace("<", "").strip()
            if version_spec
            else "latest"
        )
        target_dir = self.cache_dir / f"{package_name}_{safe_spec}"

        if target_dir.exists() and any(target_dir.iterdir()):
            logger.info(f"Package {package_name} {version_spec} is already cached.")
            return target_dir

        target_dir.mkdir(parents=True, exist_ok=True)
        cmd = self.find_installer_cmd(package_name, version_spec, target_dir)

        logger.info(f"Installing {package_name} {version_spec} with command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            shutil.rmtree(target_dir, ignore_errors=True)
            raise RuntimeError(
                f"Failed to install package {package_name} {version_spec}: {result.stderr}\nCommand: {' '.join(cmd)}"
            )

        return target_dir

    def link_package(self, cached_path: Path, plugin_site_packages: Path):
        """Create symbolic links inside plugin's site-packages pointing back to the cache."""
        plugin_site_packages.mkdir(parents=True, exist_ok=True)

        for item in cached_path.iterdir():
            # Skip metadata and pip directories to prevent conflicts
            if (
                item.name.startswith(".")
                or "dist-info" in item.name
                or "egg-info" in item.name
                or item.name == "bin"
            ):
                continue

            target_link = plugin_site_packages / item.name
            if target_link.is_symlink() or target_link.exists():
                try:
                    if target_link.is_symlink():
                        target_link.unlink()
                    elif target_link.is_dir():
                        shutil.rmtree(target_link)
                    else:
                        target_link.unlink()
                except Exception:
                    pass

            # Use absolute paths for symlinks
            os.symlink(str(item.absolute()), str(target_link.absolute()))

    def resolve_and_install_all(
        self, dependencies: dict[str, str], plugin_dir: Path, progress_callback=None
    ):
        """Batch install and link for all deps in python_dependencies."""
        if not dependencies:
            return

        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = plugin_dir / ".plugin_venv" / "lib" / py_ver / "site-packages"

        total = len(dependencies)
        for idx, (pkg_name, pkg_version) in enumerate(dependencies.items()):
            cached_path = self.install_package(pkg_name, pkg_version)
            self.link_package(cached_path, site_packages)
            if progress_callback:
                progress_callback(int(((idx + 1) / total) * 100))


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
