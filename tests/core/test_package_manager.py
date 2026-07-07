from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from biopro.core.package_manager import PackageManager, PluginInstallerWorker


def test_package_manager_default_init(monkeypatch, tmp_path):
    """Verify default cache directory initialization."""
    fake_home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    pm = PackageManager()
    assert ".biopro" in str(pm.cache_dir)
    assert pm.cache_dir.exists()


def test_install_package_fail(tmp_path):
    """Verify that installation failures raise RuntimeError."""
    pm = PackageManager(cache_dir=tmp_path)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="Pip Error")
        with pytest.raises(RuntimeError) as exc:
            pm.install_package("pkg", "1.0")
        assert "Pip Error" in str(exc.value)


def test_link_package_cleanup(tmp_path):
    """Verify that link_package cleans up pre-existing files/dirs before symlinking."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    plugin_site = tmp_path / "site"
    plugin_site.mkdir()

    # Setup pre-existing conflicts
    (plugin_site / "file_conflict").write_text("old")
    (plugin_site / "dir_conflict").mkdir()
    (plugin_site / "link_conflict").symlink_to(cache_dir)

    cached = cache_dir / "pkg"
    cached.mkdir()
    (cached / "file_conflict").write_text("new")
    (cached / "dir_conflict").mkdir()
    (cached / "link_conflict").mkdir()
    # Also test skipping metadata
    (cached / ".hidden").write_text("hide")
    (cached / "pkg.dist-info").mkdir()

    pm = PackageManager(cache_dir=cache_dir)
    pm.link_package(cached, plugin_site)

    assert (plugin_site / "file_conflict").is_symlink()
    assert (plugin_site / "dir_conflict").is_symlink()
    assert (plugin_site / "link_conflict").is_symlink()
    assert not (plugin_site / ".hidden").exists()
    assert not (plugin_site / "pkg.dist-info").exists()


@patch("biopro.core.package_manager.PackageManager.install_package")
@patch("biopro.core.package_manager.PackageManager.link_package")
def test_plugin_installer_worker(mock_link, mock_install, tmp_path: Path):
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

    mock_install.return_value = cache_dir / "scipy_1.11.3"

    worker = PluginInstallerWorker(plugin_dir, cache_dir=cache_dir)
    # Run execution directly (synchronous for test)
    worker.run()

    mock_install.assert_called_once_with("scipy", "1.11.3")
    mock_link.assert_called_once()


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
        with patch.object(worker.pm, "install_package", side_effect=Exception("Crash")):
            worker.run()
            mock_finished.emit.assert_called_with(False, "Crash")
