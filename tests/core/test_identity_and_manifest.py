"""TDD tests for the init-identity CLI command (developer and project modes)."""

import json
from pathlib import Path

import pytest
from biopro_sdk.plugin.manifest_parser import ManifestParser, ManifestValidationError


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
            "authors": [
                {"name": "Alice", "role": "Developer"},
                {"name": "Bob", "role": "Developer"},
            ],
        }

        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(json.dumps(manifest))

        parser = ManifestParser()
        result = parser.parse_file(str(manifest_file))
        assert result["id"] == "test_plugin"
        assert len(result["authors"]) == 2

    def test_legacy_manifest_file_is_rejected(self, tmp_path):
        """A manifest using the old 'author' string field raises ManifestValidationError."""

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

        manifest = {
            "manifest_version": 2,
            "id": "bad_plugin",
            "name": "Bad Plugin",
            "version": "1.0.0",
            "description": "Missing authors",
        }
        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(json.dumps(manifest))

        parser = ManifestParser()
        with pytest.raises(ManifestValidationError) as exc:
            parser.parse_file(str(manifest_file))
        assert "authors" in str(exc.value)


class TestInitIdentity:
    """TDD tests for biopro sdk init-identity (developer and project modes)."""

    def test_developer_mode_creates_expected_files(self, tmp_path, monkeypatch):
        """init_identity() creates V2 developer key files in ~/.biopro/dev_keys/."""
        from biopro_sdk.sdk_cli import SDKCLI

        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        cli = SDKCLI()
        cli.init_identity()

        dev_keys_dir = fake_home / ".biopro" / "dev_keys"
        assert (dev_keys_dir / "private.key").exists()
        assert (dev_keys_dir / "public.pub").exists()

    def test_developer_mode_cert_is_96_bytes(self, tmp_path, monkeypatch):
        """public.pub must be exactly 32 bytes (raw Ed25519 public key)."""
        from biopro_sdk.sdk_cli import SDKCLI

        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        cli = SDKCLI()
        cli.init_identity()

        dev_keys_dir = fake_home / ".biopro" / "dev_keys"
        pub_key = (dev_keys_dir / "public.pub").read_bytes()
        assert len(pub_key) == 32, f"Expected 32 bytes, got {len(pub_key)}"
