import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from biopro_sdk.host.sign_plugin import PluginSigner, TrustChain
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


@pytest.fixture
def signer_env(tmp_path, monkeypatch):
    """Setup a sandboxed PluginSigner with a clean home directory."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    return PluginSigner()


def generate_mock_keypair():
    """Helper to generate a raw PEM private key and raw public key bytes."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    return private_pem, public_bytes


class TestDoubleSigningPipeline:
    def test_init_identity_creation(self, signer_env):
        """Verify that CLI init generates valid Ed25519 identities."""
        signer_env.init_identity()
        assert signer_env.private_key_path.exists()
        assert signer_env.public_key_path.exists()

    def test_developer_sign_plugin_split_manifest(self, signer_env, tmp_path):
        """Verify developer signing creates security.json and signature.bin while keeping manifest.json pristine."""
        signer_env.init_identity()

        # Set up a mock plugin
        plugin_dir = tmp_path / "my_plugin"
        plugin_dir.mkdir()

        manifest_data = {
            "manifest_version": 2,
            "id": "my_plugin",
            "name": "My Plugin",
            "version": "1.0.0",
            "description": "A split-manifest plugin.",
            "authors": [{"name": "Alice", "role": "Developer", "permissions": ["sign_code"]}],
        }
        manifest_file = plugin_dir / "manifest.json"
        # Write manifest.json with deterministic sorting
        manifest_file.write_text(
            json.dumps(manifest_data, sort_keys=True, separators=(",", ":")), encoding="utf-8"
        )

        # Add code file
        code_file = plugin_dir / "code.py"
        code_file.write_text("print('hello world')", encoding="utf-8")

        # Developer signs the plugin folder
        signer_env.sign_plugin(plugin_dir)

        # 1. Verify signatures and trust paths are created
        assert (plugin_dir / "security.json").exists()
        assert (plugin_dir / "signature.bin").exists()
        assert (plugin_dir / "trust_chain.json").exists()

        # 2. Verify that manifest.json was NOT modified (remains pristine)
        pristine_manifest = json.loads(manifest_file.read_text())
        assert "integrity" not in pristine_manifest
        assert "hashes" not in pristine_manifest

        # 3. Verify security.json contains the manifest hash bind and correct file hashes
        sec_data = json.loads((plugin_dir / "security.json").read_text())
        assert sec_data["security_version"] == 1
        assert sec_data["plugin_id"] == "my_plugin"

        # Check manifest hash matches manifest.json exactly
        computed_manifest_hash = hashlib.sha256(manifest_file.read_bytes()).hexdigest()
        assert sec_data["manifest_hash"] == computed_manifest_hash

        # Check that code.py is hashed
        code_hash = hashlib.sha256(code_file.read_bytes()).hexdigest()
        assert sec_data["hashes"]["code.py"] == code_hash

    def test_project_sign_plugin_success(self, signer_env, tmp_path):
        """Verify that Project signing in CI/CD co-signs security.json and generates project_signature.bin."""
        signer_env.init_identity()

        # 1. Developer signs plugin first
        plugin_dir = tmp_path / "my_plugin"
        plugin_dir.mkdir()

        manifest_data = {
            "manifest_version": 2,
            "id": "my_plugin",
            "name": "My Plugin",
            "version": "1.0.0",
            "description": "Double signed plugin.",
            "authors": [{"name": "Alice", "role": "Developer", "permissions": ["sign_code"]}],
        }
        manifest_file = plugin_dir / "manifest.json"
        manifest_file.write_text(
            json.dumps(manifest_data, sort_keys=True, separators=(",", ":")), encoding="utf-8"
        )

        code_file = plugin_dir / "code.py"
        code_file.write_text("print('core logic')", encoding="utf-8")

        signer_env.sign_plugin(plugin_dir)

        # 2. Generate a mock project private key PEM
        project_pem, project_pub = generate_mock_keypair()

        # 3. Perform Project co-signing
        # Inject project private key into signature pipeline via environment or PEM path
        signer_env.project_sign_plugin(plugin_dir, project_private_key_pem=project_pem)

        # 4. Verify outputs
        assert (plugin_dir / "project_signature.bin").exists()

        # Verify that trust_chain.json contains both developer link and project co-signature link
        chain = TrustChain.from_file(plugin_dir / "trust_chain.json")
        assert chain is not None
        assert len(chain.links) >= 2

        # Check developer link and project link
        project_link = chain.links[-1]
        assert project_link.subject_name == "BioPro GitHub Actions CI"
        assert project_link.subject_pub == project_pub.hex()

    def test_project_sign_fails_if_developer_signature_missing(self, signer_env, tmp_path):
        """Ensure project co-signing fails if there is no developer signature.bin."""
        plugin_dir = tmp_path / "unsigned_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "manifest_version": 2,
                    "id": "unsigned_plugin",
                    "name": "Unsigned",
                    "version": "1.0.0",
                    "description": "Missing developer sig.",
                    "authors": [{"name": "Alice", "role": "Developer"}],
                }
            )
        )

        project_pem, _ = generate_mock_keypair()

        with patch("biopro_sdk.host.sign_plugin.logger.error") as mock_log:
            signer_env.project_sign_plugin(plugin_dir, project_private_key_pem=project_pem)
            mock_log.assert_called_with(
                "Developer signature (signature.bin) or security ledger is missing. Rejecting pipeline."
            )

    def test_project_sign_fails_if_tampered_before_project_sign(self, signer_env, tmp_path):
        """Ensure project co-signing fails if a file is tampered with after developer signed but before CI/CD runs."""
        signer_env.init_identity()

        plugin_dir = tmp_path / "tamper_plugin"
        plugin_dir.mkdir()

        manifest_data = {
            "manifest_version": 2,
            "id": "tamper_plugin",
            "name": "Tamper Test",
            "version": "1.0.0",
            "description": "Desc",
            "authors": [{"name": "Alice", "role": "Developer", "permissions": ["sign_code"]}],
        }
        (plugin_dir / "manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")

        code_file = plugin_dir / "code.py"
        code_file.write_text("print('secure')", encoding="utf-8")

        # Developer signs
        signer_env.sign_plugin(plugin_dir)

        # TAMPER: Write malicious code over code.py post developer-signing
        code_file.write_text("print('malicious backdoor!')", encoding="utf-8")

        project_pem, _ = generate_mock_keypair()

        with patch("biopro_sdk.host.sign_plugin.logger.error") as mock_log:
            signer_env.project_sign_plugin(plugin_dir, project_private_key_pem=project_pem)
            args_list = [call.args[0] for call in mock_log.call_args_list if call.args]
            assert any(
                arg.startswith(
                    "Security validation failed before project-signing. Re-check file integrity."
                )
                for arg in args_list
            )
