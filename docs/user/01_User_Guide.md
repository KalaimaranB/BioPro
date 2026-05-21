# BioPro User Guide

Welcome to the **BioPro User Guide**. This document provides operational instructions for biological researchers and lab technicians using BioPro to analyze their data.

---

## Guide Index

BioPro is organized into a modular workflow. Depending on your current task, select the relevant documentation below:

### Initial Setup
If you are running BioPro for the first time, refer to the installation and initialization instructions.
- [Getting Started](02_Getting_Started.md)

### Running Analysis
Learn the standard workflows in BioPro. Depending on the loaded module, you will encounter either a step-by-step wizard or a multi-panel workspace.
- [Tutorial: Navigating Your First Analysis](03_Tutorial_First_Analysis.md)

### Project Data and Sharing
Understand how BioPro stores your experimental data in projects and the supported data formats for exporting and sharing.
- [Project Management](04_Project_Management.md)

### Troubleshooting
Review solutions to common operational issues.
- [FAQ & Troubleshooting](05_FAQ_Troubleshooting.md)

### AI Assistance
BioPro includes an integrated AI Assistant that can help explain functionalities and navigate workflows based on the loaded context.
- [AI Assistant Overview](../internal/17_AI_Assistant.md)

---

## Core Operational Features

### Plugin Signature Verification
BioPro utilizes cryptographic signature checks to verify that installed analysis plugins have not been tampered with.
- [Security and Trust Overview](10_Security_and_Trust.md)

### State Management
BioPro records state changes during analysis. You can undo or redo actions securely, ensuring your data manipulation steps are tracked.

### Extensible Modules
BioPro acts as a host application. Specialized analysis tools are installed as plugins via the Plugin Store.

---

> [!NOTE]
> **Developer Documentation:** If you want to build your own analysis modules using the SDK, refer to the [Developer Onboarding Guide](../internal/19_Developer_Onboarding.md).
