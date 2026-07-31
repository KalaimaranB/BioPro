"""System asset downloading (Themes, SDK, Docs)."""

import io
import logging
import shutil
import zipfile
from pathlib import Path

from biopro.core.network.client import NetworkClient
from biopro.core.network.installer import safe_extract
from biopro.core.utils import AtomicJsonFile, parse_version

logger = logging.getLogger(__name__)


class SystemAssetSync:
    """Manages background syncing of non-plugin assets."""

    @staticmethod
    def sync_assets(remote_data: dict, plugin_dir: Path) -> None:
        """Synchronize newer SDK, theme, and documentation assets from remote registry metadata.

        Parameters:
            remote_data (dict): Remote asset metadata containing versions and download URLs.
            plugin_dir (Path): Directory containing the local system asset version tracking file.
        """  # noqa: E501
        if not remote_data:
            return

        local_assets_path = plugin_dir / "system_assets.json"
        local_assets = AtomicJsonFile.load(local_assets_path, default={})

        # Asset types to sync automatically
        system_types = {
            "sdk": Path.home() / ".biopro" / "sdk",
            "themes": Path.home() / ".biopro" / "themes",
            "docs": Path.home() / ".biopro" / "docs",
        }

        updated_any = False

        for asset_key, local_dir in system_types.items():
            remote_info = remote_data.get(asset_key)
            if not remote_info:
                continue

            remote_v = remote_info.get("version", "0.0.0")
            local_v = local_assets.get(asset_key, {}).get("version", "0.0.0")

            if parse_version(local_v) < parse_version(remote_v):
                download_url = remote_info.get("download_url")
                if not download_url:
                    continue

                logger.info(
                    f"Automatically updating {asset_key} from version {local_v} to {remote_v}..."
                )
                try:
                    response = NetworkClient.get(download_url)
                    response.raise_for_status()

                    # Clean local dir and extract securely
                    if local_dir.is_symlink() or local_dir.is_file():
                        local_dir.unlink()
                    elif local_dir.exists():
                        shutil.rmtree(local_dir)
                    local_dir.mkdir(parents=True, exist_ok=True)

                    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                        safe_extract(z, local_dir)

                    # Update local tracking
                    local_assets[asset_key] = {"version": remote_v}
                    updated_any = True
                    logger.info(f"Successfully updated {asset_key} to {remote_v} ✅")
                except Exception as e:
                    logger.error(f"Failed to automatically update {asset_key}: {e}")

        if updated_any:
            AtomicJsonFile.save(local_assets_path, local_assets)
