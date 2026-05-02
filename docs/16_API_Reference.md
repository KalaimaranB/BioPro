# 📖 BioPro SDK API Reference

This document provides formal technical specifications for the core functions and classes in the BioPro SDK.

---

## 🏛 CORE SDK (`biopro.sdk.core`)

### `PluginBase` (Class)
The main base class for all BioPro plugins. Inherits from `QWidget`.

| Method | Inputs | Outputs | Description |
| :--- | :--- | :--- | :--- |
| `__init__` | `plugin_id: str`, `parent=None` | `None` | Initializes the plugin with a unique ID and optional parent. |
| `get_state` | *None* | `PluginState` | **Abstract**. Must return the current analysis state object. |
| `set_state` | `state: PluginState` | `None` | **Abstract**. Must restore the plugin UI from the provided state. |
| `push_state` | *None* | `None` | Captures current state and saves it to the Undo history. |
| `publish_event`| `topic: str`, `data: Any` | `None` | Helper to publish an event to the Central Event Bus. |
| `subscribe_event`| `topic: str`, `callback: Callable`| `None` | Helper to subscribe to an event on the Central Event Bus. |
| `cleanup` | *None* | `None` | Releases heavy memory (Numpy arrays, Tensors). Called on tab close. |

### `CentralEventBus` (Singleton)
Decoupled communication system for inter-plugin events.

| Method | Inputs | Outputs | Description |
| :--- | :--- | :--- | :--- |
| `publish` | `topic: str`, `data: Any=None` | `None` | Queues an event for asynchronous delivery to all subscribers. |
| `subscribe` | `topic: str`, `callback: Callable` | `None` | Registers a function to be called when a specific topic is published. |
| `unsubscribe` | `topic: str`, `callback: Callable` | `None` | Removes an existing subscription. |

---

## 🎨 UI FRAMEWORK (`biopro.sdk.ui`)

### `WizardStep` (Abstract Class)
A single step in a multi-step analysis workflow.

| Method | Inputs | Outputs | Description |
| :--- | :--- | :--- | :--- |
| `build_page` | `panel: WizardPanel` | `QWidget` | **Abstract**. Build and return the UI widget for this step. |
| `on_next` | `panel: WizardPanel` | `bool` | **Abstract**. Validates input. Return `True` to allow navigation. |
| `on_enter` | *None* | `None` | Optional hook called when the step becomes visible. |

---

## 🔧 UTILITIES (`biopro.sdk.utils`)

### Dialog Helpers

| Function | Inputs | Outputs | Description |
| :--- | :--- | :--- | :--- |
| `get_image_path` | `parent`, `title: str`, `start_dir: str` | `Optional[str]` | Opens a file dialog. Returns path or `None` if cancelled. |
| `show_info` | `parent`, `title: str`, `message: str` | `None` | Shows a standard themed information message box. |
| `show_error` | `parent`, `title: str`, `message: str` | `None` | Shows a standard themed error message box. |
| `get_text` | `parent`, `title: str`, `label: str` | `Optional[str]` | Shows a text input dialog. Returns string or `None`. |

### `PluginConfig` (Class)
Persistent JSON storage for plugin settings (saved in `~/.biopro/plugin_configs/`).

| Method | Inputs | Outputs | Description |
| :--- | :--- | :--- | :--- |
| `__init__` | `plugin_id: str` | `None` | Loads the configuration file from disk. |
| `set` | `key: str`, `value: Any` | `None` | Sets a configuration value in memory. |
| `get` | `key: str`, `default: Any` | `Any` | Returns the value for a key, or the default. |
| `save` | *None* | `None` | Commits the current configuration to disk. |

---

## 🧪 CONTRIB (`biopro.sdk.contrib`)

### Image Utilities

| Function | Inputs | Outputs | Description |
| :--- | :--- | :--- | :--- |
| `load_and_convert`| `path: str`, `as_grayscale: bool` | `NDArray` | Loads image as normalized `float64` in range [0.0, 1.0]. |
| `adjust_contrast`| `img: NDArray`, `alpha: float`, `beta: float`| `NDArray` | Adjusts contrast (alpha) and brightness (beta). |
| `invert_image` | `img: NDArray` | `NDArray` | Performs a fast `1.0 - image` bitwise inversion. |
| `crop_to_content` | `img: NDArray`, `padding: int` | `NDArray` | Detects non-empty bounds and crops image with padding. |
