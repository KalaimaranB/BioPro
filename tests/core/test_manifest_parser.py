import pytest
from biopro_sdk.plugin.manifest_parser import ManifestParser, ManifestValidationError


def test_manifest_v2_valid_parsing():
    manifest_data = {
        "manifest_version": 2,
        "id": "test_plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "description": "A test plugin",
        "authors": [{"name": "Alice Wang", "role": "Lead Developer", "github": "@alicew"}],
    }
    parser = ManifestParser()
    parsed = parser.parse(manifest_data)
    assert parsed["id"] == "test_plugin"
    assert len(parsed["authors"]) == 1
    assert parsed["authors"][0]["role"] == "Lead Developer"


def test_manifest_fails_on_legacy_author():
    manifest_data = {
        "id": "test_plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "description": "A test plugin",
        "author": "alicew",  # Legacy field
    }
    parser = ManifestParser()
    with pytest.raises(ManifestValidationError) as exc:
        parser.parse(manifest_data)
    assert "Legacy 'author' field is no longer supported" in str(exc.value)


def test_manifest_requires_authors_array():
    manifest_data = {
        "manifest_version": 2,
        "id": "test_plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "description": "A test plugin",
    }
    parser = ManifestParser()
    with pytest.raises(ManifestValidationError) as exc:
        parser.parse(manifest_data)
    assert "Missing required field: 'authors'" in str(exc.value)


def test_manifest_fails_on_security_fields():
    # Test that signed_by or integrity inside manifest.json is strictly forbidden
    manifest_data = {
        "manifest_version": 2,
        "id": "test_plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "description": "A test plugin",
        "authors": [{"name": "Alice Wang", "role": "Lead Developer"}],
        "signed_by": {"entity_type": "project", "entity_id": "test_ci_bot"},
    }
    parser = ManifestParser()
    with pytest.raises(ManifestValidationError) as exc:
        parser.parse(manifest_data)
    assert "Security field 'signed_by' is not allowed in manifest.json" in str(exc.value)
