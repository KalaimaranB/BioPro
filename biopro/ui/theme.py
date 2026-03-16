"""Dark theme and styling constants for the BioPro UI.

This module defines the complete visual theme for the application,
including colors, fonts, and a QSS (Qt Style Sheet) stylesheet.

The theme uses a modern dark palette with:
    - Deep charcoal/navy backgrounds for reduced eye strain.
    - Teal/cyan accent color for primary actions and highlights.
    - Amber for warnings and important notices.
    - Soft rounded corners and subtle hover transitions.

To apply the theme, call ``apply_theme(app)`` with your QApplication.

Design Notes:
    - All colors are defined as constants for easy customization.
    - The QSS is a single string for simple application via
      ``QApplication.setStyleSheet()``.
    - Font sizes are in points for cross-platform consistency.
"""

from __future__ import annotations

from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import QApplication


# ── Color Palette ───────────────────────────────────────────────────

class Colors:
    """Application color constants.

    All colors are hex strings suitable for use in QSS stylesheets
    and as QColor constructors.
    """

    # Backgrounds (darkest → lightest)
    BG_DARKEST = "#0d1117"     # Main window background
    BG_DARK = "#161b22"        # Panel/card backgrounds
    BG_MEDIUM = "#21262d"      # Input fields, tabs
    BG_LIGHT = "#30363d"       # Hover states, borders

    # Foreground / text
    FG_PRIMARY = "#e6edf3"     # Primary text
    FG_SECONDARY = "#8b949e"   # Secondary/muted text
    FG_DISABLED = "#484f58"    # Disabled elements

    # Accent colors
    ACCENT_PRIMARY = "#2dccb8"     # Teal — primary actions
    ACCENT_PRIMARY_HOVER = "#3de8d2"
    ACCENT_PRIMARY_PRESSED = "#22a595"
    ACCENT_SECONDARY = "#58a6ff"   # Blue — links, info
    ACCENT_WARNING = "#d29922"     # Amber — warnings
    ACCENT_DANGER = "#f85149"      # Red — errors, destructive
    

    # Semantic
    SUCCESS = "#3fb950"
    BORDER = "#30363d"
    BORDER_FOCUS = "#2dccb8"

    # Charts
    CHART_COLORS = [
        "#2dccb8", "#58a6ff", "#d29922", "#f85149",
        "#a371f7", "#3fb950", "#f778ba", "#79c0ff",
    ]


# ── Font Configuration ──────────────────────────────────────────────

class Fonts:
    """Font family and size constants."""

    FAMILY = "Inter, -apple-system, Segoe UI, Roboto, sans-serif"
    MONO_FAMILY = "JetBrains Mono, SF Mono, Cascadia Code, Consolas, monospace"

    SIZE_SMALL = 11
    SIZE_NORMAL = 13
    SIZE_LARGE = 15
    SIZE_TITLE = 18
    SIZE_HEADER = 24


# ── QSS Stylesheet ──────────────────────────────────────────────────

