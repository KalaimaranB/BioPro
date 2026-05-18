"""Unit tests for the centralized Developer Database, Avatar Cache, and UI helpers."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Note: We will import these new classes in Phase 2. For now, our TDD tests
# define the expected interface contract.
# We will use mock/patch or stub implementations to ensure the tests scaffold the spec.


class TestDeveloperDatabase:
    @pytest.fixture
    def temp_env(self, tmp_path):
        """Creates a temporary isolated test environment representing home configuration."""
        config_dir = tmp_path / ".biopro"
        config_dir.mkdir()
        avatar_dir = config_dir / "avatars"
        avatar_dir.mkdir()

        db_file = config_dir / "trusted_developers.json"

        return {
            "config_dir": config_dir,
            "avatar_dir": avatar_dir,
            "db_file": db_file,
        }

    def test_database_persistence(self, temp_env):
        """Verifies that DeveloperProfileDatabase saves and loads profiles correctly from disk."""
        from biopro.core.developer_database import DeveloperProfileDatabase

        db = DeveloperProfileDatabase(db_file=temp_env["db_file"])

        profiles = [
            {
                "developer_id": "Kalaimaran",
                "name": "Kalaimaran Balasothy",
                "role": "Founder & Lead Architect",
                "avatar_url": "https://example.com/kalaimaran.png",
                "description": "Creator of BioPro.",
                "public_key": "83b2b0f7a243105dd83fb71d8353ea4d965e264f74bc7088dd783af05a63ec9a",
            }
        ]

        # Save profiles
        db.save_profiles(profiles)
        assert temp_env["db_file"].exists()

        # Re-load to assert persistence
        new_db = DeveloperProfileDatabase(db_file=temp_env["db_file"])
        loaded = new_db.get_profile("Kalaimaran")

        assert loaded is not None
        assert loaded["name"] == "Kalaimaran Balasothy"
        assert loaded["role"] == "Founder & Lead Architect"

    def test_database_graceful_defaults(self, temp_env):
        """Verifies that querying a non-existent developer ID returns a consistent default profile structure."""
        from biopro.core.developer_database import DeveloperProfileDatabase

        db = DeveloperProfileDatabase(db_file=temp_env["db_file"])

        default_profile = db.get_profile("UnknownDev")
        assert default_profile is not None
        assert default_profile["developer_id"] == "UnknownDev"
        assert "Developer" in default_profile["name"]
        assert default_profile["role"] == "Verified Contributor"
        assert default_profile["avatar_url"] is None

    @patch("requests.get")
    def test_avatar_manager_caching(self, mock_get, temp_env):
        """Verifies that AvatarManager downloads remote image binaries and caches them locally."""
        from biopro.core.developer_database import AvatarManager

        # Mock successful HTTP image payload
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR..."  # Dummy PNG bytes
        mock_get.return_return = mock_response
        mock_get.return_value = mock_response

        manager = AvatarManager(avatar_dir=temp_env["avatar_dir"])

        avatar_url = "https://example.com/avatars/kalaimaran.png"
        cached_path = manager.fetch_and_cache_avatar("Kalaimaran", avatar_url)

        # Assert network call was made to fetch the URL
        import certifi

        mock_get.assert_called_once_with(avatar_url, timeout=10, verify=certifi.where())

        # Assert file was written correctly
        assert cached_path is not None
        assert Path(cached_path).exists()
        assert Path(cached_path).name == "Kalaimaran.png"
        assert Path(cached_path).read_bytes() == mock_response.content

    @patch("requests.get")
    def test_avatar_manager_offline_graceful_handling(self, mock_get, temp_env):
        """Verifies that AvatarManager handles HTTP failures/offline gracefully without throwing exceptions."""
        import requests

        from biopro.core.developer_database import AvatarManager

        mock_get.side_effect = requests.RequestException("Offline connection timed out")

        manager = AvatarManager(avatar_dir=temp_env["avatar_dir"])

        # Should return None instead of raising connection exception
        cached_path = manager.fetch_and_cache_avatar(
            "Kalaimaran", "https://example.com/kalaimaran.png"
        )
        assert cached_path is None

    def test_ui_initials_extraction(self):
        """Verifies that the developer initials utility correctly processes various name styles."""
        from biopro.ui.dialogs.plugin_store import get_initials

        assert get_initials("Kalaimaran Balasothy") == "KB"
        assert get_initials("John Doe") == "JD"
        assert get_initials("SingleName") == "S"
        assert get_initials("") == "?"
        assert get_initials(None) == "?"

    def test_ui_hsl_gradient_generation(self):
        """Verifies that HSL radial stylesheet generator returns consistent, valid CSS based on developer ID hashes."""
        from biopro.ui.dialogs.plugin_store import get_developer_gradient_css

        css_1 = get_developer_gradient_css("Kalaimaran")
        css_2 = get_developer_gradient_css("OtherDeveloper")
        css_1_repeat = get_developer_gradient_css("Kalaimaran")

        # Must be valid stylesheet snippets containing stop color statements
        assert "qradialgradient" in css_1
        assert "stop:0" in css_1

        # Consistency check: Identical IDs must yield identical HSL colors
        assert css_1 == css_1_repeat

        # Uniqueness check: Different IDs should map to different dynamic palettes
        assert css_1 != css_2

    def test_trust_path_dialog_rendering(self, qapp, temp_env):
        """Verifies that TrustPathDialog resolves and builds visual paths for developers correctly."""
        from biopro.ui.dialogs.plugin_store import TrustPathDialog

        # Test Case 1: Root Verification Chain (Kalaimaran)
        dialog_root = TrustPathDialog("Kalaimaran", "Kalaimaran Balasothy", "somepubkey")
        assert dialog_root.windowTitle() == "Trust Path Verification: Kalaimaran Balasothy"

        # Test Case 2: Unverified / Untrusted Chain
        dialog_unverified = TrustPathDialog("UnverifiedDev", "John Doe", "somekey")
        assert dialog_unverified.windowTitle() == "Trust Path Verification: John Doe"

        # Verify that layout is created and contains correct nodes
        layout = dialog_root.layout()
        assert layout is not None
        assert layout.count() > 0
