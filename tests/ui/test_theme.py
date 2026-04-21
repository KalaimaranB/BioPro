"""Tests for BioPro theme engine."""

import pytest
import json
from pathlib import Path
from biopro.ui.theme import ThemeManager, Colors

class TestThemeEngine:
    @pytest.fixture
    def manager(self):
        return ThemeManager()

    def test_colors_defaults(self):
        """Verify default GitHub Dark colors are present."""
        assert Colors.BG_DARKEST == "#0d1117"
        assert Colors.ACCENT_PRIMARY == "#2f81f7"

    def test_load_valid_theme(self, manager, tmp_path):
        """Test loading a valid theme.json file."""
        theme_data = {
            "name": "Ocean Blue",
            "BG_DARKEST": "#000033",
            "ACCENT_PRIMARY": "#00ffff"
        }
        theme_file = tmp_path / "ocean.json"
        theme_file.write_text(json.dumps(theme_data))
        
        # Track signal
        signal_received = []
        manager.theme_changed.connect(lambda: signal_received.append(True))
        
        success = manager.load_theme(theme_file)
        
        assert success is True
        assert manager.current_theme_name == "Ocean Blue"
        assert Colors.BG_DARKEST == "#000033"
        assert Colors.ACCENT_PRIMARY == "#00ffff"
        assert len(signal_received) == 1

    def test_load_invalid_json(self, manager, tmp_path):
        """Test loading a corrupted JSON file."""
        theme_file = tmp_path / "bad.json"
        theme_file.write_text("{ broken json ...")
        
        success = manager.load_theme(theme_file)
        assert success is False

    def test_load_missing_file(self, manager):
        """Test loading a nonexistent file."""
        success = manager.load_theme(Path("/nonexistent/theme.json"))
        assert success is False

    def test_partial_theme_load(self, manager, tmp_path):
        """Test loading a theme with only some keys defined."""
        # Reset defaults for test consistency
        Colors.BG_DARKEST = "#0d1117"
        
        theme_data = {"BG_DARKEST": "#990000"}
        theme_file = tmp_path / "partial.json"
        theme_file.write_text(json.dumps(theme_data))
        
        manager.load_theme(theme_file)
        assert Colors.BG_DARKEST == "#990000"
        # Other colors should remain unchanged (e.g. DNA_PRIMARY which we didn't touch)
        assert Colors.DNA_PRIMARY == "#00f2ff"
