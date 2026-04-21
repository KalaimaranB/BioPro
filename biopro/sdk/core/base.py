"""Base plugin class for BioPro SDK.

Provides the main PluginBase class that all plugins should inherit from,
with integrated state management and undo/redo support.
"""

from abc import abstractmethod

from PyQt6.QtWidgets import QWidget

from biopro.core.history_manager import HistoryManager
from .signals import PluginSignals
from .state import PluginState
from .interfaces import BioProPlugin
from biopro.core.resource_inspector import ResourceInspector


class PluginBase(QWidget):
    """Abstract base class for all BioPro plugins.
    
    This class implements the BioProPlugin Protocol.
    """
    """Abstract base class for all BioPro plugins.
    
    Provides:
    - Standard signals (status, state_changed, analysis_*, etc)
    - History management integration for undo/redo
    - State serialization/deserialization
    - Consistent plugin interface
    
    All plugins must inherit from this class and implement get_state() and set_state().
    
    Example:
        >>> class MyPlugin(PluginBase):
        ...     def __init__(self, plugin_id: str):
        ...         super().__init__(plugin_id)
        ...         self.state = MyState()
        ...         self.analyzer = MyAnalyzer(plugin_id)
        ...         # Build UI...
        ...     
        ...     def get_state(self) -> PluginState:
        ...         return self.state
        ...     
        ...     def set_state(self, state: PluginState) -> None:
        ...         self.state = state
        ...         self.update_ui()
    """
    
    def __init__(self, plugin_id: str, parent=None):
        """Initialize the plugin.
        
        Args:
            plugin_id: Unique identifier for this plugin
            parent: Parent QWidget (usually None for top-level plugins)
        """
        super().__init__(parent)
        self.signals = PluginSignals()
        
        self.plugin_id = plugin_id
        self.history = HistoryManager()
        self._current_state = None

    def __getattr__(self, name: str):
        """Proxy signal access to self.signals for convenience.
        
        Allows using `self.state_changed.emit()` instead of 
        `self.signals.state_changed.emit()`.
        """
        if hasattr(self, 'signals') and hasattr(self.signals, name):
            return getattr(self.signals, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
    
    @abstractmethod
    def get_state(self) -> PluginState:
        """Return the current analysis state.
        
        Must be implemented by subclasses. Called by BioPro core to capture
        plugin state for undo/redo and workflow persistence.
        
        Returns:
            Current PluginState instance
        """
        pass
    
    @abstractmethod
    def set_state(self, state: PluginState) -> None:
        """Set the plugin state and update UI accordingly.
        
        Must be implemented by subclasses. Called by BioPro core to restore
        plugin state during undo/redo and workflow loading.
        
        Args:
            state: PluginState instance to restore
        """
        pass
    
    def push_state(self) -> None:
        """Save current state to undo history.
        
        Call this whenever the user makes a destructive edit (e.g., changing
        a parameter, drawing on an image). BioPro will emit state_changed signal
        and automatically capture this state for undo/redo.
        """
        state_dict = self.get_state().to_dict()
        self.history.get_module_history(self.plugin_id).push(state_dict)
        self.state_changed.emit()
    
    def undo(self) -> None:
        """Undo to previous state."""
        history = self.history.get_module_history(self.plugin_id)
        prev_state_dict = history.undo()
        if prev_state_dict:
            state = self.get_state().__class__.from_dict(prev_state_dict)
            self.set_state(state)
            self.state_changed.emit()
    
    def redo(self) -> None:
        """Redo to next state."""
        history = self.history.get_module_history(self.plugin_id)
        next_state_dict = history.redo()
        if next_state_dict:
            state = self.get_state().__class__.from_dict(next_state_dict)
            self.set_state(state)
            self.state_changed.emit()
    
    def can_undo(self) -> bool:
        """Check if undo is available.
        
        Returns:
            True if there are states to undo to
        """
        history = self.history.get_module_history(self.plugin_id)
        return len(history.undo_stack) > 1
    
    def can_redo(self) -> bool:
        """Check if redo is available.
        
        Returns:
            True if there are states to redo to
        """
        history = self.history.get_module_history(self.plugin_id)
        return len(history.redo_stack) > 0

    # ── Resource Lifecycle (RAII) ────────────────────────────────────

    def cleanup(self) -> None:
        """Automatic Resource Cleansing.
        
        Uses ResourceInspector to break references to heavy objects in both 
        the plugin instance and its state. This helps the GC reclaim memory 
        immediately when a tab is closed.
        """
        # 1. Clean PluginState
        state = self.get_state()
        if state:
            heavy_in_state = ResourceInspector.get_heavy_resources(state)
            for name, _ in heavy_in_state:
                setattr(state, name, None)
        
        # 2. Clean Plugin Instance attributes
        heavy_in_instance = ResourceInspector.get_heavy_resources(self)
        for name, _ in heavy_in_instance:
            if name != "state": # Don't wipe the state container itself
                setattr(self, name, None)
                
        self.state_changed.emit()
        self.status_message.emit("Resources released.")

    def shutdown(self) -> None:
        """Default shutdown. Subclasses should override if managing GPU models."""
        pass

    def closeEvent(self, event):
        """Triggers automatic cleanup when the plugin widget is closed."""
        self.cleanup()
        super().closeEvent(event)

    # ── Protocol Compliance ───────────────────────────────────────────

    @property
    def __version__(self) -> str:
        return "1.0.0" # Default for base plugins

    @property
    def __plugin_id__(self) -> str:
        return self.plugin_id

    @classmethod
    def get_panel_class(cls):
        """Standard protocol requirement: return the class itself."""
        return cls
