"""BioPro SDK — Complete plugin development framework.

Provides everything needed to build plugins:

Core Components:
    - PluginBase: Main plugin class to inherit from
    - PluginState: State management with undo/redo
    - PluginSignals: Standard signals for communication
    - AnalysisBase: Abstract analysis logic class
    - AnalysisWorker: Background worker for threads

UI Components:
    - PrimaryButton, SecondaryButton, DangerButton: Semantic buttons
    - ModuleCard, HeaderLabel: Styled components
    - WizardStep, WizardPanel: Multi-step interface framework

Utilities:
    - Dialogs: File, message, and input dialogs
    - I/O: JSON and configuration management
    - Validation: Input validation helpers

Contrib (Optional):
    - Image utilities: Common image processing functions

Example:
    >>> from biopro.sdk.core import PluginBase, PluginState
    >>> from biopro.sdk.ui import PrimaryButton, WizardPanel
    >>> from biopro.sdk.utils import show_error
    >>>
    >>> class MyState(PluginState):
    ...     image_path: str = ""
    ...
    >>> class MyPlugin(PluginBase):
    ...     def __init__(self, plugin_id: str):
    ...         super().__init__(plugin_id)
    ...         self.state = MyState()
    ...
    ...     def get_state(self) -> PluginState:
    ...         return self.state
    ...
    ...     def set_state(self, state: PluginState) -> None:
    ...         self.state = state
"""

from . import core, ui, utils, contrib

from .core.events import CentralEventBus
from .core.docs import PluginDocumentation, docs_registry
from .core.ai import AIAssistant, AIServerManager, ai_manager

from .core import (
    PluginBase,
    PluginState,
    PluginSignals,
    AnalysisBase,
    AnalysisWorker,
)

from .ui import (
    PrimaryButton,
    SecondaryButton,
    DangerButton,
    ModuleCard,
    HeaderLabel,
    SubtitleLabel,
    StepIndicator,
    WizardStep,
    WizardPanel,
)

from .utils import (
    get_image_path,
    get_save_path,
    get_directory,
    show_info,
    show_warning,
    show_error,
    ask_yes_no,
    ask_ok_cancel,
    get_text,
    get_number,
    get_double,
    load_json,
    save_json,
    PluginConfig,
    validate_file_exists,
    validate_directory_exists,
    validate_value_range,
    validate_positive,
    validate_non_negative,
    validate_not_empty,
)

__all__ = [
    # Submodules
    "core",
    "ui",
    "utils",
    "contrib",
    # Core
    "PluginBase",
    "PluginState",
    "PluginSignals",
    "AnalysisBase",
    "AnalysisWorker",
    "CentralEventBus",
    "PluginDocumentation",
    "docs_registry",
    "AIAssistant",
    "AIServerManager",
    "ai_manager",
    # UI
    "PrimaryButton",
    "SecondaryButton",
    "DangerButton",
    "ModuleCard",
    "HeaderLabel",
    "SubtitleLabel",
    "StepIndicator",
    "WizardStep",
    "WizardPanel",
    # Utils
    "get_image_path",
    "get_save_path",
    "get_directory",
    "show_info",
    "show_warning",
    "show_error",
    "ask_yes_no",
    "ask_ok_cancel",
    "get_text",
    "get_number",
    "get_double",
    "load_json",
    "save_json",
    "PluginConfig",
    "validate_file_exists",
    "validate_directory_exists",
    "validate_value_range",
    "validate_positive",
    "validate_non_negative",
    "validate_not_empty",
]
