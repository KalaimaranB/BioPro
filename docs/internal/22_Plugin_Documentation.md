# Plugin Documentation Starter Kit

To ensure the entire BioPro ecosystem remains professional and easy to navigate for users, we highly encourage all plugin developers to adopt the standard BioPro documentation theme (Material for MkDocs).

To make this effortless, we've provided a "Starter Kit" right here in the core repository.

## Getting Started

Inside the BioPro source code, navigate to the `docs/plugin_template/` directory.

You will find the following structure:
```text
docs/plugin_template/
├── .github/
│   └── workflows/
│       └── deploy-docs.yml
├── docs/
│   └── index.md
└── mkdocs.yml
```

### 1. Copy the Templates
Copy the entire contents of the `plugin_template/` folder directly into the root directory of your own Plugin's GitHub repository.

### 2. Customize `mkdocs.yml`
Open the copied `mkdocs.yml` and replace all placeholders with your actual plugin details:
*   `<PLUGIN_NAME>`: e.g., "BioPro Flow Cytometry"
*   `<GITHUB_USERNAME>`: e.g., "KalaimaranB"
*   `<REPOSITORY_NAME>`: e.g., "BioPro-flow-cytometry"
*   `<YOUR_NAME>`: e.g., "Kalaimaran Balasothy"

### 3. Enable GitHub Pages
This template comes with an automated CI/CD pipeline (`deploy-docs.yml`) that builds your documentation and pushes it to a branch called `gh-pages` every time you push to `main`.

To make it live:
1. Push the templates to your GitHub repository.
2. In your GitHub repository, go to **Settings > Pages**.
3. Under **Source**, select **Deploy from a branch**.
4. Select the `gh-pages` branch and `/ (root)` folder, then click **Save**.

Your documentation will now be automatically styled like the core BioPro site, and available at `https://<GITHUB_USERNAME>.github.io/<REPOSITORY_NAME>`!
