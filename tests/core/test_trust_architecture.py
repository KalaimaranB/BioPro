"""TDD Suite for BioPro Trust Architecture (Phase 4).

This suite defines the expected security behaviors for plugin integrity,
Chain of Trust verification, and performance optimization.
"""

import pytest
import os
import json
import shutil
import time
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# We expect these to exist after implementation
from biopro.core.trust_manager import TrustManager
from biopro.core.trust_storage import TrustCache
from biopro.core.trust_path import TrustChain, TrustLink

class PluginSigner:
    """Helper to simulate the BioPro Authority and Plugin Developers."""
    
    def __init__(self):
        # The ultimate Root of Trust
        self.root_private = ed25519.Ed25519PrivateKey.generate()
        self.root_public = self.root_private.public_key()
        
    def generate_developer_cert(self, dev_id: str):
        """Creates a signed developer key (Chain of Trust)."""
        dev_private = ed25519.Ed25519PrivateKey.generate()
        dev_public = dev_private.public_key()
        
        # In a real PKI, this would be a structured cert. 
        # For BioPro, we sign the public bytes of the dev key.
        public_bytes = dev_public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        signature = self.root_private.sign(public_bytes)
        
        return {
            "dev_id": dev_id,
            "private_key": dev_private,
            "public_key": dev_public,
            "name": dev_id
        }

    def sign_plugin(self, plugin_dir: Path, dev_cert: dict):
        """Generates integrity hashes and signs the manifest."""
        manifest_path = plugin_dir / "manifest.json"
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
            
        # Calculate Merkle-Integrity (Simple version: hash-map)
        hashes = {}
        for root, _, files in os.walk(plugin_dir):
            for file in sorted(files):
                if file in ["signature.bin", "trust_chain.json", "manifest.json"]:
                    continue
                # Smart Strictness: Skip noise
                if file == ".DS_Store" or "__pycache__" in root:
                    continue
                    
                rel_path = os.path.relpath(os.path.join(root, file), plugin_dir)
                import hashlib
                with open(os.path.join(root, file), "rb") as f:
                    hashes[rel_path] = hashlib.sha256(f.read()).hexdigest()
        
        if "integrity" not in manifest:
            manifest["integrity"] = {}
            
        manifest["integrity"]["hashes"] = hashes
        manifest["integrity"]["dev_id"] = dev_cert["dev_id"]
        
        # Update manifest on disk
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=4)
            
        # Sign the manifest bytes
        manifest_bytes = json.dumps(manifest, sort_keys=True).encode()
        signature = dev_cert["private_key"].sign(manifest_bytes)
        
        # Write artifacts
        with open(plugin_dir / "signature.bin", "wb") as f:
            f.write(signature)
            
        # Create Trust Chain (1-level for simplicity in base tests)
        dev_pub_hex = dev_cert["public_key"].public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        ).hex()
        
        root_pub_bytes = self.root_public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        # Sign dev key as root
        root_sig = self.root_private.sign(bytes.fromhex(dev_pub_hex))
        
        chain = TrustChain(links=[
            TrustLink(
                subject_name=dev_cert["name"],
                subject_pub=dev_pub_hex,
                issuer_name="BioPro Core",
                signature=root_sig.hex()
            )
        ])
        
        with open(plugin_dir / "trust_chain.json", "w") as f:
            f.write(chain.to_json())


@pytest.fixture
def auth():
    return PluginSigner()

@pytest.fixture
def temp_plugin_dir(tmp_path):
    pkg_dir = tmp_path / "test_plugin"
    pkg_dir.mkdir()
    
    # Create standard plugin structure
    (pkg_dir / "manifest.json").write_text(json.dumps({
        "id": "test_plugin",
        "version": "1.0.0"
    }))
    (pkg_dir / "__init__.py").write_text("print('Hello Trust')")
    (pkg_dir / "ui").mkdir()
    (pkg_dir / "ui" / "panel.py").write_text("class UI: pass")
    
    return pkg_dir

