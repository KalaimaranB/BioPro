# Project Management

BioPro stores all of your work inside a project folder. Each project contains its own state file, managed assets, saved workflows, and a temporary lock file while the project is open.

---

## Project Folder Layout

A BioPro project directory typically contains:

```text
ProjectName/
├── project.biopro      # Core project state saved by BioPro
├── assets/             # Managed assets such as imported images or attachments
├── workflows/          # Saved workflow snapshots created by plugins
└── .biopro.lock        # Temporary lock file during an open session
```

### What each item means

* `project.biopro` — The main project state file in JSON format.
* `assets/` — Stores project assets managed through BioPro, including files copied into the project.
* `workflows/` — Stores saved workflows and attachments produced by analysis modules.
* `.biopro.lock` — A lock file created while the project is open to prevent concurrent use.

> [!NOTE]
> The application data folder `~/.biopro` is separate from the project folder. It stores installed plugins, logs, and global settings.

---

## Saving and Reliability

BioPro saves project state atomically to minimize corruption.

* Changes are committed to `project.biopro` when you save or close the project.
* If BioPro encounters a corrupted state file, it will attempt to recover a default project state and continue safely.
* Legacy `history.json` files are automatically removed when a project is opened.

---

## Project Locking

While a project is open, BioPro creates `.biopro.lock` in the project folder.

* This prevents the same project from being opened by more than one instance of BioPro at a time.
* If the lock file exists and the recorded process is no longer running, BioPro treats it as stale and may override it.
* If BioPro crashes, a stale `.biopro.lock` file may remain. Remove it only after confirming no other BioPro instance is using the project.

---

## Sharing Projects

To share a BioPro project with a colleague:

1. Compress the entire project folder, including `project.biopro`, `assets/`, and `workflows/`.
2. Send the archive to the recipient.
3. The recipient extracts the folder and opens it in BioPro.

### Important sharing notes

* Always include the whole project folder.
* If the project depends on a plugin that the recipient does not have installed, BioPro will prompt them to install it when opening the project. If plugin or core versions do not match, the files might not load correctly.
* Do not edit `project.biopro` manually unless you understand the JSON structure.

---

## Workflow Files

BioPro saves module snapshots in the `workflows/` folder. Each workflow file is a JSON document that contains:

* module metadata
* analysis payload
* optional attachments and supporting files

Workflows are useful for preserving specific analysis steps or exporting a reproducible configuration.

---

## Common Data Formats

BioPro's core application is plugin-driven, so supported file formats depend on the active modules.

Common formats used by modules include:

* `.csv` / `.tsv` — tabular data exports and input tables
* `.tiff`, `.png`, `.jpg` — image data
* `.fcs` — flow cytometry data (plugin support required)

If a file format is not supported, look for a module that declares compatibility with that type in the Plugin Store.

---

## File Integrity and External Changes

BioPro tracks the analysis state for files imported into the project.

* If a source file changes outside the app, BioPro may mark dependent steps as stale.
* To avoid inconsistency, keep raw input files in one place and do not edit them while the project is open.
