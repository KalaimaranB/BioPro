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
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGridLayout, QSizePolicy
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

    module_selected = pyqtSignal(dict)  # Passes the entire manifest dictionary
    return_to_hub_requested = pyqtSignal()
    open_store_requested = pyqtSignal()

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

        # --- Add Store Button ---
        self.btn_store = QPushButton("☁️ Store")
        self.btn_store.setStyleSheet(
            f"QPushButton {{"
            f"  background: transparent; border: 1px solid {Colors.BORDER};"
            f"  border-radius: 5px; padding: 6px 14px; margin-left: 20px;"
            f"  color: {Colors.FG_PRIMARY}; font-size: {Fonts.SIZE_SMALL}px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {Colors.BG_MEDIUM}; border-color: {Colors.ACCENT_PRIMARY};"
            f"}}"
        )
        self.btn_store.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_store.clicked.connect(self.open_store_requested.emit)
        title_row.addWidget(self.btn_store)
        # ------------------------

        self.btn_return_hub = QPushButton("🏠 Return to Hub")
        self.btn_return_hub.setStyleSheet(
            f"QPushButton {{"
            f"  background: {Colors.BG_MEDIUM}; border: 1px solid {Colors.BORDER};"
            f"  border-radius: 5px; padding: 6px 14px; margin-left: 20px;"
            f"  color: {Colors.FG_PRIMARY}; font-size: {Fonts.SIZE_SMALL}px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {Colors.ACCENT_PRIMARY}; color: {Colors.BG_DARKEST};"
            f"}}"
        )
        self.btn_return_hub.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_return_hub.clicked.connect(self.return_to_hub_requested.emit)
        title_row.addWidget(self.btn_return_hub)

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

        # Save the grid layout to 'self' so we can populate it dynamically
        self.grid = QGridLayout()
        self.grid.setSpacing(14)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)
        self.grid.setColumnStretch(2, 1)

        # Notice: NO HARDCODED MODULE CARDS HERE ANYMORE!

        content_layout.addLayout(self.grid)
        content_layout.addStretch()

        hint = QLabel("Click an available module to begin  ·  More modules coming soon")
        hint.setStyleSheet(
            f"font-size: {Fonts.SIZE_SMALL}px; color: {Colors.FG_DISABLED};"
        )
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(hint)

        root.addWidget(content, stretch=1)

    def populate_modules(self, manifests: list[dict]) -> None:
        """Dynamically build the selection grid based on installed plugins."""
        # Clear any existing buttons
        for i in reversed(range(self.grid_layout.count())): 
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        if not manifests:
            lbl = QLabel("No analysis modules installed. Use the Module Manager to download plugins.")
            lbl.setStyleSheet(f"color: {Colors.FG_DISABLED}; font-style: italic;")
            self.grid_layout.addWidget(lbl, 0, 0)
            return

        # Build buttons from manifests
        for i, manifest in enumerate(manifests):
            icon = manifest.get("icon", "📦")
            name = manifest.get("name", "Unknown Module")
            desc = manifest.get("description", "")

            btn = QPushButton(f"{icon}  {name}\n\n{desc}")
            btn.setStyleSheet(
                f"QPushButton {{"
                f"  background: {Colors.BG_DARK}; border: 1px solid {Colors.BORDER};"
                f"  border-radius: 8px; padding: 20px; text-align: left;"
                f"  color: {Colors.FG_PRIMARY}; font-size: 14px; font-weight: bold;"
                f"}}"
                f"QPushButton:hover {{ background: {Colors.BG_MEDIUM}; border-color: {Colors.ACCENT_PRIMARY}; }}"
            )
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            # Use a lambda to pass the specific manifest when clicked
            btn.clicked.connect(lambda checked, m=manifest: self.module_selected.emit(m))

            self.grid_layout.addWidget(btn, i // 2, i % 2) # 2 columns

    def populate_modules(self, manifests: list[dict]) -> None:
        """Dynamically build the selection grid based on installed plugins."""
        # 1. Clear any existing widgets in the grid
        for i in reversed(range(self.grid.count())): 
            widget = self.grid.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # 2. Handle empty state
        if not manifests:
            lbl = QLabel("No analysis modules installed. Use the Hub to download plugins.")
            lbl.setStyleSheet(f"color: {Colors.FG_DISABLED}; font-style: italic;")
            self.grid.addWidget(lbl, 0, 0)
            return

        # 3. Build a ModuleCard for every manifest
        for i, manifest in enumerate(manifests):
            icon = manifest.get("icon", "📦")
            title = manifest.get("name", "Unknown Module")
            desc = manifest.get("description", "")

            # Create your custom UI card
            card = ModuleCard(
                icon=icon,
                title=title,
                description=desc,
                badge="Installed",
                enabled=True,
            )
            
            # Wire the click to emit the specific manifest
            card.clicked.connect(lambda *args, m=manifest: self.module_selected.emit(m))
                        
            # Calculate grid position (3 columns wide)
            row = i // 3
            col = i % 3
            self.grid.addWidget(card, row, col)