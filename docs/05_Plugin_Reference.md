# BioPro Plugin Development Quick Reference

Copy-paste guides for common patterns found in the three plugins.

---

## ✅ ALREADY AVAILABLE (Use These)

### Import Shared UI Components
```python
from biopro.sdk.ui import (
    PrimaryButton,
    SecondaryButton,
    DangerButton,
    ModuleCard,
    HeaderLabel,
)
from biopro.ui.theme import Colors, Fonts

# Usage:
btn = PrimaryButton("Save Analysis")
btn.setToolTip("Click to save")
btn.clicked.connect(self.on_save)

label = HeaderLabel("Analysis Results")
```

### Import Image Utilities
```python
from biopro.sdk.contrib import (
    load_and_convert,
    adjust_contrast,
    auto_detect_inversion,
    invert_image,
    enhance_for_band_detection,
)
import numpy as np
from numpy.typing import NDArray

# Load and preprocess image
image: NDArray[np.float64] = load_and_convert("blot.tif")  # float64 [0,1]
image = adjust_contrast(image, alpha=1.5, beta=-0.1)
should_invert = auto_detect_inversion(image)
if should_invert:
    image = 1.0 - image  # Invert
```

### Import Theme System
```python
from biopro.ui.theme import Colors, Fonts

# Colors available:
# Colors.FG_PRIMARY, FG_SECONDARY, FG_DISABLED
# Colors.BG_DARKEST, BG_DARK, BG_MEDIUM, BG_LIGHT
# Colors.BORDER
# Colors.ACCENT_PRIMARY, ACCENT_PRIMARY_HOVER, ACCENT_PRIMARY_PRESSED
# Colors.SUCCESS, WARNING, ERROR
# Colors.GRID, PLOT_BG

# Fonts available:
# Fonts.SIZE_SMALL (10px)
# Fonts.SIZE_NORMAL (12px)
# Fonts.SIZE_LARGE (14px)
# Fonts.MONO (monospace family)

# Usage:
label.setStyleSheet(f"""
    color: {Colors.FG_PRIMARY};
    font-size: {Fonts.SIZE_LARGE}px;
    background: {Colors.BG_DARK};
""")
```

---

## 🔜 COMING SOON (Will Be Available)

### Plugin Base Class
```python
from biopro.plugins.base import PluginPanel
from dataclasses import dataclass

@dataclass
class MyPluginState:
    """State for your analysis."""
    image_path: Optional[Path] = None
    results: Optional[pd.DataFrame] = None

class MyPluginPanel(PluginPanel):
    """Inherit BioPro-required signals and methods."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Inherited signals:
        # - state_changed: pyqtSignal()
        # - status_message: pyqtSignal(str)
        # - results_ready: pyqtSignal(object)
        
        self._state = MyPluginState()
    
    def export_state(self) -> dict:
        """Required: snapshot for undo/redo."""
        return {
            "image_path": str(self._state.image_path) if self._state.image_path else None,
        }
    
    def load_state(self, state_dict: dict) -> None:
        """Required: restore from snapshot."""
        if state_dict.get("image_path"):
            self._state.image_path = Path(state_dict["image_path"])
    
    def export_workflow(self) -> dict:
        """Required: full workflow for saving."""
        return {
            "plugin_id": "my.plugin",
            "version": "1.0.0",
            "state": self.export_state(),
            "results": self._state.results.to_dict() if self._state.results is not None else None,
        }
    
    def load_workflow(self, payload: dict) -> None:
        """Required: load saved workflow."""
        self.load_state(payload.get("state", {}))
```

