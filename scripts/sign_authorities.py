#!/usr/bin/env python3
"""BioPro Authorities Registry Signing Tool.

This script signs the 'authorities' array inside 'authorities.json' using your
hex-encoded Ed25519 private key and outputs the fully-signed JSON structure.
"""

import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import ed25519


def main():
    # 1. Ask for the Hex Private Key
    print("=== BioPro Authority Registry Signer ===")
    hex_key = input("Enter your 32-byte Ed25519 Private Key (hex format): ").strip()

    try:
        private_bytes = bytes.fromhex(hex_key)
        if len(private_bytes) != 32:
            raise ValueError(
                f"Private key must be exactly 32 bytes (64 hex characters). Got {len(private_bytes)} bytes."
            )

        # Load the key using standard cryptography
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_bytes)
        print("✔ Private key successfully loaded!")
    except Exception as e:
        print(f"❌ Error loading private key: {e}")
        return

    # 2. Locate authorities.json
    workspace_dir = Path(__file__).resolve().parent.parent
    auth_file = workspace_dir / "authorities.json"

    if not auth_file.exists():
        # Fallback to creating a default template if not present
        print(f"authorities.json not found at {auth_file}. Creating a template...")
        default_data = {
            "version": "1",
            "signed_by": "biopro_core",
            "signature": "",
            "authorities": [
                {
                    "id": "biopro_core",
                    "name": "BioPro Core Authority",
                    "public_key": "08f4319b6f979057b36b0db2b8faaee6eff8782f3aafd5e924ba79b04d4c8366",
                }
            ],
            "last_updated": "2026-05-18T00:00:00Z",
        }
        with open(auth_file, "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=2)

    # 3. Read authorities.json
    try:
        with open(auth_file, encoding="utf-8") as f:
            auth_data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to parse authorities.json: {e}")
        return

    authorities = auth_data.get("authorities")
    if not authorities:
        print("❌ Error: No 'authorities' list found in authorities.json.")
        return

    # 4. Canonicalize & Sign
    try:
        # Match client's exact canonical representation (sort keys, compact)
        canonical_bytes = json.dumps(authorities, sort_keys=True).encode("utf-8")

        signature = private_key.sign(canonical_bytes)
        sig_hex = signature.hex()

        # 5. Update signature and save
        auth_data["signature"] = sig_hex

        with open(auth_file, "w", encoding="utf-8") as f:
            json.dump(auth_data, f, indent=2)

        print("\n✔ authorities.json successfully signed!")
        print(f"New Signature: {sig_hex}")
        print(f"File updated at: {auth_file}\n")

        # Display the result for copy-pasting convenience
        print("--- COPY & PASTE TO YOUR REMOTE REPO ---")
        print(json.dumps(auth_data, indent=2))
        print("----------------------------------------")

    except Exception as e:
        print(f"❌ Signing failed: {e}")


if __name__ == "__main__":
    main()
