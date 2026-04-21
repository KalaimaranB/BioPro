# 📖 BioPro Wiki Manifest

This repository uses **Automated Documentation Sync**. All content in the [GitHub Wiki](https://github.com/KalaimaranB/BioPro/wiki) is mirrored from the `docs/` folder in the main repository.

## 🗂 Navigation Structure

The Wiki is organized into the following sections:

1.  **[Home](Home)**: The main introduction and landing page.
2.  **[Getting Started](01_Introduction)**: Installation guide for Windows and macOS.
3.  **[Security & Trust Model](02_Security_and_Trust)**: Deep dive into the cryptographic Trust Tree.
4.  **[Developer Handbook](03_Developer_Handbook)**: Setting up your dev environment and local building.
5.  **[Module Author Guide](04_Module_Author_Guide)**: Step-by-step instructions for building new analysis plugins.
6.  **[Plugin Development Reference](05_Plugin_Reference)**: API hooks and contract details.
7.  **[SDK Summary](06_SDK_Summary)**: Concise reference for the BioPro Plugin SDK.
8.  **[Architecture: Nervous System](07_Core_Nervous_System)**: The Event Bus and decoupled communication.
9.  **[Architecture: Project Management](08_LifeCycle_Project_Management)**: Persistence, asset tracking, and file locking.
10. **[Architecture: History Engine](09_The_Time_Machine_Engine)**: Undo/Redo logic and memory optimization.
11. **[Architecture: High-Performance Scaling](10_High_Performance_Scaling)**: Task scheduling and resource management.
12. **[Architecture: Plugin Internals](11_Dynamic_Plugin_Internals)**: Module discovery and the loader pipeline.

---

## ⚙️ How to Update

Do **not** edit the Wiki directly on GitHub. Instead:
1.  Edit the corresponding `.md` file in the `docs/` folder of this repo.
2.  Commit and push to `main`.
3.  The **Sync Wiki** GitHub Action will automatically update the public Wiki.
