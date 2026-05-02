# 📖 BioPro Wiki Manifest

This repository uses **Automated Documentation Sync**. All content in the [GitHub Wiki](https://github.com/KalaimaranB/BioPro/wiki) is mirrored from the `docs/` folder in the main repository.

## 🗂 Navigation Structure

The Wiki is organized into the following logical sections:

### 🔬 User Guides (Researchers)
1.  **[User Guide Hub](01_User_Guide)**: The central entry point for all users.
2.  **[Getting Started](02_Getting_Started)**: Installation guide and first launch.
3.  **[Tutorial: Your First Analysis](03_Tutorial_First_Analysis)**: Step-by-step walkthrough of the Wizard workflow.
4.  **[Project Management](04_Project_Management)**: Experiments, portability, and data formats.
5.  **[AI Assistant: Grogu](17_AI_Assistant_Grogu)**: Using the integrated research assistant.
6.  **[FAQ & Troubleshooting](05_FAQ_Troubleshooting)**: Common issues and answers.

### 🛠 Developer Guides (Authors)
7.  **[Developer Handbook](06_Developer_Handbook)**: Setting up your environment.
8.  **[Module Author Guide](07_Module_Author_Guide)**: Building your first analysis plugin.
9.  **[Plugin Development Reference](08_Plugin_Reference)**: UI components and API hooks.
10. **[SDK Summary](09_SDK_Summary)**: Concise reference for the BioPro SDK.
11. **[API Reference](16_API_Reference)**: Formal function specifications (inputs/outputs).

### 🏛 Architecture Deep Dives (Core)
12. **[Security & Trust Model](10_Security_and_Trust)**: The cryptographic Hierarchical Trust Tree.
13. **[Architecture: Nervous System](11_Core_Nervous_System)**: The Event Bus and communication.
14. **[Architecture: Project Management](12_LifeCycle_Project_Management)**: Persistence and asset tracking.
15. **[Architecture: History Engine](13_The_Time_Machine_Engine)**: Undo/Redo and memory optimization.
16. **[Architecture: High-Performance Scaling](14_High_Performance_Scaling)**: Task scheduling and resources.
17. **[Architecture: Plugin Internals](15_Dynamic_Plugin_Internals)**: Discovery and loader pipeline.

---

## ⚙️ How to Update

Do **not** edit the Wiki directly on GitHub. Instead:
1.  Edit the corresponding `.md` file in the `docs/` folder of this repo.
2.  Commit and push to `main`.
3.  The **Sync Wiki** GitHub Action will automatically update the public Wiki.
