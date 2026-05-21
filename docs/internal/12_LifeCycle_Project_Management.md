# Lifecycle and Project Management

The `ProjectManager` handles the lifecycle of project artifacts, encompassing raw data tracking, state persistence, and metadata management.

---

## Workspace Directory Structure

A BioPro project is identified by a top-level directory containing a `.biopro` configuration folder.

```text
my_experiment/
├── .biopro/
│   ├── project.json          # Main metadata & asset registry
│   ├── history.json          # Serialized state chain
│   └── .lock                 # Process lock
├── assets/                   # Local copies of image data
└── workflows/                # Serialized analysis configurations
```

---

## Session Locking

To prevent data corruption from concurrent access, BioPro implements a file-based locking mechanism.

### Lock Protocol
1.  **Acquisition**: Upon opening a project, `ProjectManager` writes its system process ID (PID) to `.biopro/.lock`.
2.  **Verification**: If a lock file exists, the manager checks the active system processes. If the recorded PID is dead (e.g., from an abrupt termination), the lock is claimed. If the PID is active, a `ProjectLockedError` is raised.
3.  **Release**: The lock file is deleted during graceful application shutdown or when the project is closed.

---

## Asset Management

BioPro supports two strategies for managing raw input data:

| Strategy | Behavior | Trade-offs |
| :--- | :--- | :--- |
| **Copy to Workspace** | The file is duplicated into the `assets/` directory. | Ensures project portability at the cost of disk space. |
| **External Reference** | Only the absolute file path is recorded. | Saves disk space but breaks if files are moved externally. |

### Integrity Hashing
Loaded images are hashed using SHA-256. This facilitates:
- Deduplication of assets.
- Verification of file integrity to detect external modifications since the last analysis run.

---

## Atomic Save Operations

BioPro utilizes atomic writes for critical configuration files (`project.json`, `history.json`) to prevent data loss during unexpected terminations.

1.  The serialized state is written to a temporary file (e.g., `project.json.tmp`).
2.  An atomic filesystem `replace()` operation swaps the temporary file with the target file.
3.  This ensures the file is never left in a partially written state.

---

## API Reference (`biopro.core.project_manager`)

### `ProjectManager(project_dir: Path)`
Initializes the manager instance. Does not perform I/O upon instantiation.

- `open_project()`: Reads project metadata, history, and acquires the directory lock.
- `save()`: Triggers an atomic write of all metadata and state histories.
- `add_image(path, copy_to_workspace=True)`: Registers a new data asset into the project scope.
- `save_workflow(module_id, payload)`: Persists an analysis configuration to the `workflows/` subdirectory.
