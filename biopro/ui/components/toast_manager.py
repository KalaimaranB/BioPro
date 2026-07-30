import logging

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer, pyqtSlot
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from biopro.core.event_bus import BioProEvent, event_bus

logger = logging.getLogger(__name__)


class ToastNotification(QWidget):
    """A single non-intrusive toast notification popup."""

    def __init__(self, message: str, parent=None, duration_ms: int = 4000):
        """
        Create a toast notification displaying the specified message.

        Parameters:
            message (str): Text to display in the notification.
            parent: Optional parent widget.
            duration_ms (int): Time in milliseconds before the notification begins fading out.
        """
        super().__init__(parent)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.ToolTip
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.setup_ui(message)

        # Setup fade out timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fade_out)
        self.timer.start(duration_ms)

        # Initial fade in
        self.setWindowOpacity(0.0)
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(250)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.anim.start()

    def setup_ui(self, message: str):
        """
        Build the toast layout and display the warning message with an icon.

        Parameters:
            message (str): Warning text to display.
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.container = QWidget(self)
        self.container.setObjectName("ToastContainer")
        self.container.setStyleSheet("""
            #ToastContainer {
                background-color: #2D2D2D;
                border: 1px solid #E5C07B; /* Warning yellow accent */
                border-radius: 8px;
            }
        """)

        inner_layout = QHBoxLayout(self.container)
        inner_layout.setContentsMargins(16, 12, 16, 12)
        inner_layout.setSpacing(12)

        icon_label = QLabel("⚠️")
        icon_label.setStyleSheet("font-size: 16px;")

        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("color: #E0E0E0; font-size: 13px; font-weight: 500;")

        inner_layout.addWidget(icon_label)
        inner_layout.addWidget(msg_label, 1)

        layout.addWidget(self.container)

        # Adjust size based on content
        self.adjustSize()

    def fade_out(self):
        """
        Fade out the toast notification and close it when the animation finishes.
        """
        self.anim.setDirection(QPropertyAnimation.Direction.Backward)
        self.anim.start()
        self.anim.finished.connect(self.close)


class ToastManager:
    """Manages system toast notifications and listens to the Event Bus."""

    _instance = None

    def __new__(cls):
        """
        Create and return the shared instance of the manager.

        Returns:
            ToastManager: The singleton manager instance.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """
        Initialize the toast manager and subscribe it to system warning events.
        """
        if self._initialized:
            return

        self._active_toasts = []
        event_bus.subscribe(BioProEvent.SYSTEM_WARNING, self._on_system_warning)
        self._initialized = True
        logger.info("ToastManager initialized.")

    @pyqtSlot(str)
    def _on_system_warning(self, message: str):
        """Display a system warning as a bottom-right toast notification, stacking it above visible toasts."""
        # Ensure we have a QApplication instance
        app = QApplication.instance()
        if not app:
            return

        # Clean up closed toasts
        self._active_toasts = [t for t in self._active_toasts if t.isVisible()]

        toast = ToastNotification(message)
        self._active_toasts.append(toast)

        # Position at the bottom right of the active window or screen
        active_window = app.activeWindow()
        if active_window:  # noqa: SIM108
            parent_rect = active_window.geometry()
        else:
            parent_rect = app.primaryScreen().geometry()

        # Calculate base position (bottom right with margin)
        margin = 20
        x = parent_rect.x() + parent_rect.width() - toast.width() - margin
        y = parent_rect.y() + parent_rect.height() - margin

        # Stack vertically if there are multiple active toasts
        for existing in self._active_toasts[:-1]:
            if existing.isVisible():
                y -= existing.height() + 10

        toast.move(x, y - toast.height())
        toast.show()


# Singleton accessor
toast_manager = ToastManager()
