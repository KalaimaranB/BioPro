import hashlib
import json

import pytest
from biopro_sdk.plugin.manifest_parser import ManifestParser, ManifestValidationError
from biopro_sdk.plugin.security_parser import (
    ManifestHashMismatch,
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


def test_no_backwards_compatibility_strict_failures():
    """Assert that legacy manifest structures or V1 schemas fail verification outright (No fallback allowed)."""
    parser = ManifestParser()

    # Legacy V1 manifest structure (no manifest_version, single author string)
    legacy_manifest_1 = {
        "id": "legacy_plugin",
        "name": "Legacy",
        "version": "0.9.0",
        "description": "An old plugin",
        "author": "Dr. Vance",  # Legacy single-author string
    }
    with pytest.raises(ManifestValidationError) as exc:
        parser.parse(legacy_manifest_1)
    assert "Legacy 'author' field is no longer supported" in str(exc.value)

    # V2 manifest without authors array
    legacy_manifest_2 = {
        "manifest_version": 2,
        "id": "legacy_plugin",
        "name": "Legacy",
        "version": "0.9.0",
        "description": "An old plugin",
        # Missing authors array completely
    }
    with pytest.raises(ManifestValidationError) as exc:
        parser.parse(legacy_manifest_2)
    assert "Missing required field: 'authors'" in str(exc.value)


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


def test_manifest_security_hash_binding_tampering(tmp_path):
    """Test Case D: Tamper with manifest.json and assert that the validator raises a ManifestHashMismatch when checking against security.json's bound hash."""
    manifest_data = {
        "manifest_version": 2,
        "id": "segmenter_plugin",
        "name": "Flow Segmenter",
        "version": "1.2.0",
        "description": "FCS segmentation utility.",
        "authors": [{"name": "Alice", "role": "Developer"}],
    }

    # Write initial manifest.json
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(
        json.dumps(manifest_data, sort_keys=True, separators=(",", ":")), encoding="utf-8"
    )

    # Calculate initial hash
    manifest_bytes = manifest_file.read_bytes()
    expected_hash = hashlib.sha256(manifest_bytes).hexdigest()

    security_data = {
        "security_version": 1,
        "plugin_id": "segmenter_plugin",
        "manifest_hash": expected_hash,
        "hashes": {},
    }

    # Verification with pristine manifest should succeed
    sec_parser = SecurityParser()
    sec_parser.verify_manifest_binding(manifest_file, security_data)

    # Tamper with the manifest file (change version description)
    manifest_data["description"] = "TAMPERED FCS segmentation utility."
    manifest_file.write_text(
        json.dumps(manifest_data, sort_keys=True, separators=(",", ":")), encoding="utf-8"
    )

    # Verification should now fail and raise ManifestHashMismatch
    with pytest.raises(ManifestHashMismatch) as exc:
        sec_parser.verify_manifest_binding(manifest_file, security_data)
    assert (
        "Cryptographic bind mismatch: manifest.json SHA-256 does not match security.json manifest_hash"
        in str(exc.value)
    )
