"""TDD tests for the init-identity CLI command (developer and project modes)."""

import pytest

from biopro.core.manifest_parser import ManifestParser, ManifestValidationError


class TestManifestParserIntegration:
    """Integration test: ManifestParser + ModuleManager (no Qt needed)."""

    def test_valid_v2_manifest_round_trip(self, tmp_path):
        """A well-formed V2 manifest file is parsed without error."""
        manifest = {
            "manifest_version": 2,
            "id": "test_plugin",
            "name": "Test Plugin",
            "version": "1.0.0",
            "description": "Integration test plugin",
            "signed_by": {"entity_type": "project", "entity_id": "test_ci_bot"},
            "authors": [{"name": "Alice"}, {"name": "Bob"}],
        }
        import json

        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(json.dumps(manifest))

        parser = ManifestParser()
        result = parser.parse_file(str(manifest_file))
        assert result["id"] == "test_plugin"
        assert len(result["authors"]) == 2

    def test_legacy_manifest_file_is_rejected(self, tmp_path):
        """A manifest using the old 'author' string field raises ManifestValidationError."""
        import json

        manifest = {
            "id": "old_plugin",
            "name": "Old Plugin",
            "version": "1.0.0",
            "description": "Legacy",
            "author": "alice",
        }
        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(json.dumps(manifest))

        parser = ManifestParser()
        with pytest.raises(ManifestValidationError) as exc:
            parser.parse_file(str(manifest_file))
        assert "Legacy 'author' field" in str(exc.value)

    def test_missing_required_field_rejected(self, tmp_path):
        """Missing 'authors' key raises ManifestValidationError."""
        import json

        manifest = {
            "manifest_version": 2,
            "id": "bad_plugin",
            "name": "Bad Plugin",
            "version": "1.0.0",
            "description": "Missing authors",
            "signed_by": {"entity_type": "developer", "entity_id": "alice"},
        }
        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(json.dumps(manifest))

        parser = ManifestParser()
        with pytest.raises(ManifestValidationError) as exc:
            parser.parse_file(str(manifest_file))
        assert "authors" in str(exc.value)


class TestInitIdentity:
    """TDD tests for biopro sdk init-identity (developer and project modes)."""

    def test_developer_mode_creates_expected_files(self, tmp_path):
        """init_identity() creates dev_private_key.pem, dev_cert.bin, and onboarding_root.pub."""
        from biopro_sdk.sdk_cli import SDKCLI

        cli = SDKCLI()
        cli.biopro_dir = tmp_path
        cli.trusted_roots_dir = tmp_path / "trusted_roots"

        cli.init_identity(is_project=False)

        assert (tmp_path / "dev_private_key.pem").exists()
        assert (tmp_path / "dev_cert.bin").exists()
        assert (tmp_path / "trusted_roots" / "onboarding_root.pub").exists()

    def test_developer_mode_cert_is_96_bytes(self, tmp_path):
        """dev_cert.bin must be exactly 96 bytes: 32 bytes pub key + 64 bytes signature."""
        from biopro_sdk.sdk_cli import SDKCLI

        cli = SDKCLI()
        cli.biopro_dir = tmp_path
        cli.trusted_roots_dir = tmp_path / "trusted_roots"
        cli.init_identity(is_project=False)

        cert = (tmp_path / "dev_cert.bin").read_bytes()
        assert len(cert) == 96, f"Expected 96 bytes, got {len(cert)}"

    def test_project_mode_fails_without_key(self, tmp_path, capsys):
        """init_identity(is_project=True) prints an error if no private key exists."""
        from biopro_sdk.sdk_cli import SDKCLI

        cli = SDKCLI()
        cli.biopro_dir = tmp_path
        cli.trusted_roots_dir = tmp_path / "trusted_roots"

        cli.init_identity(is_project=True)

        captured = capsys.readouterr()
        assert "ERROR" in captured.out
        assert "BIOPRO_PROJECT_PRIVATE_KEY" in captured.out

    def test_project_mode_succeeds_with_existing_key(self, tmp_path, capsys):
        """init_identity(is_project=True) loads the existing key and writes the cert stub."""
        from biopro_sdk.sdk_cli import SDKCLI
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ed25519

        # Pre-write a valid project key (as CI would inject from secrets)
        priv_key = ed25519.Ed25519PrivateKey.generate()
        priv_bytes = priv_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.OpenSSH,
            serialization.NoEncryption(),
        )
        key_file = tmp_path / "dev_private_key.pem"
        key_file.write_bytes(priv_bytes)

        cli = SDKCLI()
        cli.biopro_dir = tmp_path
        cli.trusted_roots_dir = tmp_path / "trusted_roots"
        cli.init_identity(is_project=True)

        captured = capsys.readouterr()
        assert "SUCCESS" in captured.out
        assert (tmp_path / "dev_cert.bin").exists()
