import json
import os
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal


class PackageManager:
    """Manages the global pre-compiled package cache and user-space symlinking."""

    def __init__(self, cache_dir: Path | None = None):
        """Initialize PackageManager with a global package cache folder."""
        if cache_dir is None:
            self.cache_dir = Path.home() / ".biopro" / "cache" / "packages"
        else:
            self.cache_dir = Path(cache_dir)

        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def install_package(self, package_name: str, version: str) -> Path:
        """Securely install a package into the global cache using target isolation."""
        target_dir = self.cache_dir / f"{package_name}_{version}"
        target_dir.mkdir(parents=True, exist_ok=True)

        # Secure installation arguments preventing setup.py execution (precompiled wheels only)
        cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            f"{package_name}=={version}",
            "--target",
            str(target_dir),
            "--only-binary=:all:",
            "--no-deps",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to install package {package_name}=={version}: {result.stderr}"
            )

        return target_dir

    def link_package(self, cached_path: Path, plugin_site_packages: Path):
        """Create symbolic links inside plugin's site-packages pointing back to the cache."""
        plugin_site_packages.mkdir(parents=True, exist_ok=True)

        for item in cached_path.iterdir():
            # Skip metadata and pip directories to prevent conflicts
            if item.name.startswith(".") or "dist-info" in item.name or "egg-info" in item.name:
                continue

            target_link = plugin_site_packages / item.name
            if target_link.is_symlink() or target_link.exists():
                try:
                    if target_link.is_symlink():
                        target_link.unlink()
                    elif target_link.is_dir():
                        import shutil

                        shutil.rmtree(target_link)
                    else:
                        target_link.unlink()
                except Exception:
                    pass

            os.symlink(str(item), str(target_link))


class PluginInstallerWorker(QThread):
    """Background thread to download, cache, and link dependencies for a plugin."""

    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, plugin_dir: Path | str, cache_dir: Path | None = None):
        """Initialize the background installation worker."""
        super().__init__()
        self.plugin_dir = Path(plugin_dir)
        self.pm = PackageManager(cache_dir=cache_dir)

    def run(self):
        """Execute the installation and linking lifecycle."""
        try:
            manifest_path = self.plugin_dir / "manifest.json"
            if not manifest_path.exists():
                self.finished.emit(False, "manifest.json missing from plugin directory.")
                return

            with open(manifest_path) as f:
                manifest = json.load(f)

            dependencies = manifest.get("dependencies", {})
            if not dependencies:
                self.progress.emit(100)
                self.finished.emit(True, "")
                return

            # Determine plugin site-packages path dynamically matching Python major/minor version
            py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
            site_packages = self.plugin_dir / ".venv" / "lib" / py_ver / "site-packages"

            total_deps = len(dependencies)
            for idx, (pkg_name, pkg_version) in enumerate(dependencies.items()):
                # 1. Install to global cache
                cached_path = self.pm.install_package(pkg_name, pkg_version)

                # 2. Link inside plugin space
                self.pm.link_package(cached_path, site_packages)

                # 3. Update progress
                progress_percent = int(((idx + 1) / total_deps) * 100)
                self.progress.emit(progress_percent)

            self.finished.emit(True, "")

        except Exception as e:
            self.finished.emit(False, str(e))
