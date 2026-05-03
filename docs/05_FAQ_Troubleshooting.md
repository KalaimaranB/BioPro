# ❓ FAQ & Troubleshooting

Find answers to common questions and solutions to technical issues in BioPro.

---

## 🙋 General Questions

### Is BioPro really free?
Yes. BioPro Core is open-source. Some specialized high-performance plugins may require separate licensing depending on the author, but the platform itself is free for academic use.

### Does my data leave my computer?
**No.** BioPro is a "Privacy-First" local application. Your images, results, and project files never leave your machine unless you explicitly share them or sync them to your own cloud storage.

### How do I cite BioPro in my publication?
We recommend the following format:
> "Analysis was performed using the BioPro Analysis Suite (v1.2.0), incorporating the [Plugin Name] module."

---

## 🔧 Troubleshooting

### I can't open a project.
- **Check for locks**: Ensure another instance of BioPro isn't already using the folder.
- **Permissions**: Ensure you have write access to the directory.

### My Mermaid diagrams aren't rendering.
- **Chrome Compatibility**: BioPro uses a Chromium-based engine. Ensure your system drivers are up to date.
- **JavaScript Enabled**: If you've modified internal settings, ensure JavaScript execution is not disabled.

### The "Next" button is disabled in the Wizard.
- This usually means a required field is missing or invalid. Check for red highlights in the "Input" or "Parameters" screen.

### An "Unexpected Error" dialog appeared.
Don't panic! BioPro has a built-in **Diagnostic Engine** that captures errors as they happen.
- **View Logs**: Click this in the error dialog to open your local log folder.
- **Copy Details**: Click this to copy a full technical report (including the "Black Box" history) to your clipboard.
- **Contact Developer**: Reach out to the project maintainers with the copied details for support.

---

## 🆘 Still Need Help?
- **GitHub Issues**: Report bugs on our [GitHub Repository](https://github.com/KalaimaranB/BioPro/issues).
- **Log Files**: You can find internal logs at `~/.biopro/biopro.log`.
- **Diagnostic Reports**: When reporting a bug, please use the "Copy Details" button in the error dialog to provide developers with the necessary context.
