# Tutorial: First Analysis

This tutorial walks through a simple BioPro analysis from selecting a module to reviewing results.

---

## Step 1: Open or Create a Project

Start from the Project Hub:

1. Open a recent project from the left panel, or click **📁 Open Project...**.
2. If you are new, click **✨ Create New Project** and choose a project folder.
3. Verify the project directory contains a `project.biopro` file before continuing.

---

## Step 2: Choose a Module

From the Home Screen, select an analysis module card.

* If the module is not installed yet, click **☁️ Marketplace** to install it.
* Installed modules appear in the Hub automatically.

> [!NOTE]
> If a module is blocked, untrusted, or outdated, BioPro will show a warning and guide you to the Plugin Store for resolution.

---

## Step 3: Use the Wizard Flow

Many modules use a guided wizard interface. The normal workflow is:

1. **Choose data** — select files, images, or other inputs required by the analysis.
2. **Configure parameters** — adjust sliders, thresholds, and settings.
3. **Run analysis** — execute the module and monitor progress.
4. **Review results** — inspect output plots, tables, or visual summaries.
5. **Export** — save your results as CSV, images, or other supported formats.

### Practical tips

* Use the built-in file picker to locate input files.
* If the module reports validation errors, correct the input data before continuing.
* The UI is designed to keep the main window responsive while the analysis runs.

---

## Step 4: Use the Workspace View

Some modules open in a workspace style rather than a linear wizard.

In workspace mode you will typically see:

* A top toolbar with project controls and navigation.
* Side panels for assets, workflow status, and properties.
* A central canvas for the main analysis or visualization.

Workspace modules are best for exploratory tasks and workflows that require multiple iterations.

---

## Step 5: Use Undo / Redo

BioPro preserves edit history for many modules.

* Use **Ctrl+Z** (Windows) or **Cmd+Z** (macOS) to undo.
* Use **Ctrl+Y** or **Shift+Ctrl+Z** to redo.
* The **Edit** menu includes **Undo** and **Redo** whenever a project is open.

> [!NOTE]
> The availability of undo/redo depends on the active module and the current workflow.

---

## Step 6: Close the Project Safely

When your work is complete:

* Choose **Close Project & Return to Hub** from the workspace toolbar.
* BioPro saves the project before returning to the Hub.

If the app closes unexpectedly, a stale `.biopro.lock` file may remain. Remove it only when you are sure no other instance of BioPro is using the project.

---

## Next Steps

* [Plugin Store & Security](07_Plugin_Store_and_Security.md) — Install modules and manage trust.
* [Project Management](04_Project_Management.md) — Learn how BioPro stores your data.
* [FAQ & Troubleshooting](05_FAQ_Troubleshooting.md) — Diagnose problems and view logs.
