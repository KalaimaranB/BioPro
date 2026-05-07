# 📖 BioPro SDK API Reference: Utilities (`biopro.sdk.utils`)

This document provides formal technical specifications for themed dialog dialogs, configuration managers, and validators within the `biopro.sdk.utils` namespace.

---

## 💬 Dialog Helpers

These functions invoke native themed file, message, and input dialogs on the main thread, respecting the application style.

### File & Directory Queries

##### `get_image_path(parent: QWidget, title: str = "Open Image", start_dir: str = "") -> Optional[str]`
Prompts the user to select an image file (`*.png`, `*.jpg`, `*.jpeg`, `*.tif`, `*.tiff`).
* **Returns:** `Optional[str]` — Selected file path, or `None` if cancelled.

##### `get_save_path(parent: QWidget, title: str = "Save File", start_dir: str = "", filter_str: str = "All Files (*)") -> Optional[str]`
Prompts the user to specify a file save location.
* **Returns:** `Optional[str]` — Target save path, or `None` if cancelled.

##### `get_directory(parent: QWidget, title: str = "Select Directory", start_dir: str = "") -> Optional[str]`
Prompts the user to choose a directory folder.
* **Returns:** `Optional[str]` — Selected directory path, or `None` if cancelled.

---

### Message & Question Boxes

##### `show_info(parent: QWidget, title: str, message: str) -> None`
Displays a themed information dialog box.

##### `show_warning(parent: QWidget, title: str, message: str) -> None`
Displays a themed warning alert box.

##### `show_error(parent: QWidget, title: str, message: str) -> None`
Displays a themed error alert box.

##### `ask_yes_no(parent: QWidget, title: str, message: str) -> bool`
Displays a question dialog with "Yes" and "No" buttons.
* **Returns:** `bool` — `True` if the user clicks "Yes", `False` otherwise.

##### `ask_ok_cancel(parent: QWidget, title: str, message: str) -> bool`
Displays a confirmation dialog with "OK" and "Cancel" buttons.
* **Returns:** `bool` — `True` if the user clicks "OK", `False` otherwise.

---

### Typed User Inputs

##### `get_text(parent: QWidget, title: str, label: str) -> Optional[str]`
Prompts the user to input text via a themed line edit field.
* **Returns:** `Optional[str]` — Input text, or `None` if cancelled.

##### `get_number(parent: QWidget, title: str, label: str, value: int = 0, min_val: int = -2147483648, max_val: int = 2147483647) -> Optional[int]`
Prompts the user for a single integer value with numeric boundary clamping.
* **Returns:** `Optional[int]` — Input integer, or `None` if cancelled.

##### `get_double(parent: QWidget, title: str, label: str, value: float = 0.0, min_val: float = -1e37, max_val: float = 1e37, decimals: int = 2) -> Optional[float]`
Prompts the user for a floating-point number with precision decimal formatting.
* **Returns:** `Optional[float]` — Input float, or `None` if cancelled.

---

## 💾 I/O & Persistent Configurations

### `PluginConfig` (Class)
`class biopro.sdk.utils.PluginConfig(plugin_id: str)`

Main persistent configuration engine for saving local plugin settings. Automatically loads/saves configurations as JSON files inside `~/.biopro/plugin_configs/<plugin_id>.json`.

#### Methods

##### `get(key: str, default: Optional[Any] = None) -> Any`
Retrieves a configuration value.
* **Parameters:**
  * `key` (str): Target key.
  * `default` (Any, optional): Fallback value.
* **Returns:** `Any` — Found value, or default.

##### `set(key: str, value: Any) -> None`
Sets or overwrites a configuration setting in memory.

##### `save() -> None`
Commits all active configuration changes in memory to the physical disk.

---

## 🛡 Validations

These helper functions raise a standardized `ValueError` with detailed descriptions if the tested input fails.

##### `validate_file_exists(path: str) -> None`
##### `validate_directory_exists(path: str) -> None`
##### `validate_value_range(val: float, min_val: float, max_val: float, name: str = "value") -> None`
##### `validate_positive(val: float, name: str = "value") -> None`
##### `validate_non_negative(val: float, name: str = "value") -> None`
##### `validate_not_empty(val: str, name: str = "value") -> None`

---

## 💻 Full Code Example

```python
from PyQt6.QtWidgets import QWidget
from biopro.sdk.utils import PluginConfig, get_image_path, show_info, validate_file_exists

class LoaderController(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = PluginConfig("my_custom_loader")

    def select_experiment_file(self) -> None:
        # 1. Fetch last folder from stored configuration
        last_dir = self.config.get("last_directory", "")

        # 2. Trigger native file dialog
        path = get_image_path(self, "Load TIF Raw", start_dir=last_dir)

        if path:
            try:
                # 3. Apply strict validation checks
                validate_file_exists(path)

                # 4. Save state to configuration
                import os
                self.config.set("last_directory", os.path.dirname(path))
                self.config.save()

                show_info(self, "File Loaded", f"Successfully registered file:\n{path}")
            except ValueError as err:
                from biopro.sdk.utils import show_error
                show_error(self, "Validation Failed", str(err))
```
