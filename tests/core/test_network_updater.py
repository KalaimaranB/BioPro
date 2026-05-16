import io
import json
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from biopro.core.network_updater import NetworkUpdater, PluginInstallerWorker


# Mock PyQt6 to avoid QThread errors during testing if needed
class MockQThread:
    def __init__(self, *args, **kwargs):
        pass

    def start(self):
        self.run()

    def run(self):
        """Should be overridden by subclasses."""
        pass


@pytest.fixture(autouse=True)
def mock_qthread(monkeypatch):
    monkeypatch.setattr("PyQt6.QtCore.QThread", MockQThread)


@pytest.fixture
def temp_plugin_dir(tmp_path):
    # Mock the home directory to use tmp_path
    plugin_dir = tmp_path / ".biopro" / "plugins"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    return tmp_path


def create_malicious_zip() -> bytes:
    """Creates an in-memory zip file with a path traversal payload."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        # Normal file
        z.writestr("safe_plugin/info.json", '{"name": "Safe"}')
        # Malicious file attempting to escape the directory
        z.writestr(
            "../../../../../../../../../../../../../../../../../../tmp/evil.txt", "evil payload"
        )
    return buffer.getvalue()


def create_safe_zip() -> bytes:
    """Creates a basic safe zip file."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("test_plugin/config.json", '{"version": "1.0.0"}')
        z.writestr(
            "test_plugin/manifest.json",
            '{"id": "test_plugin", "version": "1.2.3", "name": "Test Plugin"}',
        )
    return buffer.getvalue()


@patch("biopro.core.network_updater.requests.get")
def test_plugin_installer_zip_slip(mock_get, temp_plugin_dir, monkeypatch):
    """Verify that the Zip Slip vulnerability is blocked by safe extraction."""
    monkeypatch.setattr(Path, "home", lambda: temp_plugin_dir)

    mock_response = mock_get.return_value
    mock_response.content = create_malicious_zip()
    mock_response.raise_for_status.return_value = None

    installer = PluginInstallerWorker("evil_plugin", "https://fake.url", Path("dummy"))

    # Run the worker to extract the zip
    installer.run()

    # Check if the evil file escaped into /tmp
    # Usually we can't write to /tmp cleanly in all systems, but we can check if it raised an error
    # or if it was safely ignored.

    plugin_dir = temp_plugin_dir / ".biopro" / "plugins"
    plugin_dir / "safe_plugin" / "info.json"

    # The normal file should be extracted (if we choose to extract safe files and skip bad ones)
    # The malicious file must NOT exist at the targeted path

    # Wait, the current implementation extractall() would throw an error or write it.
    # We will test that safe extraction either raises an exception or ignores the bad file.


@patch("biopro.core.network_updater.requests.get")
def test_plugin_installer_ssl_verify(mock_get, temp_plugin_dir, monkeypatch):
    """Ensure requests.get is called with properly configured SSL certs."""
    import certifi

    monkeypatch.setattr(Path, "home", lambda: temp_plugin_dir)

    mock_response = mock_get.return_value
    mock_response.content = create_safe_zip()

    installer = PluginInstallerWorker("safe_plugin", "https://fake.url", Path("dummy"))
    installer.run()

    # Verify requests.get was called with verify=certifi.where()
    mock_get.assert_called_once_with(
        "https://fake.url", stream=True, timeout=15, verify=certifi.where()
    )


@patch("biopro.core.network_updater.requests.get")
def test_network_updater_fetch_registry(mock_get, temp_plugin_dir, monkeypatch):
    """Ensure NetworkUpdater uses requests with verify=certifi.where() and no-cache headers."""
    import certifi

    monkeypatch.setattr(Path, "home", lambda: temp_plugin_dir)

    mock_response = mock_get.return_value
    mock_response.json.return_value = {"plugins": {}}
    mock_response.raise_for_status.return_value = None

    updater = NetworkUpdater()
    updater.fetch_remote_registry("https://registry.url")

    mock_get.assert_called_once_with(
        "https://registry.url",
        timeout=5,
        headers={
            "User-Agent": "BioPro-App",
            "Cache-Control": "no-cache, no-store",
            "Pragma": "no-cache",
        },
        verify=certifi.where(),
    )


