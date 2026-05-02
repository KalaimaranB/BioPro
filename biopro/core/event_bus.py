"""BioPro Event Bus (The Nervous System).

Provides a global, thread-safe EventManager for decoupled communication
between core components and UI. Built on PyQt6 signals.
"""

from enum import Enum, auto
from PyQt6.QtCore import QObject, pyqtSignal
import logging

logger = logging.getLogger(__name__)

class BioProEvent(Enum):
    """Enumeration of all system-wide events."""
    # Plugin Lifecycle
    PLUGIN_INSTALLED = auto() # args: (plugin_id: str)
    PLUGIN_REMOVED = auto()   # args: (plugin_id: str)
    PLUGIN_UPDATED = auto()   # args: (plugin_id: str)
    
    # Project Lifecycle
    PROJECT_LOADED = auto()   # args: (project_path: str)
    PROJECT_CLOSED = auto()   # args: ()
    
    # System Events
    THEME_CHANGED = auto()    # args: (theme_name: str)

class EventManager(QObject):
    """Central event coordinator.
    
    Use the global 'event_bus' instance for most operations.
    """
    
    # Internal signal used to route all events through the Qt event loop
    _internal_bus = pyqtSignal(BioProEvent, tuple, dict)

    def __init__(self):
        super().__init__()
        self._listeners = {}
        self._internal_bus.connect(self._dispatch)

    def subscribe(self, event_type: BioProEvent, callback):
        """Register a callback for a specific event.
        
        Args:
            event_type (BioProEvent): The type of event to listen for.
            callback (callable): The function to call when the event occurs.
                                Must accept the arguments emitted by the event.
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        
        if callback not in self._listeners[event_type]:
            self._listeners[event_type].append(callback)
            logger.debug(f"Subscribed to {event_type.name}: {callback}")

    def unsubscribe(self, event_type: BioProEvent, callback):
        """Unregister a callback.
        
        Args:
            event_type (BioProEvent): The type of event to unsubscribe from.
            callback (callable): The previously registered function to remove.
        """
        if event_type in self._listeners:
            if callback in self._listeners[event_type]:
                self._listeners[event_type].remove(callback)
                logger.debug(f"Unsubscribed from {event_type.name}: {callback}")

    def emit(self, event_type: BioProEvent, *args, **kwargs):
        """Broadcast an event to all subscribers.
        
        Safe to call from any thread. Payloads are automatically routed 
        to the main UI thread for thread-safe processing.

        Args:
            event_type (BioProEvent): The event to broadcast.
            *args: Positional arguments to pass to listeners.
            **kwargs: Keyword arguments to pass to listeners.
        """
        # We use the internal signal to ensure that if this is called from a
        # background thread, it gets queued and dispatched on the thread 
        # where the EventManager lives (typically the Main UI Thread).
        self._internal_bus.emit(event_type, args, kwargs)

    def _dispatch(self, event_type: BioProEvent, args: tuple, kwargs: dict):
        """Invoke all listeners for the given event."""
        if event_type in self._listeners:
            for callback in self._listeners[event_type]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in listener for {event_type.name}: {e}")

# Internal singleton instance
_event_bus_instance = None

def get_event_bus() -> EventManager:
    """Get the global application event bus (Nervous System)."""
    global _event_bus_instance
    if _event_bus_instance is None:
        _event_bus_instance = EventManager()
    return _event_bus_instance

# For backward compatibility and convenience
# Note: This will still trigger instantiation if imported directly, 
# but we can now use get_event_bus() in sensitive areas.
event_bus = get_event_bus()
