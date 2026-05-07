# 📖 BioPro SDK API Reference: UI Framework (`biopro.sdk.ui`)

This document provides formal technical specifications for the theme-aware widgets, semantic components, and multi-step Wizard panels within the `biopro.sdk.ui` namespace.

---

## 🎨 Semantic Components

### `PrimaryButton` (Class)
`class biopro.sdk.ui.PrimaryButton(text: str, parent: Optional[QWidget] = None)`
*Inherits from `QPushButton`*

A prominent, high-visibility call-to-action button respecting the active BioPro accent theme color (typically Blue or Gold). Features built-in micro-animations for hover, focus, and click states.

---

### `SecondaryButton` (Class)
`class biopro.sdk.ui.SecondaryButton(text: str, parent: Optional[QWidget] = None)`
*Inherits from `QPushButton`*

A subtle secondary action button with a semi-transparent background and explicit border coloring.

---

### `DangerButton` (Class)
`class biopro.sdk.ui.DangerButton(text: str, parent: Optional[QWidget] = None)`
*Inherits from `QPushButton`*

A high-risk action button colored with critical danger warning red (`Colors.ACCENT_DANGER`).

---

### `ModuleCard` (Class)
`class biopro.sdk.ui.ModuleCard(parent: Optional[QWidget] = None)`
*Inherits from `QFrame`*

A container widget displaying a card-like layout with a rounded border, styled background (`Colors.BG_DARK`), and glowing margins. Useful for grouping related forms or listing dataset modules.

---

### `HeaderLabel` (Class)
`class biopro.sdk.ui.HeaderLabel(text: str, parent: Optional[QWidget] = None)`
*Inherits from `QLabel`*

A styled label for main section headings, utilizing `Fonts.FAMILY_HEADINGS` and sized at `Fonts.SIZE_XLARGE`.

---

### `SubtitleLabel` (Class)
`class biopro.sdk.ui.SubtitleLabel(text: str, parent: Optional[QWidget] = None)`
*Inherits from `QLabel`*

A styled label for secondary subheadings, utilizing `Fonts.FAMILY_HEADINGS` and sized at `Fonts.SIZE_LARGE` with a muted gray tone (`Colors.FG_SECONDARY`).

---

## 🧙 Workflow Wizards

### `WizardStep` (Class)
`class biopro.sdk.ui.WizardStep`
*Abstract Class*

Represents a single step or page inside a multi-step workflow wizard. Subclasses must implement the layout setup and navigation validation methods.

#### Methods

##### `build_page(panel: WizardPanel) -> QWidget`
***Abstract Method.*** Must be implemented by subclasses. Instantiates, assembles, and returns the main layout widget for this wizard step.
* **Parameters:**
  * `panel` (`WizardPanel`): The parent wizard panel controller.
* **Returns:** `QWidget` — The fully built step widget.

##### `on_next(panel: WizardPanel) -> bool`
***Abstract Method.*** Invoked when the user clicks "Next". Must validate input states. Return `True` to allow navigation to the next step, or `False` to halt.
* **Parameters:**
  * `panel` (`WizardPanel`): The parent wizard panel controller.
* **Returns:** `bool` — Validation result.

##### `on_enter() -> None`
*Optional Hook.* Invoked immediately after this step becomes the active page. Useful for loading cached data or refreshing lists.

##### `on_leave() -> None`
*Optional Hook.* Invoked immediately before this step transitions away.

---

### `WizardPanel` (Class)
`class biopro.sdk.ui.WizardPanel(steps: list[WizardStep], parent: Optional[QWidget] = None)`
*Inherits from `QWidget`*

A controller container managing a stack of `WizardStep` instances, rendering a shared `StepIndicator` at the top and navigation buttons ("Back", "Next") at the bottom.

#### Methods

##### `next_step() -> None`
Triggers validation on the current step (`on_next()`). If valid, advances the active page index by one.

##### `prev_step() -> None`
Navigates back to the previous step.

##### `get_current_step() -> WizardStep`
Returns the currently visible step instance.
* **Returns:** `WizardStep` — Active step controller.

##### `set_current_step(index: int) -> None`
Programmatically switches the wizard to the target step index.
* **Parameters:**
  * `index` (int): Zero-indexed step index.

---

### `StepIndicator` (Class)
`class biopro.sdk.ui.StepIndicator(steps: list[str], parent: Optional[QWidget] = None)`
*Inherits from `QWidget`*

A visual bar showing a horizontal sequence of step labels, highlighting the current step in the active theme accent color and rendering completed steps with checkmark indicators.

---

## 💻 Full Code Example

Below is a complete, copy-pasteable implementation of a theme-compliant multi-step wizard using the UI submodules.

```python
from PyQt6.QtWidgets import QVBoxLayout, QLabel, QLineEdit
from biopro.sdk.ui import WizardPanel, WizardStep, PrimaryButton, HeaderLabel

class LoadStep(WizardStep):
    def build_page(self, panel: WizardPanel) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(HeaderLabel("Step 1: Load Dataset"))

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter dataset identifier...")
        layout.addWidget(self.input_field)

        return widget

    def on_next(self, panel: WizardPanel) -> bool:
        # Halt navigation if input is empty
        val = self.input_field.text().strip()
        if not val:
            from biopro.sdk.utils import show_error
            show_error(panel, "Validation Error", "Dataset identifier cannot be empty!")
            return False
        return True

class ProcessStep(WizardStep):
    def build_page(self, panel: WizardPanel) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(HeaderLabel("Step 2: Analysis Execution"))
        layout.addWidget(QLabel("Ready to compute peaks..."))
        return widget

    def on_next(self, panel: WizardPanel) -> bool:
        return True

# To display the Wizard inside a window:
# steps = [LoadStep(), ProcessStep()]
# wizard = WizardPanel(steps)
# wizard.show()
```
