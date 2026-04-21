"""Tests for WorkspaceWindow UI and logic."""

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from biopro.ui.windows.workspace_window import WorkspaceWindow, _PAGE_HOME, _PAGE_ANALYSIS
from biopro.ui.theme import Colors, theme_manager
from unittest.mock import MagicMock, patch

class TestWorkspaceWindow:
    @pytest.fixture
    def window(self, qtbot):
        # Setup mocks
        pm = MagicMock()
        pm.data = {"project_name": "Unit Testing"}
        pm.history_manager = MagicMock()
        
        mm = MagicMock()
        mm.get_available_modules.return_value = [
            {"id": "plugin_a", "name": "Plugin A", "icon": "A"}
        ]
        
        up = MagicMock()
        
        hub_cb = MagicMock()
        store_cb = MagicMock()
        
        win = WorkspaceWindow(pm, mm, up, store_cb, hub_cb)
        qtbot.addWidget(win)
        return win

    def test_initialization(self, window):
        assert "Unit Testing" in window.windowTitle()
        assert window.root_stack.currentIndex() == _PAGE_HOME
        # Verify populated modules
        assert window.home_screen.modules_grid.count() == 1

    @patch("biopro.ui.windows.workspace_window.QMessageBox.critical")
    def test_open_module_success(self, mock_err, window, qtbot):
        manifest = {"id": "plugin_a", "name": "Plugin A", "icon": "A"}
        
        # Mock UI loader with a real QWidget to avoid PyQt type issues
        class MockPanel(QWidget):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.load_state = MagicMock()
                self.export_state = MagicMock()
        
        window.module_manager.load_module_ui.return_value = MockPanel
        
        window._open_module(manifest)
        
        assert window.current_module_id == "plugin_a"
        assert isinstance(window.wizard_panel, MockPanel)
        # Verify title change in toolbar
        assert "Plugin A" in window.analysis_toolbar.title_lbl.text()
        mock_err.assert_not_called()

    @patch("biopro.ui.windows.workspace_window.QMessageBox.critical")
    def test_open_module_failure(self, mock_err, window):
        manifest = {"id": "broken", "name": "Broken"}
        window.module_manager.load_module_ui.side_effect = Exception("Load Failed")
        
        window._open_module(manifest)
        mock_err.assert_called_once()

    def test_history_integration(self, window, qtbot):
        """Verify that UI triggers push/undo/redo on HistoryManager."""
        window.current_module_id = "plugin_a"
        
        # Use simple widget with required methods
        class MockPanel(QWidget):
            def __init__(self):
                super().__init__()
                self.load_state = MagicMock()
                self.export_state = MagicMock()
                
        window.wizard_panel = MockPanel()
        window.wizard_panel.export_state.return_value = {"val": 1}
        
        history = MagicMock()
        window.project_manager.history_manager.get_module_history.return_value = history
        
        # 1. Push
        window._push_history()
        history.push.assert_called_with({"val": 1})
        
        # 2. Undo
        history.undo.return_value = {"val": 0}
        window.trigger_undo()
        window.wizard_panel.load_state.assert_called_with({"val": 0})
        
        # 3. Redo
        history.redo.return_value = {"val": 1}
        window.trigger_redo()
        window.wizard_panel.load_state.assert_called_with({"val": 1})

    def test_theme_changed_signal_rebuilds_hub(self, window, qtbot):
        """Verify that changing theme triggers UI rebuild logic."""
        old_home = window.home_screen
        
        with patch.object(window, "_refresh_hub_workflows") as mock_refresh:
            theme_manager.theme_changed.emit()
            
            # The window destroys the old home and creates a new one
            assert window.home_screen is not old_home
            mock_refresh.assert_called_once()

    def test_return_to_hub_cleanup(self, window, qtbot):
        """Verify that returning to hub closes project and triggers callback."""
        window.return_to_hub()
        
        # Note: project_manager.close() might be called multiple times during window 
        # destruction/handoff, so we verify it was called at least once.
        assert window.project_manager.close.called
        window.return_to_hub_callback.assert_called_once()

    def test_transition_animation_start(self, window, qtbot):
        """Verify that page transitions initiate animations."""
        window._transition_to_page(_PAGE_ANALYSIS)
        assert hasattr(window, "_anim_out")
        # Ensure the animation is targeting our fade effect
        assert window._anim_out.targetObject() is window._fade_effect
