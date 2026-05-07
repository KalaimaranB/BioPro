import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from biopro.core.package_manager import PackageManager, PluginInstallerWorker


def test_package_manager_init(tmp_path: Path):
    """Verify PackageManager initializes cache paths correctly."""
    cache_dir = tmp_path / "cache"
    pm = PackageManager(cache_dir=cache_dir)
    assert pm.cache_dir == cache_dir
    assert pm.cache_dir.is_dir()


def test_symlink_creation(tmp_path: Path):
    """Verify link_package successfully creates symlinks pointing to cached directories."""
    cache_dir = tmp_path / "cache"
    plugin_dir = tmp_path / "plugin"
    plugin_site_packages = plugin_dir / ".venv" / "lib" / "python3.11" / "site-packages"
    plugin_site_packages.mkdir(parents=True)

    pm = PackageManager(cache_dir=cache_dir)

    # Mock a cached package folder
    cached_pkg_path = cache_dir / "scipy_1.11.3"
    cached_pkg_path.mkdir(parents=True)
    (cached_pkg_path / "scipy").mkdir()
    with open(cached_pkg_path / "scipy" / "__init__.py", "w") as f:
        f.write("# scipy init")

    # Perform symlinking
    pm.link_package(cached_pkg_path, plugin_site_packages)

    # Assert symlink was created inside plugin site-packages pointing to cached folder
    linked_folder = plugin_site_packages / "scipy"
    assert linked_folder.is_symlink()
    assert os.readlink(linked_folder) == str(cached_pkg_path / "scipy")


@patch("biopro.core.package_manager.subprocess.run")
def test_secure_pip_args(mock_run, tmp_path: Path):
    """Verify that pip installation subprocess arguments are securely constructed."""
    cache_dir = tmp_path / "cache"
    pm = PackageManager(cache_dir=cache_dir)

    mock_run.return_value = MagicMock(returncode=0)

    # Trigger installation
    pm.install_package("scipy", "1.11.3")

    # Assert subprocess arguments include security flags
    args = mock_run.call_args[0][0]
    assert sys.executable in args
    assert "-m" in args
    assert "pip" in args
    assert "install" in args
    assert "scipy==1.11.3" in args
    assert "--only-binary=:all:" in args
    assert "--no-deps" in args


@patch("biopro.core.package_manager.PackageManager.install_package")
@patch("biopro.core.package_manager.PackageManager.link_package")
def test_plugin_installer_worker(mock_link, mock_install, tmp_path: Path):
    """Verify that PluginInstallerWorker successfully runs in background and processes manifest dependencies."""
    cache_dir = tmp_path / "cache"
    plugin_dir = tmp_path / "plugin"
    plugin_dir.mkdir()

    manifest = {
        "id": "my_plugin",
        "dependencies": {
            "scipy": "1.11.3",
        },
    }
    with open(plugin_dir / "manifest.json", "w") as f:
        f.write(str(manifest).replace("'", '"'))

    mock_install.return_value = cache_dir / "scipy_1.11.3"

    # Setup signals tracking
    finished_called = False
    error_msg = ""

    def on_finished(success, err):
        nonlocal finished_called, error_msg
        finished_called = True
        error_msg = err

    worker = PluginInstallerWorker(plugin_dir, cache_dir=cache_dir)
    worker.finished.connect(on_finished)

    # Run execution directly (synchronous for test)
    worker.run()

    assert finished_called is True
    assert error_msg == ""
    mock_install.assert_called_once_with("scipy", "1.11.3")
    mock_link.assert_called_once()
