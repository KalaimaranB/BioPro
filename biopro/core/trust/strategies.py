import abc
from pathlib import Path
from typing import Any

from biopro_sdk.host.trust_manager import TrustManager, VerificationResult


class ITrustStrategy(abc.ABC):
    """Abstract interface for trust verification strategies (SOLID: Open/Closed Principle)."""

    @abc.abstractmethod
    def verify(self, manifest: dict[str, Any], plugin_path: str) -> VerificationResult:
        pass


class ProjectTrustStrategy(ITrustStrategy):
    """Verifies plugins signed by a CI/CD Project Key."""

    def verify(self, manifest: dict[str, Any], plugin_path: str) -> VerificationResult:
        signed_by = manifest.get("signed_by", {})
        if signed_by.get("entity_type") != "project":
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
        signed_by = manifest.get("signed_by", {})
        if signed_by.get("entity_type") != "developer":
            return VerificationResult(
                success=False, error_message="Invalid entity type: expected 'developer'."
            )

        # Wrap the legacy TrustManager logic
        manager = TrustManager()
        result = manager.verify_plugin(Path(plugin_path))
        return result


class TrustStrategyFactory:
    """Factory to dispatch to the correct validation strategy based on Manifest V2 entity type."""

    @staticmethod
    def get_strategy(manifest: dict[str, Any]) -> ITrustStrategy:
        entity_type = manifest.get("signed_by", {}).get("entity_type")
        if entity_type == "project":
            return ProjectTrustStrategy()
        return DeveloperTrustStrategy()  # Default to developer
