"""System asset downloading (Themes, SDK, Docs)."""

import hashlib
import io
import logging
import shutil
import zipfile
from pathlib import Path
from typing import Any

from karcytics.core.network.client import NetworkClient
from karcytics.core.network.installer import safe_extract
from karcytics.core.utils import AtomicJsonFile, parse_version

logger = logging.getLogger(__name__)


class SystemAssetSync:
    """Manages background syncing of non-plugin assets."""

    @staticmethod
    def sync_assets(remote_data: dict[str, Any], plugin_dir: Path) -> None:
        """Synchronize newer SDK, theme, and documentation assets from remote registry metadata.

        Parameters:
            remote_data (dict[str, Any]): Remote asset metadata containing versions and download URLs.
            plugin_dir (Path): Directory containing the local system asset version tracking file.
        """  # noqa: E501
        if not remote_data:
            return

        local_assets_path = plugin_dir / "system_assets.json"
        local_assets = AtomicJsonFile.load(local_assets_path, default={})
        if not isinstance(local_assets, dict):
            local_assets = {}

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
                success = SystemAssetSync._sync_single_asset(
                    asset_key, download_url, remote_info, local_dir, remote_v
                )
                if success:
                    local_assets[asset_key] = {"version": remote_v}
                    updated_any = True

        if updated_any:
            AtomicJsonFile.save(local_assets_path, local_assets)

    @staticmethod
    def _sync_single_asset(
        asset_key: str,
        download_url: str,
        remote_info: dict[str, Any],
        local_dir: Path,
        remote_v: str,
    ) -> bool:
        """Download and extract a single system asset.

        Returns:
            True if successful, False otherwise.
        """
        try:
            response = NetworkClient.get(download_url)
            response.raise_for_status()

            content_bytes = response.content

            expected_hash = remote_info.get("sha256")
            if not expected_hash:
                logger.error(
                    f"Security Block: No sha256 hash provided for {asset_key}. "
                    "Refusing to extract unverified archive."
                )
                return False

            actual_hash = hashlib.sha256(content_bytes).hexdigest()
            if actual_hash != expected_hash:
                logger.error(
                    f"Hash mismatch for {asset_key}. Expected: {expected_hash}, got: {actual_hash}"
                )
                return False

            staging_dir = local_dir.with_name(f"{local_dir.name}.staging")
            if staging_dir.exists():
                shutil.rmtree(staging_dir)
            staging_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(io.BytesIO(content_bytes)) as z:
                safe_extract(z, staging_dir)

            # Promote staging dir
            if local_dir.is_symlink() or local_dir.is_file():
                local_dir.unlink()
            elif local_dir.exists():
                shutil.rmtree(local_dir)

            staging_dir.replace(local_dir)

            logger.info(f"Successfully updated {asset_key} to {remote_v} ✅")
            return True
        except Exception as e:
            logger.error(f"Failed to automatically update {asset_key}: {e}")
            return False
