from pathlib import Path
from unittest.mock import patch

from biopro.core.package_manager import PackageManager, PluginInstallerWorker


def test_package_manager_default_init(monkeypatch, tmp_path):
    """Verify default cache directory initialization."""
    fake_home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    pm = PackageManager()
    assert ".biopro" in str(pm.cache_dir)
    assert pm.cache_dir.exists()


@patch("biopro.core.package_manager.PackageManager.resolve_and_install_all")
def test_plugin_installer_worker(mock_resolve, tmp_path: Path):
    """Verify that PluginInstallerWorker successfully runs in background and processes manifest dependencies."""
    cache_dir = tmp_path / "cache"
    plugin_dir = tmp_path / "plugin"
    plugin_dir.mkdir()

    manifest = {
        "id": "my_plugin",
        "python_dependencies": {
            "scipy": "1.11.3",
        },
    }
    with open(plugin_dir / "manifest.json", "w") as f:
        f.write(str(manifest).replace("'", '"'))

    worker = PluginInstallerWorker(plugin_dir, cache_dir=cache_dir)
    # Run execution directly (synchronous for test)
    worker.run()

    mock_resolve.assert_called_once()


def test_worker_manifest_missing(tmp_path):
    """Verify worker handles missing manifest.json."""
    with patch.object(PluginInstallerWorker, "finished") as mock_finished:
        worker = PluginInstallerWorker(tmp_path)
        worker.run()
        mock_finished.emit.assert_called_with(False, "manifest.json missing from plugin directory.")


def test_worker_no_deps(tmp_path):
    """Verify worker handles plugins with no dependencies."""
    plugin_dir = tmp_path / "plugin_no_deps"
    plugin_dir.mkdir()
    (plugin_dir / "manifest.json").write_text('{"id": "test"}')
    with patch.object(PluginInstallerWorker, "finished") as mock_finished:
        worker = PluginInstallerWorker(plugin_dir)
        worker.run()
        mock_finished.emit.assert_called_with(True, "")


def test_worker_exception(tmp_path):
    """Verify worker handles unexpected exceptions during installation."""
    plugin_dir = tmp_path / "plugin_crash"
    plugin_dir.mkdir()
    (plugin_dir / "manifest.json").write_text('{"id": "test", "python_dependencies": {"a": "1"}}')
    with patch.object(PluginInstallerWorker, "finished") as mock_finished:
        worker = PluginInstallerWorker(plugin_dir)
        with patch.object(worker.pm, "resolve_and_install_all", side_effect=Exception("Crash")):
            worker.run()
            mock_finished.emit.assert_called_with(False, "Crash")


def test_resolve_bundled_uv_windows(monkeypatch, tmp_path):
    """Verify that on Windows, uv.exe is resolved."""
    import sys

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(sys, "platform", "win32")

    pm = PackageManager()

    # Create fake uv.exe
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "uv.exe").touch()

    # Create dummy plugin and fake python
    plugin_dir = tmp_path / "test_win_uv"
    plugin_dir.mkdir()
    venv_python = plugin_dir / ".plugin_venv" / "Scripts" / "python.exe"
    venv_python.parent.mkdir(parents=True)
    venv_python.touch()
    worker_script = plugin_dir / "analysis" / "fcs_worker.py"
    worker_script.parent.mkdir(parents=True)
    worker_script.touch()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        pm.resolve_and_install_all({"dummy": "1.0"}, plugin_dir, lambda x: None)

        # Verify uv.exe was used
        args = mock_run.call_args_list[0][0][0]
        assert args[0] == str(bin_dir / "uv.exe")


def test_resolve_bundled_uv_unix(monkeypatch, tmp_path):
    """Verify that on Unix, uv is resolved."""
    import sys

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(sys, "platform", "darwin")

    pm = PackageManager()

    # Create fake uv
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "uv").touch()

    # Create dummy plugin and fake python
    plugin_dir = tmp_path / "test_unix_uv"
    plugin_dir.mkdir()
    venv_python = plugin_dir / ".plugin_venv" / "bin" / "python3.12"
    venv_python.parent.mkdir(parents=True)
    venv_python.touch()
    worker_script = plugin_dir / "analysis" / "fcs_worker.py"
    worker_script.parent.mkdir(parents=True)
    worker_script.touch()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        pm.resolve_and_install_all({"dummy": "1.0"}, plugin_dir, lambda x: None)

        # Verify uv was used
        args = mock_run.call_args_list[0][0][0]
        assert args[0] == str(bin_dir / "uv")
