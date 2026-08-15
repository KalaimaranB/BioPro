"""Tests for what a V3 (entry_point) plugin's PluginContext exposes as
"event_bus" — see karcytics/core/plugins/loader.py's `load_ui` and
docs/internal/25, "Migration status" item 2.

There is no real Hub EventManager wired into an in-process V3 plugin's
services yet. The contract under test is only that this gap fails loudly
(a RuntimeError the moment a plugin that declared `requires = ["event_bus"]`
calls `context.get("event_bus")`), not silently (a `None` a plugin would
only discover was useless the first time it tried to call a method on it).
"""

import sys
import types
from unittest.mock import MagicMock

from karcytics.core.plugins.loader import PluginLoaderFactory


def _make_mod_info(entry_point: str, requires: list[str]) -> dict:
    return {
        "loaded": False,
        "package_name": "fake_v3_plugin",
        "path": "/fake/path",
        "trust_level": "verified",
        "manifest": {
            "name": "fake_v3_plugin",
            "entry_point": entry_point,
            "requires": requires,
        },
    }


def _install_fake_module(module_name: str, init_func) -> None:
    module = types.ModuleType(module_name)
    setattr(module, "init", init_func)  # noqa: B010
    sys.modules[module_name] = module


def test_v3_plugin_not_requiring_event_bus_loads_normally(monkeypatch):
    monkeypatch.setattr(
        "karcytics.core.plugins.environment.PluginEnvironmentInjector.inject_path",
        lambda *a, **k: None,
    )

    captured = {}

    def init(context):
        captured["context"] = context
        panel = MagicMock()
        panel.get_panel_class.return_value = MagicMock()
        return panel

    _install_fake_module("fake_v3_plugin_no_bus", init)
    try:
        mod_info = _make_mod_info("fake_v3_plugin_no_bus:init", requires=[])
        result = PluginLoaderFactory.load_ui("fake_v3_plugin", mod_info)

        assert result is not None
        assert mod_info["status"] == "OK"
        # The gap is real, but scoped: a plugin that never asks for
        # event_bus never even sees that it's missing.
        assert "event_bus" not in captured["context"]._services
    finally:
        del sys.modules["fake_v3_plugin_no_bus"]


def test_v3_plugin_requiring_event_bus_fails_loudly_not_silently(monkeypatch):
    monkeypatch.setattr(
        "karcytics.core.plugins.environment.PluginEnvironmentInjector.inject_path",
        lambda *a, **k: None,
    )

    def init(context):
        # A real plugin would crash here with the same RuntimeError the
        # moment it reached for the capability it declared — this is that
        # call, made directly instead of via a fake plugin's own logic.
        return context.get("event_bus")

    _install_fake_module("fake_v3_plugin_needs_bus", init)
    try:
        mod_info = _make_mod_info("fake_v3_plugin_needs_bus:init", requires=["event_bus"])

        # PluginLoaderFactory.load_ui contains plugin entry-point exceptions
        # (RuntimeError isn't one of the re-raised types) rather than
        # crashing the Hub — so the observable contract is a clean,
        # contained failure, not a silent `None` flowing back into the
        # plugin as a usable-looking event bus.
        result = PluginLoaderFactory.load_ui("fake_v3_plugin", mod_info)

        assert result is None
        assert mod_info["status"] == "FAILED"
        assert mod_info["loaded"] is False
    finally:
        del sys.modules["fake_v3_plugin_needs_bus"]
