"""Welcome home screen for BioPro.

Shown on application launch. Users pick an analysis module from here,
then the window transitions into the relevant analysis view.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from biopro.ui.theme import Colors, Fonts


class ModuleCard(QFrame):
    """Clickable card representing one analysis module."""

    clicked = pyqtSignal()

    def __init__(
        self,
        icon: str,
        title: str,
        description: str,
        badge: str = "",
        enabled: bool = True,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._enabled = enabled
        self.setObjectName("moduleCard")
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor
        )
        self.setMinimumSize(220, 150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(6)

        # Icon + badge row
        top_row = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 26px; background: transparent;")
        top_row.addWidget(icon_lbl)
        top_row.addStretch()

        if badge:
            badge_lbl = QLabel(badge)
            badge_lbl.setStyleSheet(
                f"background: {Colors.ACCENT_PRIMARY}; color: {Colors.BG_DARKEST};"
                f" border-radius: 5px; padding: 2px 7px; font-size: 10px; font-weight: 700;"
            )
            top_row.addWidget(badge_lbl)
        elif not enabled:
            soon_lbl = QLabel("Coming soon")
            soon_lbl.setStyleSheet(
                f"background: {Colors.BG_LIGHT}; color: {Colors.FG_DISABLED};"
                f" border-radius: 5px; padding: 2px 7px; font-size: 10px; font-weight: 600;"
            )
            top_row.addWidget(soon_lbl)

        layout.addLayout(top_row)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"font-size: {Fonts.SIZE_LARGE}px; font-weight: 700;"
            f" color: {'#e6edf3' if enabled else Colors.FG_DISABLED}; background: transparent;"
        )
        layout.addWidget(title_lbl)

        desc_lbl = QLabel(description)
        desc_lbl.setStyleSheet(
            f"font-size: {Fonts.SIZE_SMALL}px; color: {Colors.FG_SECONDARY}; background: transparent;"
        )
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)

        layout.addStretch()
        self._apply_style(False)

    def _apply_style(self, hovered: bool) -> None:
        if not self._enabled:
            self.setStyleSheet(
                f"QFrame#moduleCard {{ background: {Colors.BG_DARK};"
                f" border: 1px solid {Colors.BORDER}; border-radius: 10px; }}"
            )
            return
        border = Colors.ACCENT_PRIMARY if hovered else Colors.BORDER
        bg = Colors.BG_MEDIUM if hovered else Colors.BG_DARK
        self.setStyleSheet(
            f"QFrame#moduleCard {{ background: {bg};"
            f" border: 1.5px solid {border}; border-radius: 10px; }}"
        )

    def enterEvent(self, event) -> None:
        if self._enabled:
            self._apply_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._apply_style(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if self._enabled:
            self.clicked.emit()
        super().mousePressEvent(event)


class HomeScreen(QWidget):
    """Welcome / module-selection home screen.

    Signals:
        western_blot_requested: Emitted when user selects Western Blot Analysis.
    """

    western_blot_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Hero banner ───────────────────────────────────────────────
        hero = QWidget()
        hero.setObjectName("heroWidget")
        hero.setStyleSheet(
            f"QWidget#heroWidget {{ background: {Colors.BG_DARK};"
            f" border-bottom: 1px solid {Colors.BORDER}; }}"
        )
        hero.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        hero.setFixedHeight(190)

        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(56, 36, 56, 36)
        hero_layout.setSpacing(6)

        title_row = QHBoxLayout()
        logo = QLabel("🧬")
        logo.setStyleSheet("font-size: 38px; background: transparent;")
        title_row.addWidget(logo)

        name = QLabel("BioPro")
        name.setStyleSheet(
            f"font-size: 34px; font-weight: 800; color: {Colors.FG_PRIMARY};"
            f" background: transparent; letter-spacing: -1px;"
        )
        title_row.addWidget(name)
        title_row.addStretch()

        version = QLabel("v0.1.0  ·  Beta")
        version.setStyleSheet(
            f"font-size: 11px; color: {Colors.FG_DISABLED}; background: transparent;"
        )
        title_row.addWidget(version)
        hero_layout.addLayout(title_row)

        tagline = QLabel("Bio-Image Analysis Made Simple — open-source alternative to ImageJ")
        tagline.setStyleSheet(
            f"font-size: {Fonts.SIZE_NORMAL}px; color: {Colors.FG_SECONDARY}; background: transparent;"
        )
        hero_layout.addWidget(tagline)
        root.addWidget(hero)

        # ── Module grid ───────────────────────────────────────────────
        content = QWidget()
        content.setStyleSheet(f"background: {Colors.BG_DARKEST};")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(56, 36, 56, 36)
        content_layout.setSpacing(20)

        section_lbl = QLabel("Choose an Analysis Module")
        section_lbl.setStyleSheet(
            f"font-size: {Fonts.SIZE_LARGE}px; font-weight: 600; color: {Colors.FG_PRIMARY};"
        )
        content_layout.addWidget(section_lbl)

        grid = QGridLayout()
        grid.setSpacing(14)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        wb = ModuleCard(
            icon="🔬",
            title="Western Blot",
            description=(
                "Automated lane & band detection, densitometry, "
                "and relative quantification."
            ),
            badge="Available",
            enabled=True,
        )
        wb.clicked.connect(self.western_blot_requested)
        grid.addWidget(wb, 0, 0)

        grid.addWidget(ModuleCard(
            icon="🧪", title="SDS-PAGE Gel",
            description="Molecular weight estimation and band pattern analysis.",
            enabled=False,
        ), 0, 1)

        grid.addWidget(ModuleCard(
            icon="🔆", title="Fluorescence",
            description="Multi-channel quantification and co-localisation.",
            enabled=False,
        ), 0, 2)

        grid.addWidget(ModuleCard(
            icon="🦠", title="Cell Counting",
            description="Automated segmentation, counting, and morphometry.",
            enabled=False,
        ), 1, 0)

        grid.addWidget(ModuleCard(
            icon="⚡", title="Batch Processing",
            description="Run any module across a folder of images automatically.",
            enabled=False,
        ), 1, 1)

        content_layout.addLayout(grid)
        content_layout.addStretch()

        hint = QLabel("Click an available module to begin  ·  More modules coming soon")
        hint.setStyleSheet(
            f"font-size: {Fonts.SIZE_SMALL}px; color: {Colors.FG_DISABLED};"
        )
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(hint)

        root.addWidget(content, stretch=1)