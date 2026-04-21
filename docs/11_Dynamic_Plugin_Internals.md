# 🔌 architecture: Dynamic Plugin Internals

BioPro's extensibility comes from its ability to discover, verify, and "hot-reload" Python packages at runtime. The `ModuleManager` acts as the gatekeeper for all third-party code.

---

## 🏗 Plugin Discovery & Namespaces

BioPro looks for plugins in two distinct locations:
1.  **Internal Directory**: Modules bundled with the application (e.g., in `BioPro.app/Contents/Resources/biopro/plugins`).
2.  **User Directory**: Modules installed by the user (typically in `~/.biopro/plugins`).

### The Magic Namespace (`biopro.plugins`)
To make importing easy, BioPro dynamically merges these two folders into a single virtual Python namespace. This allows a plugin in your home folder to be imported as if it were part of the core package:

```python
# Both internal and user-installed plugins are found here:
import biopro.plugins.my_cool_module
```

---

## 🧪 The Loader Pipeline

When you click an Analysis Module in the Hub, BioPro triggers the **Loader Pipeline**:

1.  **Manifest Verification**: The `ModuleManager` reads the `manifest.json` and ensures it satisfies the core version requirements.
2.  **Security Handover**: The `TrustManager` verifies the plugin's signature and file integrity (see [Security & Trust](02_Security_and_Trust.md)).
3.  **Dynamic Import**: The `importlib` library loads the package into Python's memory.
4.  **Contract Enforcement**: BioPro checks if the module satisfies the **BioProPlugin Interface Contract** (i.e., it has `__version__`, `__plugin_id__`, and `get_panel_class()`).
5.  **UI Injection**: The main widget class is returned to the `WorkspaceWindow` and parented into the layout.

---

## 🔥 Hot-Reloading

Unlike many legacy tools, BioPro doesn't require a restart when you install or update a plugin.

When the **Nervous System** (Event Bus) emits a `PLUGIN_INSTALLED` event:
1.  `ModuleManager` clears its internal cache.
2.  It uses `importlib.reload` logic to purge the old code from Python's `sys.modules`.
3.  It rescans the disk for the new version.
4.  The UI is updated instantly to reflect the change.

---

## 🛠 Internal API Reference (`biopro.core.module_manager`)

### `ModuleManager(trust_manager)`
Initializes the discovery engine and sets up the user-plugins namespace.

- `get_available_modules()`: Returns a list of all verified plugin manifests.
- `load_module_ui(module_id)`: The "High-Risk" method. Performs security checks and imports the UI class into RAM.
- `reload_modules()`: Flushes the Python module cache and rescans the disk.
- `trust_module(module_id)`: Upgrades an "Untrusted" module to "Personally Trusted" by snapshotting its current file hashes.
