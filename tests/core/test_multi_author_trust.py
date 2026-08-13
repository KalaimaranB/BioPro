import json


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
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from karcytics_sdk.host.trust_manager import TrustManager
from karcytics_sdk.host.trust_path import TrustChain, TrustLink


class MockAuthorityAndSigner:
    """Helper to simulate root authorities and multi-author signing keys."""

    def __init__(self):
        self.root_private = ed25519.Ed25519PrivateKey.generate()
        self.root_public = self.root_private.public_key()

    def generate_signed_dev(self, name: str):
        """Generates a developer key signed by the Root Authority."""
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        pub_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
        sig = self.root_private.sign(pub_bytes)

        return {
            "name": name,
            "private_key": private_key,
            "public_key": public_key,
            "signature": sig.hex(),
            "pub_hex": pub_bytes.hex(),
        }


@pytest.fixture
def trust_env(tmp_path):
    """
    Create a mock authority and signer for trust-related tests.

    Parameters:
        tmp_path: Temporary path fixture included for pytest compatibility.

    Returns:
        MockAuthorityAndSigner: Mock authority with a generated root key pair.
    """
    mock_auth = MockAuthorityAndSigner()
    return mock_auth  # noqa: RET504


@pytest.fixture
def mock_plugin_dir(tmp_path):
    plugin_dir = tmp_path / "multi_author_plugin"
    plugin_dir.mkdir()

    # Write init file
    (plugin_dir / "__init__.py").write_text("print('core logic')", encoding="utf-8")

    return plugin_dir


