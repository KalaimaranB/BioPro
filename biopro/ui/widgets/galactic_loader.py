from pathlib import Path

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtQuickWidgets import QQuickWidget

from biopro.ui.theme import Colors, theme_manager


class GalacticLoader(QQuickWidget):
    """A cinematic Galactic hyperspace loading screen using QML.

    This replaces the old QWidget/paintEvent subprocess loader. By using
    QML and a QQuickWidget, the scene graph renders on a dedicated C++ thread,
    remaining buttery smooth (60fps) even when the main Python thread is blocked
    by heavy GIL-locking imports (e.g., pandas/numpy).
    """

    warp_out_finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Transparent background for the widget itself
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setClearColor(Qt.GlobalColor.transparent)
        self.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)

        # Load the QML file
        qml_path = Path(__file__).parent / "galactic_loader.qml"
        self.setSource(QUrl.fromLocalFile(str(qml_path)))

        # Connect to theme changes
        theme_manager.theme_changed.connect(self.update_colors)

        # Connect the QML signal back to our Python signal
        root = self.rootObject()
        if root:
            root.warpOutFinished.connect(self.warp_out_finished.emit)
            self.update_colors()

    def update_colors(self):
        """Update QML properties with current theme colors."""
        root = self.rootObject()
        if not root:
            return

        bg_color = Colors.BG_DARKEST
        is_sw = "Galactic" in theme_manager.current_theme_name
        is_dark_side = is_sw and getattr(Colors, "DNA_PRIMARY", "").upper() == "#E60000"

        accent = Colors.ACCENT_PRIMARY
        if is_sw:
            accent = Colors.ACCENT_PRIMARY if not is_dark_side else Colors.DNA_PRIMARY

        text_color = Colors.FG_PRIMARY

        # QML requires standard hex codes, sometimes without alpha or properly formatted
        root.setProperty("bgColor", bg_color)
        root.setProperty("accentColor", accent)
        root.setProperty("textColor", text_color)

    def set_module(self, name: str):
        """Reset the loader for a new module."""
        root = self.rootObject()
        if root:
            root.setProperty("moduleName", name)
            import PyQt6.QtCore as QtCore

            QtCore.QMetaObject.invokeMethod(root, "reset")

    def warp_out(self):
        """Begin the cinematic warp-out sequence."""
        root = self.rootObject()
        if root:
            import PyQt6.QtCore as QtCore

            QtCore.QMetaObject.invokeMethod(root, "warpOut")


if __name__ == "__main__":
    import sys

    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    loader = GalacticLoader()
    loader.set_module("Test Module")
    loader.resize(1000, 700)
    loader.show()

    # Test warp out after 3 seconds
    from PyQt6.QtCore import QTimer

    QTimer.singleShot(3000, loader.warp_out)

    sys.exit(app.exec())
