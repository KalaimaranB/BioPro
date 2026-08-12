# Documentation & Tutorials

This section collects short, example-driven tutorials for maintainers and contributors who want to extend documentation or the SDK.

1. Writing good docstrings (Google style)
2. Adding an auto-generated API page (`mkdocstrings`)
3. Previewing docs locally with `mkdocs serve`

## Plugin Authoring Tutorial (Minimal)

1. Create a package exposing `get_plugin()` that returns a `PluginBase` instance.
2. Add a `pyproject.toml` and ensure `biopro-sdk` is declared as a dependency.
3. Install locally with:

```bash
pip install -e plugin_template/example_minimal_plugin
```

4. Use the `biopro` CLI or copy the package into the plugin directory to test loading in the app.

See `plugin_template/docs/index.md` for the template and further guidance.

Tutorials will be expanded as we convert internal architecture pages into examples.