def sign_mock_plugin(plugin_dir, manifest_data, dev_certs, mock_auth):
    """Signs mock plugin generating split-manifest formats for tests."""
    manifest_file = plugin_dir / "pyproject.toml"
    manifest_file.write_text(_dict_to_toml(manifest_data), encoding="utf-8")

    # Calculate manifest hash binding
    import hashlib

    manifest_bytes = manifest_file.read_bytes().replace(b"\r\n", b"\n")
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()

    # Simple walk to hash python files
    hashes = {}
    for file in sorted(plugin_dir.glob("*.py")):
        if file.name in [
            "pyproject.toml",
            "security.json",
            "signature.bin",
            "project_signature.bin",
        ]:
            continue
        hashes[file.name] = hashlib.sha256(file.read_bytes()).hexdigest()

    security_data = {
        "security_version": 1,
        "plugin_id": plugin_dir.name,
        "manifest_hash": manifest_hash,
        "hashes": hashes,
    }

    # Write security.json
    (plugin_dir / "security.json").write_text(json.dumps(security_data, indent=4), encoding="utf-8")

    # Developer leaf signs (first developer is the primary signer)
    primary_dev = dev_certs[0]
    canonical_bytes = json.dumps(security_data, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    signature = primary_dev["private_key"].sign(canonical_bytes)

    (plugin_dir / "signature.bin").write_bytes(signature)

    # Build Trust Chain containing all signing developer links
    links = []
    for dev in dev_certs:
        links.append(
            TrustLink(
                subject_name=dev["name"],
                subject_pub=dev["pub_hex"],
                issuer_name="Karcytics Core Authority",
                signature=dev["signature"],
            )
        )

    chain = TrustChain(links=links)
    (plugin_dir / "trust_chain.json").write_text(chain.to_json(), encoding="utf-8")


class TestMultiAuthorTrustEngine:
    def test_rbac_sign_off_tester_does_not_require_signature(self, trust_env, mock_plugin_dir):
        """Test Case A: Alice (Developer, sign_code) and Bob (Tester, test).
        Alice is trusted. Bob is untrusted/unsigned.
        Assert verification succeeds because Bob is not required to sign.
        """
        alice_dev = trust_env.generate_signed_dev("Alice Vance")

        manifest_data = {
            "manifest_version": 2,
            "id": mock_plugin_dir.name,
            "name": "Flow Cytometry",
            "version": "1.0.0",
            "description": "FCS Reader",
            "authors": [
                {"name": "Alice Vance", "role": "Lead Scientist", "permissions": ["sign_code"]},
                {
                    "name": "Bob Miller",
                    "role": "QA Tester",
                    "permissions": ["test"],  # No sign_code permission!
                },
            ],
        }

        # Sign as Alice only
        sign_mock_plugin(mock_plugin_dir, manifest_data, [alice_dev], trust_env)

        manager = TrustManager(root_public_key=trust_env.root_public)
        result = manager.verify_plugin(mock_plugin_dir)

        assert result.success is True, result.error_message
        assert result.trust_level == "verified_developer"

    def test_rbac_sign_off_fails_if_required_coauthor_unsigned(self, trust_env, mock_plugin_dir):
        """Test Case B: Alice (Developer, sign_code) and Bob (Developer, sign_code).
        Alice signs, but Bob does not sign/has no matching trusted public key in trust_chain.json.
        Assert verification fails with co-author untrusted.
        """
        alice_dev = trust_env.generate_signed_dev("Alice Vance")

        manifest_data = {
            "manifest_version": 2,
            "id": mock_plugin_dir.name,
            "name": "Flow Cytometry",
            "version": "1.0.0",
            "description": "FCS Reader",
            "authors": [
                {"name": "Alice Vance", "role": "Lead Scientist", "permissions": ["sign_code"]},
                {
                    "name": "Bob Miller",
                    "role": "Co-Developer",
                    "permissions": ["sign_code"],  # ALSO has sign_code!
                },
            ],
        }

        # Sign with Alice only
        sign_mock_plugin(mock_plugin_dir, manifest_data, [alice_dev], trust_env)

        manager = TrustManager(root_public_key=trust_env.root_public)
        result = manager.verify_plugin(mock_plugin_dir)

        assert result.success is False
        assert "Co-Author Untrusted" in result.error_message

    def test_rbac_sign_off_success_with_all_cosigners(self, trust_env, mock_plugin_dir):
        """Test Case C: Alice and Bob both have sign_code permission and both sign.
        Assert verification succeeds.
        """
        alice_dev = trust_env.generate_signed_dev("Alice Vance")
        bob_dev = trust_env.generate_signed_dev("Bob Miller")

        manifest_data = {
            "manifest_version": 2,
            "id": mock_plugin_dir.name,
            "name": "Flow Cytometry",
            "version": "1.0.0",
            "description": "FCS Reader",
            "authors": [
                {"name": "Alice Vance", "role": "Lead Scientist", "permissions": ["sign_code"]},
                {"name": "Bob Miller", "role": "Co-Developer", "permissions": ["sign_code"]},
            ],
        }

        # Both sign
        sign_mock_plugin(mock_plugin_dir, manifest_data, [alice_dev, bob_dev], trust_env)

        manager = TrustManager(root_public_key=trust_env.root_public)
        result = manager.verify_plugin(mock_plugin_dir)

        assert result.success is True, result.error_message
        assert result.trust_level == "verified_developer"

    def test_covert_backdoor_exclusion_scanning(self, trust_env, mock_plugin_dir):
        """Test Case D: Place an executable py file in an ignored directory (e.g. results/backdoor.py).
        Assert verification fails immediately with 'Unauthorized Executable in Excluded Directory'.
        """
        alice_dev = trust_env.generate_signed_dev("Alice Vance")

        manifest_data = {
            "manifest_version": 2,
            "id": mock_plugin_dir.name,
            "name": "Flow Cytometry",
            "version": "1.0.0",
            "description": "FCS Reader",
            "authors": [
                {"name": "Alice Vance", "role": "Lead Scientist", "permissions": ["sign_code"]}
            ],
        }

        # Sign mock plugin first
        sign_mock_plugin(mock_plugin_dir, manifest_data, [alice_dev], trust_env)

        # Create an ignored directory and inject a malicious backdoor py script
        ignored_dir = mock_plugin_dir / "results"
        ignored_dir.mkdir()
        (ignored_dir / "backdoor.py").write_text(
            "import os; os.system('rm -rf /')", encoding="utf-8"
        )

        manager = TrustManager(root_public_key=trust_env.root_public)
        result = manager.verify_plugin(mock_plugin_dir)

        assert result.success is False
        assert "Unauthorized Executable in Excluded Directory" in result.error_message
