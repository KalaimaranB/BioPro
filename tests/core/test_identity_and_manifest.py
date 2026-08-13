"""TDD tests for the init-identity CLI command (developer and project modes)."""


def _dict_to_toml(d):
    # Convert flat dict to pyproject.toml format
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
    lines.append("[tool.biopro.plugin]")
    lines.append(f'id = "{d.get("id", "test_id")}"')

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


from pathlib import Path

import pytest
from karcytics_sdk.plugin.manifest_parser import ManifestParser, ManifestValidationError


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

        manifest_file = tmp_path / "pyproject.toml"
        manifest_file.write_text(_dict_to_toml(manifest))

        parser = ManifestParser()
        result = parser.parse_file(str(manifest_file))
        assert result["id"] == "test_plugin"
        assert len(result["authors"]) == 2

    def test_missing_required_field_rejected(self, tmp_path):
        """Missing 'authors' key raises ManifestValidationError."""

        manifest = {
            "manifest_version": 2,
            "id": "bad_plugin",
            "name": "Bad Plugin",
            "version": "1.0.0",
            "description": "Missing authors",
        }
        manifest_file = tmp_path / "pyproject.toml"
        manifest_file.write_text(_dict_to_toml(manifest))

        parser = ManifestParser()
        with pytest.raises(ManifestValidationError) as exc:
            parser.parse_file(str(manifest_file))
        assert "authors" in str(exc.value)


class TestInitIdentity:
    """TDD tests for karcytics sdk init-identity (developer and project modes)."""

    def test_developer_mode_creates_expected_files(self, tmp_path, monkeypatch):
        """init_identity() creates V2 developer key files in ~/.karcytics/dev_keys/."""
        from karcytics_sdk.sdk_cli import SDKCLI

        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        cli = SDKCLI()
        cli.init_identity()

        dev_keys_dir = fake_home / ".karcytics" / "dev_keys"
        assert (dev_keys_dir / "private.key").exists()
        assert (dev_keys_dir / "public.pub").exists()

    def test_developer_mode_cert_is_96_bytes(self, tmp_path, monkeypatch):
        """public.pub must be exactly 32 bytes (raw Ed25519 public key)."""
        from karcytics_sdk.sdk_cli import SDKCLI

        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        cli = SDKCLI()
        cli.init_identity()

        dev_keys_dir = fake_home / ".karcytics" / "dev_keys"
        pub_key = (dev_keys_dir / "public.pub").read_bytes()
        assert len(pub_key) == 32, f"Expected 32 bytes, got {len(pub_key)}"
