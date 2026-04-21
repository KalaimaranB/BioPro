"""Centralized Resource Path Handling for PyInstaller and Development."""

import os
import sys
from pathlib import Path

def resource_path(relative_path: str) -> Path:
    """
    Get the absolute path to a resource, works for dev and for PyInstaller.
    
    PyInstaller creates a temporary folder and stores the path in `sys._MEIPASS`.
    In development, it uses the local relative path from the project root.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except AttributeError:
        # We are in development mode
        # Path(__file__) is biopro/core/resource_manager.py
        # We want the root of the project
        base_path = Path(__file__).parent.parent.parent

    # Special handling for paths that are nested differently in the bundle
    # If the relative path starts with 'biopro/', and we are in dev, it's fine.
    # But in the bundle, we might have mapped 'biopro/themes' to 'themes'.
    # We should handle both cases or ensure the .spec file matches.
    
    full_path = base_path / relative_path
    
    # If the relative path wasn't found at the root, check inside biopro/
    if not full_path.exists() and not relative_path.startswith("biopro/"):
        alt_path = base_path / "biopro" / relative_path
        if alt_path.exists():
            return alt_path

    return full_path
