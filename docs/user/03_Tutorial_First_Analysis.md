# Tutorial: Navigating Your First Analysis

BioPro plugins utilize two primary interface paradigms: **Wizard-style** (sequential steps) and **Workspace-style** (multi-panel interfaces). This tutorial outlines how to operate both.

---

## The Standard Wizard Pipeline
Many routine analysis modules use a guided multi-step pipeline.

### Step 1: Data Input
Provide your raw experimental data to the module.
1.  **Select Files**: Click the **Browse** button or drag-and-drop supported files into the application window.
2.  **Validation**: The module will parse the input and alert you if the file format is unsupported or corrupted.

### Step 2: Parameter Configuration
Adjust the mathematical parameters for the analysis.
1.  **Interactive Controls**: Use sliders or input fields to modify thresholds.
2.  **Real-Time Preview**: If supported by the plugin, the UI will reflect parameter changes on a sample of the data.

### Step 3: Analysis Execution
Execute the core computational workload.
1.  **Asynchronous Execution**: BioPro runs heavy computations in background threads, keeping the UI responsive.
2.  **Progress Tracking**: A progress indicator will display the current status of the analysis.

### Step 4: Results and Export
Review the output of the analysis.
1.  **Data Review**: Inspect the generated plots, tables, or images.
2.  **Export**: Use the provided export buttons (e.g., CSV, PNG) to save the results to your local filesystem.

---

## The Professional Workspace
Advanced exploratory modules use a persistent workspace layout, designed for non-linear workflows.

- **Ribbon Toolbar**: Located at the top of the interface, providing access to major functional contexts (e.g., File, View, Tools).
- **Sidebars**: Provide quick access to hierarchical data representations, such as sample lists or property inspectors.
- **Central Canvas**: The primary area for data visualization.
- **State Synchronization**: Changes made in one panel are immediately reflected across all related views in the workspace.

---

## State Management (Undo/Redo)
BioPro tracks state changes to allow for error recovery during analysis.
- Use **Cmd+Z** (macOS) or **Ctrl+Z** (Windows) to undo the last action.
- Depending on the module, you may also have access to a history panel to revert to specific previous states.

---

## Next Steps
- [Project Management & Data Formats](04_Project_Management.md)
- [FAQ & Troubleshooting](05_FAQ_Troubleshooting.md)
