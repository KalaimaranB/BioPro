"""Basic UI smoke tests for the BioPro Hub window."""

import pytest
from PyQt6.QtCore import Qt
from biopro.ui.windows.project_launcher import ProjectLauncherWindow
from biopro.core.module_manager import ModuleManager

@pytest.fixture
def mm():
    """ModuleManager fixture."""
    return ModuleManager()

@pytest.fixture
def launcher(qtbot, mm):
    """Fixture to create and track the Hub window."""
    # Mock callbacks
    mock_store = lambda x: None
    mock_hub = lambda: None
    
    # Note: ProjectLauncherWindow currently instantiates its own NetworkUpdater 
    # in __init__, which might trigger network logic. 
    window = ProjectLauncherWindow(mm, None, mock_store, mock_hub)
    qtbot.addWidget(window)
    return window

@pytest.mark.qt
class TestHubUI:
    """UI tests for the Project Launcher."""

    def test_window_content(self, launcher):
        """Verifies basic UI elements are present."""
        # Print for debugging in case of failure
        print(f"DEBUG: Title={launcher.windowTitle()}")
        print(f"DEBUG: lbl_title={launcher.lbl_title.text()}")
        
        assert "BioPro Hub" in launcher.windowTitle()
        assert "BioPro" in launcher.lbl_title.text()

    def test_recent_projects_list_exists(self, launcher):
        """Verifies the recent projects panel is initialized."""
        assert hasattr(launcher, 'list_recent')
        # Even if empty, it should have the 'No recent projects' item or be empty
        assert launcher.list_recent.count() >= 0

    def test_resize_scaling(self, launcher):
        """Smoke test for the dynamic coordinate scaling on resize."""
        original_size = launcher.size()
        launcher.resize(1200, 800)
        # Should not crash during resizeEvent
        assert launcher.width() == 1200
        # Restore
        launcher.resize(original_size)
