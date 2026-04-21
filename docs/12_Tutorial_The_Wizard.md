# 🧙 Tutorial: The Wizard Workflow

Every analysis module in BioPro is built on a standard **4-Step Wizard**. This ensures that whether you are performing a Western Blot analysis or complex Cytometry, the "muscle memory" remains the same.

---

## 🏗 The 4-Step Pipeline

### Step 1: Input (Data Loading)
The first screen is always about your raw data. 
- **Actions**: Click "Browse" or drag-and-drop your images/FCS files.
- **Tip**: BioPro validates your data as you load it. If a file is corrupted, the "Next" button will remain disabled to prevent errors later.

### Step 2: Parameters (The "Scientific" Phase)
This is where you apply your domain knowledge.
- **Interactive Sliders**: Adjust thresholds, filters, or gating parameters.
- **Live Preview**: Most modules provide a low-resolution live preview of how your parameters affect the output.
- **Persistence**: BioPro automatically remembers your last-used parameters.

### Step 3: Analysis (Background Engine)
When you click "Run Analysis," BioPro moves the heavy lifting to a background thread.
- **Multi-threading**: Your UI will never freeze. You can continue browsing other projects while the engine computes.
- **Progress Tracking**: A real-time progress bar shows the percentage completion of each sub-task.

### Step 4: Results (Export & Save)
The final phase is where you review your findings.
- **Visualizations**: View publication-ready graphs or heatmaps.
- **Exporting**: Save data as `.csv`, `.tsv`, or high-resolution images.
- **Project Save**: Ensure you click "Finish" to permanently commit these results to your BioPro project file.

---

## 🕰 The Time Machine Integration
Every step of the Wizard is tracked by the **History Engine**. 
- If you realize you made a mistake in Step 2, you don't need to restart. Close the wizard, use **Cmd+Z / Ctrl+Z**, or use the History tab in the Workspace to jump back to a previous state.

---

## 🤝 Next Steps
Now that you understand the workflow, learn how BioPro organizes this data in [**Project Management & Data Formats**](13_Project_Management.md).
