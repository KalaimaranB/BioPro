# 📖 BioPro SDK API Reference Manual

Welcome to the official developer reference manual for the **BioPro Software Development Kit (SDK)**. This documentation provides comprehensive technical specifications, type-annotated signatures, and in-depth class details for building high-performance, robust, and theme-compliant scientific analysis plugins.

To maintain optimal organization, the reference specifications have been divided into dedicated manuals for each major architectural submodule:

---

## 🏛 [1. Core SDK Submodule (`biopro.sdk.core`)](16_API_Reference_Core.md)

Contains the foundational classes, protocol contracts, thread execution managers, and communication brokers essential for all plugin systems.
* **Key Classes:**
  * `PluginBase` — Base controller encapsulating state capture, undo/redo stacks, and automated resource cleanup (RAII).
  * `PluginState` — Base serializable dataclass for representing current user and analysis state.
  * `PluginSignals` — Standardized PyQt6 signal manager for thread synchronization and status reporting.
  * `CentralEventBus` — Thread-safe global pub/sub event broker for decoupled inter-plugin communication.
  * `AnalysisBase` & `AnalysisWorker` — Computation separation controllers for background calculations.

---

## 🎨 [2. UI Framework Submodule (`biopro.sdk.ui`)](16_API_Reference_UI.md)

Houses theme-aware widgets, rounded card panels, semantic buttons, and the step-by-step analysis wizard framework.
* **Key Components:**
  * Semantic Buttons — `PrimaryButton`, `SecondaryButton`, and `DangerButton`.
  * `ModuleCard` — Rounded containers with glowing focus outlines for list layouts.
  * `WizardPanel` & `WizardStep` — Interactive, multi-page guided wizard workflow framework.
  * `StepIndicator` — Dynamic horizontal step tracking bar.

---

## 🔧 [3. Utilities Submodule (`biopro.sdk.utils`)](16_API_Reference_Utils.md)

A rich utility collection facilitating persistent file storage, user dialog prompt, and strict mathematical/string input validations.
* **Key Utilities:**
  * Themed Dialogs — Native dialog helpers for selecting files, folders, double numbers, integers, and text.
  * `PluginConfig` — Local persistent configuration storage engine (`~/.biopro/plugin_configs/`).
  * Strict Validators — Boundary clippers and empty-string checks (`validate_value_range`, `validate_file_exists`).

---

## 🧪 [4. Contrib Submodule (`biopro.sdk.contrib`)](16_API_Reference_Contrib.md)

Optional, community-supported scientific utility libraries designed to accelerate common domain-specific operations (e.g. image processing).
* **Key Utilities:**
  * Grayscale Loaders — Normalizing high-resolution images (`load_and_convert` to grayscale range `[0.0, 1.0]`).
  * Contrast & Inversion — Automatic contrast adjustments, rotations, and inversion checks.
  * Auto-Cropper — `crop_to_content` for removing empty margins around scientific gel blots or cytometry cell fields.
