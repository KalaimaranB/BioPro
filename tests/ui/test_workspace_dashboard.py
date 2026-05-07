"""Tests for WorkspaceDashboard UI."""

from unittest.mock import patch

import pytest

from biopro.ui.components.cards import DashboardWorkflowCard, ModuleCard
from biopro.ui.dashboards.workspace_dashboard import WorkspaceDashboard


class TestWorkspaceDashboard:
    @pytest.fixture
    def dashboard(self, qtbot):
        db = WorkspaceDashboard()
        qtbot.addWidget(db)
        return db

    def test_initial_greeting(self, dashboard):
        """Verifies that a greeting is set upon initialization."""
        assert dashboard.lbl_greeting.text().endswith(".")
        assert "Bio-Image Analysis" in dashboard.lbl_tagline.text()

    def test_populate_modules(self, dashboard):
        """Verifies module card generation."""
        manifests = [
            {"id": "m1", "name": "Mod 1", "icon": "A", "description": "Desc 1"},
            {"id": "m2", "name": "Mod 2", "icon": "B", "description": "Desc 2"},
        ]
        dashboard.populate_modules(manifests)

        # Check that cards were added
        cards = dashboard.findChildren(ModuleCard)
        assert len(cards) == 2

        # Check stat label
        text = dashboard.stat_modules.text()
        assert "2" in text
        assert "Modules" in text

        # Click a card
        signal_data = []
        dashboard.module_selected.connect(lambda m: signal_data.append(m))

        cards[0].clicked.emit()
        assert signal_data[0]["id"] == "m1"

    def test_populate_workflows(self, dashboard):
        """Verifies workflow card generation and visibility."""
        workflows = [
            {
                "filename": "w1.json",
                "module_id": "mod_a",
                "name": "Workflow 1",
                "timestamp": "2026-01-01",
            },
        ]
        dashboard.populate_workflows(workflows)

        # Verify visibility (use isHidden since isVisible depends on parent mapping)
        assert not dashboard.workflows_container.isHidden()

        # Check that we have a WorkflowCard
        cards = dashboard.findChildren(DashboardWorkflowCard)
        assert len(cards) == 1
        assert cards[0].title_lbl.text() == "Workflow 1"

        # Verify empty state
        dashboard.populate_workflows([])
        assert dashboard.workflows_container.isHidden()

    @patch("biopro.ui.dashboards.workspace_dashboard.QMessageBox.question")
    def test_workflow_delete_flow(self, mock_quest, dashboard):
        """Verifies the delete confirmation flow."""
        workflows = [{"filename": "del.json", "module_id": "m", "name": "Target"}]
        dashboard.populate_workflows(workflows)

        from PyQt6.QtWidgets import QMessageBox

        # 1. User says NO
        mock_quest.return_value = QMessageBox.StandardButton.No
        signal_received = []
        dashboard.workflow_delete_requested.connect(lambda mid, fn: signal_received.append(fn))

        cards = dashboard.findChildren(DashboardWorkflowCard)
        cards[0].delete_requested.emit()
        assert len(signal_received) == 0

        # 2. User says YES
        mock_quest.return_value = QMessageBox.StandardButton.Yes
        cards[0].delete_requested.emit()
        assert "del.json" in signal_received

    def test_galactic_mode_text(self, dashboard):
        """Verifies overrides when Galactic theme is loaded."""
        from biopro.ui.theme import Strings, theme_manager

        orig_name = theme_manager.current_theme_name
        orig_tagline = Strings.TAGLINE
        orig_greeting = Strings.GREETING

        theme_manager.current_theme_name = "Galactic (Dark Side)"
        Strings.TAGLINE = "Galactic Empire"
        Strings.GREETING = "Commander"

        dashboard._update_dashboard_text()
        assert "Galactic" in dashboard.lbl_tagline.text()
        assert "Commander" in dashboard.lbl_greeting.text()

        # Reset
        theme_manager.current_theme_name = orig_name
        Strings.TAGLINE = orig_tagline
        Strings.GREETING = orig_greeting
        dashboard._update_dashboard_text()
        assert "Galactic" not in dashboard.lbl_tagline.text()
