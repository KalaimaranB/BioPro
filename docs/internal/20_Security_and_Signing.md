# Security and Code-Signing Guide

This document provides developers with specifications for signing plugins, configuring Role-Based Access Control (RBAC) in manifests, and integrating signing into CI/CD pipelines.

---

## Signature Verification Model

BioPro utilizes an asymmetric signature model. A distributed plugin must satisfy verification against the `TrustManager`.

The core validation relies on the **Developer Signature** (`signature.bin`), which is an Ed25519 signature generated over the canonical byte representation of the `security.json` ledger.
Some organizational pipelines may also enforce a **Project CI Co-Signature** (`project_signature.bin`) to validate automated testing compliance.

---

## Generating Ed25519 Keys

Developers require an Ed25519 keypair to sign plugins.

### Using the CLI
```bash
biopro-sign init
```
This populates `~/.biopro/dev_keys/` with your credentials.

### Programmatic Generation (Python)
If integrating into automated systems, use the `cryptography` library:
```python
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

private_key = ed25519.Ed25519PrivateKey.generate()
public_key = private_key.public_key()
# ... handle serialization ...
```

---

## Author Profiles and RBAC

The `manifest.json` file dictates which authors are required to provide a valid signature.

### RBAC Constraints
* Authors listed with the `"sign_code"` permission **must** sign the plugin. A missing or invalid signature for these authors results in an immediate verification failure.
* Authors without the `"sign_code"` permission are not audited for signatures.

```json
{
  "manifest_version": 2,
  "id": "analysis_module",
  "authors": [
    {
      "name": "Primary Developer",
      "permissions": ["sign_code"]
    }
  ]
}
```

---

## CI/CD Pipeline Integration

To prevent manual errors, the signing process can be automated within Continuous Integration pipelines (e.g., GitHub Actions).

### Workflow Configuration
1. Store a dedicated CI/CD private key securely as a repository secret.
2. During the release build phase, execute the CLI utility to generate a secondary signature validating the build.

```yaml
      - name: Execute Project Signing
        env:
          BIOPRO_PRIVATE_KEY: ${{ secrets.BIOPRO_PRIVATE_KEY }}
        run: |
          for dir in plugins/*/; do
            if [ -d "$dir" ]; then
              biopro-sign project-sign "$dir"
            fi
          done
```
