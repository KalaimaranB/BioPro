"""Tests for BioPro global app configuration."""

import pytest
import json
from pathlib import Path
from biopro.core.config import AppConfig

class TestAppConfig:
    @pytest.fixture
    def config(self, tmp_path, monkeypatch):
        # Mock home to tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        return AppConfig()

    def test_config_initialization(self, config, tmp_path):
        """Verifies standard config folder and file creation."""
        assert config.config_dir == tmp_path / ".biopro"
        assert config.config_file == tmp_path / ".biopro" / "config.json"
        assert config.data["recent_projects"] == []

    def test_add_recent_projects_logic(self, config):
        """Verifies deduplication and ordering of recent projects."""
        config.add_recent_project("/p1")
        config.add_recent_project("/p2")
        config.add_recent_project("/p1") # Re-add p1 - should move to top
        
        recents = config.get_recent_projects()
        assert recents[0] == str(Path("/p1").absolute())
        assert recents[1] == str(Path("/p2").absolute())
        assert len(recents) == 2

    def test_recent_projects_limit(self, config):
        """Verifies the 10-project limit."""
        for i in range(15):
            config.add_recent_project(f"/p{i}")
            
        recents = config.get_recent_projects()
        assert len(recents) == 10
        # Most recent should be /p14
        assert recents[0] == str(Path("/p14").absolute())

    def test_config_persistence(self, config, tmp_path):
        """Verifies save and load roundtrip."""
        config.add_recent_project("/my/proj")
        config.save()
        
        # New instance should load same data
        import biopro.core.config
        from unittest.mock import patch
        
        with patch("pathlib.Path.home", return_value=tmp_path):
            config2 = AppConfig()
            assert str(Path("/my/proj").absolute()) in config2.get_recent_projects()

    def test_corrupted_config_load_gracefully(self, tmp_path, monkeypatch):
        """Verifies that corrupted config.json doesn't crash initialization."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        conf_dir = tmp_path / ".biopro"
        conf_dir.mkdir()
        (conf_dir / "config.json").write_text("{ incomplete...")
        
        # Should finish init without raising
        config = AppConfig()
        assert config.data == {"recent_projects": []}
