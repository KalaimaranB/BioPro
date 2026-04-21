"""Tests for biopro.plugins.sdk_utils module."""

import pytest
import json
import tempfile
from pathlib import Path

from biopro.sdk.utils import (
    load_json,
    save_json,
    validate_file_exists,
    validate_directory_exists,
    validate_value_range,
    PluginConfig,
    get_plugin_logger,
)


class TestJsonUtilities:
    """Test JSON loading and saving."""
    
    def test_save_json(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            data = {'key': 'value', 'nested': {'number': 42}}
            save_json(temp_path, data)
            
            with open(temp_path, 'r') as f:
                loaded = json.load(f)
            
            assert loaded['key'] == 'value'
            assert loaded['nested']['number'] == 42
        finally:
            Path(temp_path).unlink()
    
    def test_save_json_creates_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = Path(tmpdir) / 'sub' / 'dir' / 'data.json'
            data = {'test': 123}
            
            save_json(str(nested_path), data)
            
            assert nested_path.exists()
            with open(nested_path, 'r') as f:
                loaded = json.load(f)
            assert loaded['test'] == 123
    
    def test_load_json(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            data = {'test': 'data', 'array': [1, 2, 3]}
            json.dump(data, f)
            temp_path = f.name
        
        try:
            loaded = load_json(temp_path)
            assert loaded['test'] == 'data'
            assert loaded['array'] == [1, 2, 3]
        finally:
            Path(temp_path).unlink()
    
    def test_load_json_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_json('/nonexistent/path/file.json')
    
    def test_load_json_invalid_json(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("not valid json {")
            temp_path = f.name
        
        try:
            with pytest.raises(json.JSONDecodeError):
                load_json(temp_path)
        finally:
            Path(temp_path).unlink()


class TestValidationFunctions:
    """Test validation helper functions."""
    
    def test_validate_file_exists_true(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name
        
        try:
            is_valid, msg = validate_file_exists(temp_path)
            assert is_valid is True
            assert msg == ""
        finally:
            Path(temp_path).unlink()
    
    def test_validate_file_exists_false(self):
        is_valid, msg = validate_file_exists('/nonexistent/file.txt')
        assert is_valid is False
        assert "not found" in msg.lower()
    
    def test_validate_file_exists_empty_path(self):
        is_valid, msg = validate_file_exists('')
        assert is_valid is False
        assert "empty" in msg.lower()
    
    def test_validate_directory_exists_true(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            is_valid, msg = validate_directory_exists(tmpdir)
            assert is_valid is True
            assert msg == ""
    
    def test_validate_directory_exists_false(self):
        is_valid, msg = validate_directory_exists('/nonexistent/directory')
        assert is_valid is False
        assert "not found" in msg.lower()
    
    def test_validate_value_range_valid(self):
        is_valid, msg = validate_value_range(5, 0, 10, "value")
        assert is_valid is True
        assert msg == ""
    
    def test_validate_value_range_too_low(self):
        is_valid, msg = validate_value_range(-5, 0, 10, "threshold")
        assert is_valid is False
        assert "between" in msg.lower()
        assert "threshold" in msg.lower()
    
    def test_validate_value_range_too_high(self):
        is_valid, msg = validate_value_range(15, 0, 10, "ratio")
        assert is_valid is False
        assert "between" in msg.lower()
    
    def test_validate_value_range_at_boundaries(self):
        is_valid, msg = validate_value_range(0, 0, 10)
        assert is_valid is True
        
        is_valid, msg = validate_value_range(10, 0, 10)
        assert is_valid is True


class TestPluginConfig:
    """Test PluginConfig class."""
    
    def test_config_creation(self):
        config = PluginConfig("test_plugin")
        assert config.plugin_id == "test_plugin"
        assert isinstance(config.data, dict)
    
    def test_config_set_get(self):
        config = PluginConfig("test")
        
        config.set("threshold", 0.5)
        config.set("name", "test_analysis")
        
        assert config.get("threshold") == 0.5
        assert config.get("name") == "test_analysis"
    
    def test_config_get_default(self):
        config = PluginConfig("test")
        
        value = config.get("nonexistent", default=42)
        assert value == 42
    
    def test_config_has(self):
        config = PluginConfig("test")
        config.set("key1", "value1")
        
        assert config.has("key1") is True
        assert config.has("key2") is False
    
    def test_config_getitem_setitem(self):
        config = PluginConfig("test")
        
        config["threshold"] = 0.75
        assert config["threshold"] == 0.75
    
    def test_config_clear(self):
        config = PluginConfig("test")
        config.set("key1", "value1")
        config.set("key2", "value2")
        
        assert len(config.data) == 2
        config.clear()
        assert len(config.data) == 0
    
    def test_config_save_load(self):
        # Create and save config
        config1 = PluginConfig("temp_test_plugin")
        config1.set("param1", 100)
        config1.set("param2", "data")
        config1.save()
        
        # Load in new instance
        config2 = PluginConfig("temp_test_plugin")
        
        assert config2.get("param1") == 100
        assert config2.get("param2") == "data"
        
        # Cleanup
        config1.config_file.unlink(missing_ok=True)
    
    def test_config_persistence_across_instances(self):
        """Test that config persists between instances."""
        plugin_id = "persistence_test_plugin"
        
        # First instance - set values
        config1 = PluginConfig(plugin_id)
        config1.set("persistent_value", 999)
        config1.save()
        
        # Second instance - should load persisted values
        config2 = PluginConfig(plugin_id)
        assert config2.get("persistent_value") == 999
        
        # Cleanup
        config1.config_file.unlink(missing_ok=True)
    
    def test_config_file_location(self):
        config = PluginConfig("test_plugin")
        expected_dir = Path.home() / '.biopro' / 'plugin_configs'
        expected_file = expected_dir / 'test_plugin.json'
        
        assert config.config_dir == expected_dir
        assert config.config_file == expected_file


class TestPluginLogger:
    """Test logger creation."""
    
    def test_get_plugin_logger(self):
        logger = get_plugin_logger("my_plugin")
        
        assert logger is not None
        assert "my_plugin" in logger.name
        assert "biopro.plugins" in logger.name


class TestConfigIntegration:
    """Integration tests for config."""
    
    def test_config_complex_data_types(self):
        """Test config with complex data types."""
        config = PluginConfig("complex_test")
        
        config.set("list_data", [1, 2, 3, 4, 5])
        config.set("dict_data", {"nested": {"key": "value"}})
        config.set("tuple_data", (1, 2, 3))  # Will be converted to list
        
        config.save()
        
        # Load and verify
        config2 = PluginConfig("complex_test")
        assert config2.get("list_data") == [1, 2, 3, 4, 5]
        assert config2.get("dict_data")["nested"]["key"] == "value"
        
        # Cleanup
        config.config_file.unlink(missing_ok=True)
    
    def test_config_handles_missing_file(self):
        """Test config gracefully handles missing config file."""
        config = PluginConfig("nonexistent_config_test")
        
        # Should load empty
        assert len(config.data) == 0
        
        # Set and verify
        config.set("key", "value")
        assert config.get("key") == "value"


class TestAssetWorkflow:
    """Test higher-level asset import workflows added to the SDK."""
    
    @pytest.fixture
    def mock_pm(self):
        """Mock ProjectManager."""
        from unittest.mock import MagicMock
        pm = MagicMock()
        pm.batch_add_images.return_value = ["h1", "h2"]
        return pm

    def test_import_assets_workflow_multiple_with_subfolder(self, mock_pm):
        """Verifies workflow asks for subfolder and copy permission."""
        from biopro.sdk.utils.dialogs import import_assets_workflow
        from unittest.mock import patch
        
        with patch("biopro.sdk.utils.dialogs.ask_yes_no") as mock_ask, \
             patch("biopro.sdk.utils.dialogs.get_text") as mock_text:
            
            # Setup user choices: Yes to group, Yes to copy
            mock_ask.side_effect = [True, True]
            mock_text.return_value = "batch_01"
            
            files = ["/fake/img1.png", "/fake/img2.png"]
            hashes = import_assets_workflow(None, mock_pm, files)
            
            assert hashes == ["h1", "h2"]
            mock_pm.batch_add_images.assert_called_once()
            
            # Verify internal conversion to Path objects and subfolder passing
            args, _ = mock_pm.batch_add_images.call_args
            assert args[1] is True  # copy_to_workspace
            assert args[2] == "batch_01" # subfolder

    def test_import_assets_workflow_no_subfolder(self, mock_pm):
        """Verifies workflow when user declines subfolder grouping."""
        from biopro.sdk.utils.dialogs import import_assets_workflow
        from unittest.mock import patch
        
        with patch("biopro.sdk.utils.dialogs.ask_yes_no") as mock_ask:
            # Setup user choices: No to group, Yes to copy
            mock_ask.side_effect = [False, True]
            
            files = ["/fake/img1.png", "/fake/img2.png"]
            import_assets_workflow(None, mock_pm, files)
            
            args, _ = mock_pm.batch_add_images.call_args
            assert args[2] is None  # subfolder should be None

