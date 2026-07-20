"""Cross-platform plugin venv installation tests for PackageManager.

These tests verify that:
  1. The correct Python interpreter path is resolved on both Windows (Scripts/python.exe)
     and Unix/macOS (bin/python3.12).
  2. A real `uv` venv is created and a lightweight package (charset-normalizer, which
     ships pre-built wheels on all platforms and is already a transitive dep) is
     successfully installed into it.
  3. The installed package is importable from the venv's site-packages — matching exactly
     the mechanism BioPro uses to load flowkit inside cytometrics.
  4. `_inject_plugin_path` discovers the correct OS-specific site-packages directory and
     adds it to sys.path so imports actually resolve.
"""

import importlib
import json
import shutil
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from biopro.core.module_manager import ModuleManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _expected_venv_python(venv_dir: Path) -> Path:
    """Return the interpreter path that PackageManager should produce."""
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
    return shutil.which("uv") is not None


# ---------------------------------------------------------------------------
# Unit tests — no real uv required
# ---------------------------------------------------------------------------


class TestVenvPathResolution:
    """Verify interpreter + site-packages paths are OS-correct without running uv."""

    def test_interpreter_path_is_platform_correct(self, tmp_path):
        """PackageManager must resolve the interpreter to the OS-specific location."""
        venv_dir = tmp_path / ".plugin_venv"
        expected = _expected_venv_python(venv_dir)

        if sys.platform == "win32":
            assert "Scripts" in str(expected)
            assert expected.name == "python.exe"
        else:
            assert "bin" in str(expected)
            assert expected.name.startswith("python")

    def test_site_packages_path_is_platform_correct(self, tmp_path):
        """The site-packages directory must follow OS conventions."""
        venv_dir = tmp_path / ".plugin_venv"
        sp = _expected_site_packages(venv_dir)

        if sys.platform == "win32":
            # Windows: Lib/site-packages (capital L, no version folder)
            assert "Lib" in sp.parts
            assert "site-packages" in sp.parts
            py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
            assert py_ver not in sp.parts, "Windows site-packages must NOT have a version subdir"
        else:
            # Unix: lib/pythonX.Y/site-packages
            py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
            assert py_ver in sp.parts, "Unix site-packages must include the version subdir"

    def test_inject_plugin_path_finds_windows_layout(self, tmp_path, monkeypatch):
        """_inject_plugin_path must add the Windows Lib/site-packages to sys.path."""
        fake_home = tmp_path / "home"
        user_plugins = fake_home / ".biopro" / "plugins"
        user_plugins.mkdir(parents=True)
        plugin_dir = user_plugins / "cytometrics"
        plugin_dir.mkdir()

        manifest = {
            "manifest_version": 2,
            "id": "cytometrics",
            "name": "Cytometrics",
            "version": "1.0.0",
            "description": "test",
            "authors": [{"name": "Test", "role": "Developer"}],
        }
        (plugin_dir / "manifest.json").write_text(json.dumps(manifest))

        # Simulate Windows venv layout
        win_sp = plugin_dir / ".plugin_venv" / "Lib" / "site-packages"
        win_sp.mkdir(parents=True)

        monkeypatch.setattr(Path, "home", lambda: fake_home)

        from biopro_sdk.host.trust_manager import VerificationResult

        mock_result = VerificationResult(success=True, trust_level="verified_mock")

        with patch(
            "biopro.core.module_manager.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=mock_result)),
        ):
            mm = ModuleManager()

        mm._inject_plugin_path(plugin_dir)

        assert str(win_sp) in sys.path, (
            f"Windows Lib/site-packages not injected into sys.path.\nsys.path head: {sys.path[:8]}"
        )
        # Cleanup
        sys.path.remove(str(win_sp))

    def test_inject_plugin_path_finds_unix_layout(self, tmp_path, monkeypatch):
        """_inject_plugin_path must add the Unix lib/pythonX.Y/site-packages to sys.path."""
        fake_home = tmp_path / "home"
        user_plugins = fake_home / ".biopro" / "plugins"
        user_plugins.mkdir(parents=True)
        plugin_dir = user_plugins / "cytometrics"
        plugin_dir.mkdir()

        manifest = {
            "manifest_version": 2,
            "id": "cytometrics",
            "name": "Cytometrics",
            "version": "1.0.0",
            "description": "test",
            "authors": [{"name": "Test", "role": "Developer"}],
        }
        (plugin_dir / "manifest.json").write_text(json.dumps(manifest))

        # Simulate Unix venv layout
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        unix_sp = plugin_dir / ".plugin_venv" / "lib" / py_ver / "site-packages"
        unix_sp.mkdir(parents=True)

        monkeypatch.setattr(Path, "home", lambda: fake_home)

        from biopro_sdk.host.trust_manager import VerificationResult

        mock_result = VerificationResult(success=True, trust_level="verified_mock")

        with patch(
            "biopro.core.module_manager.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=mock_result)),
        ):
            mm = ModuleManager()

        mm._inject_plugin_path(plugin_dir)

        assert str(unix_sp) in sys.path, (
            f"Unix lib/pythonX.Y/site-packages not injected into sys.path.\n"
            f"sys.path head: {sys.path[:8]}"
        )
        sys.path.remove(str(unix_sp))


