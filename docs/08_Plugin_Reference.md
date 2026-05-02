# BioPro Plugin Development Quick Reference

Copy-paste guides for the modern BioPro SDK. All components listed below are available in the current version of the framework.

> [!TIP]
> For a full list of function signatures, inputs, and outputs, see the [**API Reference**](16_API_Reference.md).


---

## 🛠 CORE COMPONENTS

### 1. State & Analysis Base
```python
from biopro.sdk.core import PluginBase, PluginState, AnalysisBase
from dataclasses import dataclass
from typing import Optional

@dataclass
class MyPluginState(PluginState):
    """State for your analysis. Inherits automatic serialization."""
    image_path: Optional[str] = None
    results: Optional[list] = None

class MyAnalyzer(AnalysisBase):
    """Keep math separate from UI."""
    def run(self, state: MyPluginState) -> dict:
        # Perform computation
        return {"results": [1, 2, 3]}

class MyPluginPanel(PluginBase):
    """Main UI class with integrated Undo/Redo."""
    def __init__(self, plugin_id: str, parent=None):
        super().__init__(plugin_id, parent)
        self.state = MyPluginState()
        self.analyzer = MyAnalyzer(plugin_id)
    
    def get_state(self) -> PluginState:
        return self.state
        
    def set_state(self, state: PluginState) -> None:
        self.state = state
        self.update_ui()
```

### 2. Background Tasks & Scheduling
```python
from biopro.core.task_scheduler import task_scheduler

def _on_run_clicked(self):
    # Submit analysis to the global thread pool
    self.status_message.emit("Analyzing...")
    task_id = task_scheduler.submit(self.analyzer, self.state)
    
    # Connect to the scheduler
    task_scheduler.task_finished.connect(self._on_done)

def _on_done(self, task_id, results):
    self.state.results = results
    self.push_state() # Capture for undo/redo
    self.status_message.emit("Complete!")
```

---

## 🎨 UI & THEMING

### 1. Semantic Components
```python
from biopro.sdk.ui import (
    PrimaryButton,
    SecondaryButton,
    DangerButton,
    ModuleCard,
    HeaderLabel,
    SubtitleLabel
)

# Usage:
btn = PrimaryButton("Run Analysis")
title = HeaderLabel("Gating Results")
card = ModuleCard()
```

### 2. Workflow Wizards
```python
from biopro.sdk.ui import WizardStep, WizardPanel

class SetupStep(WizardStep):
    label = "Configuration"
    def build_page(self, panel: WizardPanel):
        return QWidget() # Your UI here
    
    def on_next(self, panel: WizardPanel) -> bool:
        # Return False to block navigation if validation fails
        return True

# In your main panel:
steps = [SetupStep(), AnalysisStep()]
wizard = WizardPanel(steps, title="My Workflow")
```

### 3. Professional Workspace Layouts
For advanced modules like Flow Cytometry, use a multi-panel layout with `QSplitter` and `QStackedWidget` for ribbons.

```python
from PyQt6.QtWidgets import QSplitter, QStackedWidget, QVBoxLayout
from biopro.sdk.ui import ModuleCard

class MyWorkspace(PluginBase):
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 1. Ribbon Stack for context switching
        self.ribbon = QStackedWidget()
        layout.addWidget(self.ribbon)
        
        # 2. Main Splitter for Sidebars and Canvas
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(MySidebar())
        self.splitter.addWidget(MyCanvas())
        layout.addWidget(self.splitter)
```

### 4. Theme System
```python
from biopro.ui.theme import Colors, Fonts

# Usage in stylesheets:
label.setStyleSheet(f"""
    color: {Colors.FG_PRIMARY};
    font-size: {Fonts.SIZE_LARGE}px;
    background: {Colors.BG_DARK};
""")
```

---

## 📡 COMMUNICATION & EVENTS

### 1. Central Event Bus
```python
from biopro.sdk.core.events import CentralEventBus

# Publish an event
CentralEventBus.publish("image_processed", {"id": "IMG_001"})

# Subscribe to an event
CentralEventBus.subscribe("image_processed", self._on_event)
```

---

## 🔧 UTILITIES

### 1. Dialogs & I/O
```python
from biopro.sdk.utils import (
    get_image_path,
    get_save_path,
    show_info,
    show_error,
    PluginConfig
)

# File Dialogs
path = get_image_path(self, "Select Image")

# Persistent Configuration
config = PluginConfig("my_plugin")
config.set("threshold", 0.5)
config.save()
```

### 2. Image Processing (Contrib)
```python
from biopro.sdk.contrib import (
    load_and_convert,
    adjust_contrast,
    auto_detect_inversion,
    invert_image
)

# Load as normalized float64 [0,1]
image = load_and_convert("blot.tif")
if auto_detect_inversion(image):
    image = invert_image(image)
```

---

## 📝 BEST PRACTICES

1. **State Persistence**: Always call `self.push_state()` after a user-initiated change to enable the "Time Machine" (Undo/Redo).
2. **UI Thread**: Never perform heavy math in button clicks. Use `task_scheduler`.
3. **RAII Cleanup**: Ensure your `PluginBase` subclass calls `super().cleanup()` if you override it, to prevent memory leaks with large datasets.
4. **Theming**: Avoid hardcoding RGB values; always use the `Colors` class.
