# Security and Trust Architecture

BioPro protects end users by verifying the origin and integrity of analysis plugins before they run.

---

## How BioPro Verifies Plugins

When BioPro loads a plugin, it checks:

* The plugin files match the signed manifest.
* The manifest signature is valid for the developer key.
* The developer key is trusted through a known authority or a local trust exception.

If any check fails, BioPro may block the plugin from running.

---

## Trust Sources

BioPro accepts trust from two sources:

* **Remote authorities** — signed registries and trusted developer lists synced from BioPro’s upstream registry services.
* **Local trust anchors** — developer keys that you explicitly approve and store in `~/.biopro/trusted_roots/`.

### Remote authorities

BioPro periodically synchronizes trusted developer keys and authority registries from the configured network services.

* Registry data is fetched from a remote `registry.json` service.
* Trusted developer keys are persisted as local `network_*.pub` files.
* Authorities are synced as `auth_*.pub` files after verifying a root signature.

### Local trust anchors

If a developer is not part of the remote trust chain, you can still approve them manually.

* The first time you try to use an untrusted developer’s plugin, BioPro may show a trust dialog.
* Choose **Trust this Developer** only if you know and trust the source.
* Approved keys are stored locally and enable those developer plugins to run in the future.

---

## Verification Outcomes

BioPro exposes several trust statuses:

* **Verified Secure** — The plugin is cryptographically verified and the developer identity is trusted.
* **Untrusted** — The plugin is intact, but the developer is not yet trusted by a known authority.
* **Outdated** — The plugin may still be valid, but it requires a newer version of BioPro or the plugin registry.

When a plugin is untrusted, BioPro may prevent it from loading until you resolve the trust state.

---

## Why this matters

Plugins can execute code on your computer. Verification ensures:

* The plugin has not been modified since it was signed.
* The declared developer identity matches the provided public key.
* The plugin is part of a trusted distribution path or approved locally.

This reduces the risk of running tampered or malicious analysis modules.

---

## When to use the Security and Signing Guide

If you are building or distributing your own plugin, refer to the Developer Security Guide:

* [Security and Signing Guide](../internal/20_Security_and_Signing.md)

For most end users, the key actions are:

* Install modules from the Plugin Store.
* Review trust badges before running new plugins.
* Approve a developer only when you trust the source.
