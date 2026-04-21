"""Tests for the formal BioPro Plugin Contract (Track 1)."""

import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QWidget
from biopro.sdk.core.interfaces import BioProPlugin
from biopro.sdk.core.base import PluginBase
from biopro.core.module_manager import ModuleManager

class MockValidPlugin:
    """A module-like object that satisfies the BioProPlugin Protocol."""
    __version__ = "1.0.0"
    __plugin_id__ = "test_mod"
    
    @staticmethod
    def get_panel_class():
        return QWidget

    def cleanup(self) -> None: pass
    def shutdown(self) -> None: pass

class MockInvalidPlugin:
    """A module-like object that fails the BioProPlugin Protocol (missing get_panel_class)."""
    __version__ = "1.0.0"
    __plugin_id__ = "bad_mod"

class TestPluginContract:
    def test_protocol_runtime_check(self):
        """Verifies that runtime_checkable protocol works on modules and classes."""
        assert isinstance(MockValidPlugin, BioProPlugin)
        assert not isinstance(MockInvalidPlugin, BioProPlugin)

    def test_plugin_base_satisfies_contract(self):
        """Verifies that the SDK's PluginBase satisfies the protocol."""
        class MyPlugin(PluginBase):
            def get_state(self): return None
            def set_state(self, s): pass
            def cleanup(self): pass
            def shutdown(self): pass
            
        # The class itself should satisfy it (via get_panel_class classmethod)
        assert isinstance(MyPlugin, BioProPlugin)

    @patch("biopro.core.module_manager.importlib.import_module")
    def test_module_manager_validation_pass(self, mock_import):
        """Verifies that ModuleManager allows loading valid plugins."""
        from tests.core.test_module_manager import PermissiveTrustManager
        mm = ModuleManager(trust_manager=PermissiveTrustManager())
        mm.modules["mod_a"] = {"package_name": "mod_a", "loaded": False}
        
        mock_import.return_value = MockValidPlugin
        
        # Should not raise exception
        ui_class = mm.load_module_ui("mod_a")
        assert ui_class == QWidget
        assert mm.modules["mod_a"]["loaded"] is True

    @patch("biopro.core.module_manager.importlib.import_module")
    def test_module_manager_validation_fail(self, mock_import):
        """Verifies that ModuleManager rejects invalid plugins."""
        from tests.core.test_module_manager import PermissiveTrustManager
        mm = ModuleManager(trust_manager=PermissiveTrustManager())
        mm.modules["bad_mod"] = {"package_name": "bad_mod", "loaded": False}
        
        mock_import.return_value = MockInvalidPlugin
        
        # Should raise TypeError during validation
        with pytest.raises(TypeError) as exc:
            mm.load_module_ui("bad_mod")
        
        assert "does not satisfy BioProPlugin protocol" in str(exc.value)
        assert mm.modules["bad_mod"]["loaded"] is False
