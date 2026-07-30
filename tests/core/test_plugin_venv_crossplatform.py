"""Tests for biopro.core.plugins.environment cross-platform plugin venv resolution."""

import importlib
import shutil
import sys
from pathlib import Path

import pytest

from biopro.core.plugins.environment import PluginEnvironmentInjector


def _dict_to_toml(d):
    # Convert flat dict to pyproject.toml format
    """
    Convert a flat dictionary into a minimal pyproject.toml configuration string.

    Parameters:
        d (dict): Configuration values for the project and BioPro plugin.

    Returns:
        str: TOML-formatted project and plugin configuration.
    """
    lines = []
    lines.append("[project]")
    lines.append(f'name = "{d.get("name", "test")}"')
    lines.append(f'version = "{d.get("version", "1.0.0")}"')
    if "description" in d:
        lines.append(f'description = "{d["description"]}"')

    lines.append("")
    lines.append("[tool.biopro.plugin]")
    lines.append(f'id = "{d.get("id", "test_id")}"')
    return "\n".join(lines)


def _expected_venv_python(venv_dir: Path) -> Path:
    """
    Determine the expected Python interpreter path within a virtual environment.

    Parameters:
        venv_dir (Path): Root directory of the virtual environment.

    Returns:
        Path: Platform-specific path to the virtual environment's Python interpreter.
    """
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / f"python{sys.version_info.major}.{sys.version_info.minor}"


def _expected_site_packages(venv_dir: Path) -> Path:
    """Return the site-packages path for the current OS."""
    if sys.platform == "win32":
        return venv_dir / "Lib" / "site-packages"
    py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
    return venv_dir / "lib" / py_ver / "site-packages"


def _uv_available() -> bool:
    """Determine whether the `uv` executable is available on the system PATH.

    Returns:
        bool: `True` if `uv` is available, `False` otherwise.
    """
    return shutil.which("uv") is not None


class TestVenvPathResolution:
    """Verify interpreter + site-packages paths are OS-correct without running uv."""

    def test_interpreter_path_is_platform_correct(self, tmp_path):
        venv_dir = tmp_path / ".venv"
        expected = _expected_venv_python(venv_dir)

        if sys.platform == "win32":
            assert "Scripts" in str(expected)
            assert expected.name == "python.exe"
        else:
            assert "bin" in str(expected)
            assert expected.name.startswith("python")

    def test_site_packages_path_is_platform_correct(self, tmp_path):
        venv_dir = tmp_path / ".venv"
        sp = _expected_site_packages(venv_dir)

        if sys.platform == "win32":
            assert "Lib" in sp.parts
            assert "site-packages" in sp.parts
            py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
            assert py_ver not in sp.parts
        else:
            py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
            assert py_ver in sp.parts

    def test_inject_plugin_path_finds_windows_layout(self, tmp_path):
        plugin_dir = tmp_path / "cytometrics"
        plugin_dir.mkdir()
        internal_dir = tmp_path / "biopro" / "plugins"

        # Simulate Windows venv layout
        win_sp = plugin_dir / ".venv" / "Lib" / "site-packages"
        win_sp.mkdir(parents=True)

        PluginEnvironmentInjector.inject_path(plugin_dir, internal_dir)

        assert str(win_sp) in sys.path
        sys.path.remove(str(win_sp))

    def test_inject_plugin_path_finds_unix_layout(self, tmp_path):
        plugin_dir = tmp_path / "cytometrics"
        plugin_dir.mkdir()
        internal_dir = tmp_path / "biopro" / "plugins"

        # Simulate Unix venv layout
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        unix_sp = plugin_dir / ".venv" / "lib" / py_ver / "site-packages"
        unix_sp.mkdir(parents=True)

        PluginEnvironmentInjector.inject_path(plugin_dir, internal_dir)

        assert str(unix_sp) in sys.path
        sys.path.remove(str(unix_sp))


@pytest.mark.skipif(
    not _uv_available(), reason="uv not on PATH — skipped in environments without uv"
)
class TestRealVenvInstallation:
    LIGHTWEIGHT_PACKAGE = "charset-normalizer"

    def test_venv_created_with_correct_interpreter(self, tmp_path):
        import subprocess as sp

        uv = shutil.which("uv")
        venv_dir = tmp_path / ".venv"

        result = sp.run(
            [uv, "venv", str(venv_dir), "--python", "3.12"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        expected_python = _expected_venv_python(venv_dir)
        assert expected_python.exists()

    def test_package_installs_and_is_importable(self, tmp_path):
        import subprocess as sp

        uv = shutil.which("uv")
        plugin_dir = tmp_path / "cytometrics_integration"
        plugin_dir.mkdir()
        venv_dir = plugin_dir / ".venv"

        sp.run([uv, "venv", str(venv_dir), "--python", "3.12"], capture_output=True, text=True)
        expected_python = _expected_venv_python(venv_dir)

        sp.run(
            [uv, "pip", "install", "--python", str(expected_python), self.LIGHTWEIGHT_PACKAGE],
            capture_output=True,
            text=True,
        )

        site_packages = _expected_site_packages(venv_dir)
        assert site_packages.exists()

        installed_names = [p.name.lower() for p in site_packages.iterdir()]
        assert any(
            self.LIGHTWEIGHT_PACKAGE.replace("-", "_") in name or self.LIGHTWEIGHT_PACKAGE in name
            for name in installed_names
        )

    def test_inject_and_import_from_real_venv(self, tmp_path):
        """Verifies that a package installed in a plugin's virtual environment can be imported after its site-packages directory is injected.

        Parameters:
            tmp_path: Temporary directory used to create the plugin and virtual environment.
        """
        import subprocess as sp

        uv = shutil.which("uv")

        plugin_dir = tmp_path / "cytometrics"
        plugin_dir.mkdir()
        internal_dir = tmp_path / "biopro" / "plugins"
        venv_dir = plugin_dir / ".venv"

        sp.run([uv, "venv", str(venv_dir), "--python", "3.12"], capture_output=True, check=True)
        expected_python = _expected_venv_python(venv_dir)
        sp.run(
            [uv, "pip", "install", "--python", str(expected_python), self.LIGHTWEIGHT_PACKAGE],
            capture_output=True,
            check=True,
        )

        site_packages = _expected_site_packages(venv_dir)
        original_path = sys.path.copy()

        try:
            PluginEnvironmentInjector.inject_path(plugin_dir, internal_dir)
            assert str(site_packages) in sys.path

            pkg_name = self.LIGHTWEIGHT_PACKAGE.replace("-", "_")
            if pkg_name in sys.modules:
                del sys.modules[pkg_name]

            mod = importlib.import_module(pkg_name)
            assert mod is not None
        finally:
            sys.path[:] = original_path
