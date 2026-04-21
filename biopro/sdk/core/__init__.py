"""BioPro SDK Core — Base classes for plugin development.

Provides:
- PluginSignals: Standard PyQt6 signals for plugin communication
- PluginState: Base class for serializable plugin state
- AnalysisBase: Abstract base for analysis logic
- AnalysisWorker: Background worker for thread execution
- PluginBase: Main plugin class to inherit from
"""

from .signals import PluginSignals
from .state import PluginState
from .analysis import AnalysisBase, AnalysisWorker
from .base import PluginBase
from .managed_task import FunctionalTask

__all__ = [
    "PluginSignals",
    "PluginState",
    "AnalysisBase",
    "AnalysisWorker",
    "PluginBase",
    "FunctionalTask",
]
