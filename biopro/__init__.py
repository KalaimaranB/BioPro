"""BioPro — Bio-Image Analysis Made Simple.

An open-source, intuitive alternative to ImageJ for lab students
and professionals. Automates tedious bio-image analysis workflows
through a modern desktop interface.

Modules:
    analysis: Headless image processing engine (usable without GUI).
    ui: PyQt6 desktop interface components.
"""

def _get_version():
    """Extract version from package metadata or pyproject.toml fallback."""
    import sys
    from pathlib import Path

    # 1. Try standard metadata (for installed packages)
    if sys.version_info >= (3, 8):
        from importlib.metadata import version, PackageNotFoundError
    else:
        try:
            from importlib_metadata import version, PackageNotFoundError
        except ImportError:
            version = None

    if version:
        try:
            return version("biopro")
        except (PackageNotFoundError, Exception):
            pass

    # 2. Fallback: Parse pyproject.toml directly (for dev/source environments)
    try:
        # Python 3.11+ has tomllib built-in
        import tomllib
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                return data.get("project", {}).get("version", "unknown")
    except Exception:
        pass

    return "1.0.3" # Absolute fallback

__version__ = _get_version()
__author__ = "BioPro Contributors"