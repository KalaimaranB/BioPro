# Project Management and Data Formats

BioPro organizes scientific workflows into specific project directories. This structure ensures that raw data, analysis results, and history are kept logically grouped.

---

## The Project Directory Structure

When a project is created, BioPro initializes a hidden `.biopro` directory within the chosen workspace to manage metadata.

```text
Project_Workspace/
├── .biopro/
│   ├── project_manifest.json  # Core metadata and system state
│   ├── history_ledger.db      # SQLite database tracking state changes
│   └── .lock                  # Process lock to prevent concurrent writes
├── raw_data/                  # (User defined) Input files
└── analysis_results/          # (User defined) Output files
```

### Process Locking
BioPro implements OS-level file locking (`.lock`). Attempting to open the same project simultaneously in multiple BioPro instances will be blocked. This protects the `history_ledger.db` from concurrent write corruption.

---

## Project Sharing

BioPro projects can be shared across different machines by transferring the entire project directory.
1.  **Package**: Compress the entire project directory (including the `.biopro` folder) into an archive (e.g., `.zip`).
2.  **Transfer**: Send the archive to the recipient.
3.  **Open**: The recipient can extract the archive and open the directory in their BioPro instance. The application will restore the last saved state and history.
Note: If a project requires a plugin the recipient has not installed, BioPro will prompt them to install it.

---

## Supported Data Formats

BioPro's core supports common structured formats. Specialized formats are handled by specific plugins.

| Format | Common Usage |
| :--- | :--- |
| `.fcs` | Flow Cytometry data |
| `.tiff / .png / .jpg` | Imaging data (Microscopy, Blots) |
| `.csv / .tsv` | Tabular data exports |

---

## File Integrity

BioPro records the hashes of loaded input files within the project state. If underlying files are modified outside of the application, BioPro may flag associated analysis steps as stale or requiring re-computation.
