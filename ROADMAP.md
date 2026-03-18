# BioPro: Production Architecture & Scaling Roadmap

This document outlines the multi-phase engineering plan to transition BioPro from a Minimum Viable Product (MVP) into a production-grade, extensible bio-image analysis ecosystem.

## Phase 1: Foundation & Version Control
Before we automate the build, we must protect the codebase. We are moving away from committing directly to the production branch and establishing baseline stability.

### 1. Git Branching Strategy (Dev vs. Main)
* **`main` branch:** The sacred, production-ready code. This branch must *always* be in a deployable state. No direct commits are allowed here.
* **`develop` branch:** The active integration branch. All new features and refactors are merged here first.
* **Feature Branches:** For every new task (e.g., `feature/auto-updater`, `fix/ui-colors`), we branch off `develop`, do the work, and submit a Pull Request (PR) back to `develop`.
* **The Flow:** Once `develop` is stable and tested, we merge it into `main` and tag a release (e.g., `v1.1.0`).

### 2. Automated Testing (The Safety Net)
BioPro currently lacks a test suite. We will implement `pytest` to ensure core functionality never silently breaks.
* **Unit Tests:** Test individual utility functions (e.g., ensuring `image_utils.crop` returns the exact correct matrix dimensions).
* **Integration Tests:** Ensure the `ProjectManager` correctly writes and hashes files, and the `ModuleManager` successfully parses valid JSON manifests.
* **Pre-commit Hooks:** Code cannot be pushed if it fails the local test suite.

## Phase 2: The Plugin Ecosystem Standardization
To prevent malicious or poorly written plugins from crashing the Core app, we must enforce strict architectural contracts for all downloaded modules.

### 1. The Strict Plugin Standard
Every module submitted to the BioPro ecosystem MUST contain:
* **`manifest.json`:** Must include `id`, `name`, `version`, `author`, `description`, and a strict `dependencies` list. The app will reject plugins missing this.
* **`README.md` / Help UI:** Every plugin must provide documentation or a localized Help button within its UI panel explaining the biological workflow.
* **Namespace Isolation:** Plugins must strictly use relative imports or their designated `biopro.plugins.plugin_name` namespace to prevent cross-contamination.

### 2. The Dedicated Plugin Registry
* Decouple plugin `.zip` files from the main BioPro application releases.
* Create a lightweight GitHub repository (`BioPro-Plugins`) to host a centralized `registry.json`.
* The `NetworkUpdater` will query this static GitHub Pages API to populate the in-app Store.

## Phase 3: CI/CD Pipeline & Build Optimization
Automating the deployment pipeline so BioPro compiles natively for all users.

### 1. GitHub Actions (Multi-OS Matrix)
* Write a `.github/workflows/build.yml` pipeline.
* On every push to `main`, GitHub servers will spin up macOS, Windows, and Ubuntu virtual machines.
* The pipeline will automatically run the `pytest` suite. If tests pass, it will execute PyInstaller and publish a `.dmg`, `.exe`, and `.AppImage` to the Release page.

### 2. Trimming the Fat (Build Optimization)
* Refine the PyInstaller `.spec` file to aggressively exclude unused libraries (e.g., `QtWebEngine`, `QtQml`, massive unused `scipy` submodules).
* Goal: Reduce the Core binary size by 20-30% while retaining the "Fat Core" standard data science libraries.

## Phase 4: True Production Features
The final layer of polish to match commercial software standards.

### 1. Core Application Auto-Updates
* Upgrade the `NetworkUpdater` to handle Core app patches, not just plugins. 
* Implement a bootstrapper or leverage existing frameworks (like Sparkle/Squirrel) to pull down binary diffs and update the host `.app` or `.exe` over the air.

### 2. Telemetry & Crash Reporting (Optional but Recommended)
* Integrate a silent crash reporter (e.g., Sentry).
* When a user encounters a fatal unhandled exception, the app safely captures the stack trace and OS environment and logs it to a developer dashboard for rapid patching.