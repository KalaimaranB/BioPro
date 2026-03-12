"""BioPro application entry point.

This module serves as the entry point for both:
    - ``python -m biopro`` (module execution)
    - ``biopro`` (console script, via pyproject.toml entry point)

It creates the QApplication, applies the dark theme, and launches
the main window.
"""

from __future__ import annotations

import logging
import sys


def main() -> int:
    """Launch the BioPro desktop application.

    Returns:
        Exit code (0 = success).
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Import PyQt6 (deferred to keep CLI usage fast)
    from PyQt6.QtWidgets import QApplication

    from biopro.ui.main_window import MainWindow
    from biopro.ui.theme import apply_theme

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("BioPro")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("BioPro")

    # Apply theme
    apply_theme(app)

    # Create and show main window
    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
