"""BioPro — Bio Analysis Made Simple.

An open-source, intuitive platform for lab students
and professionals. Automates tedious bio-image analysis workflows
through a modern desktop interface.

Modules:
    analysis: Headless image processing engine (usable without GUI).
    ui: PyQt6 desktop interface components.
"""

def _get_version():
    """Extract version from package metadata or pyproject.toml fallback."""
    from pathlib import Path
    version_str = "1.0.3"
    
    # 1. Try standard metadata (for installed packages)
    try:
        from importlib.metadata import version, PackageNotFoundError
        version_str = version("biopro")
    except (PackageNotFoundError, ImportError, Exception):
        pass

    # 2. Fallback: Parse pyproject.toml directly (for dev/source environments)
    try:
        import tomllib
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                version_str = data.get("project", {}).get("version", version_str)
    except Exception:
        pass

    return version_str

__version__ = _get_version()
__author__ = "BioPro Contributors"