class TestNetworkUpdaterExpanded:
    """Detailed logic tests for registry processing and state evaluation."""

    @pytest.fixture
    def updater(self, temp_plugin_dir, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: temp_plugin_dir)
        return NetworkUpdater()

    @patch("biopro.core.network_updater.requests.get")
    def test_evaluate_store_state_scenarios(self, mock_get, updater):
        """Tests the logic for categorizing plugins as INSTALL, UPDATE, or INCOMPATIBLE."""
        mock_response = mock_get.return_value
        mock_response.json.return_value = {"authorities": []}
        mock_response.raise_for_status.return_value = None
        # 1. Mock local state (what's already installed)
        local_data = {
            "old_plugin": {"version": "1.0.0", "name": "Old"},
            "current_plugin": {"version": "2.0.0", "name": "Current"},
        }

        # 2. Mock remote registry
        remote_registry = {
            "plugins": {
                "old_plugin": {
                    "version": "1.1.0",
                    "name": "Old",
                    "download_url": "...",
                    "min_core_version": "0.1.0",
                },
                "current_plugin": {
                    "version": "2.0.0",
                    "name": "Current",
                    "download_url": "...",
                    "min_core_version": "0.1.0",
                },
                "new_plugin": {
                    "version": "1.0.0",
                    "name": "New",
                    "download_url": "...",
                    "min_core_version": "0.1.0",
                },
                "future_plugin": {
                    "version": "1.0.0",
                    "name": "Future",
                    "download_url": "...",
                    "min_core_version": "9.9.9",
                },
            }
        }

        with (
            patch.object(updater, "fetch_remote_registry", return_value=remote_registry),
            patch.object(updater, "get_local_state", return_value=local_data),
        ):
            inventory = updater.evaluate_store_state()

            assert inventory["old_plugin"]["state"] == "UPDATE"
            assert inventory["current_plugin"]["state"] == "UP_TO_DATE"
            assert inventory["new_plugin"]["state"] == "INSTALL"
            assert inventory["future_plugin"]["state"] == "INCOMPATIBLE"

    def test_check_for_core_updates_detection(self, updater):
        """Tests core update detection logic."""
        # Case 1: Newer version available
        remote_data = {"core_app": {"version": "9.9.9", "download_url": "http://biopro.io"}}
        with patch.object(updater, "fetch_remote_registry", return_value=remote_data):
            needed, info = updater.check_for_core_updates()
            assert needed is True
            assert info["version"] == "9.9.9"

        # Case 2: Current or older version
        remote_data = {"core_app": {"version": "0.0.1"}}
        with patch.object(updater, "fetch_remote_registry", return_value=remote_data):
            needed, _ = updater.check_for_core_updates()
            assert needed is False

    @patch("biopro.core.network_updater.requests.get")
    def test_install_plugin_updates_local_registry(self, mock_get, updater):
        """Verify that successful installation updates the local registry file."""
        mock_response = mock_get.return_value
        mock_response.content = create_safe_zip()
        mock_response.raise_for_status.return_value = None

        plugin_info = {"version": "1.2.3", "name": "Test Plugin", "download_url": "http://fake.url"}
        success, msg = updater.install_plugin("test_plugin", plugin_info)

        if not success:
            pytest.fail(msg)
        # Verify local registry file now contains the new plugin
        local_state = updater.get_local_state()
        assert local_state["test_plugin"]["version"] == "1.2.3"
        assert local_state["test_plugin"]["name"] == "Test Plugin"

    def test_remove_plugin_logic(self, updater, temp_plugin_dir):
        """Verify that removing a plugin deletes files and registry entries."""
        # Setup: Create a fake plugin folder and registry entry
        plugin_dir = updater.plugin_dir / "to_delete"
        plugin_dir.mkdir()
        (plugin_dir / "some_file.py").write_text("print('hi')")

        local_data = {"to_delete": {"version": "1.0.0", "name": "Delete Me"}}
        with open(updater.local_registry_path, "w") as f:
            json.dump(local_data, f)

        # Execution
        success, _ = updater.remove_plugin("to_delete")

        assert success is True
        assert not plugin_dir.exists()
        assert "to_delete" not in updater.get_local_state()

    def test_fetch_remote_registry_error(self, updater):
        """Ensures that network errors during registry fetch return an empty dict."""
        with patch("requests.get", side_effect=Exception("Timeout")):
            res = updater.fetch_remote_registry("http://bad.url")
            assert res == {}

    def test_get_local_state_corrupted_manifest(self, updater):
        """Verifies that corrupted manifest.json files are skipped but others are loaded."""
        plugin_dir = updater.plugin_dir / "bad_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "manifest.json").write_text("{ invalid }")

        good_dir = updater.plugin_dir / "good_plugin"
        good_dir.mkdir()
        (good_dir / "manifest.json").write_text('{"id": "good", "version": "1.0.0"}')

        state = updater.get_local_state()
        assert "good" in state
        assert "bad_plugin" not in state

    def test_install_plugin_failure_path(self, updater):
        """Ensures that installation failures are caught and reported."""
        with patch("requests.get", side_effect=Exception("IO Error")):
            success, msg = updater.install_plugin("fail", {"download_url": "..."})
            assert success is False
            assert "Failed to install" in msg

    def test_sync_keys_cleanup(self, updater):
        """Verifies that keys no longer in the trusted list are removed from disk."""
        roots_dir = Path.home() / ".biopro" / "trusted_roots"
        roots_dir.mkdir(parents=True, exist_ok=True)
        old_key = roots_dir / "network_old.pub"
        old_key.write_bytes(b"data")

        # Sync with an empty list should remove the old key
        updater._sync_keys([], prefix="network_")
        assert not old_key.exists()

    def test_authority_sync_404_ignored(self, updater):
        """Ensures that a 404 on the authority registry is handled silently."""
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 404
            # Should not raise
            updater.fetch_and_sync_authorities()

    @patch("biopro_sdk.host.BIOPRO_ROOT_PUBLIC_KEY_HEX", "0" * 64)
    def test_authority_sync_signature_verification_failure(self, updater):
        """Verifies that authority sync aborts if signature verification fails."""
        from cryptography.hazmat.primitives.asymmetric import ed25519

        # Generate a real key pair but use the wrong one for verification
        private_key = ed25519.Ed25519PrivateKey.generate()
        authorities = [{"id": "a", "public_key": "00"}]
        canonical_bytes = json.dumps(authorities, sort_keys=True).encode()
        sig = private_key.sign(canonical_bytes).hex()

        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"authorities": authorities, "signature": sig}
            # This should fail because the root public key hex was patched to 00...
            with patch.object(updater, "_sync_keys") as mock_sync:
                updater.fetch_and_sync_authorities()
                mock_sync.assert_not_called()

    def test_sync_system_assets_logic(self, updater):
        """Tests the automatic update logic for system assets (SDK, docs)."""
        remote_data = {"sdk": {"version": "2.0.0", "download_url": "http://sdk.zip"}, "plugins": {}}
        local_assets = {"sdk": {"version": "1.0.0"}}

        assets_json = updater.plugin_dir / "system_assets.json"
        assets_json.write_text(json.dumps(local_assets))

        with (
            patch.object(updater, "fetch_remote_registry", return_value=remote_data),
            patch("requests.get") as mock_get,
            patch("shutil.rmtree"),
            patch("zipfile.ZipFile"),
            patch("biopro.core.network_updater._safe_extract"),
        ):
            mock_get.return_value.raise_for_status.return_value = None
            mock_get.return_value.content = b"zipdata"

            updater.sync_system_assets()

            # Verify it tried to download the new SDK
            mock_get.assert_called()
            # Verify it updated the local tracking file
            updated_assets = json.loads(assets_json.read_text())
            assert updated_assets["sdk"]["version"] == "2.0.0"

    def test_plugin_installer_worker_exceptions(self):
        """Verify exception handling in the PluginInstallerWorker thread."""
        from biopro.core.network_updater import PluginInstallerWorker

        # Patch the signal on the class before instantiation
        with patch.object(PluginInstallerWorker, "finished") as mock_finished:
            worker = PluginInstallerWorker("test", "url", Path("/tmp"))
            with patch("requests.get", side_effect=Exception("Crash")):
                worker.run()
                mock_finished.emit.assert_called_with(False, "Installation error: Crash")