class TestTrustArchitecture:
    """TDD Test Suite for Trust Architecture."""

    def test_default_key_loading(self):
        """Regression test for valid hex-encoded root public key."""
        try:
            manager = TrustManager() # Should NOT raise ValueError
            assert len(manager.trusted_roots) > 0
        except ValueError as e:
            pytest.fail(f"TrustManager failed to load hardcoded root key: {e}")

    def test_valid_plugin_verification(self, auth, temp_plugin_dir):
        """Verifies that a correctly signed plugin passes the check."""
        dev_cert = auth.generate_developer_cert("dev_01")
        auth.sign_plugin(temp_plugin_dir, dev_cert)
        
        # Inject Root Key into Manager for testing
        manager = TrustManager(root_public_key=auth.root_public)
        result = manager.verify_plugin(temp_plugin_dir)
        
        assert result.success is True, result.error_message
        assert result.trust_level == "verified_developer"

    def test_unauthorized_file_rejection(self, auth, temp_plugin_dir):
        """Verifies that extra unauthorized files cause rejection."""
        dev_cert = auth.generate_developer_cert("dev_01")
        auth.sign_plugin(temp_plugin_dir, dev_cert)
        
        # Add a rogue script AFTER signing
        (temp_plugin_dir / "backdoor.py").write_text("import os; os.system('rm -rf /')")
        
        manager = TrustManager(root_public_key=auth.root_public)
        result = manager.verify_plugin(temp_plugin_dir)
        
        assert result.success is False, "Should have rejected extra file"
        assert "unauthorized file" in result.error_message.lower()

    def test_file_tampering_rejection(self, auth, temp_plugin_dir):
        """Verifies that modified code causes rejection."""
        dev_cert = auth.generate_developer_cert("dev_01")
        auth.sign_plugin(temp_plugin_dir, dev_cert)
        
        # Tamper with __init__.py
        (temp_plugin_dir / "__init__.py").write_text("print('TAMPERED')")
        
        manager = TrustManager(root_public_key=auth.root_public)
        result = manager.verify_plugin(temp_plugin_dir)
        
        assert result.success is False, "Should have rejected tampered file"
        assert "integrity mismatch" in result.error_message.lower()

    def test_smart_strictness_ignores(self, auth, temp_plugin_dir):
        """Verifies that __pycache__ and noise files don't break verification."""
        dev_cert = auth.generate_developer_cert("dev_01")
        auth.sign_plugin(temp_plugin_dir, dev_cert)
        
        # Add system noise
        (temp_plugin_dir / ".DS_Store").write_text("noise")
        pycache = temp_plugin_dir / "__pycache__"
        pycache.mkdir()
        (pycache / "init.pyc").write_text("bytecode")
        
        manager = TrustManager(root_public_key=auth.root_public)
        result = manager.verify_plugin(temp_plugin_dir)
        
        assert result.success is True, result.error_message

    def test_identity_swapping_protection(self, auth, temp_plugin_dir, tmp_path):
        """Verifies that signature A cannot be used for Plugin B."""
        # Setup Plugin A
        dev_cert = auth.generate_developer_cert("dev_01")
        auth.sign_plugin(temp_plugin_dir, dev_cert)
        
        # Setup Plugin B (unprotected)
        plugin_b = tmp_path / "malicious_plugin"
        plugin_b.mkdir()
        (plugin_b / "manifest.json").write_text(json.dumps({"id": "malicious_plugin"}))
        (plugin_b / "__init__.py").write_text("dangerous code")
        
        # Copy signature, chain, AND THE SIGNED MANIFEST from A to B
        shutil.copy(temp_plugin_dir / "signature.bin", plugin_b / "signature.bin")
        shutil.copy(temp_plugin_dir / "trust_chain.json", plugin_b / "trust_chain.json")
        shutil.copy(temp_plugin_dir / "manifest.json", plugin_b / "manifest.json")
        
        manager = TrustManager(root_public_key=auth.root_public)
        result = manager.verify_plugin(plugin_b)
        
        assert result.success is False, "Should have rejected identity swap"
        assert "identity mismatch" in result.error_message.lower()

    def test_trust_cache_performance(self, auth, temp_plugin_dir):
        """Verifies that re-loading a verified plugin is extremely fast."""
        dev_cert = auth.generate_developer_cert("dev_01")
        auth.sign_plugin(temp_plugin_dir, dev_cert)
        
        manager = TrustManager(root_public_key=auth.root_public)
        
        # Initial verify (cold cache)
        start_cold = time.time()
        manager.verify_plugin(temp_plugin_dir)
        cold_time = time.time() - start_cold
        
        # Second verify (warm cache)
        start_warm = time.time()
        manager.verify_plugin(temp_plugin_dir)
        warm_time = time.time() - start_warm
        
        # Warm should be at least 10x faster (actually 100x usually)
        assert warm_time < (cold_time / 10)

    def test_multi_level_trust_chain(self, auth, temp_plugin_dir):
        """Verifies a 3-level chain: Root -> Uni -> Lab -> Researcher."""
        # 1. Setup Keys
        uni_priv = ed25519.Ed25519PrivateKey.generate()
        uni_pub = uni_priv.public_key()
        
        lab_priv = ed25519.Ed25519PrivateKey.generate()
        lab_pub = lab_priv.public_key()
        
        dev_priv = ed25519.Ed25519PrivateKey.generate()
        dev_pub = dev_priv.public_key()
        
        # 2. Build Signatures
        # Root signs Uni
        uni_pub_bytes = uni_pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        sig_root_to_uni = auth.root_private.sign(uni_pub_bytes)
        
        # Uni signs Lab
        lab_pub_bytes = lab_pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        sig_uni_to_lab = uni_priv.sign(lab_pub_bytes)
        
        # Lab signs Dev
        dev_pub_bytes = dev_pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        sig_lab_to_dev = lab_priv.sign(dev_pub_bytes)
        
        # 3. Create TrustChain JSON
        chain = TrustChain(links=[
            TrustLink("Dr. Alice", dev_pub_bytes.hex(), "MICB Lab", sig_lab_to_dev.hex()),
            TrustLink("MICB Lab", lab_pub_bytes.hex(), "UBC", sig_uni_to_lab.hex()),
            TrustLink("UBC", uni_pub_bytes.hex(), "BioPro Core", sig_root_to_uni.hex())
        ])
        
        with open(temp_plugin_dir / "trust_chain.json", "w") as f:
            f.write(chain.to_json())
            
        # 4. Sign Plugin Manifest as Dev
        manifest_path = temp_plugin_dir / "manifest.json"
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        
        import hashlib
        # Ensure we hash EVERY file in the temp_plugin_dir so integrity passes
        hashes = {}
        for f in temp_plugin_dir.rglob("*"):
            if f.is_file() and f.name not in ["manifest.json", "signature.bin", "trust_chain.json"]:
                rel = f.relative_to(temp_plugin_dir)
                hashes[str(rel)] = hashlib.sha256(f.read_bytes()).hexdigest()

        manifest["integrity"] = {"hashes": hashes}
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=4)
            
        manifest_bytes = json.dumps(manifest, sort_keys=True).encode()
        signature = dev_priv.sign(manifest_bytes)
        with open(temp_plugin_dir / "signature.bin", "wb") as f:
            f.write(signature)
            
        # 5. Verify
        manager = TrustManager(root_public_key=auth.root_public)
        result = manager.verify_plugin(temp_plugin_dir)
        
        if not result.success:
            print(f"VERIFICATION FAILED: {result.error_message}")
            
        assert result.success is True, result.error_message
        # Full path should be Core -> UBC -> Lab -> Alice (4 nodes)
        assert len(result.trust_path) == 4
        assert result.trust_path[1]['name'] == "UBC"
        assert result.trust_path[3]['name'] == "Dr. Alice"
