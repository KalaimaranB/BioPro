from unittest.mock import MagicMock, patch

from biopro_sdk.host.trust_manager import VerificationResult

from biopro.core.trust.strategies import DeveloperTrustStrategy, ProjectTrustStrategy


def test_project_trust_strategy_validates_successfully():
    """TDD test to ensure ProjectTrustStrategy correctly implements ITrustStrategy."""
    strategy = ProjectTrustStrategy()

    mock_manifest = {"signed_by": {"entity_type": "project", "entity_id": "test_bot"}}

    mock_manager = MagicMock()
    mock_manager.verify_plugin.return_value = VerificationResult(
        success=True, trust_level="verified_project"
    )

    with patch("biopro.core.trust.strategies.TrustManager", return_value=mock_manager):
        result = strategy.verify(mock_manifest, "/fake/plugin/path")

    assert result.success is True
    assert result.trust_level == "verified_project"


def test_developer_trust_strategy_validates_successfully():
    """TDD test for legacy/developer strategy."""
    strategy = DeveloperTrustStrategy()

    mock_manifest = {"signed_by": {"entity_type": "developer", "entity_id": "alice"}}

    mock_manager = MagicMock()
    mock_manager.verify_plugin.return_value = VerificationResult(
        success=True, trust_level="verified_developer"
    )

    with patch("biopro.core.trust.strategies.TrustManager", return_value=mock_manager):
        result = strategy.verify(mock_manifest, "/fake/plugin/path")

    assert result.success is True
    assert result.trust_level == "verified_developer"


def test_project_trust_strategy_rejects_wrong_entity():
    strategy = ProjectTrustStrategy()
    mock_manifest = {"signed_by": {"entity_type": "developer", "entity_id": "alice"}}
    result = strategy.verify(mock_manifest, "/fake/plugin/path")
    assert result.success is False
    assert "Invalid entity type" in result.error_message
