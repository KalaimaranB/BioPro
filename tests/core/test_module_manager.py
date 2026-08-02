"""Tests for biopro.core.module_manager plugin discovery."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from biopro_sdk.host.trust_manager import VerificationResult

from biopro.core.module_manager import ModuleManager

MOCK_TRUST_RESULT = VerificationResult(success=True, trust_level="verified_mock")


def _dict_to_toml(d):  # noqa: C901
    # Convert flat dict to pyproject.toml format
    """
    Convert plugin metadata into a pyproject.toml-formatted string.

    Parameters:
        d (dict): Flat plugin metadata containing project and plugin configuration fields.

    Returns:
        str: TOML-formatted project and plugin configuration.
    """
    lines = []

    lines.append("[project]")
    lines.append(f'name = "{d.get("name", "test")}"')
    lines.append(f'version = "{d.get("version", "1.0.0")}"')
    if "description" in d:
        lines.append(f'description = "{d["description"]}"')

    authors = d.get("authors", [])
    if authors:
        lines.append("authors = [")
        for a in authors:
            lines.append(f'  {{ name = "{a.get("name", "Test")}" }},')
        lines.append("]")

    lines.append("")
    lines.append("[tool.biopro.plugin]")
    lines.append(f'id = "{d.get("id", "test_id")}"')

    if "icon" in d:
        lines.append(f'icon = "{d["icon"]}"')

    if "entry_point" in d:
        lines.append(f'entry_point = "{d["entry_point"]}"')

    if "ui_components" in d:
        lines.append("ui_components = [")
        for comp in d["ui_components"]:
            lines.append(f'  "{comp}",')
        lines.append("]")

    if authors:
        lines.append("authors = [")
        for a in authors:
            role = a.get("role", "Developer")
            perms = a.get("permissions", [])
            perms_str = '", "'.join(perms)
            if perms_str:
                lines.append(
                    f'  {{ name = "{a.get("name", "Test")}", role = "{role}", permissions = ["{perms_str}"] }},'
                )
            else:
                lines.append(f'  {{ name = "{a.get("name", "Test")}", role = "{role}" }},')
        lines.append("]")

    return "\n".join(lines)


def make_v2_manifest(plugin_id: str, name: str, icon: str = "🧪") -> dict:
    """Build a valid V2 manifest for test fixtures."""
    return {
        "manifest_version": 2,
        "id": plugin_id,
        "name": name,
        "version": "1.0.0",
        "description": f"{name} plugin",
        "authors": [{"name": "Test Dev", "role": "Developer"}],
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
    with open(plugin_dir / "pyproject.toml", "w", encoding="utf-8") as f:
        f.write(_dict_to_toml(make_v2_manifest("test_module_a", "Test Module A")))

    monkeypatch.setattr(Path, "home", lambda: fake_home)
    return user_plugins


class TestModuleManager:
    """Test suite for ModuleManager Facade."""

    def test_module_discovery(self, mock_plugin_environment):
        """Verifies that the manager finds V2 modules in the user plugins directory."""
        with patch(
            "biopro.core.plugins.discovery.TrustStrategyFactory.get_strategy",
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
            "biopro.core.plugins.discovery.TrustStrategyFactory.get_strategy",
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
            "biopro.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=mock_strategy,
        ):
            mm = ModuleManager()
            assert "test_module_a" in mm.modules

            new_plugin = mock_plugin_environment / "test_module_b"
            new_plugin.mkdir()
            with open(new_plugin / "pyproject.toml", "w", encoding="utf-8") as f:
                f.write(_dict_to_toml(make_v2_manifest("test_module_b", "B")))

            mm.reload_modules()

        assert "test_module_a" in mm.modules
        assert "test_module_b" in mm.modules
        assert len(mm.modules) >= 2

    def test_corrupted_manifest_ignored(self, mock_plugin_environment):
        """Ensures that invalid JSON in a manifest doesn't crash the discovery process."""
        bad_plugin = mock_plugin_environment / "broken_plugin"
        bad_plugin.mkdir()
        with open(bad_plugin / "pyproject.toml", "w", encoding="utf-8") as f:
            f.write("{ invalid json... }")

        with patch(
            "biopro.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()

        assert "broken_plugin" not in mm.modules
        assert "test_module_a" in mm.modules

    def test_load_module_ui_untrusted_blocked(self, mock_plugin_environment):
        """Verifies that an untrusted module cannot be loaded."""
        with patch(
            "biopro.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(
                verify=MagicMock(
                    return_value=VerificationResult(success=False, trust_level="untrusted")
                )
            ),
        ):
            mm = ModuleManager()

        # Create dummy venv so it doesn't fail on missing dependency
        venv_bin = (
            mm.modules["test_module_a"]["path"]
            / ".venv"
            / ("Scripts" if sys.platform == "win32" else "bin")
        )
        venv_bin.mkdir(parents=True)
        (venv_bin / ("python.exe" if sys.platform == "win32" else "python3")).touch()

        with pytest.raises(PermissionError, match="Security Block"):
            mm.load_module_ui("test_module_a")

    def test_load_module_ui_missing_venv_raises_dependency_error(self, mock_plugin_environment):
        """Verifies that loading a verified module with missing dependencies raises a specific error."""
        with patch(
            "biopro.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(
                verify=MagicMock(
                    return_value=VerificationResult(success=True, trust_level="verified_cache")
                )
            ),
        ):
            mm = ModuleManager()

        with pytest.raises(RuntimeError, match="DependencyMissingError"):
            mm.load_module_ui("test_module_a")

    def test_load_module_ui_already_loaded(self, mock_plugin_environment):
        """Verifies that subsequent calls to load_module_ui use the cached plugin reference."""
        with patch(
            "biopro.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()
            mock_plugin = MagicMock()
            mm.modules["test_module_a"]["loaded"] = True
            mm.modules["test_module_a"]["plugin_ref"] = mock_plugin

            venv_bin = (
                mm.modules["test_module_a"]["path"]
                / ".venv"
                / ("Scripts" if sys.platform == "win32" else "bin")
            )
            venv_bin.mkdir(parents=True, exist_ok=True)
            (venv_bin / ("python.exe" if sys.platform == "win32" else "python3")).touch()

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
            "biopro.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()

        venv_bin = (
            mm.modules["test_module_a"]["path"]
            / ".venv"
            / ("Scripts" if sys.platform == "win32" else "bin")
        )
        venv_bin.mkdir(parents=True, exist_ok=True)
        (venv_bin / ("python.exe" if sys.platform == "win32" else "python3")).touch()

        plugin_instance = DummyPlugin()
        with (
            patch("biopro.core.plugins.environment.PluginEnvironmentInjector.inject_path"),
            patch("importlib.import_module", return_value=plugin_instance),
        ):
            mm.load_module_ui("test_module_a")
            assert mm.modules["test_module_a"]["loaded"] is True
            assert mm.modules["test_module_a"]["plugin_ref"] == plugin_instance

    def test_load_module_ui_invalid_interface(self, mock_plugin_environment):
        """Verifies that a module not implementing the BioProPlugin interface is rejected."""
        with patch(
            "biopro.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()

        venv_bin = (
            mm.modules["test_module_a"]["path"]
            / ".venv"
            / ("Scripts" if sys.platform == "win32" else "bin")
        )
        venv_bin.mkdir(parents=True, exist_ok=True)
        (venv_bin / ("python.exe" if sys.platform == "win32" else "python3")).touch()

        mock_module = MagicMock()
        with (
            patch("biopro.core.plugins.environment.PluginEnvironmentInjector.inject_path"),
            patch("importlib.import_module", return_value=mock_module),
            pytest.raises(TypeError, match="Missing required hooks"),
        ):
            mm.load_module_ui("test_module_a")

    def test_trust_module_flow(self, mock_plugin_environment):
        """Tests the manual trust-override flow for a module."""
        untrusted_result = VerificationResult(
            success=False, trust_level="untrusted", calculated_hashes={"file.py": "hash"}
        )
        with patch(
            "biopro.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=untrusted_result)),
        ):
            mm = ModuleManager()
            mm.trust_manager.overrides = MagicMock()
            mm.trust_manager._get_cache = MagicMock(return_value=MagicMock(data={}))

            assert mm.modules["test_module_a"]["trust_level"] == "untrusted"

            success = mm.trust_module("test_module_a")
            assert success is True
            mm.trust_manager.overrides.trust_current_state.assert_called_once_with(
                "test_module_a", {"file.py": "hash"}
            )

    def test_trust_module_reverify_if_missing_hashes(self, mock_plugin_environment):
        """Ensures that trust_module re-verifies the plugin if hashes are not already cached."""
        with patch(
            "biopro.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()
            mm.trust_manager.verify_plugin = MagicMock(
                return_value=MagicMock(calculated_hashes={"file.py": "new_hash"})
            )
            mm.trust_manager.overrides = MagicMock()
            mm.trust_manager._get_cache = MagicMock(return_value=MagicMock(data={}))

            if "calculated_hashes" in mm.modules["test_module_a"]:
                del mm.modules["test_module_a"]["calculated_hashes"]

            mm.trust_module("test_module_a")
            mm.trust_manager.verify_plugin.assert_called_once()
            mm.trust_manager.overrides.trust_current_state.assert_called_once_with(
                "test_module_a", {"file.py": "new_hash"}
            )
