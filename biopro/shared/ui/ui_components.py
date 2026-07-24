import warnings

warnings.warn(
    "Importing UI components from `biopro.shared.ui.ui_components` is deprecated and will be removed in a future version. "
    "Please import from `biopro_sdk.plugin.components` instead.",
    DeprecationWarning,
    stacklevel=2,
)

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtWidgets import QFrame, QLabel, QPushButton  # noqa: E402


class PrimaryButton(QPushButton):
    """The main action button (accent color)."""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("PrimaryButton")


class SecondaryButton(QPushButton):
    """The standard outline/cancel button."""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("SecondaryButton")


class ModuleCard(QFrame):
    """A standardized, interactive card for lists and grids."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("BioCard")
        self.setObjectName("BioCard")


class HeaderLabel(QLabel):
    """Standardized H1 Header."""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setObjectName("HeaderLabel")


class DangerButton(QPushButton):
    """The standard destructive/remove button."""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("DangerButton")
