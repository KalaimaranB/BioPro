# 🔬 BioPro: The Modular Lab Analysis Hub

**BioPro** is a cross-platform desktop suite designed to bridge the gap between "messy" raw lab data and publication-ready results. Built on a dynamic plugin architecture, BioPro provides a unified, mathematically rigorous environment for biological image analysis without the steep learning curve of traditional tools.

---

### 📖 Documentation
- [**User Guide**](docs/01_User_Guide.md) - For researchers and lab technicians.
- [**Developer Handbook**](docs/06_Developer_Handbook.md) - For building your own analysis modules.


---

## 🌟 Key Features

---

## 🚀 Installation Guide (Core App)

### Windows
1. Navigate to the [Releases](https://github.com/KalaimaranB/BioPro/releases) page.
2. Download the latest `BioPro-Windows.zip` asset.
3. Extract the `.zip` folder to your preferred location on your PC.
4. Open the extracted folder and double-click `BioPro.exe` to launch the application.

### macOS
1. Navigate to the [Releases](https://github.com/KalaimaranB/BioPro/releases) page.
2. Download the latest `BioPro-macOS.tar.gz` asset.
3. Double-click the downloaded file to extract the `BioPro.app` bundle.
4. Drag `BioPro.app` into your **Applications** folder.

**⚠️ macOS Security Notice (Gatekeeper):**
Because BioPro is an open-source application, macOS may initially block it from opening, displaying a warning that the developer cannot be verified. To safely bypass this:
* **Method 1:** Right-click (or Control-click) `BioPro.app` and select **Open**. Click **Open** again on the pop-up warning.
* **Method 2:** Try opening the app normally. When it fails, open your Mac's **System Settings** > **Privacy & Security**, scroll down to the Security section, and click **Open Anyway** next to the BioPro notification.

---

## 🧩 Installing Analysis Modules

BioPro's core application is a lightweight hub. To actually analyze data, you need to download modules (like the Western Blot analyzer) directly within the app.

1. Launch the **BioPro** core application.
2. From the Home Screen, navigate to the **Plugin Store**.
3. Browse the available modules (e.g., **Western Blot Pro**).
4. Click **Install**. BioPro will automatically fetch the module from the cloud registry and configure it.
5. Return to the Home Screen and click the newly installed module to launch your analysis workspace.

---

## 🔄 How Updates Work

BioPro uses a split-update architecture to ensure your tools are always cutting-edge without forcing you to constantly reinstall the main application.

* **Module Updates (Automated):** Our plugins are hosted on an independent cloud registry. Whenever a new feature or bug fix is pushed for a specific module (like CytoMetrics or Flow Cytometry), BioPro's `NetworkUpdater` will detect it. You can update individual modules with a single click directly from the in-app **Plugin Store**.
* **Core App Updates (Manual):** Updates to the BioPro Core (which handle the UI engine, theming, and workspace management) are less frequent. When a new core version is released, you will need to download the latest `.zip` or `.tar.gz` from the GitHub Releases page and replace your old application file. *Note: Updating the core application will not delete your installed plugins or project files.*

---

## 🛠 For Developers
BioPro is designed to be extensible. You can build your own analysis modules using our `ModuleManager` API. Simply create a Python package with a `manifest.json` and drop it into the `plugins/` directory. For a highly detailed walkthrough of the module creation process, see [**Module Author Guide**](docs/07_Module_Author_Guide.md).

### Repository Architecture

If you are contributing to the core application itself, familiarizing yourself with the file hierarchy will help:

- **`biopro/core/`**: The brains of the application. Handles non-UI logic like the `HistoryManager` (Tracks user edits for global Undo/Redo operations), `ProjectManager` (Handles `.biopro` file structures and asserts lockfiles), and `ModuleManager` (Dynamically discovering, loading, and binding new analysis plugins).
- **`biopro/ui/`**: The visual layer, strictly adhering to SOLID principles.
  - `windows/`: Top-level native OS windows (`ProjectLauncherWindow` and `WorkspaceWindow`).
  - `dashboards/`: Full screen panels living inside windows (e.g., the `WorkspaceDashboard`).
  - `components/`: Granular, reusable, mathematically distinct QWidgets (`Cards`, `Toolbars`, `Overlays`) isolated to prevent God classes.
  - `dialogs/` & `tabs/`: Specialized modal windows like the Plugin Store and contextual workflows.
- **`tests/`**: Contains all unit and integration coverage for the application logic. 
- **`biopro/themes/`**: JSON payloads mapped to the `theme.py` engine defining global application colors (e.g. `default.json`, `star_wars.json`).

---

> **Note:** BioPro is currently in active development. Please report any bugs or feature requests via GitHub Issues.
