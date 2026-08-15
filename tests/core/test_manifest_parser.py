import pytest
from karcytics_sdk.plugin.manifest_parser import ManifestParser, ManifestValidationError


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
