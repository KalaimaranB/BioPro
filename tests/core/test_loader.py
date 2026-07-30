"""Tests for the generic PyInstaller frozen environment fix."""

import sys

from biopro.core.plugins.loader import isolate_frozen_environment


def test_isolate_frozen_environment_context_manager():
    """Verify that isolate_frozen_environment safely toggles sys.frozen."""

    # Simulate a PyInstaller frozen state
    sys.frozen = True

    # Inside the context, frozen should be false
    with isolate_frozen_environment():
        assert getattr(sys, "frozen", False) is False

    # Outside the context, frozen should be restored
    assert getattr(sys, "frozen", False) is True

    # Cleanup
    del sys.frozen


def test_isolate_frozen_environment_when_not_frozen():
    """Verify that it does nothing harmful if run in a normal python environment."""

    # Simulate normal python run (no sys.frozen)
    if hasattr(sys, "frozen"):
        del sys.frozen

    with isolate_frozen_environment():
        assert getattr(sys, "frozen", False) is False

    assert getattr(sys, "frozen", False) is False
