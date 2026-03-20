# 🔬 BioPro: The Modular Lab Analysis Hub

**BioPro** is a cross-platform desktop suite designed to bridge the gap between "messy" raw lab data and publication-ready results. Built on a dynamic plugin architecture, BioPro provides a unified, mathematically rigorous environment for biological image analysis without the steep learning curve of traditional tools.

---

## 🌟 Key Features
* **Dynamic Plugin Store:** Install only the modules you need (Western Blot, Flow Cytometry, etc.) directly from the cloud registry.
* **The "Time Machine" Engine:** Full undo/redo support for every single adjustment, from crops to band deletions.
* **Automated Reproducibility:** Every analysis step is tracked and saved, ensuring that your $n=3$ is analyzed identically every time.
* **Cross-Platform Performance:** Native support for **Windows** and **macOS** with high-fidelity Matplotlib rendering.

## 🚀 Getting Started
1.  **Download:** Grab the latest release for your OS from the [Releases](https://github.com/KalaimaranB/BioPro/releases) tab.
2.  **Initialize:** Open the app and head to the **Plugin Store**.
3.  **Install:** Download the **Western Blot Pro** module to begin your first analysis.
4.  **Analyze:** Return to the Home Screen and click the module to launch the Wizard.

## 🛠 For Developers
BioPro is designed to be extensible. You can build your own analysis modules using our `ModuleManager` API. Simply create a Python package with a `manifest.json` and drop it into the `plugins/` directory.

---

> **Note:** BioPro is currently in active development. Please report any bugs or feature requests via GitHub Issues.