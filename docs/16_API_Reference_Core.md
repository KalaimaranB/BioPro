# 📖 BioPro SDK API Reference: Core Submodule (`biopro.sdk.core`)

This document provides formal technical specifications for the core classes, protocols, and communication mechanisms within the `biopro.sdk.core` namespace.

---

## 🏛 Classes

### `PluginBase` (Class)

`class biopro.sdk.core.PluginBase(plugin_id: str, parent: Optional[QWidget] = None)`
*Inherits from `QWidget`*

This is the main abstract base controller for all BioPro plugins. It implements integrated state capturing, undo/redo histories, automatic memory cleanup (RAII), and global stylesheet reactivity.

#### Methods

##### `publish_event(topic: str, data: Optional[Any] = None) -> None`
Publishes an event to the global central event bus.
* **Parameters:**
  * `topic` (str): Unique topic identifier.
  * `data` (Any, optional): Context payload sent to subscribers. Defaults to `None`.

##### `subscribe_event(topic: str, callback: Callable[[Any], None]) -> None`
Subscribes the plugin to a global event topic.
* **Parameters:**
  * `topic` (str): Unique topic identifier.
  * `callback` (Callable): Callback method taking the data payload as its single parameter.

##### `get_state() -> PluginState`
***Abstract Method.*** Must be overridden by subclasses. Returns the current serializable state of the plugin.
* **Returns:** `PluginState` — The active state container.

##### `set_state(state: PluginState) -> None`
***Abstract Method.*** Must be overridden by subclasses. Restores the plugin's state and updates UI widgets.
* **Parameters:**
  * `state` (`PluginState`): The state instance to load into the plugin.

##### `push_state() -> None`
Captures the current state via `get_state()`, converts it to a dictionary, and pushes it to the undo history stack. Also emits the `state_changed` signal.

##### `undo() -> None`
Rolls back the plugin's state to the previous snapshot in the history stack, invoking `set_state()` with the recovered state.

##### `redo() -> None`
Advances the plugin's state to the next snapshot in the history stack, invoking `set_state()` with the recovered state.

##### `can_undo() -> bool`
Queries whether there is a valid previous state available on the undo stack.
* **Returns:** `bool` — `True` if undoing is possible.

##### `can_redo() -> bool`
Queries whether there is a valid next state available on the redo stack.
* **Returns:** `bool` — `True` if redoing is possible.

##### `cleanup() -> None`
Automatic Resource Cleansing. Uses the `ResourceInspector` to break references to high-memory attributes (such as NumPy arrays and Torch tensors) inside both the plugin controller and its state object, ensuring rapid reclamation by the garbage collector.

---

### `PluginState` (Class)

`class biopro.sdk.core.PluginState`
*Base dataclass*

The base class for serializable plugin states. All subclasses must be decorated with `@dataclass`.

#### Methods

##### `to_dict() -> dict[str, Any]`
Serializes the state's dataclass fields into a standard JSON-compatible Python dictionary.
* **Returns:** `dict[str, Any]` — Serialized representation of the state.

##### `@classmethod from_dict(state_dict: dict[str, Any]) -> PluginState`
Instantiates a new state instance using data from a serialized state dictionary.
* **Parameters:**
  * `state_dict` (`dict`): The serialized field data.
* **Returns:** `PluginState` — An initialized subclass instance.

---

### `PluginSignals` (Class)

`class biopro.sdk.core.PluginSignals`
*Inherits from `QObject`*

Standardized PyQt6 signals for communicating state changes, status bar updates, and analysis thread progress.

#### Signals

* `state_changed = pyqtSignal()` — Emitted when the plugin state is modified or an undo/redo action completes.
* `status_message = pyqtSignal(str)` — Emitted to display a temporary message in the application's global status bar.
* `analysis_started = pyqtSignal()` — Emitted when a background analysis worker begins execution.
* `analysis_finished = pyqtSignal(object)` — Emitted when a background analysis worker completes successfully, passing the results.
* `analysis_error = pyqtSignal(str)` — Emitted when a background analysis worker encounters an unhandled exception, passing the error description.

