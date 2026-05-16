# 🗂 architecture: Project Lifecycle & Data Management

The `ProjectManager` is the orchestrator of all data artifacts within BioPro. It ensures that scientific data (images), analysis states (history), and metadata (project settings) are stored safely and remains portable.

---

## 🏗 The Workspace Anatomy

Every BioPro project is a folder. The presence of a `project.biopro` file identifies it as a valid workspace.

```text
my_experiment/
├── project.biopro        # Main metadata & asset registry (JSON)
├── history.json          # Full undo/redo chain for the session
├── .biopro.lock          # Prevents multi-process corruption
├── assets/               # Folder for local copies of raw images
└── workflows/            # Saved analysis configurations
```

---

## 🔒 Session Safety & Locking

Scientific data integrity depends on preventing race conditions. If two people (or two instances of BioPro) try to edit the same project folder simultaneously, the data would likely corrupt.

### The Lock Mechanism
1.  **Acquire**: When a project is opened, `ProjectManager` writes the current process ID (PID) to `.biopro.lock`.
2.  **Verify**: If a lock exists, it checks if that PID is still running. If the PID is dead (e.g., after a crash), it "steals" the lock. If the PID is alive, it raises `ProjectLockedError`.
3.  **Release**: The lock is deleted only when the project is safely closed (via `close()`).

---

## 💾 Asset Handling (Portability vs. Reference)

BioPro supports two ways to handle your raw data (images/tensors).

| Method | Behavior | Pros | Cons |
| :--- | :--- | :--- | :--- |
| **Copy to Workspace** | File is copied into `assets/` and hashed. | Portable (can move folder to USB). | Uses more disk space. |
| **Reference External** | Only the absolute path is stored. | Zero extra disk space. | Breaks if you move the raw data. |

### Merkle-Integrity Hashing
Every image is hashed using **SHA-256**. This allows BioPro to:
- Detect if you've already added an image (avoiding duplicates).
- Verify that a file hasn't been tampered with or corrupted since it was last analyzed.

---

## ⚛️ Atomic Saving

BioPro never overwrites a `project.biopro` file directly. This prevents "partial saves" if the power goes out or the app crashes.

1.  Current state is written to `project.biopro.tmp`.
2.  The OS `replace()` command moves the temp file over the real one.
3.  This operation is **atomic** at the filesystem level—it either succeeds entirely or fails without touching the old data.

---

## 🛠 Internal API Reference (`biopro.core.project_manager`)

### `ProjectManager(project_dir: Path)`
Constructor initializes the paths but does not open the files.

- `open_project()`: Reads metadata, history, and acquires the lock.
- `save()`: Triggers an atomic save of all metadata and history threads.
- `add_image(path, copy_to_workspace=True)`: Registers a new biological asset.
- `save_workflow(module_id, payload)`: Persists a specific analysis configuration to the `workflows/` directory.
