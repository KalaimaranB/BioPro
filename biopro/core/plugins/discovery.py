"""Plugin discovery and manifest parsing service."""

import logging
from pathlib import Path
from typing import Any

from biopro_sdk.plugin.manifest_parser import ManifestParser, ManifestValidationError

from biopro.core.trust.strategies import TrustStrategyFactory
from biopro.core.utils import AtomicJsonFile

logger = logging.getLogger(__name__)


class PluginDiscoveryService:
    """Handles directory scanning, manifest validation, and trust verification."""

    @staticmethod
    def _load_manifest(manifest_path: Path) -> dict[str, Any] | None:
        """Load and parse a plugin manifest from the specified file.

        Parameters:
                manifest_path (Path): Path to the plugin manifest file.

        Returns:
                dict[str, Any] | None: The parsed manifest, or `None` if parsing fails.
        """
        try:
            parser = ManifestParser()
            return parser.parse_file(str(manifest_path))
        except Exception:
            return None

    @staticmethod
    def discover_modules(internal_dir: Path, user_dir: Path) -> dict[str, dict[str, Any]]:  # noqa: C901
        """Discovers plugins in internal and user directories and collects trust metadata.

        Parameters:
                internal_dir (Path): Directory containing built-in plugins.
                user_dir (Path): Directory containing user-installed plugins.

        Returns:
                dict[str, dict[str, Any]]: Mapping of plugin IDs to manifest, path, loading, and
                trust metadata.
        """
        modules: dict[str, dict[str, Any]] = {}
        directories_to_scan = [internal_dir, user_dir]

        for directory in directories_to_scan:
            if not directory.exists():
                continue

            for plugin_path in directory.iterdir():
                if plugin_path.is_dir():
                    manifest_file = plugin_path / "pyproject.toml"
                    if not manifest_file.exists():
                        continue

                    try:
                        parser = ManifestParser()
                        try:
                            manifest = parser.parse_file(str(manifest_file))
                        except ManifestValidationError as e:
                            error_str = str(e)
                            if "Legacy 'author' field" in error_str:
                                mod_id, mod_info = PluginDiscoveryService._handle_legacy_manifest(
                                    plugin_path, manifest_file, error_str
                                )
                                if mod_id and mod_info:
                                    from typing import cast

                                    modules[mod_id] = cast(dict[str, Any], mod_info)
                                continue

                            msg = f"Plugin {plugin_path.name} failed manifest validation: {e}"
                            logger.warning(msg)
                            continue

                        mod_id = manifest.get("id")
                        if not mod_id:
                            continue

                        # Dispatch to the correct trust strategy
                        strategy = TrustStrategyFactory.get_strategy(manifest, str(plugin_path))
                        trust_result = strategy.verify(manifest, str(plugin_path))

                        modules[mod_id] = {
                            "manifest": manifest,
                            "path": plugin_path,
                            "package_name": plugin_path.name,
                            "loaded": False,
                            "plugin_ref": None,
                            "trust_level": trust_result.trust_level,
                            "trust_error": trust_result.error_message,
                            "trust_path": trust_result.trust_path,
                            "calculated_hashes": trust_result.calculated_hashes,
                        }

                        # Add metadata for UI
                        manifest["trust_level"] = trust_result.trust_level
                        manifest["trust_path"] = trust_result.trust_path
                        manifest["developer_name"] = trust_result.developer_name
                        manifest["developer_key"] = trust_result.developer_key

                        if not trust_result.success:
                            logger.warning(
                                f"Plugin {mod_id} discovered in UNTRUSTED state: {trust_result.error_message}"  # noqa: E501
                            )

                    except Exception as e:
                        logger.error(
                            f"Failed to read manifest for {plugin_path.name}: {e}", exc_info=True
                        )

        return modules

    @staticmethod
    def _handle_legacy_manifest(
        plugin_path: Path, manifest_file: Path, error_str: str
    ) -> tuple[str, dict] | tuple[None, None]:  # noqa: E501
        """Create module metadata for a legacy manifest using the outdated V1 author format.

        Parameters:
            plugin_path (Path): Path to the plugin directory.
            manifest_file (Path): Path to the legacy manifest file.
            error_str (str): Manifest validation error associated with the legacy format.

        Returns:
            tuple[str, dict] | tuple[None, None]: The module identifier and outdated module
            metadata, or `(None, None)` if the legacy manifest cannot be processed.
        """
        try:
            raw_manifest = AtomicJsonFile.load(manifest_file, default={})
            mod_id = raw_manifest.get("id", plugin_path.name)

            manifest = {
                "id": mod_id,
                "name": raw_manifest.get("name", plugin_path.name),
                "description": "This module is outdated and must be updated.",
                "version": raw_manifest.get("version", "Unknown"),
                "trust_level": "outdated",
                "trust_path": None,
                "developer_name": "Unknown",
                "developer_key": "Unknown",
            }

            mod_info = {
                "manifest": manifest,
                "path": plugin_path,
                "package_name": plugin_path.name,
                "loaded": False,
                "plugin_ref": None,
                "trust_level": "outdated",
                "trust_error": error_str,
                "trust_path": None,
                "calculated_hashes": None,
            }
            return mod_id, mod_info
        except Exception as inner_e:
            logger.error(f"Failed to parse outdated manifest: {inner_e}")
            return None, None
