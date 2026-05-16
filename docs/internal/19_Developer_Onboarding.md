# 🚀 BioPro Developer Onboarding Guide

Welcome to the BioPro team! We are building a professional platform for scientific workflows. As we are currently in Beta, we use a modern, fast, and test-driven stack.

This guide will get you from zero to executing your first test suite in minutes.

---

## 🛠️ 1. Prerequisites
Before you start, make sure you have the following installed on your machine:
- **Python 3.10+**
- **[uv](https://docs.astral.sh/uv/)**: Our ultra-fast Python package manager. (Install via `curl -LsSf https://astral.sh/uv/install.sh | sh` or `brew install uv`)
- **Git**

## 📥 2. Workspace Setup
All our plugin and core repositories use standardized `uv` environments.

```bash
# Clone the repository you are assigned to (e.g., cytometrics plugin)
git clone https://github.com/KalaimaranB/BioPro-cytometrics.git
cd BioPro-cytometrics

# Sync the environment instantly with uv
uv sync
```
This automatically sets up a sandboxed `.venv` with the BioPro SDK and all testing tools.

## 🔐 3. Local Cryptographic Identity
BioPro relies on a strict Trust System. You do not need access to the production "Project Keys" to do your work. Instead, you will generate a local development identity.

Activate your environment and run the SDK initializer:
```bash
uv run biopro sdk init-identity
```
This generates a personal `dev_cert.bin` in your `~/.biopro/` directory. You will use this to sign your local builds for testing.

## 🧪 4. The TDD Workflow (Test-Driven Development)
We adhere strictly to SOLID principles and TDD.
1. **Write the Test First**: Open the `tests/` directory and write a failing test for your new feature.
2. **Run Tests**:
   ```bash
   uv run pytest
   ```
3. **Implement**: Write the minimal code to pass the test.
4. **Evaluate SDK Compliance**: Before committing, ensure your plugin meets all structural requirements:
   ```bash
   uv run biopro sdk evaluate .
   ```

## 🤝 5. Collaboration & Code Review
We use a **Project Identity Model** for production releases. This means:
- You will NEVER sign a production release locally.
- When your feature is done, push your branch and **open a Pull Request (PR)** against `main`.
- **Pre-flight Checks**: Our GitHub Actions will automatically run `pytest` and `biopro sdk evaluate .`.
- **Code Review**: At least one other core team member must approve your PR.
- **Merge & Release**: Upon merge, the CI/CD pipeline uses the secured Project Key to cryptographically sign the plugin and publish it to the registry.

## 👥 6. Credits & Manifest Updates
When you contribute to a plugin, make sure your name is in the `manifest.json`! We do not use legacy single-author IDs.
Add yourself to the `authors` array:
```json
"authors": [
  {
    "name": "Your Name",
    "role": "Software Engineer",
    "github": "@yourusername"
  }
]
```
The BioPro Hub UI parses this array and will display your GitHub avatar on the Plugin Store page.

---
**Happy coding! If you run into issues, ping the maintainers in the team channel.**
