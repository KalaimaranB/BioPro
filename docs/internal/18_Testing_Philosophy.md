# 🧪 BioPro Testing Philosophy & Coverage

BioPro is built on a foundation of **Test-Driven Development (TDD)** and **SOLID principles**. Because the application handles sensitive scientific data and executes third-party plugin code, our testing suite is divided into three critical layers: **Unit**, **Integration**, and **Security**.

---

## 📊 Current Core Coverage (May 2026)

As of the latest audit, the BioPro core library maintains a **59% overall coverage** with 108 tests passing. High-risk modules (Communication, Security, Data Integrity) are prioritized with coverage exceeding **85%**.

| Component | Coverage | Status |
| :--- | :---: | :--- |
| **Event Bus (Nervous System)** | 96% | ✅ Robust |
| **Diagnostics Engine** | 94% | ✅ Robust |
| **Trust Architecture** | 88% | ✅ High |
| **History Manager (Undo/Redo)** | 86% | ✅ High |
| **Project & Asset Manager** | 75% | ✅ Target Met |
| **Network & Plugin Updates** | 65% | 🎯 Targeting 80% |
| **Resource Inspector** | 51% | 🎯 Targeting 80% |
| **SBOM & Supply Chain** | 0% | 🎯 Targeting 90% |

> [!NOTE]
> Coverage of 0% in modules like `preferences.py` or `sign_plugin.py` is intentional; these are either purely aesthetic UI panels or CLI wrappers that are verified via end-to-end integration tests rather than unit tests.

---

## 🛠️ Testing Infrastructure

### 1. Headless Qt Testing
We use `pytest-qt` combined with an offscreen buffer to run UI tests without a physical display. This allows our CI/CD pipelines to verify signals, slots, and widget states.
```bash
# Run tests headlessly
QT_QPA_PLATFORM=offscreen .venv/bin/python3 -m pytest tests/core/
```

### 2. Cryptographic Verification
Tests in `test_trust_architecture.py` verify that the application correctly rejects tampered plugins, unauthorized authors, and corrupted manifests. We use mocked keys to simulate "Project" vs "Developer" trust levels.

### 3. Undo/Redo (The Time Machine)
The `HistoryManager` is subjected to heavy stress tests to ensure that complex scientific states can be serialized, saved, and restored without data loss or memory leaks.

---

## 🚀 Running the Suite

All developers are expected to run the suite locally before opening a Pull Request.

### Standard Run
```bash
uv run pytest
```

### With Coverage Report
```bash
uv run pytest --cov=biopro/core --cov-report=term-missing
```

---

## 📝 Best Practices
1. **Mock External IO**: Use `monkeypatch` or `unittest.mock` for network requests and home directory access.
2. **Clean Teardown**: Always use the `temp_config_dir` fixture to avoid polluting your local `~/.biopro` folder.
3. **Signal Tracking**: Use `qtbot.waitSignal` to verify asynchronous UI behavior.
---

## 📈 Roadmap to 75% Coverage

We are currently executing an [Acceleration Plan](file:///Users/kalaimaranbalasothy/.gemini/antigravity/brain/159bddc8-d8c2-4f18-b9b3-c2b79f004fbb/artifacts/coverage_acceleration_plan.md) to move from 59% to 75% coverage by Q3 2026.

**Priority Tracks:**
1.  **Infrastructure Gaps**: Closing missing logic paths in `module_manager.py` and `network_updater.py`.
2.  **Supply Chain Security**: Achieving 90% coverage on the new `SBOMGenerator` and `TrustManager`.
3.  **Memory Stability**: Increasing coverage of the `ResourceInspector` to 80% to ensure large-dataset reliability.
