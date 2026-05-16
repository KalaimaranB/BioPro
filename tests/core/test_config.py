from pathlib import Path
from unittest.mock import patch

import pytest

from biopro.core.config import AppConfig


@pytest.fixture
def app_config(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    return AppConfig()


def test_app_config_lifecycle(app_config):
    # Test recent projects
    app_config.add_recent_project("/path/a")
    app_config.add_recent_project("/path/b")
    assert app_config.get_recent_projects()[0] == str(Path("/path/b").absolute())

    # Test duplicates handling
    app_config.add_recent_project("/path/a")
    assert app_config.get_recent_projects()[0] == str(Path("/path/a").absolute())
    assert len(app_config.get_recent_projects()) == 2

    # Test limit
    for i in range(15):
        app_config.add_recent_project(f"/path/{i}")
    assert len(app_config.get_recent_projects()) == 10


def test_skipped_update_version(app_config):
    app_config.set_skipped_update_version("2.0.0")
    assert app_config.get_skipped_update_version() == "2.0.0"


def test_config_load_error(tmp_path, monkeypatch):
    fake_home = tmp_path / "home_err"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    config_file = fake_home / ".biopro" / "config.json"
    config_file.parent.mkdir()
    config_file.write_text("{ broken }")

    with patch("biopro.core.diagnostics.diagnostics.report_error") as mock_diag:
        config = AppConfig()
        assert config.data["ai_enabled"] is True  # Default
        mock_diag.assert_called()


def test_config_save_error(app_config):
    with (
        patch("builtins.open", side_effect=PermissionError("Locked")),
        patch("biopro.core.diagnostics.diagnostics.report_error") as mock_diag,
    ):
        app_config.save()
        mock_diag.assert_called()


def test_get_docs_dir():
    docs = AppConfig.get_docs_dir()
    assert docs.name == "docs"
    assert docs.is_absolute()
