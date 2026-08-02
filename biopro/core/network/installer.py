"""Plugin installation and extraction logic."""

import logging
import os
import shutil
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_EXTRACT_MEMBERS = 10000
MAX_UNCOMPRESSED_SIZE = 500 * 1024 * 1024  # 500 MB


def safe_extract(zip_ref: zipfile.ZipFile, dest_dir: Path) -> None:
    """Safely extract archive members within the destination directory.

    Parameters:
        zip_ref (zipfile.ZipFile): Archive containing the members to extract.
        dest_dir (Path): Directory into which valid members are extracted.
    """
    dest_dir_str = os.path.abspath(dest_dir)
    infolist = zip_ref.infolist()

    if len(infolist) > MAX_EXTRACT_MEMBERS:
        raise ValueError(f"Archive exceeds maximum member limit ({MAX_EXTRACT_MEMBERS}).")

    total_size = sum(member.file_size for member in infolist)
    if total_size > MAX_UNCOMPRESSED_SIZE:
        raise ValueError(
            f"Archive exceeds maximum uncompressed size ({MAX_UNCOMPRESSED_SIZE} bytes)."
        )

    for member in infolist:
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
    """Safely removes a plugin directory, including directories containing locked files.

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