---

### `CentralEventBus` (Class/Singleton)

`biopro.sdk.core.CentralEventBus`

A thread-safe global event broker enabling publishers and subscribers to interact asynchronously without direct component coupling.

#### Methods

##### `@staticmethod publish(topic: str, data: Optional[Any] = None) -> None`
Queues a payload for asynchronous dispatching to all active subscribers.
* **Parameters:**
  * `topic` (str): Target topic.
  * `data` (Any, optional): Context payload.

##### `@staticmethod subscribe(topic: str, callback: Callable[[Any], None]) -> None`
Registers a callback to receive data payloads whenever the specified topic is published.
* **Parameters:**
  * `topic` (str): Target topic.
  * `callback` (Callable): Target callback.

##### `@staticmethod unsubscribe(topic: str, callback: Callable[[Any], None]) -> None`
Removes an existing subscriber callback from a topic.
* **Parameters:**
  * `topic` (str): Target topic.
  * `callback` (Callable): Callback to remove.

---

### `AnalysisBase` (Class)

`class biopro.sdk.core.AnalysisBase`
*Abstract Class*

Abstract class representing the mathematical or scientific processing logic, completely separated from PyQt UI classes.

#### Methods

##### `run(state: PluginState) -> Any`
***Abstract Method.*** Must be overridden by subclasses to perform computations in background threads.
* **Parameters:**
  * `state` (`PluginState`): Snapshot of the plugin state to operate on.
* **Returns:** `Any` — Any computational results to send back to the main thread.

---

### `AnalysisWorker` (Class)

`class biopro.sdk.core.AnalysisWorker(analyzer: AnalysisBase, state: PluginState)`
*Inherits from `QRunnable`*

Execution wrapper for running an `AnalysisBase` instance inside BioPro's global thread pool, automatically managing PyQt signal emissions for progress and errors.

---

## 💻 Full Code Example

Below is a complete, type-annotated implementation of a custom scientific plugin using the Core SDK components.

```python
from dataclasses import dataclass
from typing import Any
from PyQt6.QtWidgets import QVBoxLayout, QLabel
from biopro.sdk.core import PluginBase, PluginState, AnalysisBase, AnalysisWorker

@dataclass
class PeakState(PluginState):
    signal_threshold: float = 2.5
    filter_kernel: int = 5

class PeakAnalyzer(AnalysisBase):
    def run(self, state: PeakState) -> int:
        # Heavily computed background task
        # Returns number of peaks found
        threshold = state.signal_threshold
        kernel = state.filter_kernel
        return 42  # Dummy computational result

class PeakDetectionPlugin(PluginBase):
    def __init__(self, plugin_id: str, parent=None):
        super().__init__(plugin_id, parent)
        self.state = PeakState()
        self.analyzer = PeakAnalyzer()

        # UI Assembly
        layout = QVBoxLayout(self)
        self.label = QLabel("Peaks Found: 0")
        layout.addWidget(self.label)

        # Connect background worker lifecycle signals
        self.analysis_finished.connect(self._on_analysis_complete)
        self.analysis_error.connect(self._on_analysis_failed)

    def get_state(self) -> PeakState:
        return self.state

    def set_state(self, state: PeakState) -> None:
        self.state = state
        self.logger.info(f"State loaded: threshold={state.signal_threshold}")

    def trigger_computation(self) -> None:
        # 1. Save state to undo history before initiating work
        self.push_state()

        # 2. Dispatch worker to background thread pool
        worker = AnalysisWorker(self.analyzer, self.state)
        from PyQt6.QtCore import QThreadPool
        QThreadPool.globalInstance().start(worker)
        self.analysis_started.emit()

    def _on_analysis_complete(self, result: Any) -> None:
        self.label.setText(f"Peaks Found: {result}")
        self.status_message.emit("Analysis successful.")

    def _on_analysis_failed(self, error_msg: str) -> None:
        self.logger.error(f"Computation failed: {error_msg}")
        self.status_message.emit("Analysis failed!")
```
