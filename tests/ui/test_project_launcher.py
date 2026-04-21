"""Tests for ProjectLauncherWindow (BioPro Hub)."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import Qt
from biopro.ui.windows.project_launcher import ProjectLauncherWindow

class TestProjectLauncher:
    @pytest.fixture
    def launcher(self, qtbot):
        # Dependencies
        mock_mm = MagicMock()
        mock_updater = MagicMock()
        mock_store_cb = MagicMock()
        mock_hub_cb = MagicMock()
        
        # Prevent perform_startup_check from blocking during init (it uses timers)
        with patch("biopro.ui.windows.project_launcher.QTimer.singleShot"):
            win = ProjectLauncherWindow(mock_mm, mock_updater, mock_store_cb, mock_hub_cb)
            qtbot.addWidget(win)
            return win

    def test_launcher_initialization(self, launcher):
        """Verify window titles and branding elements."""
        assert "BioPro Hub" in launcher.windowTitle()
        assert launcher.lbl_title.text() == "BioPro"
        assert launcher.lbl_badge.text() == "BETA"

    @patch("biopro.ui.windows.project_launcher.AppConfig")
    def test_load_recent_projects(self, mock_config_class, launcher):
        """Verify that recent projects from config are listed."""
        mock_config = mock_config_class.return_value
        temp_proj = Path("fake_project.biopro")
        mock_config.get_recent_projects.return_value = [str(temp_proj.parent)]
        
        with patch.object(Path, "exists", return_value=True):
            launcher._load_recent_projects()
            assert launcher.list_recent.count() == 1

    @patch("biopro.ui.windows.project_launcher.QInputDialog.getText")
    @patch("biopro.ui.windows.project_launcher.QFileDialog.getExistingDirectory")
    @patch("biopro.ui.windows.project_launcher.ProjectManager")
    def test_on_new_project_flow(self, mock_pm_class, mock_file_dig, mock_input_dig, launcher):
        """Verify successful project creation flow."""
        with patch.object(launcher, "_launch_workspace"):
            mock_input_dig.return_value = ("NewProject", True)
            mock_file_dig.return_value = "/fake/path"
            launcher._on_new_project()
            mock_pm_class.assert_called_once()

    @patch("biopro.ui.windows.project_launcher.QFileDialog.getExistingDirectory")
    @patch("biopro.ui.windows.project_launcher.ProjectManager")
    def test_on_open_project_flow(self, mock_pm_class, mock_file_dig, launcher):
        """Verify successful project opening flow."""
        with patch.object(launcher, "_launch_workspace"):
            mock_file_dig.return_value = "/fake/existing_project"
            launcher._on_open_project()
            mock_pm_class.assert_called_once()

    @patch("biopro.ui.windows.project_launcher.WorkspaceWindow")
    @patch("biopro.ui.windows.project_launcher.AppConfig")
    def test_launch_workspace_transition(self, mock_config_class, mock_workspace_class, launcher):
        """Verify transition from Hub to Workspace."""
        mock_pm = MagicMock(project_dir=Path("/fake/proj"))
        launcher._launch_workspace(mock_pm)
        mock_workspace_class.assert_called_once()
        # close() hides the window
        assert launcher.isHidden() is True
