# 📂 User Trust Directory & Visual Safety Manual

This manual explains how BioPro visually guides you through cryptographic security events, how to manage manual keys in your **Personal Trust Directory**, and how to safely navigate local security overrides.

---

## 🎨 1. Deciphering Visual Safety Badges

BioPro evaluates plugins at startup and renders real-time visual statuses in the UI. Understanding these badges helps you guarantee the integrity of your computational research pipelines.

| Visual Badge | Visual Description | Cryptographic Meaning & Action |
| :--- | :--- | :--- |
| **🛡️ VERIFIED SECURE** | Green gradient glowing header | The plugin is fully double-signed! Its manifest and file hashes match, and it traces back to a trusted root anchor key. |
| **⚠️ UNTRUSTED / PENDING KEY** | Orange border & warning tree | The plugin's code integrity is verified, but its developer's key is unrecognized. Add them to your Trust Directory if you trust them. |
| **🚨 SECURITY CRITICAL** | Solid Red card with alerts | **EXCLUDED payload execution blocked!** An unauthorized executable file (e.g. `.py` or `.exe`) was found inside an ignored folder. Run is locked. |
| **❌ SPOOFED IMAGE BLOCKED** | Red dashed preview card | A remote screenshot or author portrait failed SHA-256 validation. Display was suppressed to prevent spoofing or buffer-overflow attacks. |

---

## 📂 2. Managing Your Personal Trust Directory

If you are working with an independent researcher or downloading an academic plugin that isn't signed by a central institutional authority, you can manually trust their key. This registers them locally as a trusted anchor on your computer.

### Listing & Searching Anchors
1. Open the **Personal Trust Directory** tab in the sidebar.
2. The panel lists all manually trusted anchors currently recognized in `~/.biopro/trusted_roots/`.
3. Use the search input `🔍 Filter trusted developers...` at the top to filter names instantly.

### Adding a Trusted Developer Key
To register a new independent developer key:
1. Obtain the developer's public key (a 32-byte hex string, e.g. `2f81f7...`).
2. Navigate to the **Add Trusted Developer Anchor** form in the sidebar.
3. Enter their full name and paste the public key hex.
4. Click **Add Anchor Key**. They are instantly added to your trusted keys, and any plugin signed by them will now display as **Verified Secure**!

### Revoking Developer Keys
If a key is compromised, or you no longer trust a developer:
1. Locate the developer in your **Personal Trust Directory** list.
2. Click the red **Revoke** button next to their name.
3. BioPro instantly deletes their key anchor (`.pub`) file and refreshes the trust evaluation tree. Any plugins using their signature are immediately demoted back to untrusted status.

---

## 🔒 3. Resolving Safety Locks & Manual Overrides

For advanced research workflows, you might need to make local, temporary modifications to an existing plugin. Since modifying any file breaks the cryptographic signature, BioPro will display an **Integrity Check Failed** warning.

BioPro provides a secure, background **Local Trust Overrides** registry to authorize safe local changes.

### Local Machine Overrides Flow:
1. When a plugin integrity check fails, BioPro presents a **Manual Trust Acceptance Dialog**.
2. If you are confident the changes are safe, click **"Trust and Lock Current State"**.
3. BioPro records the current hashes of all files in the plugin and saves them in `~/.biopro/trust_overrides.json`.
4. To prevent offline tampering with your overrides, BioPro cryptographically signs the overrides ledger using a **background Machine Key** (`~/.biopro/machine_private.pem`) generated on first boot.
5. On subsequent startups, if your local modifications match your signed override snapshot, the plugin is loaded securely under a **"Verified Local Override (🔒 Manual Lock)"** status.
6. If any files are modified *again*, the override is broken, and you must review the changes before re-signing.
