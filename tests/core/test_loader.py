"""Tests for the generic PyInstaller frozen environment fix."""

import sys

from biopro.core.plugins.loader import isolate_frozen_environment


def test_isolate_frozen_environment_context_manager(monkeypatch) -> None:
    """Verify that isolate_frozen_environment safely toggles sys.frozen."""

    # Simulate a PyInstaller frozen state
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    # Inside the context, frozen should be false
    with isolate_frozen_environment():
        assert getattr(sys, "frozen", False) is False

    # Outside the context, frozen should be restored
    assert getattr(sys, "frozen", False) is True


def test_isolate_frozen_environment_when_not_frozen(monkeypatch) -> None:
    """Verify that it does nothing harmful if run in a normal python environment."""

    # Simulate normal python run (no sys.frozen)
    monkeypatch.delattr(sys, "frozen", raising=False)

    with isolate_frozen_environment():
        assert getattr(sys, "frozen", False) is False

    assert getattr(sys, "frozen", False) is False
