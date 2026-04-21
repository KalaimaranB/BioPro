"""Verification tests for Phase 7: Trust Overrides and Manual Lock."""

import pytest
import os
import json
import shutil
from pathlib import Path
from biopro.core.trust_manager import TrustManager
from tests.core.test_trust_architecture import PluginSigner

def test_manual_lock_workflow(tmp_path):
    """Verify that a user can 'Lock' a tampered plugin to make it trusted locally."""
    plugin_dir = tmp_path / "custom_plugin"
    plugin_dir.mkdir()
    (plugin_dir / "manifest.json").write_text(json.dumps({"id": "custom_plugin"}))
    (plugin_dir / "__init__.py").write_text("orig = 1")
    
    # 1. Sign it officially
    signer = PluginSigner()
    signer.sign_plugin(plugin_dir, signer.generate_developer_cert("dev_id"))
    
    manager = TrustManager(root_public_key=signer.root_public)
    
    # Verify it passes normally
    assert manager.verify_plugin(plugin_dir).success is True
    
    # 2. TAMPER with it (Add scientific customization)
    (plugin_dir / "__init__.py").write_text("orig = 2 # Scientific Modification")
    
    # Should fail now
    res_fail = manager.verify_plugin(plugin_dir)
    assert res_fail.success is False
    assert res_fail.trust_level == "untrusted"
    assert res_fail.calculated_hashes is not None
    
    # 3. USER CLICKS 'LOCK' (Simulated)
    # This calls manager.overrides.trust_current_state
    manager.overrides.trust_current_state("custom_plugin", res_fail.calculated_hashes)
    
    # 4. RE-VERIFY (Should now pass as verified_local)
    res_pass = manager.verify_plugin(plugin_dir)
    assert res_pass.success is True
    assert res_pass.trust_level == "verified_local"
    
    # 5. CHANGE AGAIN (Tamper it even more)
    (plugin_dir / "__init__.py").write_text("orig = 3 # Malicious Modification")
    
    # Should fail again because hashes don't match the override snap
    assert manager.verify_plugin(plugin_dir).success is False

def test_multi_root_trust():
    """Verify that TrustManager trusts custom roots in ~/.biopro/trusted_roots."""
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    
    manager = TrustManager()
    
    # Create a custom root
    custom_root_priv = ed25519.Ed25519PrivateKey.generate()
    custom_root_pub = custom_root_priv.public_key()
    
    # Initially not trusted
    assert custom_root_pub not in manager.trusted_roots
    
    # Add to trusted_roots dir (Mocking the directory)
    roots_dir = Path.home() / ".biopro" / "trusted_roots"
    roots_dir.mkdir(parents=True, exist_ok=True)
    
    key_path = roots_dir / "test_root.pub"
    with open(key_path, "wb") as f:
        f.write(custom_root_pub.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        ))
        
    try:
        # Refresh Roots
        manager._load_all_roots()
        
        # Now it should be trusted!
        # Note: We compare pub_bytes because of how cryptography objects work
        trusted_bytes = [k.public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw) for k in manager.trusted_roots]
        custom_bytes = custom_root_pub.public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
        
        assert custom_bytes in trusted_bytes
        
    finally:
        # Cleanup
        key_path.unlink()