### Wizard-Based UI
```python
from biopro.ui.wizard import WizardPanel, WizardStep
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSpinBox, QFileDialog, QMessageBox
)

class LoadImageStep(WizardStep):
    """Step 1: Load image file."""
    
    label = "Load Image"
    
    def build_page(self, panel: WizardPanel) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        
        self.btn_open = QPushButton("📁 Open Image File")
        self.btn_open.clicked.connect(lambda: self._open_file())
        layout.addWidget(self.btn_open)
        
        self.lbl_status = QLabel("No file loaded")
        layout.addWidget(self.lbl_status)
        
        layout.addStretch()
        return page
    
    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(None, "Open Image", "", "Images (*.tif *.png *.jpg)")
        if path:
            self.lbl_status.setText(f"Loaded: {Path(path).name}")
            # Store in panel or state for next step
            self.panel._image_path = path
    
    def on_next(self, panel: WizardPanel) -> bool:
        """Called when user clicks Next."""
        if not hasattr(panel, "_image_path"):
            QMessageBox.warning(None, "Error", "Please load an image first")
            return False  # Block advance
        
        # Load image
        panel._state.image = load_and_convert(panel._image_path)
        panel.status_message.emit("Image loaded")
        return True  # Allow advance

class AnalysisStep(WizardStep):
    """Step 2: Run analysis."""
    
    label = "Analyze"
    
    def build_page(self, panel: WizardPanel) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        
        self.spin_threshold = QSpinBox()
        self.spin_threshold.setRange(1, 100)
        self.spin_threshold.setValue(50)
        layout.addWidget(QLabel("Threshold:"))
        layout.addWidget(self.spin_threshold)
        
        self.btn_analyze = QPushButton("🔬 Analyze")
        self.btn_analyze.clicked.connect(lambda: self._run_analysis(panel))
        layout.addWidget(self.btn_analyze)
        
        layout.addStretch()
        return page
    
    def _run_analysis(self, panel):
        threshold = self.spin_threshold.value()
        panel.status_message.emit(f"Analyzing with threshold={threshold}...")
        # ... run analysis, update state ...
        panel.status_message.emit("Done!")
    
    def on_next(self, panel: WizardPanel) -> bool:
        """Validation before advancing."""
        if panel._state.results is None:
            QMessageBox.warning(None, "Error", "Please run analysis first")
            return False
        return True

class ResultsStep(WizardStep):
    """Step 3: Show results."""
    
    label = "Results"
    
    def build_page(self, panel: WizardPanel) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        
        # Display results table, plots, etc.
        layout.addWidget(QLabel("Results here"))
        
        btn_export = PrimaryButton("💾 Export Results")
        btn_export.clicked.connect(lambda: self._export_results(panel))
        layout.addWidget(btn_export)
        
        layout.addStretch()
        return page
    
    def _export_results(self, panel):
        # ... export logic ...
        panel.results_ready.emit(panel._state.results)

# In main panel:
class MyPluginPanel(PluginPanel):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        steps = [LoadImageStep(), AnalysisStep(), ResultsStep()]
        self._wizard = WizardPanel(steps, parent=self)
        
        layout = QVBoxLayout(self)
        layout.addWidget(self._wizard)
```

### Canvas with Zoom/Pan
```python
from biopro.ui.graphics import ZoomPanCanvas
from PyQt6.QtGui import QPixmap, QColor, QPen, QBrush
from PyQt6.QtWidgets import QGraphicsRectItem

class MyCanvas(ZoomPanCanvas):
    """Custom canvas for my analysis."""
    
    band_clicked = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Inherited: zoom/pan on wheel, middle-click
        # Inherited: fit_view(), zoom_changed signal
        
        self._overlays = []
    
    def load_image(self, image_path: str):
        """Load and display image."""
        pixmap = QPixmap(image_path)
        super().load_image(pixmap)  # Inherited method
    
    def draw_regions(self, regions: list):
        """Draw detection overlays."""
        for item in self._overlays:
            self._scene.removeItem(item)
        self._overlays.clear()
        
        for i, region in enumerate(regions):
            rect = QGraphicsRectItem(region.x, region.y, region.w, region.h)
            rect.setPen(QPen(QColor("#00FF00"), 2))
            rect.setBrush(QBrush(QColor(0, 255, 0, 30)))
            
            # Make clickable
            rect.region_id = i
            rect.mousePressEvent = lambda e, rid=i: self.band_clicked.emit(rid)
            
            self._scene.addItem(rect)
            self._overlays.append(rect)
```

### Background Task
```python
from biopro.workers import BackgroundTask

class AnalysisTask(BackgroundTask):
    """Long-running analysis in background thread."""
    
    def __init__(self, image: NDArray, params: dict):
        super().__init__()
        self.image = image
        self.params = params
    
    def run(self) -> object:
        """Override to implement task logic."""
        try:
            self.status.emit("Starting analysis...")
            self.progress.emit(10)
            
            # Expensive computation
            result = expensive_analysis(self.image, self.params)
            
            self.status.emit("Finishing up...")
            self.progress.emit(90)
            
            # Final results
            self.progress.emit(100)
            self.status.emit("Complete!")
            return result
            
        except Exception as e:
            self.error.emit(f"Analysis failed: {str(e)}")
            return None

# In UI:
class MyPluginPanel(PluginPanel):
    def _run_analysis(self):
        task = AnalysisTask(self._state.image, {"threshold": 50})
        
        # Connect signals
        task.progress.connect(self.progress_bar.setValue)
        task.status.connect(self.status_label.setText)
        task.finished.connect(self._on_analysis_done)
        task.error.connect(self._on_analysis_error)
        
        # Start in background
        task.start()
    
    def _on_analysis_done(self, results):
        self._state.results = results
        self.results_ready.emit(results)
    
    def _on_analysis_error(self, error_msg):
        QMessageBox.critical(self, "Error", error_msg)
```

---

## 📊 STATE PATTERN

