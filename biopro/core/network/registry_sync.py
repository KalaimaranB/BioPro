"""Local and remote registry state management."""

import logging
from pathlib import Path
from typing import Any

from biopro.core.network.client import NetworkClient
from biopro.core.network.system_assets import SystemAssetSync
from biopro.core.utils import AtomicJsonFile

logger = logging.getLogger(__name__)


class RegistrySync:
    """Handles fetching remote registries and managing the local installed.json state."""

    @staticmethod
    def get_local_state(plugin_dir: Path, local_registry_path: Path) -> Any:
        """
        Build the installed plugin state from manifests in a plugin directory.
        
        Parameters:
            plugin_dir (Path): Directory containing installed plugin directories.
            local_registry_path (Path): Path where the generated local registry state is saved.
        
        Returns:
            dict: Mapping of plugin identifiers to their names and versions.
        """
        local_state: dict = {}

        if not plugin_dir.exists():
            return local_state

        try:
            from biopro_sdk.plugin.manifest_parser import ManifestParser

            parser = ManifestParser()
        except ImportError:
            parser = None

        for item in plugin_dir.iterdir():
            if item.is_dir():
                manifest_path = item / "pyproject.toml"
                if manifest_path.exists() and parser:
                    try:
                        manifest = parser.parse_file(str(manifest_path))
                        plugin_id = manifest.get("id") or item.name
                        local_state[plugin_id] = {
                            "version": manifest.get("version", "0.0.0"),
                            "name": manifest.get("name", item.name),
                        }
                    except Exception as e:
                        logger.warning(f"Could not read pyproject.toml for {item.name}: {e}")

        if not AtomicJsonFile.save(local_registry_path, local_state):
            logger.error("Failed to sync local registry")

        return local_state

    @staticmethod
    def fetch_remote_registry(registry_url: str) -> dict:
        """
        Fetch the remote plugin registry data.
        
        Parameters:
            registry_url (str): URL of the remote registry.
        
        Returns:
            dict: Parsed registry data, or an empty dictionary if fetching fails.
        """
        try:
            response = NetworkClient.get(registry_url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            msg = f"Network error fetching registry: {e}"
            logger.error(msg, exc_info=True)
            return {}

    @staticmethod
    def fetch_remote_developers(registry_url: str) -> list:
        """
        Load developer profiles from the developers registry associated with the registry URL.
        
        Parameters:
            registry_url (str): URL of the remote plugin registry.
        
        Returns:
            list: Developer profiles, or an empty list when the data cannot be loaded.
        """
        dev_url = registry_url.replace("registry.json", "developers.json")
        try:
            response = NetworkClient.get(dev_url)
            if response.status_code == 200:
                data = response.json()
                devs_data = data.get("developers", {})
                if isinstance(devs_data, dict):
                    dev_list = []
                    for dev_id, info in devs_data.items():
                        dev_item = dict(info)
                        dev_item["developer_id"] = dev_id
                        dev_list.append(dev_item)
                    return dev_list
                if isinstance(devs_data, list):
                    return devs_data
        except Exception as e:
            logger.debug(f"Could not fetch separate developers.json, falling back: {e}")
        return []

    @staticmethod
    def evaluate_store_state(
        core_version: str, registry_url: str, plugin_dir: Path, local_registry_path: Path
    ):  # noqa: E501
        """
        Compare installed plugins with the remote registry and classify their availability and compatibility.
        
        Parameters:
            core_version (str): Current application core version.
            registry_url (str): URL of the remote plugin registry.
            plugin_dir (Path): Directory containing installed plugins.
            local_registry_path (Path): Path used to store the local registry state.
        
        Returns:
            tuple: Store inventory, trusted developer information, and the remote registry data.
        """
        remote_data = RegistrySync.fetch_remote_registry(registry_url)
        local_data = RegistrySync.get_local_state(plugin_dir, local_registry_path)
        store_inventory = {}
        plugins_data = remote_data.get("plugins", {})

        # Use the parse_version utility
        app_v = SystemAssetSync._parse_version(core_version)

        logger.info(f"Checking Store State. App Version: {core_version} (Parsed: {app_v})")

        for plugin_id, remote_info in plugins_data.items():
            state = "INSTALL"
            min_core_str = remote_info.get("min_core_version", "0.0.0")
            min_core_v = SystemAssetSync._parse_version(min_core_str)

            logger.info(
                f"Plugin {plugin_id}: MinCoreReq={min_core_str} ({min_core_v}), AppVersion={core_version} ({app_v})"  # noqa: E501
            )

            if app_v < min_core_v:
                state = "INCOMPATIBLE"
                logger.warning(f"MARKING {plugin_id} AS INCOMPATIBLE: {app_v} < {min_core_v}")
            elif plugin_id in local_data:
                local_v = SystemAssetSync._parse_version(
                    local_data[plugin_id].get("version", "0.0.0")
                )  # noqa: E501
                remote_v = SystemAssetSync._parse_version(remote_info.get("version", "0.0.0"))

                state = "UPDATE" if local_v < remote_v else "UP_TO_DATE"

            # Check if the developer is Verified
            is_verified = False
            author_id = remote_info.get("author_id", remote_info.get("author"))
            if author_id:
                roots_dir = Path.home() / ".biopro" / "trusted_roots"
                if (roots_dir / f"network_{author_id}.pub").exists():
                    is_verified = True

            store_inventory[plugin_id] = {
                "info": remote_info,
                "state": state,
                "local_version": local_data.get(plugin_id, {}).get("version", None),
                "is_verified": is_verified,
            }

        trusted_devs = RegistrySync.fetch_remote_developers(registry_url)
        if not trusted_devs:
            trusted_devs = remote_data.get("trusted_developers", [])

        return store_inventory, trusted_devs, remote_data
