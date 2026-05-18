"""Tests for PluginStoreDialog UI."""

from unittest.mock import MagicMock, patch

import pytest
from biopro_sdk.plugin import DangerButton, ModuleCard, PrimaryButton
from PyQt6.QtWidgets import QPushButton

from biopro.core.event_bus import BioProEvent, event_bus
from biopro.ui.dialogs.plugin_store import PluginStoreDialog


class TestPluginStore:
    @pytest.fixture
    def store(self, qtbot):
        mock_mm = MagicMock()
        mock_updater = MagicMock()

        dlg = PluginStoreDialog(mock_mm, mock_updater)
        qtbot.addWidget(dlg)
        return dlg

    def test_store_inventory_population(self, store):
        """Verifies that inventory data is rendered correctly into cards."""
        mock_inventory = {
            "p1": {
                "info": {
                    "name": "Plugin 1",
                    "version": "1.0.0",
                    "description": "Desc 1",
                    "icon": "📦",
                },
                "state": "INSTALL",
                "local_version": None,
            },
            "p2": {
                "info": {
                    "name": "Plugin 2",
                    "version": "2.0.0",
                    "description": "Desc 2",
                    "icon": "🚀",
                },
                "state": "UP_TO_DATE",
                "local_version": "2.0.0",
            },
        }

        with patch.object(store.updater, "evaluate_store_state", return_value=mock_inventory):
            store._load_store_data()

            # Should have 2 cards
            cards = store.findChildren(ModuleCard)
            assert len(cards) == 2

            # Check p1 button (INSTALL state)
            p1_btn = cards[0].findChild(PrimaryButton)
            assert p1_btn.text() == "Install"

            # Check p2 status (UP_TO_DATE state)
            # Find the "Remove" button
            p2_rm_btn = cards[1].findChild(DangerButton)
            assert p2_rm_btn.text() == "Remove"

    def test_install_module_flow(self, store):
        """Verifies the transition when 'Download' is clicked."""
        mod_data = {"name": "Test Plugin"}
        store.updater.install_plugin.return_value = (True, "Success")

        with patch.object(store, "_load_store_data") as mock_refresh:
            store._install_module("test_id", mod_data)

            # Simulate the "Nervous System" pulse
            event_bus.emit(BioProEvent.PLUGIN_INSTALLED, "test_id")

            store.updater.install_plugin.assert_called_with("test_id", mod_data)
            mock_refresh.assert_called_once()

    def test_remove_module_flow(self, store):
        """Verifies the transition when 'Remove' is clicked."""
        store.updater.remove_plugin.return_value = (True, "Success")

        with patch.object(store, "_load_store_data") as mock_refresh:
            store._remove_module("test_id")

            # Simulate the "Nervous System" pulse
            event_bus.emit(BioProEvent.PLUGIN_REMOVED, "test_id")

            store.updater.remove_plugin.assert_called_with("test_id")
            mock_refresh.assert_called_once()

    def test_incompatible_module_display(self, store):
        """Verifies display for incompatible plugins."""
        mock_inventory = {
            "p3": {
                "info": {"name": "New Plugin", "version": "3.0", "min_core_version": "2.0"},
                "state": "INCOMPATIBLE",
                "local_version": None,
            }
        }
        with patch.object(store.updater, "evaluate_store_state", return_value=mock_inventory):
            store._load_store_data()
            card = store.findChild(ModuleCard)
            buttons = card.findChildren(QPushButton)

            # Assert both 'Details' and 'Incompatible' buttons exist
            assert any(b.text() == "Details" for b in buttons)

            btn = next(b for b in buttons if b.text() == "Incompatible")
            assert "v2.0" in btn.toolTip()
            assert btn.isEnabled() is False

    def test_store_multi_author_display(self, store):
        """Verifies that an array of authors is joined correctly."""
        mock_inventory = {
            "p_multi": {
                "info": {
                    "name": "Team Plugin",
                    "version": "1.0",
                    "authors": [{"name": "Alice"}, {"name": "Bob"}],
                },
                "state": "INSTALL",
                "local_version": None,
            }
        }
        with patch.object(store.updater, "evaluate_store_state", return_value=mock_inventory):
            store._load_store_data()
            card = store.findChild(ModuleCard)
            from PyQt6.QtWidgets import QLabel

            labels = card.findChildren(QLabel)
            author_text = [lbl.text() for lbl in labels if "by Alice, Bob" in lbl.text()]
            assert len(author_text) == 1
