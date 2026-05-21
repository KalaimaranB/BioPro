# Developer Onboarding and Contribution

This manual outlines the operational workflows for contributing to BioPro, detailing the cryptographic configuration required for developers and institutional authorities.

---

## Contribution Roles

BioPro delineates roles to enforce security policies and track contributions accurately.

1. **Contributor/Tester**: Individuals providing QA, testing, or documentation without committing executable code. They do not require cryptographic signing keys.
2. **Developer/Publisher**: Engineers authoring plugin code. They must sign their releases with an Ed25519 key.
3. **Institutional Authority**: Organizations that manage root-trusted keys to issue delegation certificates to internal developers.

---

## Tier 1: Contributor

Contributors who do not author executing code are credited in the plugin's `manifest.json`.

### Manifest Entry
Contributors are added to the `authors` array but omitted from the `"sign_code"` permission. This exempts them from signature validation during the plugin load sequence.

```json
{
  "authors": [
    {
      "name": "Jane Doe",
      "role": "QA Analyst",
      "permissions": ["run_tests"]
    }
  ]
}
```

---

## Tier 2: Developer

Developers must cryptographically sign their plugins to pass BioPro's integrity checks.

### 1. Initialize Cryptographic Keypair
Generate a personal Ed25519 key pair using the BioPro CLI:
```bash
biopro-sign init
```
This generates your private key (`private.key`) and public key (`public.pub`) in `~/.biopro/dev_keys/`.

### 2. Profile Registration
To be recognized globally, your public key must be registered with the central BioPro directory. Submit your generated public hex string to the repository administrators.

### 3. Plugin Signing
Before distributing a plugin, execute the signing process:
```bash
biopro-sign sign .
```
This routine validates your `manifest.json` and generates `security.json` (the file hashes) and `signature.bin` (your cryptographic signature).

---

## Tier 3: Institutional Authority

Institutions establish a root of trust, allowing them to issue "Delegated Trust Certificates" to affiliated developers.

### 1. Authority Registration
Generate an authority key pair and submit the public key to the BioPro core administrators to be added to the official `authorities.json` registry.

### 2. Issuing Delegation Certificates
Use the institutional private key to sign a developer's public key:
```bash
biopro-sign delegate <path_to_researcher_public.pub> "Researcher Name" --authority <path_to_your_authority_private.pem>
```
The resulting `delegation.json` must be included by the developer in their workspace. Plugins signed by that developer will subsequently validate against the Institutional Authority's root key.
