import json
from pathlib import Path
from unittest.mock import patch

import pytest

from biopro.core.sign_plugin import PluginSigner, TrustChain, TrustLink


@pytest.fixture
def signer_env(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    return PluginSigner()


class TestTrustArchitecture:
    def test_trust_link_to_dict(self):
        link = TrustLink("Sub", "00", "Iss", "AA")
        d = link.to_dict()
        assert d["subject_name"] == "Sub"
        assert d["signature"] == "AA"

    def test_trust_chain_serialization(self, tmp_path):
        link = TrustLink("Sub", "00", "Iss", "AA")
        chain = TrustChain([link])
        json_str = chain.to_json()
        assert "Sub" in json_str

        # Test from_file
        chain_file = tmp_path / "chain.json"
        chain_file.write_text(json_str)
        loaded = TrustChain.from_file(chain_file)
        assert loaded is not None
        assert len(loaded.links) == 1
        assert loaded.links[0].subject_name == "Sub"


class TestPluginSigner:
    def test_init_identity(self, signer_env):
        signer_env.init_identity()
        assert signer_env.private_key_path.exists()
        assert signer_env.public_key_path.exists()

        # Test duplicate init blocked
        with patch("biopro.core.sign_plugin.logger.error") as mock_log:
            signer_env.init_identity()
            mock_log.assert_called_with(
                "Identity already exists. Delete ~/.biopro/dev_keys/ to regenerate."
            )

    def test_sign_plugin_success(self, signer_env, tmp_path):
        # 1. Setup Identity
        signer_env.init_identity()

        # 2. Setup Plugin
        plugin_dir = tmp_path / "test_plugin"
        plugin_dir.mkdir()
        manifest = {"id": "test_plugin", "name": "Test", "version": "1.0.0", "author": "Dev"}
        (plugin_dir / "manifest.json").write_text(json.dumps(manifest))
        (plugin_dir / "code.py").write_text("print('hello')")

        # 3. Sign
        signer_env.sign_plugin(plugin_dir)

        # 4. Verify outputs
        assert (plugin_dir / "signature.bin").exists()
        assert (plugin_dir / "trust_chain.json").exists()

        updated_manifest = json.loads((plugin_dir / "manifest.json").read_text())
        assert "integrity" in updated_manifest
        assert "code.py" in updated_manifest["integrity"]["hashes"]

    def test_sign_plugin_missing_manifest(self, signer_env, tmp_path):
        signer_env.init_identity()
        plugin_dir = tmp_path / "no_manifest"
        plugin_dir.mkdir()

        with patch("biopro.core.sign_plugin.logger.error") as mock_log:
            signer_env.sign_plugin(plugin_dir)
            mock_log.assert_called()

    def test_delegate_identity(self, signer_env, tmp_path):
        signer_env.init_identity()

        sub_pub = tmp_path / "subject.pub"
        sub_pub.write_bytes(b"0" * 32)

        signer_env.delegate_identity(sub_pub, "Researcher Name")

        # Check for delegation file (it's created in CWD, so we check CWD)
        # Wait, the tool's CWD is the project root.
        expected_file = Path("delegation_researcher_name.json")
        try:
            assert expected_file.exists()
            data = json.loads(expected_file.read_text())
            assert data[0]["subject_name"] == "Researcher Name"
        finally:
            if expected_file.exists():
                expected_file.unlink()

    def test_delegate_identity_with_authority(self, signer_env, tmp_path):
        """Verify delegation using a custom authority key."""
        signer_env.init_identity()

        auth_key = tmp_path / "root.key"
        # Generate a real ed25519 key for the mock authority
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ed25519

        private_key = ed25519.Ed25519PrivateKey.generate()
        auth_key.write_bytes(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

        sub_pub = tmp_path / "researcher.pub"
        sub_pub.write_bytes(b"0" * 32)

        signer_env.delegate_identity(sub_pub, "Researcher", authority_key_path=auth_key)
        assert Path("delegation_researcher.json").exists()
        Path("delegation_researcher.json").unlink()

    def test_delegate_identity_invalid_pub(self, signer_env, tmp_path):
        """Verify handling of invalid public key formats during delegation."""
        signer_env.init_identity()
        bad_pub = tmp_path / "bad.pub"
        bad_pub.write_text("not a key")

        with patch("biopro.core.sign_plugin.logger.error") as mock_log:
            signer_env.delegate_identity(bad_pub, "Fail")
            mock_log.assert_called_with("Invalid public key format.")

    def test_sign_plugin_with_delegation(self, signer_env, tmp_path):
        """Verify that signing a plugin includes the local delegation chain if present."""
        signer_env.init_identity()

        # Create a fake delegation
        link = TrustLink("Dev", "00", "Boss", "AA")
        chain = TrustChain([link])
        signer_env.delegation_path.write_text(chain.to_json())

        plugin_dir = tmp_path / "signed_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "manifest.json").write_text(
            json.dumps({"id": "signed_plugin", "author": "Dev"})
        )

        signer_env.sign_plugin(plugin_dir)

        trust_file = plugin_dir / "trust_chain.json"
        assert trust_file.exists()
        loaded = TrustChain.from_file(trust_file)
        assert loaded is not None
        assert loaded.links[0].issuer_name == "Boss"

    def test_print_registry_entry_missing_identity(self, signer_env):
        """Verify error handling when printing registry entry without an identity."""
        with patch("biopro.core.sign_plugin.logger.error") as mock_log:
            signer_env.print_registry_entry()
            mock_log.assert_called_with("No identity found. Run 'init' first.")


class TestSignPluginCLI:
    """Tests the command-line interface of sign_plugin.py."""

    def test_cli_init(self, signer_env):
        with patch("sys.argv", ["sign_plugin", "init"]):
            from biopro.core.sign_plugin import main

            main()
            assert signer_env.private_key_path.exists()

    def test_cli_sign(self, signer_env, tmp_path):
        signer_env.init_identity()
        plugin_dir = tmp_path / "cli_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "manifest.json").write_text(json.dumps({"id": "cli_plugin", "author": "Dev"}))

        with patch("sys.argv", ["sign_plugin", "sign", str(plugin_dir)]):
            from biopro.core.sign_plugin import main

            main()
            assert (plugin_dir / "signature.bin").exists()

    def test_cli_registry(self, signer_env):
        signer_env.init_identity()
        with (
            patch("sys.argv", ["sign_plugin", "registry"]),
            patch("builtins.print") as mock_print,
        ):
            from biopro.core.sign_plugin import main

            main()
            mock_print.assert_any_call("\n--- COPY THIS TO YOUR registry.json ---")

    def test_cli_delegate(self, signer_env, tmp_path):
        signer_env.init_identity()
        sub_pub = tmp_path / "sub.pub"
        sub_pub.write_bytes(b"0" * 32)

        with patch("sys.argv", ["sign_plugin", "delegate", str(sub_pub), "SubName"]):
            from biopro.core.sign_plugin import main

            main()
            assert Path("delegation_subname.json").exists()
            Path("delegation_subname.json").unlink()

    def test_cli_help(self):
        with (
            patch("sys.argv", ["sign_plugin", "--help"]),
            pytest.raises(SystemExit),
        ):
            from biopro.core.sign_plugin import main

            main()
