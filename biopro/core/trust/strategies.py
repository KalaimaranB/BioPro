"""Core module."""

import abc
from pathlib import Path
from typing import Any

from biopro_sdk.host.trust_manager import TrustManager, VerificationResult


class ITrustStrategy(abc.ABC):
    """Abstract interface for trust verification strategies (SOLID: Open/Closed Principle)."""

    @abc.abstractmethod
    def verify(self, manifest: dict[str, Any], plugin_path: str) -> VerificationResult:
        """Documentation."""
        pass


class ProjectTrustStrategy(ITrustStrategy):
    """Verifies plugins signed by a CI/CD Project Key."""

    def verify(self, manifest: dict[str, Any], plugin_path: str) -> VerificationResult:
        """Documentation."""
        # Load security.json to determine entity type
        entity_type = ""
        path_obj = Path(plugin_path)
        if path_obj.exists() and path_obj.is_dir():
            if (path_obj / "project_signature.bin").exists():
                entity_type = "project"
            else:
                security_file = path_obj / "security.json"
                if security_file.exists():
                    try:
                        from biopro.core.utils import AtomicJsonFile

                        sec_data = AtomicJsonFile.load(security_file, default={})
                        entity_type = sec_data.get("signed_by", {}).get("entity_type", "")
                    except Exception:
                        import logging

                        logging.getLogger(__name__).debug(
                            f"Failed to load security file {security_file}", exc_info=True
                        )

        # Fallback to manifest if disk check did not yield a result (e.g., in unit tests)
        if not entity_type:
            entity_type = manifest.get("signed_by", {}).get("entity_type", "project")

        if entity_type != "project":
            return VerificationResult(
                success=False, error_message="Invalid entity type: expected 'project'."
            )

        # Wrap the legacy TrustManager logic
        manager = TrustManager()
        result = manager.verify_plugin(Path(plugin_path))

        # Override the trust level for UI display clarity
        if result.success and result.trust_level == "verified_developer":
            result.trust_level = "verified_project"

        return result


class DeveloperTrustStrategy(ITrustStrategy):
    """Verifies plugins signed by an individual Developer Key."""

    def verify(self, manifest: dict[str, Any], plugin_path: str) -> VerificationResult:
        """Documentation."""
        # Load security.json to determine entity type
        entity_type = ""
        path_obj = Path(plugin_path)
        if path_obj.exists() and path_obj.is_dir():
            if (path_obj / "project_signature.bin").exists():
                entity_type = "project"
            else:
                security_file = path_obj / "security.json"
                if security_file.exists():
                    try:
                        from biopro.core.utils import AtomicJsonFile

                        sec_data = AtomicJsonFile.load(security_file, default={})
                        entity_type = sec_data.get("signed_by", {}).get("entity_type", "")
                    except Exception:
                        import logging

                        logging.getLogger(__name__).debug(
                            f"Failed to load security file {security_file}", exc_info=True
                        )

        # Fallback to manifest if disk check did not yield a result (e.g., in unit tests)
        if not entity_type:
            entity_type = manifest.get("signed_by", {}).get("entity_type", "developer")

        if entity_type != "developer":
            return VerificationResult(
                success=False, error_message="Invalid entity type: expected 'developer'."
            )

        # Wrap the legacy TrustManager logic
        manager = TrustManager()
        return manager.verify_plugin(Path(plugin_path))


class TrustStrategyFactory:
    """Factory to dispatch to the correct validation strategy based on Manifest V2 entity type."""

    @staticmethod
    def get_strategy(manifest: dict[str, Any], plugin_path: str = "") -> ITrustStrategy:
        """Documentation."""
        entity_type = ""
        if plugin_path:
            path_obj = Path(plugin_path)
            if path_obj.exists() and path_obj.is_dir():
                # If project_signature.bin exists, it's a project co-signed plugin
                if (path_obj / "project_signature.bin").exists():
                    entity_type = "project"
                else:
                    security_file = path_obj / "security.json"
                    if security_file.exists():
                        try:
                            from biopro.core.utils import AtomicJsonFile

                            sec_data = AtomicJsonFile.load(security_file, default={})
                            entity_type = sec_data.get("signed_by", {}).get("entity_type", "")
                        except Exception:
                            import logging

                            logging.getLogger(__name__).debug(
                                f"Failed to load security file {security_file}", exc_info=True
                            )

        # Fallback to manifest if disk check did not yield a result (e.g., in unit tests)
        if not entity_type:
            entity_type = manifest.get("signed_by", {}).get("entity_type", "developer")

        if entity_type == "project":
            return ProjectTrustStrategy()
        return DeveloperTrustStrategy()
