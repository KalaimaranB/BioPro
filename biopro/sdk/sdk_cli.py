"""SDK CLI Utilities for BioPro developers.

Handles developer identity setup, plugin signing, and manifest generation.
"""

import os
import sys
import json
import hashlib
import logging
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger(__name__)

class SDKCLI:
    """CLI handler for BioPro SDK operations."""
    
    def __init__(self):
        self.biopro_dir = Path.home() / ".biopro"
        self.trusted_roots_dir = self.biopro_dir / "trusted_roots"

    def setup_identity(self):
        """Bootstrap a local developer identity and root trust."""
        self.biopro_dir.mkdir(parents=True, exist_ok=True)
        self.trusted_roots_dir.mkdir(parents=True, exist_ok=True)

        print("--- BioPro Developer Onboarding ---")
        
        # 1. Generate Local Onboarding Root (Used to trust yourself locally)
        root_private = ed25519.Ed25519PrivateKey.generate()
        root_public = root_private.public_key()
        
        root_pub_file = self.trusted_roots_dir / "onboarding_root.pub"
        root_pub_bytes = root_public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        with open(root_pub_file, "wb") as f:
            f.write(root_pub_bytes)
        print(f"Created Local Trust Root: {root_pub_file}")

        # 2. Generate Developer Keypair
        dev_private = ed25519.Ed25519PrivateKey.generate()
        dev_public = dev_private.public_key()
        
        dev_priv_file = self.biopro_dir / "dev_private_key.pem"
        dev_priv_bytes = dev_private.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.OpenSSH,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        with open(dev_priv_file, "wb") as f:
            f.write(dev_priv_bytes)
        print(f"Created Developer Private Key: {dev_priv_file}")

        # 3. Create 'dev_cert.bin' (Self-signed by the local onboarding root)
        # Format: [32 bytes dev_pub_raw] + [64 bytes signature]
        dev_pub_raw = dev_public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        signature = root_private.sign(dev_pub_raw)
        
        cert_file = self.biopro_dir / "dev_cert.bin"
        with open(cert_file, "wb") as f:
            f.write(dev_pub_raw + signature)
            
        print(f"Created Developer Certificate: {cert_file}")
        print("\nSUCCESS: Your local machine now trusts plugins signed with this identity.")
        print("Use 'biopro sdk sign <plugin_dir>' to sign your work.")

    def sign_plugin(self, plugin_dir: str):
        """Sign a plugin using the local developer identity."""
        from biopro.core.trust_manager import TrustManager
        
        p_dir = Path(plugin_dir)
        cert_file = self.biopro_dir / "dev_cert.bin"
        priv_file = self.biopro_dir / "dev_private_key.pem"
        manifest_file = p_dir / "manifest.json"

        # Check for Identity first
        if not cert_file.exists() or not priv_file.exists():
            print("ERROR: Developer identity not found. Run 'biopro sdk setup-identity' first.")
            return

        # Check for Target Manifest
        if not manifest_file.exists():
            print(f"ERROR: No manifest.json found in '{p_dir}'. Are you in the right plugin folder?")
            return

        # 1. Load Keys
        with open(priv_file, "rb") as f:
            dev_private = serialization.load_ssh_private_key(f.read(), password=None)
        
        with open(manifest_file, "r") as f:
            manifest = json.load(f)

        # 2. Calculate Integrity Hashes (Merkle-style)
        # Prune ignored directories to avoid over-inclusion (e.g. __pycache__)
        # We synchronize with the main TrustManager list
        ignore_list = TrustManager.IGNORE_LIST.union({
            "signature.bin", "dev_cert.bin", "manifest.json", ".venv"
        })
        hashes = {}
        
        for root, dirs, files in os.walk(p_dir):
            # Prune directories in-place to skip them entirely
            dirs[:] = [d for d in dirs if d not in ignore_list]
            
            for file in files:
                if file in ignore_list: continue
                rel_path = os.path.relpath(os.path.join(root, file), p_dir)
                
                hasher = hashlib.sha256()
                with open(os.path.join(root, file), "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hasher.update(chunk)
                hashes[rel_path] = hasher.hexdigest()

        # 3. Update Manifest
        if "integrity" not in manifest: manifest["integrity"] = {}
        manifest["integrity"]["hashes"] = hashes
        
        with open(manifest_file, "w") as f:
            json.dump(manifest, f, indent=4)

        # 4. Sign the Canonicalized Manifest
        manifest_bytes = json.dumps(manifest, sort_keys=True).encode()
        signature = dev_private.sign(manifest_bytes)
        
        # 5. Write artifacts to plugin folder
        with open(p_dir / "signature.bin", "wb") as f:
            f.write(signature)
            
        import shutil
        shutil.copy(cert_file, p_dir / "dev_cert.bin")
        
        print(f"Successfully signed plugin: {manifest.get('id', p_dir.name)}")

    def sign_all(self, parent_dir: str):
        """Batch sign all valid plugins in a parent directory."""
        p_dir = Path(parent_dir)
        if not p_dir.is_dir():
            print(f"ERROR: '{p_dir}' is not a directory.")
            return

        print(f"--- Batch Signing: {p_dir} ---")
        signed_count = 0
        for sub in p_dir.iterdir():
            if sub.is_dir() and (sub / "manifest.json").exists():
                print(f"Signing {sub.name}...")
                try:
                    self.sign_plugin(str(sub))
                    signed_count += 1
                except Exception as e:
                    print(f"  FAILED: {e}")
        
        print(f"--- Batch Complete: Signed {signed_count} modules ---")

def main():
    if len(sys.argv) < 3:
        print("Usage: biopro sdk [setup-identity | sign <dir> | sign-all <dir>]")
        return

    cli = SDKCLI()
    cmd = sys.argv[2]
    
    if cmd == "setup-identity":
        cli.setup_identity()
    elif cmd == "sign" and len(sys.argv) > 3:
        cli.sign_plugin(sys.argv[3])
    elif cmd == "sign-all" and len(sys.argv) > 3:
        cli.sign_all(sys.argv[3])
    else:
        print("Unknown SDK command.")

if __name__ == "__main__":
    main()
