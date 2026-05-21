# FAQ & Troubleshooting

This document addresses common questions and operational issues encountered when using BioPro.

---

## General Questions

### Is BioPro open source?
Yes, the BioPro Core application is open-source. However, specific third-party plugins may carry their own licensing terms.

### Does BioPro upload my data to the cloud?
No. BioPro operates locally. Your data, project files, and analysis results remain on your local filesystem unless you intentionally export or sync them.

### How do I cite BioPro?
We recommend the following format:
> "Analysis was performed using the BioPro Analysis Suite, incorporating the [Plugin Name] module."

---

## Troubleshooting Guide

### Cannot open a project
- **Lock File Issue**: Check if another instance of BioPro is running. If BioPro crashed previously, a stale `.lock` file may remain in the `.biopro/` directory. Delete the `.lock` file manually if no other instances are running.
- **File Permissions**: Verify that your user account has read/write permissions for the project directory.

### Diagrams or UI elements are not rendering
- **Browser Engine**: BioPro utilizes a Chromium-based web engine for UI rendering. Ensure your system drivers are up to date.

### Wizard execution is blocked
- **Validation Failure**: The "Next" or "Run" buttons will remain disabled if the current input parameters fail validation. Review the interface for highlighted errors or missing required fields.

### Application Exception (Error Dialog)
BioPro includes a diagnostic module to handle unexpected exceptions.
- **Diagnostic Logs**: Click the "View Logs" option in the error dialog to inspect the application logs located at `~/.biopro/biopro.log`.
- **Bug Reporting**: Click "Copy Details" to copy the stack trace and state information to your clipboard for reporting the issue to developers.

---

## Additional Support
- **Issue Tracker**: Report bugs via the [GitHub Repository](https://github.com/KalaimaranB/BioPro/issues).
- **Logs Directory**: Routine logs can be found at `~/.biopro/biopro.log`.
