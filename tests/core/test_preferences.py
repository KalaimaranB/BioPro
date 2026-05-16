from pathlib import Path

import pytest

from biopro.core.preferences import CorePreferenceManager


@pytest.fixture
def pref_manager(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    # Re-initialize to use fake home
    return CorePreferenceManager()


def test_preferences_lifecycle(pref_manager):
    # Test setting and getting
    pref_manager.set("theme", "dark")
    assert pref_manager.get("theme") == "dark"
    assert pref_manager.has("theme") is True

    # Verify persistence
    new_manager = CorePreferenceManager()
    assert new_manager.get("theme") == "dark"

    # Test default
    assert pref_manager.get("nonexistent", "default") == "default"

    # Test clear
    pref_manager.clear()
    assert pref_manager.has("theme") is False
    assert pref_manager.data == {}


def test_preferences_load_error(tmp_path, monkeypatch):
    fake_home = tmp_path / "home_error"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    config_file = fake_home / ".biopro" / "preferences.json"
    config_file.parent.mkdir()
    config_file.write_text("{ invalid json }")

    manager = CorePreferenceManager()
    assert manager.data == {}
