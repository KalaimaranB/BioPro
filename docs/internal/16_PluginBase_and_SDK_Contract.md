# PluginBase & SDK Contract

The real plugin contract, as implemented in `karcytics_sdk.plugin.base.PluginBase`
and wired up via a V3 `entry_point` — not the `get_plugin()`/`karcytics_sdk.core`
shape this page used to describe, which never matched the code. See
`docs/internal/15_ModuleManager_and_PluginContract.md` for how a plugin gets
discovered and this entry point gets called in the first place.

## The `entry_point` function

A plugin's `pyproject.toml` declares one under `[tool.karcytics.plugin]`:

```toml
[tool.karcytics.plugin]
entry_point = "karcytics_plugins.flow_cytometry:initialize"
```

`module:function` — the named module is imported, the named function is
called with a `PluginContext`, and its return value (a `PluginBase`
instance, in practice) is what the Hub inserts into `WorkspaceWindow`:

```python
# karcytics_plugins/flow_cytometry/__init__.py (the real, current shape)
from karcytics_sdk.plugin.context import PluginContext


def initialize(context: PluginContext) -> Any:
    ...
    return FlowCytometryPanel(plugin_id="flow_cytometry")
```

## `PluginBase` (`karcytics_sdk/plugin/base.py`)

A `QWidget` subclass, not a bare interface — a plugin's panel *is* a
`PluginBase`, not something that owns one separately.

```python
class PluginBase(QWidget):
    def __init__(self, plugin_id: str, parent=None): ...

    # Must be implemented by every subclass:
    def get_state(self) -> PluginState: ...
    def set_state(self, state: PluginState) -> None: ...

    # Provided, ready to use:
    def push_state(self) -> None: ...  # snapshot get_state() into undo history
    def undo(self) -> None: ...
    def redo(self) -> None: ...
    def can_undo(self) -> bool: ...
    def can_redo(self) -> bool: ...
    def cleanup(self) -> None: ...  # RAII-style resource release via ResourceInspector
    def publish_event(self, topic: str, data: Any = None) -> None: ...  # CentralEventBus
    def subscribe_event(self, topic: str, callback) -> None: ...  # CentralEventBus
```

`get_state()`/`set_state()` work in terms of `PluginState`
(`karcytics_sdk/plugin/state.py`), not a raw dict — `push_state()` calls
`.to_dict()` on it before handing the result to `HistoryManager`, and
`undo()`/`redo()` reconstruct via `.from_dict()` on the same class
`get_state()` returned. `self.state_changed` (proxied through `__getattr__`
to `self.signals`, a `PluginSignals` instance covering
`status`/`state_changed`/`analysis_started`/`analysis_finished`/
`analysis_error`, etc.) fires automatically from `push_state()`/`undo()`/`redo()`.

`self.history` lazily resolves the Hub's real `HistoryManager` — but only
when `karcytics.core.history_manager` is actually importable. In a genuinely
isolated plugin's own `.venv` (see doc 24), it never is, so this falls back
to an in-memory `MockHistoryManager` instead — undo/redo works locally
within that process but nothing persists across the plugin's own restarts.
This is the same "resolves differently per process, transparently" pattern
`theme_fallback.py` and the Academy engine use (see doc 27) — not a bug
specific to this class, and not something a plugin author needs to branch
on.

## Minimal example

```python
from karcytics_sdk.plugin.base import PluginBase
from karcytics_sdk.plugin.state import PluginState


class MyState(PluginState):
    threshold: float = 0.5


class MyPlugin(PluginBase):
    def __init__(self, plugin_id: str):
        super().__init__(plugin_id)
        self._state = MyState()
        # build UI here

    def get_state(self) -> MyState:
        return self._state

    def set_state(self, state: MyState) -> None:
        self._state = state
        self.update_ui()

    def cleanup(self) -> None:
        super().cleanup()  # releases heavy references via ResourceInspector
```

## Analysis workers (off-UI thread)

Long-running computation belongs in an `AnalysisBase` subclass
(`karcytics_sdk/plugin/analysis.py`), submitted to a `TaskScheduler`
(`context.get("task_scheduler")` for an in-process plugin; a local,
per-process one for an isolated plugin — see doc 25's "Where UI comes from,
where analysis comes from"). `task_started`/`task_finished`/`task_error`/
`task_progress` signals, keyed by `task_id`, are how a result gets back to
the UI thread — never a direct return value across a thread boundary.

## Signing & distribution

Covered in full by `docs/internal/20_Security_and_Signing.md` and
`21_Supply_Chain_Security.md` — summary: a plugin ships with a signed
`security.json` (per-file SHA-256 + an Ed25519 signature chaining to the
Karcytics Core Authority root key, a project CI key, or an explicit local
override), verified by `TrustManager` before `module_manager.py` will load
or spawn it. The SDK CLI's `security.py` commands (`init-identity`, `sign`,
`project-sign`) generate the identity and produce that signature.

## Testing & contract verification

`karcytics_sdk.testing.contract.ContractTestBase` — a pytest base class a
plugin author subclasses to get `test_manifest_is_valid` and
`test_headless_initialization` for free (the latter mocks every capability
the manifest declares under `requires` and confirms the plugin's
`entry_point` resolves and initializes with no running Hub at all). See
`tests/sdk/test_plugin_contract.py` in this repo for worked examples.

## Links

- `docs/internal/15_ModuleManager_and_PluginContract.md` — discovery,
  trust verification, and how `entry_point` gets invoked.
- `docs/internal/25_Core_and_SDK_Boundary.md` — which package owns
  `PluginBase` vs. `PluginContext` vs. the concrete services behind them.
- `karcytics_sdk/plugin/base.py`, `state.py`, `context.py`, `analysis.py` —
  the real source.
