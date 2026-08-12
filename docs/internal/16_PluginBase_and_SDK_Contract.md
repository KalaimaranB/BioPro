# PluginBase & SDK Contract

This document describes the recommended plugin contract for authors using the BioPro SDK, with minimal examples, lifecycle hooks, signing guidance, and common best-practices.

## Goal

Plugins must safely interoperate with the core: support state capture/restore, obey threading rules (UI vs worker), and provide lifecycle cleanup so `ModuleManager` can load/unload plugins without leaking resources.

## Minimal contract (summary)

- Export a `get_plugin()` factory returning an instance that implements the `PluginBase` surface described below, or expose a `Plugin` class subclassing the SDK `PluginBase`.
- Implement `get_state()`, `set_state(state)`, `cleanup()`, and optionally `push_state()` for integration with `HistoryManager`.

## `PluginBase` (recommended surface)

```py
class PluginBase:
    def __init__(self, plugin_id: str, parent=None):
        self.plugin_id = plugin_id

    def get_state(self) -> dict:
        """Return a JSON-serializable dict capturing minimal plugin state."""

    def set_state(self, state: dict) -> None:
        """Restore state and update the UI accordingly."""

    def push_state(self) -> None:
        """Capture and push state into `HistoryManager` via ModuleManager."""

    def cleanup(self) -> None:
        """Stop background workers and release heavy resources (NumPy arrays, threads)."""
```

## Minimal example plugin

```py
from biopro.plugins.sdk_utils import PluginConfig, get_plugin_logger
from biopro_sdk.core import PluginBase as SDKPluginBase


class MyPlugin(SDKPluginBase):
    def __init__(self, plugin_id: str, parent=None):
        super().__init__(plugin_id, parent=parent)
        self._state = {"threshold": 0.5}

    def get_state(self):
        return dict(self._state)

    def set_state(self, state):
        self._state.update(state)

    def cleanup(self):
        # stop workers, drop heavy arrays
        pass


def get_plugin():
    return MyPlugin(plugin_id="example.my_plugin")
```

Place `get_plugin()` at the package top-level or expose a `Plugin` class — `ModuleManager` will call the factory to instantiate and integrate the UI.

## Analysis workers (off-UI thread)

Long-running computation belongs in `AnalysisBase` and should be executed via `AnalysisWorker` so the UI remains responsive. Example pattern:

1. Create an `AnalysisBase` subclass that implements `run(state)`.
2. Submit it to the global thread pool with `AnalysisWorker(analyzer, state)`.
3. Emit lifecycle signals (`analysis_started`, `analysis_finished`, `analysis_error`) consumed by the plugin UI.

## Cleanup patterns

- Always implement `cleanup()` to cancel futures, join threads, and dereference large arrays.
- Use `ResourceInspector.is_heavy()` to guide what to keep by reference in `HistoryManager` snapshots.

## Signing & Distribution (high-level)

BioPro validates plugin packages before loading them. Authors should:

1. Package your plugin as a Python wheel or editable source with a correct `pyproject.toml` and `manifest.json` containing `plugin_id`, `entrypoint`, and `sdk_version`.
2. Sign your distribution using our signing tool (see `scripts/sign_authorities.py`) or the SDK CLI which bundles signing helpers.
3. Publish to the plugin registry or distribute the zip. The `NetworkUpdater` and `TrustManager` perform verification during install and before load.

If a plugin is intended for development only, the developer can use a local trust override via `TrustManager` (the UI exposes an explicit confirmation flow).

## Testing & Contract verification

- Add unit tests that validate `get_state()` / `set_state()` round-trips.
- Use `tests/sdk/` contract tests as examples (see `tests/sdk/test_plugin_contract.py`).

## Links

- `biopro/plugins/sdk_utils.py` — utilities and example helpers for plugins.
- `biopro/core/module_manager.py` — loading lifecycle and integration points.
- `tests/sdk/test_plugin_contract.py` — test-driven examples of the plugin contract.
