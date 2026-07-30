"""Plugin installation and extraction logic."""

import io
import logging
import os
import shutil
import zipfile
from pathlib import Path
from typing import Any

import requests
from PyQt6.QtCore import QThread, pyqtSignal

from biopro.core.network.client import NetworkClient

logger = logging.getLogger(__name__)


def safe_extract(zip_ref: zipfile.ZipFile, dest_dir: Path) -> Any:
    """
    Safely extract archive members within the destination directory.
    
    Parameters:
        zip_ref (zipfile.ZipFile): Archive containing the members to extract.
        dest_dir (Path): Directory into which valid members are extracted.
    """
    dest_dir_str = os.path.abspath(dest_dir)
    for member in zip_ref.infolist():
        # Get absolute path of extracted file
        member_target_path = os.path.abspath(os.path.join(dest_dir_str, member.filename))

        # Ensure that the resolved path is within the intended destination directory
        if not member_target_path.startswith(dest_dir_str + os.sep):
            logger.warning(
                f"Prevented directory traversal attack! Skipping file: {member.filename}"
            )
            continue

        zip_ref.extract(member, dest_dir)


def safe_remove(plugin_dir: Path, plugin_folder: Path) -> None:
    """
    Safely removes a plugin directory, including directories containing locked files.
    
    Parameters:
        plugin_dir (Path): Parent directory used to store temporary removal entries.
        plugin_folder (Path): Plugin file or directory to remove.
    
    Raises:
        RuntimeError: If the plugin directory cannot be moved for removal.
    """
    if not plugin_folder.exists():
        return

    if plugin_folder.is_symlink() or plugin_folder.is_file():
        plugin_folder.unlink()
        return

    trash_dir = plugin_dir / ".trash"
    trash_dir.mkdir(parents=True, exist_ok=True)

    import time

    trash_path = trash_dir / f"{plugin_folder.name}_{int(time.time())}"

    try:
        # Rename gets the active folder out of the way immediately, even if files are locked.
        plugin_folder.rename(trash_path)
    except OSError as e:
        raise RuntimeError(
            f"The plugin is currently locked by the system and cannot be updated. "
            f"Please restart BioPro and try again. ({e})"
        ) from e

    # Try to quietly delete the trashed folder. Locked DLLs will survive this sweep.
    shutil.rmtree(trash_path, ignore_errors=True)

    # Self-cleaning loop: Try to clean up any past trashed folders that are no longer locked
    for item in trash_dir.iterdir():
        shutil.rmtree(item, ignore_errors=True)


class PluginInstallerWorker(QThread):
    """Downloads, extracts, and installs a plugin into the user directory."""

    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, plugin_id: str, download_url: str, plugins_dir: Path):  # noqa: ARG002
        """
        Initialize a plugin installation worker using the per-user plugin directory.
        
        Parameters:
            plugin_id (str): Identifier of the plugin to install.
            download_url (str): URL of the plugin archive.
        """
        super().__init__()
        self.plugin_id = plugin_id
        self.download_url = download_url

        # Override plugins_dir to strictly use the safe user folder
        self.plugins_dir = Path.home() / ".biopro" / "plugins"

    def run(self) -> None:
        """
        Install the plugin and report progress and completion status.
        
        Download failures, invalid archives, and unexpected errors are reported through
        the completion signal with an appropriate failure message.
        """
        try:
            # 1. Ensure the user plugin directory exists
            self.plugins_dir.mkdir(parents=True, exist_ok=True)

            # 2. Download the Zip File
            self.progress.emit(10, f"Downloading {self.plugin_id}...")
            response = NetworkClient.get(self.download_url, stream=True)
            response.raise_for_status()

            # 3. Extract the Zip (Safely!)
            self.progress.emit(60, "Extracting plugin files...")
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                safe_extract(z, self.plugins_dir)

            self.progress.emit(100, "Installation complete!")
            self.finished.emit(True, f"Successfully installed {self.plugin_id}")

        except requests.RequestException as e:
            msg = f"Network error downloading plugin: {e}"
            logger.error(msg, exc_info=True)
            self.finished.emit(False, "Download failed: Check your internet connection.")
        except zipfile.BadZipFile:
            msg = "Downloaded file is not a valid zip archive."
            logger.error(msg, exc_info=True)
            self.finished.emit(False, "Installation failed: Corrupted zip file.")
        except Exception as e:
            msg = f"Unexpected error installing plugin {self.plugin_id}"
            logger.exception(msg)
            self.finished.emit(False, f"Installation error: {str(e)}")
