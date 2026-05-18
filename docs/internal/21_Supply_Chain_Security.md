# 📐 BioPro Architectural Cryptographic Specification

This document details the mathematical rules, deterministic serialization constraints, and directory-traversal isolation bounds of the BioPro Security and Trust subsystem.

---

## 🏛️ 1. Hashing & Verification Math Specs

BioPro utilizes asymmetric cryptography (Ed25519) combined with deterministic hashing to guarantee code integrity and verifiable consensus.

### Signature Validation Formula:
Let:
* $M_{raw}$ be the raw bytes of `manifest.json`.
* $H_{manifest} = \text{SHA-256}(M_{raw})$ be the 32-byte hexadecimal manifest binding hash.
* $S_{ledger}$ be the dictionary representing `security.json`, parsed and sorted.
* $C_{bytes} = \text{SerializeCanonical}(S_{ledger})$ be the deterministic canonicalized byte string of the ledger.
* $K_{dev\_pub}$ be the developer's 32-byte Ed25519 public key.
* $\sigma_{dev}$ be the 64-byte developer leaf signature (`signature.bin`).

The host verifier performs the following validation steps:
1. **Check Manifest Hash Bind**:
   $$\text{Extract}(S_{ledger}, \text{"manifest\_hash"}) \equiv H_{manifest}$$
   If they mismatch, a `ManifestHashMismatch` error is raised.
2. **Verify Leaf Signature**:
   $$\text{VerifyEd25519}(K_{dev\_pub}, C_{bytes}, \sigma_{dev}) \equiv \text{True}$$
3. **Verify Project Co-Signature**:
   Given project public key $K_{proj\_pub}$ and project signature $\sigma_{proj}$ (`project_signature.bin`):
   $$\text{VerifyEd25519}(K_{proj\_pub}, C_{bytes}, \sigma_{proj}) \equiv \text{True}$$

```
   +-----------------------+
   |     manifest.json     |
   +-----------+-----------+
               |
           SHA-256
               v
     [ manifest_hash ]
               |
               | (Cryptographic Bind)
               v
   +-----------------------+
   |     security.json     |
   +-----------+-----------+
               |
         Canonicalize
               v
      [ Sorted Bytes ]  ---(Ed25519 Sign)--->  signature.bin & project_signature.bin
```

---

## ⚙️ 2. Split-Manifest Serialization Rules

Because signature verification is highly sensitive to string representation, BioPro enforces strict **Deterministic Canonical JSON Serialization**. The signature is verified against sorted, whitespace-collapsed, UTF-8 encoded bytes.

### Python Canonicalization Rules:
```python
import json

def get_canonical_bytes(data: dict) -> bytes:
    """Produces sorted, compact, deterministic JSON bytes for signing/verification."""
    return json.dumps(
        data,
        sort_keys=True,
        separators=(',', ':')
    ).encode('utf-8')
```
* **Key Sorting (`sort_keys=True`)**: Keys at all nesting levels must be sorted alphabetically (e.g. `{"a": 1, "b": 2}`).
* **Compact Separators (`separators=(',', ':')`)**: Removes all optional whitespaces around object key-value separators and array delimiters.
* **Encoding**: UTF-8 encoded bytes.

Any variation in spacing, sorting, or formatting (such as adding spaces or tabs to the ledger) will result in verification failure.

---

## 📦 3. Cache Directory Sandbox Boundaries

To prevent malicious plugins from hijacking the local filesystem via remote asset injection, downloaded developer screenshots and author portraits are quarantined within a sandboxed caching layout.

### Directory Path Traversal Prevention:
Let $D_{cache}$ be the resolved absolute path of the sandbox root directory (`~/.biopro/cache/marketplace/`).
For any target asset request containing parameters:
* $P_{id}$: Plugin ID
* $A_{type}$: Asset Type (e.g. `avatars` or `screenshots`)
* $F_{name}$: Remote Filename (e.g. `alice.png`)

The Sandbox Cache service calculates the path:
$$T_{path} = \text{Resolve}(\text{Path}(D_{cache}) \mathbin{/} \text{Name}(P_{id}) \mathbin{/} \text{Name}(A_{type}) \mathbin{/} \text{Name}(F_{name}))$$

The verifier enforces the **Descendant Boundary Constraint**:
$$\text{StartsWith}(T_{path}, D_{cache}) \equiv \text{True}$$

If an attacker injects traversal tokens (e.g., $F_{name} = \text{"../../etc/passwd"}$), the path calculations:
1. Reject the input if relative traversal characters `..` are present.
2. Filter individual components using `.name` stripping.
3. Throw an immediate `ValueError` if the resolved path exits the boundary of $D_{cache}$.

---

## 🔒 4. Covert Backdoor Ignored-Zone Auditing

To block adversaries from hiding malicious scripts inside ignored or non-scanned directories (e.g. `results/`, `logs/`, `cache/`, `output/`), the `TrustManager` integrity engine performs a recursive directory scan:

```python
import os

BLACKLISTED_EXTENSIONS = {".py", ".pyw", ".sh", ".exe", ".bat", ".cmd", ".msi", ".dll", ".so", ".dylib"}

def scan_ignored_backdoors(ignored_dir: Path) -> None:
    """Recursively checks that no blacklisted executable files exist in ignored zones."""
    for root, _, files in os.walk(ignored_dir):
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix.lower() in BLACKLISTED_EXTENSIONS:
                raise ValueError(
                    f"Unauthorized Executable in Excluded Directory: "
                    f"Detected malicious file '{file_path}' inside ignored zone."
                )
```
This recursive scanner prevents attackers from committing pristine manifest files and hiding secondary malicious python/shell backdoors in untracked folders.
