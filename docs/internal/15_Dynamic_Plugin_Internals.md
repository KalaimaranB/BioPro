# Dynamic Plugin Internals

BioPro's extensibility relies on runtime discovery, verification, and dynamic loading of Python packages. The `ModuleManager` coordinates the loading of third-party code into the core application.

---

## Plugin Discovery and Namespaces

BioPro scans for plugins in two primary locations:
1.  **Internal Directory**: Bundled core modules (e.g., within the application package `biopro/plugins`).
2.  **User Directory**: Modules installed manually or via the store (typically `~/.biopro/plugins`).

### The Unified Namespace
BioPro dynamically configures Python's module resolution to merge these distinct directories into a unified `biopro.plugins` virtual namespace. This enables standard import syntax regardless of physical location:

```python
import biopro.plugins.custom_module
```

---

## The Loader Pipeline

When a user initiates an Analysis Module, the `ModuleManager` executes the following sequence:

1.  **Manifest Verification**: The module's `manifest.json` is parsed to validate API compatibility and version constraints.
2.  **Security Handover**: The `TrustManager` evaluates the plugin's cryptographic signature and validates file hashes against the manifest.
3.  **Dynamic Import**: The `importlib` library is utilized to dynamically import the verified package into the active Python interpreter.
4.  **Interface Validation**: BioPro verifies that the loaded module implements the required `BioProPlugin` interfaces (e.g., `get_panel_class()`).
5.  **UI Integration**: The plugin's main widget class is instantiated and integrated into the `WorkspaceWindow` layout.

---

## Hot-Reloading Support

BioPro supports dynamic module reloading without requiring a full application restart, facilitating rapid plugin development.

When the Event Bus broadcasts a `PLUGIN_INSTALLED` or `PLUGIN_UPDATED` event:
1.  The `ModuleManager` invalidates its internal cache for the target plugin.
2.  It utilizes `importlib.reload` semantics to purge the existing module references from `sys.modules`.
3.  The disk is rescanned, and the new module version is imported.
4.  The active UI components are refreshed to reflect the updated plugin state.

---

## API Reference (`biopro.core.module_manager`)

### `ModuleManager(trust_manager)`
Coordinates plugin discovery and manages the virtual namespace.

- `get_available_modules()`: Returns a parsed list of manifests for all discovered and structurally valid plugins.
- `load_module_ui(module_id)`: Orchestrates the security verification and dynamic import pipeline to return the plugin's UI class.
- `reload_modules()`: Invalidates the Python module cache and rescans the plugin directories.
- `trust_module(module_id)`: Instructs the `TrustManager` to establish a local override for an untrusted or modified plugin by recording its current file hashes.
