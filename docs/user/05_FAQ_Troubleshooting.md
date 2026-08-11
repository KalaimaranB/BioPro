# FAQ & Troubleshooting

This page answers common issues and points you to the logs, support resources, and recovery strategies.

---

## General Questions

### Is BioPro open source?

Yes. The BioPro core application is open-source. Some plugins may be developed by third parties and carry their own licensing or usage terms.

### Does BioPro upload my data to the cloud?

No. BioPro stores your projects and analysis data locally. Only plugin metadata and trusted developer registries are fetched from the network.

### Why does BioPro use a plugin store?

The core app is intentionally lightweight. Analysis modules are installed on demand from the Plugin Store so you can add only the tools you need.

---

## Cannot open a project

### The project is locked

BioPro creates `.biopro.lock` inside the project folder while the project is open.

* If another BioPro instance is already running, close it before reopening the project.
* If BioPro crashed and the lock file remains, delete `.biopro.lock` after verifying that no BioPro instance is still using the project.

### Permission denied

Make sure your operating system account has read and write permission for the project folder and all files inside it. This is especially important for folders synced by cloud services or shared network drives.

---

## Plugin and module issues

### A plugin fails to install or update

* Check your internet connection.
* Open the **Marketplace** and retry the installation.
* If the plugin still fails, use the **Repair** action or **Repair All Plugins** in the Plugin Store.

### A plugin is blocked as untrusted

BioPro will not execute plugins that are not trusted.

* Inspect the developer identity in the Plugin Store.
* If you recognize the source, approve the developer when prompted.
* If you do not trust the source, do not run the plugin.

### A plugin says it is outdated

This means the installed module requires a newer BioPro core or plugin version.

* Go to the **Available Updates** collection in the Marketplace.
* Update the plugin.
* If the problem persists, update the core application from the Hub’s update banner.

---

## Logs and diagnostics

### View logs

BioPro stores runtime logs at `~/.biopro/biopro.log`.

* In the workspace, open **Help → 📜 View Logs**.
* In the Project Hub, open the same Help menu option.

### When to report a bug

Report issues when:

* BioPro crashes unexpectedly.
* A plugin repeatedly fails to install or load.
* A project cannot be opened even after removing a stale lock file.

Include the log file contents and a description of what you were doing when the problem occurred.

---

## Application update issues

### Update banner not appearing

BioPro checks for core updates on Hub startup.

* If you do not see an update banner, your current version is likely up to date.
* If you suspect a newer version exists, visit the GitHub Releases page and compare versions manually.

### Skipping a version

The update banner includes **Skip This Version** so you can stay on your current release temporarily. If you skip a version, the banner will not reappear for that version again.

---

## AI Assistant

The AI Assistant panel is part of the application roadmap but is not currently exposed in the main toolbar. Use the Help Center and built-in guides to continue working normally.

---

## Additional support

* **GitHub Issues:** [https://github.com/KalaimaranB/BioPro/issues](https://github.com/KalaimaranB/BioPro/issues)
* **Documentation portal:** [https://kalaimaranb.github.io/BioPro/](https://kalaimaranb.github.io/BioPro/)
* **Log file:** `~/.biopro/biopro.log`
