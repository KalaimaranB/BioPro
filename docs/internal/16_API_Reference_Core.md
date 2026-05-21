# BioPro SDK API Reference: Core Submodule (`biopro.sdk.core`)

This document outlines the technical specifications for the core classes, protocols, and event mechanisms within the `biopro.sdk.core` namespace.

---

## Abstract Base Classes

### `PluginBase`

`class biopro.sdk.core.PluginBase(plugin_id: str, parent: Optional[QWidget] = None)`
*Inherits from `QWidget`*

The abstract controller for BioPro plugins. It implements state capturing, undo/redo capabilities, and integration with the global event bus.

#### Core Methods

##### `publish_event(topic: str, data: Optional[Any] = None) -> None`
Publishes an event to the global event bus.
* **Parameters:**
  * `topic` (str): Unique identifier for the event.
  * `data` (Any, optional): Context payload.

##### `subscribe_event(topic: str, callback: Callable[[Any], None]) -> None`
Subscribes to a global event topic.

##### `get_state() -> PluginState`
***Abstract Method.*** Returns the current serializable state of the plugin.

##### `set_state(state: PluginState) -> None`
***Abstract Method.*** Restores the plugin's state and updates the user interface.

##### `push_state() -> None`
Captures the current state via `get_state()` and pushes it to the undo history stack.

##### `undo() / redo() -> None`
Navigates the history stack and invokes `set_state()` with the targeted snapshot.

##### `cleanup() -> None`
Executes resource clearance by dereferencing high-memory attributes (e.g., NumPy arrays) via the `ResourceInspector`.

---

### `PluginState`

`class biopro.sdk.core.PluginState`
*Base dataclass*

The base class for serializable plugin states. Subclasses must be decorated with `@dataclass`.

#### Serialization Methods
* `to_dict() -> dict[str, Any]`: Serializes fields into a dictionary.
* `@classmethod from_dict(state_dict: dict[str, Any]) -> PluginState`: Instantiates a state object from a dictionary.

---

### `AnalysisBase`

`class biopro.sdk.core.AnalysisBase`
*Abstract Class*

Represents scientific processing logic, isolated from PyQt UI classes to allow execution in background threads.

#### Methods
* `run(state: PluginState) -> Any`: ***Abstract Method.*** Executes the computational workload.

---

## Execution and Communication

### `AnalysisWorker`

`class biopro.sdk.core.AnalysisWorker(analyzer: AnalysisBase, state: PluginState)`
*Inherits from `QRunnable`*

A wrapper for executing an `AnalysisBase` instance within BioPro's global thread pool. It automatically manages standard lifecycle signals (`analysis_started`, `analysis_finished`, `analysis_error`).

### `CentralEventBus` (Singleton)

A thread-safe global event broker enabling decoupled asynchronous communication across components.

#### Methods
* `publish(topic: str, data: Optional[Any] = None) -> None`: Queues a payload for dispatch.
* `subscribe(topic: str, callback: Callable[[Any], None]) -> None`: Registers a listener callback.
* `unsubscribe(topic: str, callback: Callable[[Any], None]) -> None`: Removes a listener callback.
