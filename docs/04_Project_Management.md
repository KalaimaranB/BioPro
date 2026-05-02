# 📂 Guide: Project Management & Data Formats

BioPro organizes all scientific work into **Projects**. A project is more than just a folder; it is a versioned, cryptographically-consistent snapshot of your analysis history.

---

## 🏗 The Project Structure

When you create a project named `MyExperiment`, BioPro creates a `.biopro` directory with the following structure:

```text
MyExperiment/
├── project_manifest.json  # Core metadata and system state
├── analysis_results/      # Processed data, graphs, and csv exports
├── history_ledger.db      # The "Time Machine" database
└── .lock                  # Prevents data corruption from multiple apps
```

### 🔐 The Project Lock
BioPro uses OS-native file locking. If you try to open the same project in two different instances of BioPro, you will receive a security warning. This prevents two different "History Engines" from writing conflicting data to the same ledger.

---

## 📤 Sharing & Portability

BioPro projects are designed to be shared. To send your work to a colleague:
1.  **Zip the Project Folder**: Zip the entire `MyExperiment` directory.
2.  **Send**: Your colleague can "Open Project" in their BioPro Hub, and they will see your entire Analysis History, and results exactly as you left them.

> [!NOTE]
> **Plugin Compatibility**: If your colleague opens a project that uses a plugin they don't have installed, BioPro will offer to download it from the **Plugin Store** automatically.

---

## 📊 Supported Data Formats

BioPro is a modular system, but it has first-class support for:

| Format | Category | Common Use |
| :--- | :--- | :--- |
| `.fcs` | Flow Cytometry | Standard cell population data |
| `.tiff / .png` | Imaging | Western Blots, Microscopy |
| `.csv / .tsv` | Tabular | Raw threshold data |

---

## 🛡 Data Integrity
Every result saved in a BioPro project is hashed. If the raw data files are modified outside of BioPro, the app will flag the analysis step as **"Stale"** or **"Compromised"**, ensuring the scientific integrity of your final publication.

---

## 🏁 Final Step
You are now ready to perform your first analysis! If you have questions, visit the [**FAQ & Troubleshooting**](05_FAQ_Troubleshooting.md).
