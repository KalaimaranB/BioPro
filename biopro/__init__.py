"""BioPro — Bio Analysis Made Simple.

An open-source, intuitive platform for lab students
and professionals. Automates tedious bio-image analysis workflows
through a modern desktop interface.

Modules:
    analysis: Headless image processing engine (usable without GUI).
    ui: PyQt6 desktop interface components.
"""

def _get_version():
    """Extract version from pyproject.toml (dev) or package metadata (installed)."""
    from pathlib import Path
    import importlib.metadata
    
    # 1. Parse pyproject.toml directly (Primary for dev/source environments)
    # This ensures that local changes are reflected immediately.
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    if pyproject_path.exists():
        try:
            import tomllib
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                version = data.get("project", {}).get("version")
                if version:
                    return version
        except Exception as e:
            # Raise a clear error if the TOML exists but is broken
            raise RuntimeError(f"Malformed pyproject.toml: {e}") from e

    # 2. Fallback: Try standard metadata (for installed packages)
    try:
        return importlib.metadata.version("biopro")
    except importlib.metadata.PackageNotFoundError:
        pass

    raise RuntimeError(
        "Could not determine BioPro version. "
        "Ensure pyproject.toml exists and is valid, or that the package is installed."
    )

__version__ = _get_version()
__author__ = "BioPro Contributors"