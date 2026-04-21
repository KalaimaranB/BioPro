"""Tests for biopro.core.module_manager plugin discovery."""

import os
import json
import pytest
from pathlib import Path
from biopro.core.module_manager import ModuleManager
from biopro.core.trust_manager import VerificationResult

class PermissiveTrustManager:
    """Mock security engine that trusts everything for discovery tests."""
    def verify_plugin(self, path):
        return VerificationResult(success=True, trust_level="verified_mock")

@pytest.fixture
def mock_plugin_environment(tmp_path, monkeypatch):
    """Creates a temporary environment for plugin discovery tests."""
    # 1. Create a fake user plugin directory
    # ModuleManager expects Path.home() / ".biopro" / "plugins"
    fake_home = tmp_path / "home"
    user_plugins = fake_home / ".biopro" / "plugins"
    user_plugins.mkdir(parents=True)
    
    # 2. Add a dummy plugin
    plugin_dir = user_plugins / "test_module_a"
    plugin_dir.mkdir()
    
    manifest = {
        "id": "test_module_a",
        "name": "Test Module A",
        "version": "1.0.0",
        "icon": "🧪"
    }
    with open(plugin_dir / "manifest.json", "w") as f:
        json.dump(manifest, f)
        
    # 3. Mock Path.home to return our fake home
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    
    return user_plugins

class TestModuleManager:
    """Test suite for ModuleManager."""

    def test_module_discovery(self, mock_plugin_environment):
        """Verifies that the manager finds modules in the user plugins directory."""
        mm = ModuleManager(trust_manager=PermissiveTrustManager())
        
        # Should have found 'test_module_a'
        assert "test_module_a" in mm.modules
        info = mm.modules["test_module_a"]
        assert info["manifest"]["name"] == "Test Module A"
        assert info["package_name"] == "test_module_a"

    def test_get_available_modules(self, mock_plugin_environment):
        """Verifies that get_available_modules returns a list of manifest dicts."""
        mm = ModuleManager(trust_manager=PermissiveTrustManager())
        modules = mm.get_available_modules()
        
        assert len(modules) >= 1
        # Check if our mock manifest is in the list
        matches = [m for m in modules if m["id"] == "test_module_a"]
        assert len(matches) == 1
        assert matches[0]["icon"] == "🧪"

    def test_reload_modules(self, mock_plugin_environment):
        """Tests the hot-reload capability when plugins are added or removed."""
        mm = ModuleManager(trust_manager=PermissiveTrustManager())
        assert "test_module_a" in mm.modules
        
        # 1. Add a second plugin manually
        new_plugin = mock_plugin_environment / "test_module_b"
        new_plugin.mkdir()
        with open(new_plugin / "manifest.json", "w") as f:
            json.dump({"id": "test_module_b", "name": "B"}, f)
            
        # 2. Reload
        mm.reload_modules()
        
        # 3. Verify both are now present
        assert "test_module_a" in mm.modules
        assert "test_module_b" in mm.modules
        assert len(mm.modules) == 2

    def test_corrupted_manifest_ignored(self, mock_plugin_environment):
        """Ensures that invalid JSON in a manifest doesn't crash the discovery process."""
        bad_plugin = mock_plugin_environment / "broken_plugin"
        bad_plugin.mkdir()
        with open(bad_plugin / "manifest.json", "w") as f:
            f.write("{ invalid json... }")
            
        # Should not raise exception
        mm = ModuleManager(trust_manager=PermissiveTrustManager())
        assert "broken_plugin" not in mm.modules
        # Other plugins should still work
        assert "test_module_a" in mm.modules
