"""Analysis toolbars."""

from biopro_sdk.plugin import SecondaryButton
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from biopro.ui.theme import Colors, Fonts, theme_manager


class AnalysisToolBar(QWidget):
    """Slim contextual toolbar shown above the analysis splitter."""

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("analysisToolBar")
        self.setStyleSheet(
            f"QWidget#analysisToolBar {{"
            f"  background: {Colors.BG_DARK};"
            f"  border-bottom: 1px solid {Colors.BORDER};"
            f"}}"
        )
        self.setFixedHeight(42)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 14, 0)
        layout.setSpacing(8)

        self.btn_close_project = SecondaryButton("🏠 Return to Hub")
        layout.addWidget(self.btn_close_project)

        self.btn_home = SecondaryButton("← Home")
        self.btn_home.setObjectName("btn_home")
        layout.addWidget(self.btn_home)

        self.btn_ai = SecondaryButton("🧠 AI Chat")
        layout.addWidget(self.btn_ai)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {Colors.BORDER};")
        layout.addWidget(sep)

        self.title_lbl = QLabel(f"🔬  {title}")
        self.title_lbl.setStyleSheet(
            f"font-size: {Fonts.SIZE_NORMAL}px; font-weight: 600;"
            f" color: {Colors.FG_PRIMARY}; background: transparent;"
        )
        layout.addWidget(self.title_lbl)
        layout.addStretch()

        theme_manager.theme_changed.connect(self._apply_theme_styles)
        self.btn_academy = SecondaryButton("🎓 Cyto Academy")
        self.btn_academy.setStyleSheet(
            f"background-color: {Colors.ACCENT_PRIMARY}; color: {Colors.FG_PRIMARY};"
            f" font-weight: bold; border-radius: 4px; padding: 4px 12px;"
        )
        layout.addWidget(self.btn_academy)

        self._apply_theme_styles()

    def set_title(self, icon: str, name: str) -> None:
        self.title_lbl.setText(f"{icon}  {name}")

    def _apply_theme_styles(self) -> None:
        self.setStyleSheet(
            f"QWidget#analysisToolBar {{"
            f"  background: {Colors.BG_DARK};"
            f"  border-bottom: 1px solid {Colors.BORDER};"
            f"}}"
        )
        self.title_lbl.setStyleSheet(
            f"font-size: {Fonts.SIZE_NORMAL}px; font-weight: 600;"
            f" color: {Colors.FG_PRIMARY}; background: transparent;"
        )
        self.btn_academy.setStyleSheet(
            f"background-color: {Colors.ACCENT_PRIMARY}; color: {Colors.FG_PRIMARY};"
            f" font-weight: bold; border-radius: 4px; padding: 4px 12px;"
        )