### Define State Dataclass
```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import numpy as np
import pandas as pd

@dataclass
class MyAnalysisState:
    """Mutable state for one analysis session."""
    
    # Input
    image_path: Optional[Path] = None
    raw_image: Optional[np.ndarray] = None
    
    # Processing
    processed_image: Optional[np.ndarray] = None
    processing_params: dict = field(default_factory=dict)
    
    # Results
    detected_objects: list = field(default_factory=list)
    results_df: Optional[pd.DataFrame] = None
    
    # View state
    current_view: str = "image"  # "image" or "results"
    
    def to_workflow_dict(self) -> dict:
        """Serialize for workflow save."""
        return {
            "image_path": str(self.image_path) if self.image_path else None,
            "processing_params": self.processing_params,
            "results": self.results_df.to_dict() if self.results_df is not None else None,
        }
    
    @classmethod
    def from_workflow_dict(cls, data: dict) -> "MyAnalysisState":
        """Deserialize from workflow."""
        state = cls()
        if data.get("image_path"):
            state.image_path = Path(data["image_path"])
        state.processing_params = data.get("processing_params", {})
        if data.get("results"):
            state.results_df = pd.DataFrame(data["results"])
        return state
```

### Analyzer Pattern
```python
class MyAnalyzer:
    """Performs analysis on state."""
    
    def __init__(self, state: MyAnalysisState):
        self.state = state
    
    def load_image(self, path: Path) -> None:
        """Load and preprocess image."""
        self.state.raw_image = load_and_convert(path)
        self.state.image_path = path
        self.state.processed_image = self.state.raw_image.copy()
    
    def detect_objects(self, **params) -> None:
        """Run detection."""
        self.state.processing_params = params
        
        # Detection logic
        objects = self._find_objects(
            self.state.processed_image,
            threshold=params.get("threshold", 0.5),
        )
        
        self.state.detected_objects = objects
    
    def generate_results(self) -> pd.DataFrame:
        """Produce results DataFrame."""
        data = []
        for i, obj in enumerate(self.state.detected_objects):
            data.append({
                "ID": i,
                "Area": obj.area,
                "Intensity": obj.mean_intensity,
                "X": obj.center_x,
                "Y": obj.center_y,
            })
        
        self.state.results_df = pd.DataFrame(data)
        return self.state.results_df
    
    def _find_objects(self, image, threshold):
        # ... your detection algorithm ...
        pass

# Usage in UI:
analyzer = MyAnalyzer(self._state)
analyzer.load_image(path)
analyzer.detect_objects(threshold=0.5)
analyzer.generate_results()
```

---

## 🎨 UI STYLING

### Common Patterns
```python
from biopro.ui.theme import Colors, Fonts

# Large heading
label = QLabel("Analysis Results")
label.setStyleSheet(f"""
    color: {Colors.FG_PRIMARY};
    font-size: {Fonts.SIZE_LARGE}px;
    font-weight: bold;
""")

# Input field with dark theme
input_field = QLineEdit()
input_field.setStyleSheet(f"""
    QLineEdit {{
        background-color: {Colors.BG_DARK};
        color: {Colors.FG_PRIMARY};
        border: 1px solid {Colors.BORDER};
        border-radius: 4px;
        padding: 6px;
    }}
    QLineEdit:focus {{
        border: 1px solid {Colors.ACCENT_PRIMARY};
    }}
""")

# Grouped controls
group = QGroupBox("Parameters")
group.setStyleSheet(f"""
    QGroupBox {{
        color: {Colors.FG_PRIMARY};
        border: 1px solid {Colors.BORDER};
        border-radius: 4px;
        padding: 12px;
        margin-top: 6px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        margin-left: 10px;
    }}
""")

# Action button
btn = PrimaryButton("Run Analysis")
btn.setMinimumHeight(40)
btn.clicked.connect(self.on_run)
layout.addWidget(btn)

# Info label (secondary text)
info = QLabel("Status: Ready")
info.setStyleSheet(f"color: {Colors.FG_SECONDARY};")
```

---

## 📝 SIGNALS & SLOTS

### Common Signal Patterns
```python
# Emit status updates
self.status_message.emit("Loading image...")
self.status_message.emit("Detecting objects...")
self.status_message.emit("Complete!")

# Emit state changes (triggers undo/redo)
self._state.some_field = new_value
self.state_changed.emit()

# Report analysis results
analysis_results = compute_results()
self.results_ready.emit(analysis_results)

# Domain-specific signals
self.image_loaded.emit(image_path)
self.analysis_complete.emit(results)
self.error_occurred.emit("Something went wrong")
```

