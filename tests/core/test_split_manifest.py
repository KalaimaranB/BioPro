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


import pytest
from karcytics_sdk.plugin.manifest_parser import ManifestParser, ManifestValidationError
from karcytics_sdk.plugin.security_parser import (
    SecurityParser,
    SecurityValidationError,
)


def test_manifest_v2_split_valid_parsing():
    """Test Case A: Parse a valid manifest.json (pure metadata) and verify dependencies are correctly extracted."""
    manifest_data = {
        "manifest_version": 2,
        "id": "segmenter_plugin",
        "name": "Flow Segmenter",
        "version": "1.2.0",
        "description": "FCS single-cell segmentation utility.",
        "authors": [
            {
                "name": "Dr. Alice Vance",
                "email": "alice@vance-lab.org",
                "avatar": "assets/avatar_alice.png",
                "role": "Lead Scientist",
                "details": "Director of Vance Lab.",
                "permissions": ["sign_code", "admin"],
            }
        ],
        "screenshots": ["assets/screenshots/screen1.png"],
        "dependencies": {"numpy": "1.24.0", "scipy": "1.10.0"},
    }

    parser = ManifestParser()
    parsed = parser.parse(manifest_data)

    assert parsed["id"] == "segmenter_plugin"
    assert parsed["version"] == "1.2.0"
    assert len(parsed["authors"]) == 1
    assert parsed["dependencies"]["numpy"] == "1.24.0"
    assert parsed["screenshots"][0] == "assets/screenshots/screen1.png"
    # Ensure integrity hashes are NOT in manifest.json (SOLID violation prevention)
    assert "integrity" not in parsed
    assert "hashes" not in parsed


def test_manifest_v2_detailed_authors_validation():
    """Test Case B: Parse a detailed authors array inside manifest.json asserting that role, details, and permissions fields are successfully parsed and validated."""
    manifest_data = {
        "manifest_version": 2,
        "id": "segmenter_plugin",
        "name": "Flow Segmenter",
        "version": "1.2.0",
        "description": "FCS segmentation utility.",
        "authors": [
            {
                "name": "Bob Miller",
                "email": "bob@tester.org",
                "avatar": "assets/avatar_bob.png",
                "role": "QA Tester",
                "details": "Conducted functional integration testing.",
                "permissions": ["test"],
            }
        ],
    }

    parser = ManifestParser()
    parsed = parser.parse(manifest_data)
    author = parsed["authors"][0]

    assert author["name"] == "Bob Miller"
    assert author["role"] == "QA Tester"
    assert author["details"] == "Conducted functional integration testing."
    assert author["permissions"] == ["test"]


def test_manifest_v2_author_validation_strictness():
    """Ensure that invalid author schemas (e.g. missing role or invalid permissions type) raise ManifestValidationError."""
    parser = ManifestParser()

    # Missing required 'role' in author dictionary
    bad_manifest_1 = {
        "manifest_version": 2,
        "id": "plugin",
        "name": "Test",
        "version": "1.0.0",
        "description": "Desc",
        "authors": [
            {
                "name": "Alice",
                "email": "alice@test.com",
                # Missing 'role'
            }
        ],
    }
    with pytest.raises(ManifestValidationError) as exc:
        parser.parse(bad_manifest_1)
    assert "Author profile must contain 'role'" in str(exc.value)

    # Invalid permissions format (must be a list of strings)
    bad_manifest_2 = {
        "manifest_version": 2,
        "id": "plugin",
        "name": "Test",
        "version": "1.0.0",
        "description": "Desc",
        "authors": [
            {
                "name": "Alice",
                "role": "Developer",
                "permissions": "sign_code",  # Should be a list
            }
        ],
    }
    with pytest.raises(ManifestValidationError) as exc:
        parser.parse(bad_manifest_2)
    assert "Author 'permissions' must be a list of strings" in str(exc.value)


def test_security_parser_valid_parsing():
    """Test Case C: Parse security.json and ensure it extracts all file hashes and the manifest binding hash."""
    security_data = {
        "security_version": 1,
        "plugin_id": "segmenter_plugin",
        "manifest_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "exclusions": ["custom_outputs/"],
        "hashes": {"__init__.py": "a4d3f283...", "analysis.py": "7c8e9b1a..."},
    }

    parser = SecurityParser()
    parsed = parser.parse(security_data)

    assert parsed["plugin_id"] == "segmenter_plugin"
    assert (
        parsed["manifest_hash"]
        == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    assert parsed["exclusions"] == ["custom_outputs/"]
    assert "__init__.py" in parsed["hashes"]


def test_security_parser_validation_strictness():
    """Ensure missing fields or invalid versions throw SecurityValidationError."""
    parser = SecurityParser()

    # Missing manifest_hash
    bad_security = {"security_version": 1, "plugin_id": "plugin", "hashes": {}}
    with pytest.raises(SecurityValidationError) as exc:
        parser.parse(bad_security)
    assert "Missing required security field: 'manifest_hash'" in str(exc.value)

    # Invalid security version
    bad_version = {
        "security_version": 99,
        "plugin_id": "plugin",
        "manifest_hash": "hash",
        "hashes": {},
    }
    with pytest.raises(SecurityValidationError) as exc:
        parser.parse(bad_version)
    assert "Only security_version: 1 is supported" in str(exc.value)
