# Example Minimal Plugin

This is a minimal example plugin demonstrating the required plugin contract for Karcytics.

Install locally for development:

```bash
pip install -e plugin_template/example_minimal_plugin
```

Structure:

- `src/example_plugin/__init__.py` — exposes `get_plugin()` factory.

Notes:

- This plugin depends on `karcytics-sdk` and is intended as a starter template for authors.
