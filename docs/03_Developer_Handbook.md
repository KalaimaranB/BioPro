# 🧬 BioPro Developer Handbook

Welcome to the BioPro ecosystem! This guide is designed to take you from a raw idea to a **Verified Developer** with a signed, distributable analysis module.

---

## 🚀 Quick Start: The 5-Minute Plugin

BioPro plugins are standard Python packages that follow a simple structure.

### 1. File Structure
```text
my_plugin/
├── manifest.json         # Metadata (ID, Version, Hashes)
├── trust_chain.json      # Cryptographic proof (ID, Chain)
├── __init__.py           # Entry point
└── ui/
    └── main_panel.py     # Your UI code
```

### 2. The Manifest (`manifest.json`)
```json
{
    "id": "my_plugin",
    "name": "My Discovery Tool",
    "author": "Dr. Scientist",
    "version": "1.0.0",
    "min_core_version": "1.2.0",
    "icon": "🧪"
}
```

### 3. The Entry Point (`__init__.py`)
```python
__version__ = "1.0.0"
__plugin_id__ = "my_plugin"

def get_panel_class():
    from .ui.main_panel import MyAnalysisPanel
    return MyAnalysisPanel
```

---

## 🏗 SDK Components

BioPro provides a powerful SDK to handle the "heavy lifting" like state management, undo/redo, and theming.

### 1. State Management (`biopro.sdk.core.PluginState`)
Define your analysis parameters in a `@dataclass`. BioPro will automatically handle saving, loading, and undoing these values.

```python
from dataclasses import dataclass
from biopro.sdk.core import PluginState

@dataclass
class MyState(PluginState):
    threshold: float = 0.5
    filter_type: str = "Gaussian"
    results: list = None
```

### 2. Analysis Logic (`biopro.sdk.core.AnalysisBase`)
Keep your math separate from your UI. Inherit from `AnalysisBase` to run logic in the background.

```python
from biopro.sdk.core import AnalysisBase

class MyAnalyzer(AnalysisBase):
    def run(self, state: MyState) -> dict:
        # Long running math here...
        return {"results": [1, 2, 3]}
```

### 3. User Interface (`biopro.sdk.ui`)
Use BioPro's semantic components to ensure your plugin matches the application's look and feel automatically.

```python
from biopro.sdk.ui import PrimaryButton, WizardPanel, HeaderLabel

# Inside your main panel:
self.btn = PrimaryButton("Run My Analysis")
self.lbl = HeaderLabel("Results Checklist")
```

---

## 🔒 Security & Trust (Hierarchical Trust)

BioPro uses a **Hierarchical Trust Tree** model (Root -> Authority -> Lab -> Developer). All plugins must be cryptographically signed.

### The Developer Utility (`biopro-sign`)
The standalone `biopro-sign` tool handles your identity and security chains.

1.  **Initialize Identity** (Run once):
    ```bash
    biopro-sign init
    ```
    *This creates your private/public key pair in `~/.biopro/dev_keys/`. Keep this secret!*

2.  **Obtain Trust (Delegation)**:
    Authorities (Labs/Universities) grant you institutional trust via a delegation file:
    ```bash
    # Authority runs (on their machine):
    biopro-sign delegate <your_pub_hex> "Your Name"
    ```
    Place the returned `delegation.json` in your `~/.biopro/dev_keys/` folder.

3.  **Sign Your Plugin**:
    ```bash
    biopro-sign sign path/to/plugin
    ```
    *Validates integrity and bundles the full `trust_chain.json`.*

---

## 🌍 Distribution: Becoming a "Verified Developer"

BioPro allows you to share your plugins with others through a central registry.

### 1. Export Your Public Key
To let others trust your plugins without manual confirmation, run:
```bash
python3 -m biopro.core.sign_plugin registry
```
### 2. Update the Central Registry
Copy the JSON output and submit it to the `registry.json` on the BioPro GitHub repository.

### 3. Silent Verification
Once your ID is in the registry:
- Users will see a **🛡 Verified Developer** badge on your plugin.
- Your plugin will load instantly without "Untrusted State" warnings.
- All file integrity checks happen silently in the background.

---

## 💡 Best Practices

1.  **Never block the UI thread**: Use `AnalysisWorker` or the `TaskScheduler` for any task taking longer than 100ms.
2.  **Use `push_state()`**: Call this whenever the user makes a significant change to enable the "Time Machine" (Undo/Redo) feature.
3.  **Respect the Theme**: Avoid hardcoding colors like `white` or `black`. Use the `Colors` class from `biopro.ui.theme`.

---

> [!TIP]
> Need help? Check the [MODULE_AUTHOR_GUIDE.md](MODULE_AUTHOR_GUIDE.md) for deep-dive technical API references.
