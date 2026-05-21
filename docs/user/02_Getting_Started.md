# Getting Started

**BioPro** is a cross-platform desktop application designed for biological data analysis. It uses a plugin architecture to provide various analysis modules within a unified environment.

---

## Core Workflow

### 1. Project Initialization
When you launch BioPro, the application opens the **Project Hub**. BioPro organizes work by experiment; you must create a new project or open an existing one before running any analysis.

### 2. Loading Analysis Modules
BioPro's functionality is provided by plugins. These modules typically follow one of two interaction models:
1.  **Standard Wizards**: A sequential, step-by-step interface for routine tasks.
2.  **Professional Workspaces**: Multi-panel layouts for exploratory data analysis.

### 3. Plugin Verification
When a plugin is loaded, BioPro's TrustManager verifies the module's cryptographic signature against your configured trust settings to ensure the plugin has not been modified. You can manage developer keys in the Security Center.

---

## Next Steps
*   [Tutorial: Navigating Your First Analysis](03_Tutorial_First_Analysis.md) — Learn how to interact with plugins.
*   [Project Management](04_Project_Management.md) — Understand BioPro's data storage format.
*   [Developer Onboarding Guide](../internal/19_Developer_Onboarding.md) — Instructions for building custom plugins with the BioPro SDK.
