"""BioPro application entry point.

This module serves as the entry point for both:
    - ``python -m biopro`` (module execution)
    - ``biopro`` (console script, via pyproject.toml entry point)

It creates the QApplication, applies the dark theme, and launches
the Hub window.
"""

from __future__ import annotations

import logging
import sys
import shutil
from pathlib import Path


def apply_staged_updates() -> None:
    """Checks for downloaded core updates and applies them before boot."""
    staging_dir = Path.home() / ".biopro" / ".staging"
    app_dir = Path(__file__).parent  # The live biopro folder
    
    if staging_dir.exists() and any(staging_dir.iterdir()):
        print("Applying Core Update...")
        try:
            # Copy all files from .staging into the live app directory, overwriting old ones
            shutil.copytree(staging_dir, app_dir, dirs_exist_ok=True)
            # Delete the staging folder so we don't apply it again next boot
            shutil.rmtree(staging_dir)
            print("Update applied successfully!")
        except Exception as e:
            print(f"Failed to apply update: {e}")


def main() -> int:
    """Launch the BioPro desktop application.

    Returns:
        Exit code (0 = success).
    """
    # 1. Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # 2. ALWAYS run the bootloader first, before loading heavy UI modules!
    apply_staged_updates()

    # 3. Deferred imports
    # We import these HERE so that if apply_staged_updates() just replaced
    # these files, Python loads the brand new versions, not the old ones!
    from PyQt6.QtWidgets import QApplication
    from biopro.ui.hub_window import HubWindow

    # 4. Create application
    app = QApplication(sys.argv)
    app.setApplicationName("BioPro")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("BioPro")
    app.setStyle("Fusion")
    
    # If you have an apply_theme function in biopro.ui.theme, you would call it here:
    # from biopro.ui.theme import apply_theme
    # apply_theme(app)

    # 5. Launch the Hub
    hub = HubWindow()
    hub.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())