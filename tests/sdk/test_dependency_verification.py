def _dict_to_toml(d):
    # Convert flat dict to pyproject.toml format
    lines = []

    lines.append("[project]")
    lines.append(f'name = "{d.get("name", "test")}"')
    lines.append(f'version = "{d.get("version", "1.0.0")}"')
    if "description" in d:
        lines.append(f'description = "{d["description"]}"')

    authors = d.get("authors", [])
    if authors:
        lines.append("authors = [")
        for a in authors:
            lines.append(f'  {{ name = "{a.get("name", "Test")}" }},')
        lines.append("]")

    lines.append("")
    lines.append("[tool.karcytics.plugin]")
    lines.append(f'id = "{d.get("id", "test_id")}"')

    if authors:
        lines.append("authors = [")
        for a in authors:
            role = a.get("role", "Developer")
            perms = a.get("permissions", [])
            perms_str = "', '".join(perms)
            if perms_str:
                lines.append(
                    f'  {{ name = "{a.get("name", "Test")}", role = "{role}", permissions = ["{perms_str}"] }},'
                )
            else:
                lines.append(f'  {{ name = "{a.get("name", "Test")}", role = "{role}" }},')
        lines.append("]")

    deps = d.get("dependencies") or d.get("python_dependencies")
    if deps:
        lines.append("[tool.karcytics.plugin.python_dependencies]")
        for k, v in deps.items():
            lines.append(f'{k} = "{v}"')

    return "\n".join(lines)


import sys
from io import StringIO
from pathlib import Path

from karcytics_sdk.host import TrustManager
from karcytics_sdk.sdk_cli import SDKCLI


def test_trust_manager_ignore_list():
    """Assert that .venv and venv are correctly in the TrustManager ignore list."""
    assert ".venv" in TrustManager.IGNORE_LIST
    assert "venv" in TrustManager.IGNORE_LIST


def test_evaluate_plugin_no_dependencies(tmp_path: Path):
    """Test evaluating a plugin manifest without any dependencies block."""
    manifest = {
        "manifest_version": 2,
        "id": "test_plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "description": "Just a test",
        "authors": [{"name": "Karcytics Developer", "role": "Developer"}],
    }
    with open(tmp_path / "pyproject.toml", "w", encoding="utf-8") as f:
        f.write(_dict_to_toml(manifest))

    # Create a dummy python file to pass structure check
    with open(tmp_path / "main.py", "w", encoding="utf-8") as f:
        f.write("# dummy file with AnalysisBase reference")

    cli = SDKCLI()
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    try:
        cli.evaluate_plugin(str(tmp_path))
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout

    assert "Auditing Plugin Dependencies" not in output


def test_evaluate_plugin_pinned_dependencies(tmp_path: Path):
    """Test evaluating a plugin manifest with perfectly pinned dependencies."""
    manifest = {
        "manifest_version": 2,
        "id": "test_plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "description": "Just a test",
        "authors": [{"name": "Karcytics Developer", "role": "Developer"}],
        "dependencies": {
            "scipy": "1.11.3",
            "opencv-python-headless": "4.8.0.76",
        },
    }
    with open(tmp_path / "pyproject.toml", "w", encoding="utf-8") as f:
        f.write(_dict_to_toml(manifest))

    with open(tmp_path / "main.py", "w", encoding="utf-8") as f:
        f.write("# AnalysisBase reference")

    cli = SDKCLI()
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    try:
        cli.evaluate_plugin(str(tmp_path))
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout

    assert "Auditing Plugin Dependencies" in output or "Auditing" in output
    assert "scipy' is pinned to version '1.11.3'" in output
    assert "All declared dependencies are securely pinned" in output


def test_evaluate_plugin_unpinned_dependencies(tmp_path: Path):
    """Test evaluating a plugin manifest with unpinned dependencies (fuzzy versioning)."""
    manifest = {
        "manifest_version": 2,
        "id": "test_plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "description": "Just a test",
        "authors": [{"name": "Karcytics Developer", "role": "Developer"}],
        "dependencies": {
            "scipy": ">=1.11.3",
        },
    }
    with open(tmp_path / "pyproject.toml", "w", encoding="utf-8") as f:
        f.write(_dict_to_toml(manifest))

    with open(tmp_path / "main.py", "w", encoding="utf-8") as f:
        f.write("# AnalysisBase reference")

    cli = SDKCLI()
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    try:
        cli.evaluate_plugin(str(tmp_path))
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout

    assert "is not pinned. Recommend exact pinning" in output