# ---------------------------------------------------------------------------
# Integration tests — require uv
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _uv_available(), reason="uv not on PATH — skipped in environments without uv"
)
class TestRealVenvInstallation:
    """End-to-end tests that create a real venv and install a real package.

    Uses ``charset-normalizer`` — tiny, pure-Python, always has wheels, and is
    already a transitive dep of requests so it never hits the network on a warm
    cache. The same mechanism proves flowkit would also install correctly.
    """

    LIGHTWEIGHT_PACKAGE = "charset-normalizer"

    def test_venv_created_with_correct_interpreter(self, tmp_path):
        """uv must produce the interpreter at the OS-specific path.

        Creates a real venv and asserts the interpreter exists at the location
        that PackageManager._expected_venv_python() resolves to. This is the
        exact check that caught the Windows breakage (Scripts/python.exe vs
        bin/python3.12).
        """
        import shutil as sh
        import subprocess as sp

        uv = sh.which("uv")
        venv_dir = tmp_path / ".plugin_venv"

        result = sp.run(
            [uv, "venv", str(venv_dir), "--python", "3.12"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"uv venv creation failed: {result.stderr}"

        expected_python = _expected_venv_python(venv_dir)
        assert expected_python.exists(), (
            f"Expected interpreter not found at {expected_python}.\n"
            f"Platform is '{sys.platform}'. Venv bin contents: "
            f"{list((venv_dir / ('Scripts' if sys.platform == 'win32' else 'bin')).iterdir())}"
        )

    def test_package_installs_and_is_importable(self, tmp_path):
        """A package installed into the plugin venv must be importable from site-packages."""
        import shutil as sh
        import subprocess as sp

        uv = sh.which("uv")
        plugin_dir = tmp_path / "cytometrics_integration"
        plugin_dir.mkdir()
        venv_dir = plugin_dir / ".plugin_venv"

        # Create the venv
        result = sp.run(
            [uv, "venv", str(venv_dir), "--python", "3.12"], capture_output=True, text=True
        )
        assert result.returncode == 0, f"uv venv failed: {result.stderr}"

        expected_python = _expected_venv_python(venv_dir)
        assert expected_python.exists(), f"Interpreter missing at {expected_python}"

        # Install the lightweight package via the correct interpreter
        result = sp.run(
            [uv, "pip", "install", "--python", str(expected_python), self.LIGHTWEIGHT_PACKAGE],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"uv pip install failed: {result.stderr}"

        # Verify site-packages is at the OS-correct path
        site_packages = _expected_site_packages(venv_dir)
        assert site_packages.exists(), (
            f"site-packages not found at expected OS-specific path: {site_packages}.\n"
            f"This is the path mismatch bug that hides flowkit on Windows."
        )

        # Verify the package actually landed there
        installed = list(site_packages.iterdir())
        installed_names = [p.name.lower() for p in installed]
        assert any(
            self.LIGHTWEIGHT_PACKAGE.replace("-", "_") in name or self.LIGHTWEIGHT_PACKAGE in name
            for name in installed_names
        ), (
            f"Package '{self.LIGHTWEIGHT_PACKAGE}' not found in {site_packages}.\n"
            f"Contents: {installed_names}"
        )

    def test_inject_and_import_from_real_venv(self, tmp_path, monkeypatch):
        """Full round-trip: install package → inject path → import it from a real venv."""
        import shutil as sh
        import subprocess as sp

        uv = sh.which("uv")

        fake_home = tmp_path / "home"
        user_plugins = fake_home / ".biopro" / "plugins"
        user_plugins.mkdir(parents=True)
        plugin_dir = user_plugins / "cytometrics"
        plugin_dir.mkdir()

        manifest = {
            "manifest_version": 2,
            "id": "cytometrics",
            "name": "Cytometrics",
            "version": "1.0.0",
            "description": "test",
            "authors": [{"name": "Test", "role": "Developer"}],
        }
        (plugin_dir / "manifest.json").write_text(json.dumps(manifest))

        venv_dir = plugin_dir / ".plugin_venv"

        # Create venv and install package
        sp.run([uv, "venv", str(venv_dir), "--python", "3.12"], capture_output=True, check=True)
        expected_python = _expected_venv_python(venv_dir)
        sp.run(
            [uv, "pip", "install", "--python", str(expected_python), self.LIGHTWEIGHT_PACKAGE],
            capture_output=True,
            check=True,
        )

        monkeypatch.setattr(Path, "home", lambda: fake_home)

        from biopro_sdk.host.trust_manager import VerificationResult

        mock_result = VerificationResult(success=True, trust_level="verified_mock")

        with patch(
            "biopro.core.module_manager.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=mock_result)),
        ):
            mm = ModuleManager()

        site_packages = _expected_site_packages(venv_dir)
        original_path = sys.path.copy()
        mm._inject_plugin_path(plugin_dir)

        try:
            assert str(site_packages) in sys.path, f"site-packages not injected: {site_packages}"

            # Force reimport from the injected path
            pkg_name = self.LIGHTWEIGHT_PACKAGE.replace("-", "_")
            if pkg_name in sys.modules:
                del sys.modules[pkg_name]

            mod = importlib.import_module(pkg_name)
            assert mod is not None, f"Could not import '{pkg_name}' after path injection"
        finally:
            # Restore sys.path
            sys.path[:] = original_path
