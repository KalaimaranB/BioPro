"""Tests for biopro.core.module_manager plugin discovery."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from biopro_sdk.host.trust_manager import VerificationResult

from biopro.core.module_manager import ModuleManager

MOCK_TRUST_RESULT = VerificationResult(success=True, trust_level="verified_mock")


def make_v2_manifest(plugin_id: str, name: str, icon: str = "🧪") -> dict:
    """Build a valid V2 manifest for test fixtures."""
    return {
        "manifest_version": 2,
        "id": plugin_id,
        "name": name,
        "version": "1.0.0",
        "description": f"{name} plugin",
        "signed_by": {"entity_type": "developer", "entity_id": "test_dev"},
        "authors": [{"name": "Test Dev"}],
        "icon": icon,
    }


@pytest.fixture
def mock_plugin_environment(tmp_path, monkeypatch):
    """Creates a temporary environment for plugin discovery tests."""
    fake_home = tmp_path / "home"
    user_plugins = fake_home / ".biopro" / "plugins"
    user_plugins.mkdir(parents=True)

    plugin_dir = user_plugins / "test_module_a"
    plugin_dir.mkdir()
    with open(plugin_dir / "manifest.json", "w") as f:
        json.dump(make_v2_manifest("test_module_a", "Test Module A"), f)

    monkeypatch.setattr(Path, "home", lambda: fake_home)
    return user_plugins


class TestModuleManager:
    """Test suite for ModuleManager."""

    def test_module_discovery(self, mock_plugin_environment):
        """Verifies that the manager finds V2 modules in the user plugins directory."""
        with patch(
            "biopro.core.module_manager.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()

        assert "test_module_a" in mm.modules
        info = mm.modules["test_module_a"]
        assert info["manifest"]["name"] == "Test Module A"
        assert info["package_name"] == "test_module_a"

    def test_get_available_modules(self, mock_plugin_environment):
        """Verifies that get_available_modules returns a list of manifest dicts."""
        with patch(
            "biopro.core.module_manager.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()
        modules = mm.get_available_modules()

        assert len(modules) >= 1
        matches = [m for m in modules if m["id"] == "test_module_a"]
        assert len(matches) == 1
        assert matches[0]["icon"] == "🧪"

    def test_reload_modules(self, mock_plugin_environment):
        """Tests the hot-reload capability when plugins are added or removed."""
        mock_strategy = MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT))
        with patch(
            "biopro.core.module_manager.TrustStrategyFactory.get_strategy",
            return_value=mock_strategy,
        ):
            mm = ModuleManager()
            assert "test_module_a" in mm.modules

            new_plugin = mock_plugin_environment / "test_module_b"
            new_plugin.mkdir()
            with open(new_plugin / "manifest.json", "w") as f:
                json.dump(make_v2_manifest("test_module_b", "B"), f)

            mm.reload_modules()

        assert "test_module_a" in mm.modules
        assert "test_module_b" in mm.modules
        assert len(mm.modules) == 2

    def test_corrupted_manifest_ignored(self, mock_plugin_environment):
        """Ensures that invalid JSON in a manifest doesn't crash the discovery process."""
        bad_plugin = mock_plugin_environment / "broken_plugin"
        bad_plugin.mkdir()
        with open(bad_plugin / "manifest.json", "w") as f:
            f.write("{ invalid json... }")

        with patch(
            "biopro.core.module_manager.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()

        assert "broken_plugin" not in mm.modules
        assert "test_module_a" in mm.modules

    def test_sys_path_injection(self, mock_plugin_environment):
        """Verifies that the manager successfully injects plugin venv site-packages to sys.path."""
        import sys

        with patch(
            "biopro.core.module_manager.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()

        plugin_path = mock_plugin_environment / "test_module_a"
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = plugin_path / ".venv" / "lib" / py_ver / "site-packages"
        site_packages.mkdir(parents=True)

        mm._inject_plugin_path(plugin_path)

        assert str(site_packages) in sys.path
        assert sys.path[0] == str(site_packages)

        if str(site_packages) in sys.path:
            sys.path.remove(str(site_packages))

    def test_sys_path_cleanup(self, mock_plugin_environment):
        """Verifies that the manager cleans up dynamic plugin venv paths from sys.path."""
        import sys

        with patch(
            "biopro.core.module_manager.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()

        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        fake_site_packages = (
            Path.home()
            / ".biopro"
            / "plugins"
            / "test_module_a"
            / ".venv"
            / "lib"
            / py_ver
            / "site-packages"
        )
        sys.path.insert(0, str(fake_site_packages))
        mm._cleanup_plugin_paths()
        assert str(fake_site_packages) not in sys.path

    def test_load_module_ui_untrusted_blocked(self, mock_plugin_environment):
        """Verifies that an untrusted module cannot be loaded."""
        with patch(
            "biopro.core.module_manager.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(
                verify=MagicMock(
                    return_value=VerificationResult(success=False, trust_level="untrusted")
                )
            ),
        ):
            mm = ModuleManager()

        with pytest.raises(PermissionError, match="Security Block"):
            mm.load_module_ui("test_module_a")

    def test_load_module_ui_already_loaded(self, mock_plugin_environment):
        """Verifies that subsequent calls to load_module_ui use the cached plugin reference."""
        with patch(
            "biopro.core.module_manager.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()
            mock_plugin = MagicMock()
            mm.modules["test_module_a"]["loaded"] = True
            mm.modules["test_module_a"]["plugin_ref"] = mock_plugin

            mm.load_module_ui("test_module_a")
            mock_plugin.get_panel_class.assert_called_once()

    def test_load_module_ui_success(self, mock_plugin_environment):
        """Tests the full successful path of loading a plugin UI."""

        class DummyPlugin:
            def get_panel_class(self):
                return MagicMock()

            __version__ = "1.0.0"
            __plugin_id__ = "test_module_a"

            def cleanup(self):
                pass

            def shutdown(self):
                pass

        with patch(
            "biopro.core.module_manager.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()

        plugin_instance = DummyPlugin()
        with patch("importlib.import_module", return_value=plugin_instance):
            mm.load_module_ui("test_module_a")
            assert mm.modules["test_module_a"]["loaded"] is True
            assert mm.modules["test_module_a"]["plugin_ref"] == plugin_instance

    def test_load_module_ui_not_found(self, mock_plugin_environment):
        """Ensures that loading a non-existent module raises ValueError."""
        mm = ModuleManager()
        with pytest.raises(ValueError, match="is not installed"):
            mm.load_module_ui("non_existent_id")

    def test_load_module_ui_invalid_interface(self, mock_plugin_environment):
        """Verifies that a module not implementing the BioProPlugin interface is rejected."""
        with patch(
            "biopro.core.module_manager.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()

        # Mock sys.modules to simulate successful import but failed interface check
        mock_module = MagicMock()
        # It's NOT an instance of BioProPlugin
        with (
            patch("importlib.import_module", return_value=mock_module),
            pytest.raises(TypeError, match="does not satisfy BioProPlugin protocol"),
        ):
            mm.load_module_ui("test_module_a")

    def test_trust_module_flow(self, mock_plugin_environment):
        """Tests the manual trust-override flow for a module."""
        # Start with an untrusted module
        untrusted_result = VerificationResult(
            success=False, trust_level="untrusted", calculated_hashes={"file.py": "hash"}
        )
        with patch(
            "biopro.core.module_manager.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=untrusted_result)),
        ):
            mm = ModuleManager()
            # Mock the trust manager overrides
            mm.trust_manager.overrides = MagicMock()
            mm.trust_manager._get_cache = MagicMock(return_value=MagicMock(data={}))

            assert mm.modules["test_module_a"]["trust_level"] == "untrusted"

            # Manually trust it
            success = mm.trust_module("test_module_a")
            assert success is True
            mm.trust_manager.overrides.trust_current_state.assert_called_once_with(
                "test_module_a", {"file.py": "hash"}
            )

    def test_trust_module_reverify_if_missing_hashes(self, mock_plugin_environment):
        """Ensures that trust_module re-verifies the plugin if hashes are not already cached."""
        with patch(
            "biopro.core.module_manager.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()
            mm.trust_manager.verify_plugin = MagicMock(
                return_value=MagicMock(calculated_hashes={"file.py": "new_hash"})
            )
            mm.trust_manager.overrides = MagicMock()
            mm.trust_manager._get_cache = MagicMock(return_value=MagicMock(data={}))

            # Remove hashes from mod_info
            if "calculated_hashes" in mm.modules["test_module_a"]:
                del mm.modules["test_module_a"]["calculated_hashes"]

            mm.trust_module("test_module_a")
            mm.trust_manager.verify_plugin.assert_called_once()
            mm.trust_manager.overrides.trust_current_state.assert_called_once_with(
                "test_module_a", {"file.py": "new_hash"}
            )

    def test_trust_module_cache_clearing(self, mock_plugin_environment):
        """Verifies that trust_module invalidates the trust cache for the module."""
        with patch(
            "biopro.core.module_manager.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()
            mm.modules["test_module_a"]["calculated_hashes"] = {"f": "h"}

            mock_cache = MagicMock(data={"test_module_a": "something"})
            mm.trust_manager._get_cache = MagicMock(return_value=mock_cache)
            mm.trust_manager.overrides = MagicMock()

            mm.trust_module("test_module_a")

            assert "test_module_a" not in mock_cache.data
            mock_cache._save.assert_called_once()

    def test_reload_modules_purges_sys_modules(self, mock_plugin_environment):
        """Verifies that hot-reload correctly purges cached plugin modules from sys.modules."""
        import sys

        with patch(
            "biopro.core.module_manager.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()
            mm.modules["test_module_a"]["loaded"] = True
            mm.modules["test_module_a"]["package_name"] = "test_module_a"

            # Simulate module being in sys.modules
            sys.modules["biopro.plugins.test_module_a"] = MagicMock()
            sys.modules["biopro.plugins.test_module_a.ui"] = MagicMock()

            mm.reload_modules()

            assert "biopro.plugins.test_module_a" not in sys.modules
            assert "biopro.plugins.test_module_a.ui" not in sys.modules