STYLESHEET = f"""
/* ── Global ─────────────────────────────────────────── */

QWidget {{
    background-color: {Colors.BG_DARKEST};
    color: {Colors.FG_PRIMARY};
    font-family: {Fonts.FAMILY};
    font-size: {Fonts.SIZE_NORMAL}px;
}}

QMainWindow {{
    background-color: {Colors.BG_DARKEST};
}}

/* ── Menu Bar ───────────────────────────────────────── */

QMenuBar {{
    background-color: {Colors.BG_DARK};
    border-bottom: 1px solid {Colors.BORDER};
    padding: 2px 8px;
}}

QMenuBar::item {{
    padding: 6px 12px;
    border-radius: 4px;
}}

QMenuBar::item:selected {{
    background-color: {Colors.BG_LIGHT};
}}

QMenu {{
    background-color: {Colors.BG_DARK};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 4px;
}}

QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {Colors.BG_LIGHT};
}}

/* ── Buttons ────────────────────────────────────────── */

QPushButton {{
    background-color: {Colors.BG_MEDIUM};
    color: {Colors.FG_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
    min-height: 20px;
}}

QPushButton:hover {{
    background-color: {Colors.BG_LIGHT};
    border-color: {Colors.FG_SECONDARY};
}}

QPushButton:pressed {{
    background-color: {Colors.BG_DARK};
}}

QPushButton:disabled {{
    color: {Colors.FG_DISABLED};
    border-color: {Colors.BG_MEDIUM};
}}

QPushButton#primaryButton {{
    background-color: {Colors.ACCENT_PRIMARY};
    color: {Colors.BG_DARKEST};
    border: none;
    font-weight: 600;
}}

QPushButton#primaryButton:hover {{
    background-color: {Colors.ACCENT_PRIMARY_HOVER};
}}

QPushButton#primaryButton:pressed {{
    background-color: {Colors.ACCENT_PRIMARY_PRESSED};
}}

/* ── Input Fields ───────────────────────────────────── */

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {Colors.BG_MEDIUM};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    color: {Colors.FG_PRIMARY};
    min-height: 20px;
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {Colors.BORDER_FOCUS};
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {Colors.BG_DARK};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    selection-background-color: {Colors.BG_LIGHT};
}}

/* ── Sliders ────────────────────────────────────────── */

QSlider::groove:horizontal {{
    background: {Colors.BG_MEDIUM};
    height: 6px;
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: {Colors.ACCENT_PRIMARY};
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}}

QSlider::handle:horizontal:hover {{
    background: {Colors.ACCENT_PRIMARY_HOVER};
}}

/* ── Labels ─────────────────────────────────────────── */

QLabel {{
    background-color: transparent;
}}

QLabel#sectionHeader {{
    font-size: {Fonts.SIZE_LARGE}px;
    font-weight: 600;
    color: {Colors.FG_PRIMARY};
    padding: 8px 0 4px 0;
}}

QLabel#stepTitle {{
    font-size: {Fonts.SIZE_TITLE}px;
    font-weight: 700;
    color: {Colors.ACCENT_PRIMARY};
}}

QLabel#subtitle {{
    font-size: {Fonts.SIZE_SMALL}px;
    color: {Colors.FG_SECONDARY};
}}

/* ── Group Boxes (Cards) ────────────────────────────── */

QGroupBox {{
    background-color: {Colors.BG_DARK};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    margin-top: 12px;
    padding: 16px 12px 12px 12px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 12px;
    color: {Colors.FG_SECONDARY};
}}

/* ── Scroll Areas ──────────────────────────────────── */

QScrollArea {{
    border: none;
    background: transparent;
}}

QScrollBar:vertical {{
    background: {Colors.BG_DARKEST};
    width: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background: {Colors.BG_LIGHT};
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {Colors.FG_SECONDARY};
}}

QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0;
}}

QScrollBar:horizontal {{
    background: {Colors.BG_DARKEST};
    height: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal {{
    background: {Colors.BG_LIGHT};
    border-radius: 4px;
    min-width: 30px;
}}

/* ── Table Widget ──────────────────────────────────── */

QTableWidget {{
    background-color: {Colors.BG_DARK};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    gridline-color: {Colors.BG_MEDIUM};
    selection-background-color: {Colors.BG_LIGHT};
}}

QTableWidget::item {{
    padding: 4px 8px;
}}

QHeaderView::section {{
    background-color: {Colors.BG_MEDIUM};
    color: {Colors.FG_SECONDARY};
    font-weight: 600;
    border: none;
    border-bottom: 1px solid {Colors.BORDER};
    padding: 6px 8px;
}}

/* ── Tab Widget ─────────────────────────────────────── */

QTabWidget::pane {{
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    background: {Colors.BG_DARK};
}}

QTabBar::tab {{
    background: {Colors.BG_MEDIUM};
    border: 1px solid {Colors.BORDER};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 16px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background: {Colors.BG_DARK};
    color: {Colors.ACCENT_PRIMARY};
    border-bottom: 2px solid {Colors.ACCENT_PRIMARY};
}}

/* ── Status Bar ─────────────────────────────────────── */

QStatusBar {{
    background-color: {Colors.BG_DARK};
    border-top: 1px solid {Colors.BORDER};
    color: {Colors.FG_SECONDARY};
    font-size: {Fonts.SIZE_SMALL}px;
}}

/* ── Splitter ───────────────────────────────────────── */

QSplitter::handle {{
    background: {Colors.BORDER};
    width: 2px;
    height: 2px;
}}

/* ── Progress Bar ──────────────────────────────────── */

QProgressBar {{
    background: {Colors.BG_MEDIUM};
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}}

QProgressBar::chunk {{
    background: {Colors.ACCENT_PRIMARY};
    border-radius: 4px;
}}

/* ── Tool Tips ──────────────────────────────────────── */

QToolTip {{
    background-color: {Colors.BG_DARK};
    color: {Colors.FG_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 4px;
    padding: 4px 8px;
}}
"""


def apply_theme(app: QApplication) -> None:
    """Apply the BioPro dark theme to a QApplication.

    This sets both the QSS stylesheet and the QPalette for
    consistent styling across all widgets.

    Args:
        app: The QApplication instance to style.
    """
    app.setStyleSheet(STYLESHEET)

    # Also set the palette for widgets that don't use QSS
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(Colors.BG_DARKEST))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(Colors.FG_PRIMARY))
    palette.setColor(QPalette.ColorRole.Base, QColor(Colors.BG_MEDIUM))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(Colors.BG_DARK))
    palette.setColor(QPalette.ColorRole.Text, QColor(Colors.FG_PRIMARY))
    palette.setColor(QPalette.ColorRole.Button, QColor(Colors.BG_MEDIUM))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(Colors.FG_PRIMARY))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(Colors.ACCENT_PRIMARY))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(Colors.BG_DARKEST))
    app.setPalette(palette)
