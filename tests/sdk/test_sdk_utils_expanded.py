"""Comprehensive tests for biopro.plugins.sdk_utils."""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from PyQt6.QtWidgets import QMessageBox, QInputDialog

from biopro.plugins.sdk_utils import (
    get_image_path, get_image_paths, import_assets_workflow,
    get_save_path, get_directory,
    show_info, show_warning, show_error, ask_yes_no, ask_ok_cancel,
    get_text, get_number, get_double,
    load_json, save_json, PluginConfig,
    validate_file_exists, validate_directory_exists, validate_value_range,
    get_plugin_logger, ProgressDialog
)

class TestSDKFileDialogs:
    """Tests for file and directory selection dialogs."""

    @patch("biopro.plugins.sdk_utils.QFileDialog.getOpenFileName")
    def test_get_image_path(self, mock_dialog):
        mock_dialog.return_value = ("/path/to/img.png", "filter")
        assert get_image_path() == "/path/to/img.png"
        
        mock_dialog.return_value = ("", "")
        assert get_image_path() is None

    @patch("biopro.plugins.sdk_utils.QFileDialog.getOpenFileNames")
    def test_get_image_paths(self, mock_dialog):
        mock_dialog.return_value = (["/a.png", "/b.png"], "filter")
        assert get_image_paths() == ["/a.png", "/b.png"]

    @patch("biopro.plugins.sdk_utils.QFileDialog.getSaveFileName")
    def test_get_save_path(self, mock_dialog):
        mock_dialog.return_value = ("/save/here.csv", "filter")
        assert get_save_path() == "/save/here.csv"

    @patch("biopro.plugins.sdk_utils.QFileDialog.getExistingDirectory")
    def test_get_directory(self, mock_dialog):
        mock_dialog.return_value = "/some/dir"
        assert get_directory() == "/some/dir"


class TestSDKMessaging:
    """Tests for standard message boxes (info, warning, error, questions)."""

    @patch("biopro.plugins.sdk_utils.QMessageBox.information")
    def test_show_info(self, mock_info):
        show_info(None, "Title", "Msg")
        mock_info.assert_called_once()

    @patch("biopro.plugins.sdk_utils.QMessageBox.warning")
    def test_show_warning(self, mock_warn):
        show_warning(None, "Title", "Msg")
        mock_warn.assert_called_once()

    @patch("biopro.plugins.sdk_utils.QMessageBox.critical")
    def test_show_error(self, mock_err):
        show_error(None, "Title", "Msg")
        mock_err.assert_called_once()

    @patch("biopro.plugins.sdk_utils.QMessageBox.question")
    def test_ask_yes_no(self, mock_quest):
        mock_quest.return_value = QMessageBox.StandardButton.Yes
        assert ask_yes_no() is True
        
        mock_quest.return_value = QMessageBox.StandardButton.No
        assert ask_yes_no() is False

    @patch("biopro.plugins.sdk_utils.QMessageBox.question")
    def test_ask_ok_cancel(self, mock_quest):
        mock_quest.return_value = QMessageBox.StandardButton.Ok
        assert ask_ok_cancel() is True


class TestSDKInputHelpers:
    """Tests for standard input dialogs (text, int, double)."""

    @patch("biopro.plugins.sdk_utils.QInputDialog.getText")
    def test_get_text(self, mock_input):
        mock_input.return_value = ("hello", True)
        assert get_text() == "hello"

    @patch("biopro.plugins.sdk_utils.QInputDialog.getInt")
    def test_get_number(self, mock_input):
        mock_input.return_value = (42, True)
        assert get_number() == 42

    @patch("biopro.plugins.sdk_utils.QInputDialog.getDouble")
    def test_get_double(self, mock_input):
        mock_input.return_value = (3.14, True)
        assert get_double() == 3.14


class TestSDKWorkflowIntegration:
    """Tests for high-level workflow utility functions."""

    @patch("biopro.plugins.sdk_utils.ask_yes_no")
    @patch("biopro.plugins.sdk_utils.get_text")
    def test_import_assets_workflow_full(self, mock_get_text, mock_ask):
        pm = MagicMock()
        mock_ask.side_effect = [True, True]
        mock_get_text.return_value = "batch_v1"
        
        files = ["/tmp/a.png", "/tmp/b.png"]
        import_assets_workflow(None, pm, files)
        
        pm.batch_add_images.assert_called_once()

    def test_import_assets_workflow_empty(self):
        pm = MagicMock()
        assert import_assets_workflow(None, pm, []) == []


class TestSDKJsonHelpers:
    """Tests for JSON I/O and persistence."""

    def test_json_io_logic(self, tmp_path):
        data = {"foo": "bar", "num": 123}
        path = tmp_path / "subdir" / "conf.json"
        save_json(str(path), data)
        assert load_json(str(path)) == data

    def test_plugin_config_persistence(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        config = PluginConfig("test_plugin")
        config.set("threshold", 0.75)
        config.save()
        
        config2 = PluginConfig("test_plugin")
        assert config2.get("threshold") == 0.75


class TestSDKValidation:
    """Tests for file and value validation logic."""

    def test_validation_logic(self, tmp_path):
        # File exists
        f = tmp_path / "probe.txt"
        f.write_text("content")
        ok, _ = validate_file_exists(str(f))
        assert ok is True
        
        # Range
        ok, msg = validate_value_range(5, 0, 10)
        assert ok is True
        ok, msg = validate_value_range(-1, 0, 10)
        assert ok is False


class TestSDKProgressUI:
    """Tests for progress dialog UI behavior."""

    def test_progress_dialog_behavior(self, qtbot):
        dialog = ProgressDialog(None, "Running", "Scaling...")
        qtbot.addWidget(dialog)
        
        dialog.setValue(25)
        assert dialog.value == 25
        assert dialog.label.text() == "25%"
        
        # Clamp behavior
        dialog.setValue(150)
        assert dialog.value == 100
        dialog.setValue(-50)
        assert dialog.value == 0


class TestSDKLogging:
    """Tests for plugin-specific logging utilities."""

    def test_plugin_logger_naming(self):
        logger = get_plugin_logger("my_cool_plugin")
        assert logger.name == "biopro.plugins.my_cool_plugin"
