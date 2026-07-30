"""Background network fetcher and plugin installer for BioPro (Facade)."""

import json
import logging
import os
import webbrowser
from pathlib import Path
from typing import Any

from biopro.core.config import AppConfig
from biopro.core.event_bus import BioProEvent, event_bus
from biopro.core.network.client import NetworkClient
from biopro.core.network.installer import PluginInstallerWorker, safe_extract, safe_remove
from biopro.core.network.registry_sync import RegistrySync
from biopro.core.network.system_assets import SystemAssetSync
from biopro.core.network.trust_sync import TrustSync

logger = logging.getLogger(__name__)

# Re-export for backward compatibility
PluginInstallerWorker = PluginInstallerWorker


class NetworkUpdater:
    """Facade for network operations, delegating to specialized network packages."""

    def __init__(self) -> None:
        """Documentation."""
        self.core_version = AppConfig.CORE_VERSION
        self.registry_url = AppConfig.REGISTRY_URL
        self.authority_url = AppConfig.AUTHORITY_REGISTRY_URL

        self.plugin_dir = Path.home() / ".biopro" / "plugins"
        self.plugin_dir.mkdir(parents=True, exist_ok=True)

        self.local_registry_path = self.plugin_dir / "installed.json"

        if not self.local_registry_path.exists():
            from biopro.core.utils import AtomicJsonFile

            AtomicJsonFile.save(self.local_registry_path, {})

        self.setup_developer_tools()

    def setup_developer_tools(self) -> None:
        """Ensures a copy of the signing utility is available in the plugins folder for developers."""  # noqa: E501
        try:
            signer_source = Path(__file__).parent / "sign_plugin.py"
            signer_dest = self.plugin_dir / "biopro-sign.py"

            if signer_source.exists() and (
                not signer_dest.exists()
                or os.path.getmtime(signer_source) > os.path.getmtime(signer_dest)
            ):
                import shutil

                shutil.copy(signer_source, signer_dest)
                logger.info(f"Deployed biopro-sign tool to {signer_dest}")
        except Exception as e:
            logger.warning(f"Could not deploy signing tool: {e}")

    def get_local_state(self) -> dict:
        """Documentation."""
        return RegistrySync.get_local_state(self.plugin_dir, self.local_registry_path)

    def fetch_remote_registry(self, registry_url: str) -> dict:
        """Documentation."""
        return RegistrySync.fetch_remote_registry(registry_url)

    def fetch_remote_developers(self) -> list:
        """Documentation."""
        return RegistrySync.fetch_remote_developers(self.registry_url)

    def evaluate_store_state(self) -> dict:
        """Documentation."""
        store_inventory, trusted_devs, remote_data = RegistrySync.evaluate_store_state(
            self.core_version, self.registry_url, self.plugin_dir, self.local_registry_path
        )
        self.sync_trusted_developers(trusted_devs)
        self.fetch_and_sync_authorities()
        SystemAssetSync.sync_assets(remote_data, self.plugin_dir)
        return store_inventory

    def fetch_and_sync_authorities(self) -> None:
        """Documentation."""
        TrustSync.fetch_and_sync_authorities(self.authority_url)

    def sync_trusted_developers(self, trusted_list: list) -> Any:
        """Documentation."""
        TrustSync.sync_trusted_developers(trusted_list)

    def sync_system_assets(self) -> None:
        """Documentation."""
        remote_data = self.fetch_remote_registry(self.registry_url)
        SystemAssetSync.sync_assets(remote_data, self.plugin_dir)

    def check_for_core_updates(self) -> Any:
        """Documentation."""
        remote_data = self.fetch_remote_registry(self.registry_url)
        core_info = remote_data.get("core_app", {})
        remote_version = core_info.get("version", "0.0.0")

        if SystemAssetSync._parse_version(self.core_version) < SystemAssetSync._parse_version(
            remote_version
        ):  # noqa: E501
            return True, core_info
        return False, None

    def launch_core_update_page(self) -> bool:
        """Documentation."""
        remote_data = self.fetch_remote_registry(self.registry_url)
        core_info = remote_data.get("core_app", {})
        download_url = core_info.get("download_url")

        if download_url:
            webbrowser.open_new_tab(download_url)
            return True
        return False

    def install_plugin(self, plugin_id, remote_info) -> Any:
        """Downloads a .zip plugin package, extracts it securely, and updates the registry."""
        import io
        import zipfile

        try:
            response = NetworkClient.get(remote_info["download_url"], timeout=15)
            response.raise_for_status()
            zip_bytes = response.content

            plugin_folder = self.plugin_dir / plugin_id
            safe_remove(self.plugin_dir, plugin_folder)

            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                has_nested_folder = False
                namelist = z.namelist()
                if namelist:
                    first_member = namelist[0]
                    if first_member.startswith(plugin_id + "/") or first_member.startswith(
                        plugin_id + os.sep
                    ):  # noqa: E501
                        has_nested_folder = True

                extract_target = self.plugin_dir if has_nested_folder else plugin_folder
                extract_target.mkdir(parents=True, exist_ok=True)
                safe_extract(z, extract_target)

            local_data = self.get_local_state()
            local_data[plugin_id] = {"version": remote_info["version"], "name": remote_info["name"]}

            with open(self.local_registry_path, "w", encoding="utf-8") as f:
                json.dump(local_data, f, indent=4)

            # Broadcast the installation success
            event_bus.emit(BioProEvent.PLUGIN_INSTALLED, plugin_id)

            return True, "Installation successful."
        except Exception as e:
            logger.error(f"Failed to install {plugin_id}: {e}")
            return False, f"Failed to install: {e}"

    def remove_plugin(self, plugin_id) -> Any:
        """Documentation."""
        try:
            plugin_folder = self.plugin_dir / plugin_id
            safe_remove(self.plugin_dir, plugin_folder)

            local_data = self.get_local_state()
            if plugin_id in local_data:
                del local_data[plugin_id]

            with open(self.local_registry_path, "w", encoding="utf-8") as f:
                json.dump(local_data, f, indent=4)

            # Broadcast the removal
            event_bus.emit(BioProEvent.PLUGIN_REMOVED, plugin_id)

            return True, "Plugin removed successfully."
        except Exception as e:
            return False, f"Failed to remove: {e}"
