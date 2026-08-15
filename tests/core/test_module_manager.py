"""Tests for karcytics.core.module_manager plugin discovery."""

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest
from karcytics_sdk.host.trust_manager import VerificationResult

from karcytics.core.module_manager import ModuleManager

MOCK_TRUST_RESULT = VerificationResult(success=True, trust_level="verified_mock")


def _dict_to_toml(d):  # noqa: C901
    # Convert flat dict to pyproject.toml format
    """
    Convert plugin metadata into a pyproject.toml-formatted string.

    Parameters:
        d (dict): Flat plugin metadata containing project and plugin configuration fields.

    Returns:
        str: TOML-formatted project and plugin configuration.
    """
    lines = []

    lines.append("[project]")
    lines.append(f'name = "{d.get("name", "test")}"')
    lines.append(f'version = "{d.get("version", "1.0.0")}"')
    if "description" in d:
        lines.append(f'description = "{d["description"]}"')

    authors = d.get("authors", [])
    if authors:
        lines.append("authors = [")
        for a in authors:
            lines.append(f'  {{ name = "{a.get("name", "Test")}" }},')
        lines.append("]")

    lines.append("")
    lines.append("[tool.karcytics.plugin]")
    lines.append(f'id = "{d.get("id", "test_id")}"')

    if "icon" in d:
        lines.append(f'icon = "{d["icon"]}"')

    if "entry_point" in d:
        lines.append(f'entry_point = "{d["entry_point"]}"')

    if "ui_components" in d:
        lines.append("ui_components = [")
        for comp in d["ui_components"]:
            lines.append(f'  "{comp}",')
        lines.append("]")

    if authors:
        lines.append("authors = [")
        for a in authors:
            role = a.get("role", "Developer")
            perms = a.get("permissions", [])
            perms_str = '", "'.join(perms)
            if perms_str:
                lines.append(
                    f'  {{ name = "{a.get("name", "Test")}", role = "{role}", permissions = ["{perms_str}"] }},'
                )
            else:
                lines.append(f'  {{ name = "{a.get("name", "Test")}", role = "{role}" }},')
        lines.append("]")

    return "\n".join(lines)


def make_v2_manifest(plugin_id: str, name: str, icon: str = "🧪") -> dict:
    """Build a valid V2 manifest for test fixtures."""
    return {
        "manifest_version": 2,
        "id": plugin_id,
        "name": name,
        "version": "1.0.0",
        "description": f"{name} plugin",
        "authors": [{"name": "Test Dev", "role": "Developer"}],
        "icon": icon,
    }


@pytest.fixture
def mock_plugin_environment(tmp_path, monkeypatch):
    """Creates a temporary environment for plugin discovery tests."""
    fake_home = tmp_path / "home"
    user_plugins = fake_home / ".karcytics" / "plugins"
    user_plugins.mkdir(parents=True)

    plugin_dir = user_plugins / "test_module_a"
    plugin_dir.mkdir()
    with open(plugin_dir / "pyproject.toml", "w", encoding="utf-8") as f:
        f.write(_dict_to_toml(make_v2_manifest("test_module_a", "Test Module A")))

    monkeypatch.setattr(Path, "home", lambda: fake_home)
    return user_plugins


