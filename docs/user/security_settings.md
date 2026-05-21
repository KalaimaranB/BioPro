# Security Settings and Trust Directory

This document details how BioPro displays security statuses in the user interface and how to manage cryptographic keys within your local environment.

---

## 1. Plugin Security Statuses

BioPro evaluates plugins upon startup and assigns a status based on cryptographic verification.

| Status | Description | Cryptographic Result |
| :--- | :--- | :--- |
| **Verified Secure** | The plugin is verified. | The manifest and file hashes match, and the developer's key traces to a trusted root anchor. |
| **Untrusted** | The plugin integrity is intact, but the key is unknown. | The code has not been modified, but the developer's key is not in your Trust Directory. Execution may require a manual override. |
| **Security Critical** | Execution is blocked. | An unauthorized or modified file was found within the plugin directory. The hashes do not match the manifest. |

---

## 2. Managing the Local Trust Directory

If you utilize plugins from independent developers not signed by a central authority, you must manually add their public key to your local Trust Directory (`~/.biopro/trusted_roots/`).

### Adding a Trusted Key
1. Obtain the developer's public key (a hex string).
2. Open the **Security Center** or **Personal Trust Directory** in the BioPro sidebar.
3. Enter the developer's name and paste the public key.
4. Click **Add Anchor Key**. Plugins signed by this key will now be verified.

### Revoking a Key
1. Locate the developer in the Trust Directory list.
2. Click **Revoke**.
3. The public key is removed from your local system. Any plugins relying on this key will immediately be downgraded to an untrusted status.

---

## 3. Local Trust Overrides

During active development or debugging, you may need to modify plugin files locally. Doing so breaks the cryptographic signature and causes the integrity check to fail. BioPro allows you to establish a secure local override for these situations.

### Establishing an Override:
1. When BioPro detects a modified plugin, it presents a **Trust Dialog**.
2. If the modifications are intentional, select **Trust and Lock Current State**.
3. BioPro calculates new hashes for the modified files and stores them in `~/.biopro/trust_overrides.json`.
4. This override file is signed locally using a machine-specific key (`~/.biopro/machine_private.pem`) generated during the application's initial setup.
5. On subsequent loads, if the plugin files match the local override snapshot, the plugin is loaded under a **Verified Local Override** status.
6. Further modifications to the plugin will invalidate the override, requiring a new review and lock process.
