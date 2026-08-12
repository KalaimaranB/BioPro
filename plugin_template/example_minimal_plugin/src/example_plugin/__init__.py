"""Example minimal plugin exposing `get_plugin()` for BioPro."""

from biopro_sdk.core import PluginBase as SDKPluginBase


class ExamplePlugin(SDKPluginBase):
    """Minimal plugin implementation.

    This plugin demonstrates the required contract: `get_state`, `set_state`, and
    `cleanup`.
    """

    def __init__(self, plugin_id: str = "example.minimal", parent: object | None = None):
        """Initialize the example plugin.

        Args:
            plugin_id: Optional plugin identifier used by the host.
            parent: Optional parent object for lifecycle ownership.
        """
        super().__init__(plugin_id, parent=parent)
        self._state = {"counter": 0}

    def get_state(self) -> dict:
        """Return a shallow copy of the plugin state.

        Returns:
            A dict representing the plugin's current state.
        """
        return dict(self._state)

    def set_state(self, state: dict) -> None:
        """Merge the provided `state` into the plugin's internal state.

        Args:
            state: A mapping of state keys to values to merge.
        """
        self._state.update(state)

    def cleanup(self) -> None:
        """Perform plugin teardown: stop workers and release resources.

        The host will call this method when the plugin is being unloaded.
        """
        # stop background workers, remove timers
        pass


def get_plugin():
    """Factory function invoked by ModuleManager to instantiate the plugin."""
    return ExamplePlugin()
