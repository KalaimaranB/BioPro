# 🔬 Tutorial: Navigating Your First Analysis

BioPro modules generally fall into two categories: **Wizard-style** (streamlined, step-by-step) and **Workspace-style** (free-form, multi-panel). This tutorial explains both so you can navigate any analysis tool with confidence.

---

## 🧙 The 4-Step Wizard (Standard Modules)
Many modules, such as **Western Blot Pro**, use a guided 4-step pipeline to ensure scientific reproducibility.

### Step 1: Input (Data Loading)
The first screen is where you provide your raw data.
1.  **Select Your Files**: Click the **Browse** button or drag-and-drop your images (TIFF, PNG) or data files into the drop zone.
2.  **Validation**: BioPro automatically scans the files for corruption or incompatible formats. 

### Step 2: Parameters (The "Scientific" Phase)
This is where you apply your domain knowledge.
1.  **Interactive Sliders**: Move sliders to adjust thresholds or filters. Results update in real-time.
2.  **Fine-Tuning**: Double-click any slider to type in a precise numerical value.

### Step 3: Analysis (Background Engine)
When you click **Run Analysis**, the heavy computation begins.
1.  **Non-Blocking**: Your UI remains responsive. You can open other tabs while the engine computes.
2.  **Progress**: A progress bar shows real-time status.

### Step 4: Results (Export & Save)
The final phase is where you review and export your findings.
1.  **Review**: Use interactive plots or tables to zoom in on specific data points.
2.  **Export**: Click **Export to CSV** or **Save Image** for publication.

---

## 🖥 The Professional Workspace (Advanced Modules)
Advanced modules like **Flow Cytometry** use a persistent "Workspace" layout instead of a step-by-step wizard. This is designed for complex, non-linear workflows.

- **Ribbon Toolbar**: Located at the top. Switches between different contexts (e.g., *Compensation*, *Gating*, *Reports*).
- **Sidebars**: Provide quick access to your **Sample List**, **Gate Hierarchy**, and **Properties**.
- **Central Canvas**: The main area where your data visualizations (plots, histograms) live.
- **Auto-Sync**: Unlike wizards, changes in a Workspace are often applied instantly to all open windows.

---

## 🕰 The "Time Machine" (Undo/Redo)
Regardless of the module style, BioPro's **History Engine** is always active.
- Use **Cmd+Z** (macOS) or **Ctrl+Z** (Windows) to undo any mistake.
- In Workspace modules, you can also use the **History Tab** to jump back to any specific point in your session.

---

## 🤝 Next Steps

Now that you've mastered the basic workflow, learn how BioPro keeps your data safe and portable:
- [**Project Management & Data Formats**](04_Project_Management.md)
- [**FAQ & Troubleshooting**](05_FAQ_Troubleshooting.md)