class TestModuleManager:
    """Test suite for ModuleManager Facade."""

    def test_module_discovery(self, mock_plugin_environment):
        """Verifies that the manager finds V2 modules in the user plugins directory."""
        with patch(
            "karcytics.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()

        assert "test_module_a" in mm.modules
        info = mm.modules["test_module_a"]
        assert info["manifest"]["name"] == "Test Module A"
        assert info["package_name"] == "test_module_a"

    def test_get_available_modules(self, mock_plugin_environment):
        """Verifies that get_available_modules returns a list of manifest dicts."""
        with patch(
            "karcytics.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()
        modules = mm.get_available_modules()

        assert len(modules) >= 1
        matches = [m for m in modules if m["id"] == "test_module_a"]
        assert len(matches) == 1
        assert matches[0]["icon"] == "🧪"

    def test_reload_modules(self, mock_plugin_environment):
        """Tests the hot-reload capability when plugins are added or removed."""
        mock_strategy = MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT))
        with patch(
            "karcytics.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=mock_strategy,
        ):
            mm = ModuleManager()
            assert "test_module_a" in mm.modules

            new_plugin = mock_plugin_environment / "test_module_b"
            new_plugin.mkdir()
            with open(new_plugin / "pyproject.toml", "w", encoding="utf-8") as f:
                f.write(_dict_to_toml(make_v2_manifest("test_module_b", "B")))

            mm.reload_modules()

        assert "test_module_a" in mm.modules
        assert "test_module_b" in mm.modules
        assert len(mm.modules) >= 2

    def test_corrupted_manifest_ignored(self, mock_plugin_environment):
        """Ensures that invalid JSON in a manifest doesn't crash the discovery process."""
        bad_plugin = mock_plugin_environment / "broken_plugin"
        bad_plugin.mkdir()
        with open(bad_plugin / "pyproject.toml", "w", encoding="utf-8") as f:
            f.write("{ invalid json... }")

        with patch(
            "karcytics.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()

        assert "broken_plugin" not in mm.modules
        assert "test_module_a" in mm.modules

    def test_load_module_ui_untrusted_blocked(self, mock_plugin_environment):
        """Verifies that an untrusted module cannot be loaded."""
        with patch(
            "karcytics.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(
                verify=MagicMock(
                    return_value=VerificationResult(success=False, trust_level="untrusted")
                )
            ),
        ):
            mm = ModuleManager()

        # Create dummy venv so it doesn't fail on missing dependency
        venv_bin = (
            mm.modules["test_module_a"]["path"]
            / ".venv"
            / ("Scripts" if sys.platform == "win32" else "bin")
        )
        venv_bin.mkdir(parents=True)
        (venv_bin / ("python.exe" if sys.platform == "win32" else "python3")).touch()

        with pytest.raises(PermissionError, match="Security Block"):
            mm.load_module_ui("test_module_a")

    def test_load_module_ui_missing_venv_raises_dependency_error(self, mock_plugin_environment):
        """Verifies that loading a verified module with missing dependencies raises a specific error."""
        with patch(
            "karcytics.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(
                verify=MagicMock(
                    return_value=VerificationResult(success=True, trust_level="verified_cache")
                )
            ),
        ):
            mm = ModuleManager()

        with pytest.raises(RuntimeError, match="DependencyMissingError"):
            mm.load_module_ui("test_module_a")

    def test_load_module_ui_already_loaded(self, mock_plugin_environment):
        """Verifies that subsequent calls to load_module_ui use the cached plugin reference."""
        with patch(
            "karcytics.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()
            mock_plugin = MagicMock()
            mm.modules["test_module_a"]["loaded"] = True
            mm.modules["test_module_a"]["plugin_ref"] = mock_plugin

            venv_bin = (
                mm.modules["test_module_a"]["path"]
                / ".venv"
                / ("Scripts" if sys.platform == "win32" else "bin")
            )
            venv_bin.mkdir(parents=True, exist_ok=True)
            (venv_bin / ("python.exe" if sys.platform == "win32" else "python3")).touch()

            mm.load_module_ui("test_module_a")
            mock_plugin.get_panel_class.assert_called_once()

    def test_load_module_ui_success(self, mock_plugin_environment):
        """Tests the full successful path of loading a plugin UI."""

        class DummyPlugin:
            def get_panel_class(self):
                return MagicMock()

            __version__ = "1.0.0"
            __plugin_id__ = "test_module_a"

            def cleanup(self):
                pass

            def shutdown(self):
                pass

        with patch(
            "karcytics.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()

        venv_bin = (
            mm.modules["test_module_a"]["path"]
            / ".venv"
            / ("Scripts" if sys.platform == "win32" else "bin")
        )
        venv_bin.mkdir(parents=True, exist_ok=True)
        (venv_bin / ("python.exe" if sys.platform == "win32" else "python3")).touch()

        plugin_instance = DummyPlugin()
        with (
            patch("karcytics.core.plugins.environment.PluginEnvironmentInjector.inject_path"),
            patch("importlib.import_module", return_value=plugin_instance),
        ):
            mm.load_module_ui("test_module_a")
            assert mm.modules["test_module_a"]["loaded"] is True
            assert mm.modules["test_module_a"]["plugin_ref"] == plugin_instance

    def test_load_module_ui_snapshot_diff_excludes_preexisting_modules(
        self, mock_plugin_environment
    ):
        """The ownership snapshot must only capture modules newly imported during
        this load, not ones already present in sys.modules beforehand — this is
        the mechanism that replaces enforce_priority's site-packages heuristic and
        (unlike it) also covers a plugin's own injected src/ package tree.
        """

        class DummyPlugin:
            def get_panel_class(self):
                return MagicMock()

            __version__ = "1.0.0"
            __plugin_id__ = "test_module_a"

            def cleanup(self):
                pass

            def shutdown(self):
                pass

        plugin_instance = DummyPlugin()

        def fake_import(name, *args, **kwargs):
            # Simulate the plugin's own import machinery pulling in a brand-new
            # dependency (this is what a real `importlib.import_module` call
            # would do as a side effect; the test mocks the call itself).
            sys.modules["_fake_plugin_owned_dep"] = ModuleType("_fake_plugin_owned_dep")
            return plugin_instance

        with patch(
            "karcytics.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()

        venv_bin = (
            mm.modules["test_module_a"]["path"]
            / ".venv"
            / ("Scripts" if sys.platform == "win32" else "bin")
        )
        venv_bin.mkdir(parents=True, exist_ok=True)
        (venv_bin / ("python.exe" if sys.platform == "win32" else "python3")).touch()

        try:
            with (
                patch("karcytics.core.plugins.environment.PluginEnvironmentInjector.inject_path"),
                patch("importlib.import_module", side_effect=fake_import),
            ):
                mm.load_module_ui("test_module_a")

            owned = mm.modules["test_module_a"]["_owned_modules"]
            assert "_fake_plugin_owned_dep" in owned
            assert "os" not in owned
            assert "sys" not in owned
        finally:
            sys.modules.pop("_fake_plugin_owned_dep", None)

    def test_unload_module_calls_cleanup_and_shutdown(self, mock_plugin_environment):
        """Verifies unload_module() invokes the SDK's documented cleanup()/shutdown()
        contract and resets the module's loaded state."""
        with patch(
            "karcytics.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()

        mock_plugin = MagicMock()
        mm.modules["test_module_a"]["loaded"] = True
        mm.modules["test_module_a"]["plugin_ref"] = mock_plugin
        mm.modules["test_module_a"]["_owned_modules"] = set()
        mm.modules["test_module_a"]["_owned_paths"] = []

        mm.unload_module("test_module_a")

        mock_plugin.cleanup.assert_called_once()
        mock_plugin.shutdown.assert_called_once()
        assert mm.modules["test_module_a"]["loaded"] is False
        assert mm.modules["test_module_a"]["plugin_ref"] is None

    def test_unload_module_purges_only_owned_sys_modules(self, mock_plugin_environment):
        """unload_module() must purge exactly the recorded owned set — nothing else
        in sys.modules should be touched."""
        with patch(
            "karcytics.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()

        sys.modules["_fake_owned_dep_mm"] = ModuleType("_fake_owned_dep_mm")
        try:
            mm.modules["test_module_a"]["loaded"] = True
            mm.modules["test_module_a"]["plugin_ref"] = MagicMock()
            mm.modules["test_module_a"]["_owned_modules"] = {"_fake_owned_dep_mm"}
            mm.modules["test_module_a"]["_owned_paths"] = []

            mm.unload_module("test_module_a")

            assert "_fake_owned_dep_mm" not in sys.modules
            assert "os" in sys.modules
        finally:
            sys.modules.pop("_fake_owned_dep_mm", None)

    def test_unload_module_noop_if_not_loaded(self, mock_plugin_environment):
        """Calling unload_module() on a module that isn't currently loaded must be
        a safe no-op (e.g. a stale/duplicate call from the UI layer)."""
        with patch(
            "karcytics.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()

        assert mm.modules["test_module_a"]["loaded"] is False
        mm.unload_module("test_module_a")
        assert mm.modules["test_module_a"]["loaded"] is False

    def test_unload_module_unknown_id_is_noop(self, mock_plugin_environment):
        with patch(
            "karcytics.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()

        mm.unload_module("does_not_exist")  # must not raise

    def test_load_module_ui_invalid_interface(self, mock_plugin_environment):
        """Verifies that a module not implementing the KarcyticsPlugin interface is rejected."""
        with patch(
            "karcytics.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()

        venv_bin = (
            mm.modules["test_module_a"]["path"]
            / ".venv"
            / ("Scripts" if sys.platform == "win32" else "bin")
        )
        venv_bin.mkdir(parents=True, exist_ok=True)
        (venv_bin / ("python.exe" if sys.platform == "win32" else "python3")).touch()

        mock_module = MagicMock()
        with (
            patch("karcytics.core.plugins.environment.PluginEnvironmentInjector.inject_path"),
            patch("importlib.import_module", return_value=mock_module),
            pytest.raises(TypeError, match="Missing required hooks"),
        ):
            mm.load_module_ui("test_module_a")

    def test_load_module_ui_isolated_never_imports_plugin_package(self, mock_plugin_environment):
        """The actual isolation proof: an isolated module's load must never
        call importlib.import_module for the plugin's own package, and the
        Hub's sys.modules must never gain an entry for it — this is the
        mechanism (not just a config flag) that makes switching between two
        isolated modules unable to corrupt shared C-extension state.
        """
        with patch(
            "karcytics.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()

        mm.modules["test_module_a"]["manifest"]["process_model"] = "isolated"

        venv_bin = (
            mm.modules["test_module_a"]["path"]
            / ".venv"
            / ("Scripts" if sys.platform == "win32" else "bin")
        )
        venv_bin.mkdir(parents=True, exist_ok=True)
        (venv_bin / ("python.exe" if sys.platform == "win32" else "python3")).touch()

        with patch("importlib.import_module") as mock_import:
            panel_factory = mm.load_module_ui("test_module_a")

        mock_import.assert_not_called()
        assert "karcytics.plugins.test_module_a" not in sys.modules
        assert callable(panel_factory)
        assert mm.modules["test_module_a"]["loaded"] is True

    def test_unload_module_isolated_stops_daemon_not_purge(self, mock_plugin_environment):
        """Isolated unload must go through PluginUIDaemon.stop_instance(), not
        the sys.modules purge machinery — there's nothing in the Hub's own
        sys.modules to purge for a module that was never imported."""
        with patch(
            "karcytics.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()

        mm.modules["test_module_a"]["manifest"]["process_model"] = "isolated"
        mm.modules["test_module_a"]["loaded"] = True

        with patch("karcytics_sdk.plugin.daemon.PluginUIDaemon.stop_instance") as mock_stop:
            mm.unload_module("test_module_a")

        mock_stop.assert_called_once_with("test_module_a")
        assert mm.modules["test_module_a"]["loaded"] is False

    def test_reload_modules_stops_running_isolated_daemons(self, mock_plugin_environment):
        """reload_modules() discards and rebuilds self.modules from scratch —
        for an isolated plugin that's currently running, its daemon process
        is tracked separately (PluginUIDaemon._instances) and would
        otherwise be orphaned: still running, but with no entry in the
        freshly rebuilt registry pointing back to it.
        """
        with patch(
            "karcytics.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()

        mm.modules["test_module_a"]["manifest"]["process_model"] = "isolated"
        mm.modules["test_module_a"]["loaded"] = True

        with patch("karcytics_sdk.plugin.daemon.PluginUIDaemon.stop_instance") as mock_stop:
            mm.reload_modules()

        mock_stop.assert_called_once_with("test_module_a")

    def test_trust_module_flow(self, mock_plugin_environment):
        """Tests the manual trust-override flow for a module."""
        untrusted_result = VerificationResult(
            success=False, trust_level="untrusted", calculated_hashes={"file.py": "hash"}
        )
        with patch(
            "karcytics.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=untrusted_result)),
        ):
            mm = ModuleManager()
            mm.trust_manager.overrides = MagicMock()
            mm.trust_manager._get_cache = MagicMock(return_value=MagicMock(data={}))

            assert mm.modules["test_module_a"]["trust_level"] == "untrusted"

            success = mm.trust_module("test_module_a")
            assert success is True
            mm.trust_manager.overrides.trust_current_state.assert_called_once_with(
                "test_module_a", {"file.py": "hash"}
            )

    def test_trust_module_reverify_if_missing_hashes(self, mock_plugin_environment):
        """Ensures that trust_module re-verifies the plugin if hashes are not already cached."""
        with patch(
            "karcytics.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()
            mm.trust_manager.verify_plugin = MagicMock(
                return_value=MagicMock(calculated_hashes={"file.py": "new_hash"})
            )
            mm.trust_manager.overrides = MagicMock()
            mm.trust_manager._get_cache = MagicMock(return_value=MagicMock(data={}))

            if "calculated_hashes" in mm.modules["test_module_a"]:
                del mm.modules["test_module_a"]["calculated_hashes"]

            mm.trust_module("test_module_a")
            mm.trust_manager.verify_plugin.assert_called_once()
            mm.trust_manager.overrides.trust_current_state.assert_called_once_with(
                "test_module_a", {"file.py": "new_hash"}
            )


def _module_with_file(name: str, file_path: Path) -> ModuleType:
    """Build a fake module object whose __file__ resolves within a given directory,
    for simulating which plugin's copy of a shared dependency is currently active.
    """
    mod = ModuleType(name)
    mod.__file__ = str(file_path)
    return mod


def _module_file(name: str) -> str:
    """Return sys.modules[name].__file__, asserting it's set (test helper only)."""
    origin = sys.modules[name].__file__
    assert origin is not None
    return origin


class TestModuleHotswap:
    """End-to-end regression test for the reported hot-swap crash: switching from
    one module to another must not leave sys.modules/sys.path in a state where the
    outgoing module's dependencies collide with the incoming one's. Drives the real
    ModuleManager.load_module_ui()/unload_module() pair — the same sequence
    PluginLoaderManager.open_module() now uses — rather than testing the
    environment-layer primitives in isolation.
    """

    class _DummyPlugin:
        def __init__(self, plugin_id: str):
            self._plugin_id = plugin_id
            self.cleanup = MagicMock()
            self.shutdown = MagicMock()

        def get_panel_class(self):
            return MagicMock()

        __version__ = "1.0.0"

        @property
        def __plugin_id__(self):
            return self._plugin_id

    @pytest.fixture
    def hotswap_env(self, tmp_path, monkeypatch):
        """Two plugins, each declaring their own installed copy of a colliding
        'shared_dep' distribution — mirrors the real matplotlib/pandas collision
        between Flow Cytometry and Synthetic Biology.
        """
        fake_home = tmp_path / "home"
        user_plugins = fake_home / ".karcytics" / "plugins"
        user_plugins.mkdir(parents=True)
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        def make_plugin(plugin_id: str, name: str) -> Path:
            plugin_dir = user_plugins / plugin_id
            plugin_dir.mkdir()
            with open(plugin_dir / "pyproject.toml", "w", encoding="utf-8") as f:
                f.write(_dict_to_toml(make_v2_manifest(plugin_id, name)))

            py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
            site_packages = plugin_dir / ".venv" / "lib" / py_ver / "site-packages"
            site_packages.mkdir(parents=True)
            dist_info = site_packages / "shared_dep-1.0.0.dist-info"
            dist_info.mkdir()
            (dist_info / "METADATA").write_text(
                "Metadata-Version: 2.1\nName: shared_dep\nVersion: 1.0.0\n"
            )

            venv_bin = plugin_dir / ".venv" / ("Scripts" if sys.platform == "win32" else "bin")
            venv_bin.mkdir(parents=True)
            (venv_bin / ("python.exe" if sys.platform == "win32" else "python3")).touch()
            return site_packages

        site_packages_a = make_plugin("hotswap_a", "Module A")
        site_packages_b = make_plugin("hotswap_b", "Module B")
        return site_packages_a, site_packages_b

    def test_switching_modules_unloads_a_and_isolates_shared_dependency_for_b(self, hotswap_env):
        site_packages_a, site_packages_b = hotswap_env

        with patch(
            "karcytics.core.plugins.discovery.TrustStrategyFactory.get_strategy",
            return_value=MagicMock(verify=MagicMock(return_value=MOCK_TRUST_RESULT)),
        ):
            mm = ModuleManager()

        plugin_a = self._DummyPlugin("hotswap_a")
        plugin_b = self._DummyPlugin("hotswap_b")

        def fake_import_a(name, *args, **kwargs):
            sys.modules["shared_dep"] = _module_with_file(
                "shared_dep", site_packages_a / "shared_dep" / "__init__.py"
            )
            return plugin_a

        def fake_import_b(name, *args, **kwargs):
            sys.modules["shared_dep"] = _module_with_file(
                "shared_dep", site_packages_b / "shared_dep" / "__init__.py"
            )
            return plugin_b

        try:
            # 1. Load module A. Its own copy of shared_dep resolves and is recorded
            # as owned.
            with patch("importlib.import_module", side_effect=fake_import_a):
                mm.load_module_ui("hotswap_a")

            assert mm.modules["hotswap_a"]["loaded"] is True
            assert "shared_dep" in mm.modules["hotswap_a"]["_owned_modules"]
            assert str(site_packages_a) in _module_file("shared_dep")
            assert str(site_packages_a) in sys.path

            # 2. Switch away from A — this is exactly what PluginLoaderManager's
            # _begin_unload() now does once A's panel is confirmed destroyed, and
            # must happen (and succeed) before B's load ever starts.
            mm.unload_module("hotswap_a")

            plugin_a.cleanup.assert_called_once()
            plugin_a.shutdown.assert_called_once()
            assert mm.modules["hotswap_a"]["loaded"] is False
            assert "shared_dep" not in sys.modules
            assert str(site_packages_a) not in sys.path

            # 3. Load module B. No crash, and it resolves its own copy of the
            # dependency rather than colliding with (or shadow-purging) A's.
            with patch("importlib.import_module", side_effect=fake_import_b):
                mm.load_module_ui("hotswap_b")

            assert mm.modules["hotswap_b"]["loaded"] is True
            assert str(site_packages_b) in _module_file("shared_dep")
        finally:
            sys.modules.pop("shared_dep", None)
            for p in (str(site_packages_a), str(site_packages_b)):
                if p in sys.path:
                    sys.path.remove(p)
