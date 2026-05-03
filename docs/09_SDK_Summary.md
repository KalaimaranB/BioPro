# BioPro SDK Summary

## Overview

The BioPro SDK is a comprehensive development framework that enables researchers and developers to build specialized analysis plugins. It provides standardized infrastructure for state management, UI components, background analysis, and cross-plugin communication.

## Core Architecture

The SDK is organized into four main pillars within the `biopro.sdk` namespace:

### 1. **Core SDK** (`biopro.sdk.core`)
The foundational logic for all plugins.
- **PluginBase**: Main widget class with integrated undo/redo, state persistence, and RAII cleanup.
- **PluginState**: Dataclass-based state management with automatic serialization.
- **AnalysisBase**: Abstract class for mathematical logic, decoupled from the UI.
- **AnalysisWorker**: Translation layer for running analysis in background threads.
- **Central Event Bus**: Asynchronous, decoupled communication system using `CentralEventBus.publish/subscribe`.
- **AI Assistant**: Integration for Gemma 4 powered analysis and natural language queries.

### 2. **UI Framework** (`biopro.sdk.ui`)
High-level semantic components that respect the BioPro theme.
- **Semantic Buttons**: `PrimaryButton`, `SecondaryButton`, `DangerButton`.
- **Workflow Wizards**: `WizardPanel` and `WizardStep` for step-by-step analysis flows.
- **Data Visualization**: Specialized components like `StepIndicator` and `ModuleCard`.

### 3. **Utilities** (`biopro.sdk.utils`)
Common helper functions to reduce boilerplate.
- **Standard Dialogs**: Image selection, save dialogs, and user prompts.
- **I/O Helpers**: Robust JSON and configuration management (`PluginConfig`).
- **Validation**: Pre-built validators for files, ranges, and input types.
- **Security**: The `biopro-sign` tool for cryptographic plugin verification.

### 4. **Contrib** (`biopro.sdk.contrib`)
Community-contributed utilities and domain-specific helpers.
- **Image Processing**: Helpers for contrast adjustment, inversion detection, and denoising.

---

## New & Key Features

### 🔄 Time Machine (Undo/Redo)
BioPro provides automatic state capture. By calling `self.push_state()` in your plugin, the framework takes a snapshot of your `@dataclass` state. This enables:
- Infinite Undo/Redo without manual history tracking.
- Structural sharing (large arrays like TIFs are only stored once if they haven't changed).

### 📡 Central Event Bus
Plugins can now communicate without direct dependencies.
```python
from biopro.sdk.core.events import CentralEventBus

# In Plugin A
CentralEventBus.publish("experiment_id_changed", "EXP-402")

# In Plugin B
CentralEventBus.subscribe("experiment_id_changed", self._on_experiment_update)
```

### 🧠 AI Assistant Integration
Every SDK plugin can now query the built-in Gemma 4 model for technical help or data analysis assistance via `biopro.sdk.core.ai`.

### 🧹 Automatic Resource Cleansing (RAII)
To prevent memory leaks with large scientific datasets, `PluginBase` implements an automatic `cleanup()` method. When a plugin tab is closed, BioPro's `ResourceInspector` automatically:
1. Nulls out heavy Numpy arrays and Torch tensors.
2. Closes dangling file handles.
3. Releases GPU memory if applicable.

### ⏺️ Context-Aware Logging & Diagnostics
Every plugin now features a built-in `self.logger`. Messages logged here are:
1. **Scoped**: Automatically tagged with the `plugin_id`.
2. **Recorded**: Piped into the system-wide **Black Box** diagnostic recorder.
3. **Actionable**: Captured in detailed crash reports, allowing developers to see the exact state of a plugin before a system failure.

---

## Benefits

- **60% Less Boilerplate**: Common tasks (threading, saving, undo) are handled by the SDK.
- **UI Consistency**: Plugins automatically match the core application's theme and font system.
- **Memory Efficiency**: Structural sharing in history and automatic cleanup prevent application crashes during long sessions.
- **Security**: Built-in signing ensures code integrity and scientific reproducibility.

## Getting Started

New developers should follow these steps:
1. Read the [Developer Handbook](06_Developer_Handbook.md) for a quick start.
2. Follow the [Module Author Guide](07_Module_Author_Guide.md) for deep-dive technical references.
3. Use the `biopro-sign` CLI tool to initialize your developer identity.

---

## FAQ

**Q: Do I have to use the SDK?**
A: No, it's optional. Existing plugins work as-is. But new plugins should use it for better integration and stability.

**Q: Where should I store my plugin's configuration?**
A: Use `PluginConfig` — it automatically stores JSON settings in `~/.biopro/plugin_configs/`.

**Q: How do I make my analysis run in the background?**
A: Use `task_scheduler.submit(analyzer, state)`. It handles all threading for you and avoids UI freezing.