### Connecting Custom Signals
```python
class MyPluginPanel(PluginPanel):
    # Define custom signals
    image_loaded = pyqtSignal(str)  # path
    analysis_complete = pyqtSignal(dict)  # results
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Connect to other UI components
        self.canvas.image_loaded.connect(self._on_image_loaded)
        self.analyzer_task.finished.connect(self._on_analysis_done)
    
    def _on_image_loaded(self, image_path: str):
        """Called when canvas loads image."""
        self.image_loaded.emit(image_path)
        self.status_message.emit(f"Loaded: {Path(image_path).name}")
    
    def _on_analysis_done(self, results):
        """Called when analysis completes."""
        self.analysis_complete.emit(results)
        self.results_ready.emit(results)
        self.state_changed.emit()  # Trigger undo/redo
```

---

## 🔧 COMMON TASKS

### Load and Display Image
```python
from biopro.sdk.contrib import load_and_convert
from PyQt6.QtGui import QPixmap, QImage
import cv2

def load_image_display(path: str) -> QPixmap:
    """Load image and convert to QPixmap for display."""
    # Load as numpy array
    image = load_and_convert(path, as_grayscale=False)
    
    # Convert float [0,1] to uint8 [0,255]
    image_uint8 = (image * 255).astype(np.uint8)
    
    # Convert to RGB if needed
    if image_uint8.ndim == 2:  # Grayscale
        image_uint8 = cv2.cvtColor(image_uint8, cv2.COLOR_GRAY2RGB)
    
    # Convert to QImage
    h, w, c = image_uint8.shape
    bytes_per_line = 3 * w
    q_image = QImage(image_uint8.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
    
    return QPixmap.fromImage(q_image)

# Usage:
pixmap = load_image_display("analysis.tif")
self.canvas.load_image(pixmap)
```

### Save Analysis Results
```python
import json
from pathlib import Path

def export_results(results: dict, output_path: str) -> None:
    """Export analysis results to JSON."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert numpy arrays to lists for JSON serialization
    def convert_to_serializable(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [convert_to_serializable(v) for v in obj]
        return obj
    
    serializable = convert_to_serializable(results)
    
    with open(path, "w") as f:
        json.dump(serializable, f, indent=2)

# Usage:
results = {
    "image_path": "analysis.tif",
    "detected_objects": detected_list,
    "statistics": {"mean": np.mean(data), "std": np.std(data)},
}
export_results(results, "results.json")
```

### Progress Reporting
```python
def long_running_task(items: list, callback_progress=None):
    """Process items with progress reporting."""
    total = len(items)
    
    for i, item in enumerate(items):
        # Do work
        result = process_item(item)
        
        # Report progress
        if callback_progress:
            percent = int((i + 1) / total * 100)
            callback_progress(percent)

# Usage in UI:
def _run_task(self):
    def on_progress(percent):
        self.progress_bar.setValue(percent)
        self.status_label.setText(f"Progress: {percent}%")
    
    long_running_task(self.items, callback_progress=on_progress)
```

---

## 📦 MANIFEST.json Template

```json
{
    "id": "biopro.modules.my_analysis",
    "name": "My Analysis Plugin",
    "version": "1.0.0",
    "min_core_version": "1.0.1",
    "description": "Performs custom analysis on images and data.",
    "author": "Your Name",
    "icon": "🔬",
    "release_notes": "Initial release",
    
    "core_dependencies": [
        "numpy",
        "pandas",
        "scikit-image"
    ]
}
```

---

## 🧪 TESTING STATE SERIALIZATION

```python
import json
from pathlib import Path

def test_state_round_trip():
    """Test that state can be exported and re-imported."""
    # Create initial state
    state1 = MyAnalysisState()
    state1.image_path = Path("test.tif")
    state1.processing_params = {"threshold": 0.5}
    
    # Export to dict
    data = state1.to_workflow_dict()
    
    # Should be JSON-serializable
    json_str = json.dumps(data)
    data_loaded = json.loads(json_str)
    
    # Import back to state
    state2 = MyAnalysisState.from_workflow_dict(data_loaded)
    
    # Verify
    assert state2.image_path == state1.image_path
    assert state2.processing_params == state1.processing_params

if __name__ == "__main__":
    test_state_round_trip()
    print("✓ State serialization test passed")
```

---

## 💡 TIPS & BEST PRACTICES

1. **Keep state separate from UI** → Makes testing easier, enables serialization
2. **Use dataclasses for state** → Simple, automatic serialization
3. **Emit signals at key points** → Enables undo/redo, extensions
4. **Use inherited shared components** → PrimaryButton, HeaderLabel, etc
5. **Put expensive computation in background tasks** → Keep UI responsive
6. **Document signals and their signatures** → Help future developers
7. **Test state round-trips** → Ensure save/load works correctly
8. **Use theme colors/fonts** → Consistency, easy theme switching
9. **Validate before advancing in wizards** → Better UX, error prevention
10. **Keep canvas operations vectorized** → Performance with large images

