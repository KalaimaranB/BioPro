"""Reusable UI Cards for BioPro."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout

from biopro.ui.theme import Colors, Fonts


class ModuleCard(QFrame):
    """Clickable card representing one analysis module."""

    clicked = pyqtSignal()
    trust_requested = pyqtSignal()
    trust_visual_requested = pyqtSignal()

    def __init__(
        self,
        icon: str,
        title: str,
        description: str,
        badge: str = "",
        enabled: bool = True,
        trust_level: str = "verified",
        trust_path: list | None = None,
        developer_name: str | None = None,
        developer_key: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._enabled = enabled
        self._trust_level = trust_level
        self._trust_path = trust_path
        self._developer_name = developer_name
        self._developer_key = developer_key
        self._title = title
        self.setObjectName("moduleCard")
        # Generate a unique tutorial_id based on the title so specific cards can be spotlighted
        safe_title = title.lower().replace(" ", "_")
        self.setProperty("tutorial_id", f"module_card_{safe_title}")

        self.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
        self.setMinimumSize(220, 150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 26px; background: transparent;")
        top_row.addWidget(icon_lbl)
        top_row.addStretch()

        if badge:
            badge_lbl = QLabel(badge)
            badge_lbl.setStyleSheet(
                f"background: {Colors.ACCENT_PRIMARY}; color: {Colors.BG_DARKEST}; border-radius: 5px; padding: 2px 7px; font-size: 10px; font-weight: 700;"
            )
            top_row.addWidget(badge_lbl)

        # Add Trust Indicator
        self.lock_btn = QPushButton()
        self.lock_btn.setFixedSize(24, 24)
        self.lock_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lock_btn.clicked.connect(self._on_lock_clicked)
        self._update_trust_ui()
        top_row.addWidget(self.lock_btn)

        if not enabled:
            soon_lbl = QLabel("Coming soon")
            soon_lbl.setStyleSheet(
                f"background: {Colors.BG_LIGHT}; color: {Colors.FG_DISABLED}; border-radius: 5px; padding: 2px 7px; font-size: 10px; font-weight: 600;"
            )
            top_row.addWidget(soon_lbl)

        layout.addLayout(top_row)

        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet(
            f"font-size: {Fonts.SIZE_LARGE}px; font-weight: 700; color: {Colors.FG_PRIMARY if enabled else Colors.FG_DISABLED}; background: transparent;"
        )
        layout.addWidget(self.title_lbl)

        self.desc_lbl = QLabel(description)
        self.desc_lbl.setStyleSheet(
            f"font-size: {Fonts.SIZE_SMALL}px; color: {Colors.FG_SECONDARY}; background: transparent;"
        )
        self.desc_lbl.setWordWrap(True)
        layout.addWidget(self.desc_lbl)

        layout.addStretch()
        self._apply_style(False)

    def _update_trust_ui(self):
        """Update the lock icon and style based on trust level."""
        if self._trust_level in ["verified_developer", "verified_cache"]:
            self.lock_btn.setText("🛡️")
            self.lock_btn.setToolTip("Verified via Trust Tree. Click to view chain.")
            self.lock_btn.setStyleSheet("background: transparent; border: none; font-size: 14px;")
        elif self._trust_level == "verified_local":
            self.lock_btn.setText("🔒")
            self.lock_btn.setToolTip("Verified Local Override (Manual Lock). Click to view.")
            self.lock_btn.setStyleSheet(
                f"background: transparent; border: none; font-size: 14px; color: {Colors.ACCENT_SUCCESS};"
            )
        else:
            self.lock_btn.setText("⚠️")
            self.lock_btn.setToolTip("Modified or Untrusted! Click to verify and lock.")
            self.lock_btn.setStyleSheet(
                f"background: transparent; border: 1px solid {Colors.ACCENT_DANGER}; border-radius: 4px; font-size: 14px;"
            )

    def _on_lock_clicked(self):
        """Logic for when the trust icon is clicked."""
        if self._trust_level == "untrusted":
            if self._developer_key and self._developer_name:
                from biopro.ui.dialogs.trust_acceptance_dialog import TrustAcceptanceDialog

                dialog = TrustAcceptanceDialog(
                    self._title, self._developer_name, self._developer_key, self
                )
                if dialog.exec() and dialog.is_accepted():
                    # Update card state instantly
                    self._trust_level = "verified_cache"  # Simulated local trust state
                    self._update_trust_ui()
                    self._apply_style(False)
            else:
                self.trust_requested.emit()
        else:
            # Show the visual tree!
            from biopro.ui.dialogs.trust_dialog import TrustTimelineDialog

            dialog = TrustTimelineDialog(self._title, self._trust_path or [], self)
            dialog.exec()

    def _apply_style(self, hovered: bool) -> None:
        if not self._enabled:
            self.setStyleSheet(
                f"QFrame#moduleCard {{ background: {Colors.BG_DARK}; border: 1px solid {Colors.BORDER}; border-radius: 10px; }}"
            )
            return

        # Highlight border if untrusted
        if self._trust_level == "untrusted":
            border = Colors.ACCENT_DANGER if hovered else Colors.ACCENT_DANGER + "88"
        else:
            border = Colors.ACCENT_PRIMARY if hovered else Colors.BORDER

        bg = Colors.BG_MEDIUM if hovered else Colors.BG_DARK
        self.setStyleSheet(
            f"QFrame#moduleCard {{ background: {bg}; border: 1.5px solid {border}; border-radius: 10px; }}"
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


class DashboardWorkflowCard(QFrame):
    """Clickable card representing a saved workflow with a settings button.

    When ``has_academy=True`` the card shows a 🎓 pill badge and a subtle blue
    left-border accent.  Clicking the pill emits ``academy_requested`` (independent
    from the card's main ``clicked`` signal).
    """

    clicked = pyqtSignal()
    settings_requested = pyqtSignal()
    academy_requested = pyqtSignal()

    def __init__(
        self,
        title: str,
        date_str: str,
        module_name: str,
        description: str = "",
        has_academy: bool = False,
        course_count: int = 0,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._has_academy = has_academy
        self.setObjectName("workflowCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(220, 130)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        # Top row: Module Name, Academy pill (optional), and Settings Button
        top_row = QHBoxLayout()
        mod_lbl = QLabel(module_name)
        mod_lbl.setStyleSheet(
            f"font-size: 10px; font-weight: bold; color: {Colors.ACCENT_PRIMARY}; background: transparent; text-transform: uppercase;"
        )
        top_row.addWidget(mod_lbl)
        top_row.addStretch()

        # Academy badge pill — shown only when courses are registered for this module
        self._academy_btn: QPushButton | None = None
        if has_academy:
            label = (
                f"🎓 {course_count} course" if course_count == 1 else f"🎓 {course_count} courses"
            )
            self._academy_btn = QPushButton(label)
            self._academy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._academy_btn.setStyleSheet(
                "QPushButton {"
                "  background: rgba(31, 111, 235, 0.18);"
                "  color: #79c0ff;"
                "  border: 1px solid #1f6feb;"
                "  border-radius: 8px;"
                "  padding: 1px 7px;"
                "  font-size: 10px;"
                "  font-weight: bold;"
                "}"
                "QPushButton:hover {"
                "  background: rgba(31, 111, 235, 0.35);"
                "}"
            )
            self._academy_btn.clicked.connect(self._on_academy_clicked)
            top_row.addWidget(self._academy_btn)

        self.btn_settings = QPushButton("⚙️")
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.setFixedSize(24, 24)
        self.btn_settings.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; border-radius: 4px; font-size: 14px; }}
            QPushButton:hover {{ background: {Colors.BG_LIGHT}; border: 1px solid {Colors.BORDER}; }}
        """)
        self.btn_settings.clicked.connect(self._on_settings_clicked)
        top_row.addWidget(self.btn_settings)
        layout.addLayout(top_row)

        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet(
            f"font-size: {Fonts.SIZE_LARGE}px; font-weight: 700; color: {Colors.FG_PRIMARY}; background: transparent;"
        )
        layout.addWidget(self.title_lbl)

        if description:
            self.desc_lbl = QLabel(description)
            self.desc_lbl.setStyleSheet(
                f"font-size: 11px; color: {Colors.FG_SECONDARY}; background: transparent;"
            )
            self.desc_lbl.setWordWrap(True)
            layout.addWidget(self.desc_lbl)

        self.date_lbl = QLabel(f"Saved: {date_str}")
        self.date_lbl.setStyleSheet(
            f"font-size: 10px; color: {Colors.FG_SECONDARY}; background: transparent;"
        )
        layout.addWidget(self.date_lbl)

        layout.addStretch()
        self._apply_style(False)

    def _on_settings_clicked(self) -> None:
        self.settings_requested.emit()

    def _on_academy_clicked(self) -> None:
        """Emits academy_requested without also triggering the card's main click."""
        self.academy_requested.emit()

    def _apply_style(self, hovered: bool) -> None:
        if self._has_academy:
            # Blue left-border accent when academy courses are available
            border_left = "#1f6feb"
            border = "#1f6feb" if hovered else "#1f6feb88"
            bg = Colors.BG_MEDIUM if hovered else Colors.BG_DARK
            self.setStyleSheet(
                f"QFrame#workflowCard {{"
                f"  background: {bg};"
                f"  border: 1px solid {border};"
                f"  border-left: 3px solid {border_left};"
                f"  border-radius: 8px;"
                f"}}"
            )
        else:
            border = Colors.FG_SECONDARY if hovered else Colors.BORDER
            bg = Colors.BG_MEDIUM if hovered else Colors.BG_DARK
            self.setStyleSheet(
                f"QFrame#workflowCard {{ background: {bg}; border: 1px solid {border}; border-radius: 8px; }}"
            )

    def enterEvent(self, event) -> None:
        self._apply_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._apply_style(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        pos = event.position().toPoint()
        # Ignore clicks on overlay buttons — they handle their own signals
        if self.btn_settings.geometry().contains(pos):
            super().mousePressEvent(event)
            return
        if self._academy_btn and self._academy_btn.geometry().contains(pos):
            super().mousePressEvent(event)
            return
        self.clicked.emit()
        super().mousePressEvent(event)


class DetailedWorkflowCard(QFrame):
    """A visual card representing a saved workflow with tags and load button."""

    def __init__(self, metadata: dict, on_load_callback):
        super().__init__()
        self.metadata = metadata
        self.setFrameShape(QFrame.Shape.StyledPanel)

        self.setStyleSheet(
            f"QFrame {{ "
            f"  background-color: {Colors.BG_MEDIUM}; "
            f"  border: 1px solid {Colors.BORDER}; "
            f"  border-radius: 8px; "
            f"  margin: 4px; "
            f"}}"
        )

        layout = QVBoxLayout(self)

        # Header: Name and Module Tag
        header = QHBoxLayout()
        name_lbl = QLabel(metadata.get("name", "Untitled"))
        name_lbl.setStyleSheet(
            f"font-weight: bold; font-size: 14px; color: {Colors.FG_PRIMARY}; border: none;"
        )

        mod_lbl = QLabel(metadata.get("module", "").replace("_", " ").upper())
        mod_lbl.setStyleSheet(
            f"color: {Colors.ACCENT_PRIMARY}; "
            f"font-size: 10px; "
            f"font-weight: bold; "
            f"border: 1px solid {Colors.ACCENT_PRIMARY}; "
            f"border-radius: 4px; "
            f"padding: 2px 4px;"
        )

        header.addWidget(name_lbl)
        header.addStretch()
        header.addWidget(mod_lbl)
        layout.addLayout(header)

        # Description
        desc = QLabel(metadata.get("description", "No description provided."))
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {Colors.FG_SECONDARY}; border: none;")
        layout.addWidget(desc)

        # Tags
        tags = metadata.get("tags", [])
        if tags:
            tag_str = "  ".join([f"#{t}" for t in tags])
            tag_lbl = QLabel(tag_str)
            tag_lbl.setStyleSheet(
                f"color: {Colors.FG_SECONDARY}; font-size: 11px; font-style: italic; border: none;"
            )
            layout.addWidget(tag_lbl)

        # Load Button
        self.btn_load = QPushButton("Open Workflow")
        self.btn_load.setCursor(header.itemAt(0).widget().cursor())  # Safety for cursor
        self.btn_load.clicked.connect(lambda: on_load_callback(metadata))
        layout.addWidget(self.btn_load)
