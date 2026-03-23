"""Global Theme and Typography Engine."""

import json
import logging
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

class Colors:
    """Static class to hold current colors. Defaults to GitHub Dark."""
    BG_DARKEST = "#0d1117"
    BG_DARK = "#161b22"
    BG_MEDIUM = "#21262d"
    BG_LIGHT = "#30363d"
    FG_PRIMARY = "#c9d1d9"
    FG_SECONDARY = "#8b949e"
    DNA_PRIMARY = "#00f2ff"   # Default Cyan
    DNA_SECONDARY = "#a371f7" # Default Purple
    FG_DISABLED = "#484f58"
    BORDER = "#30363d"
    BORDER_FOCUS = "#58a6ff"
    ACCENT_PRIMARY = "#2f81f7"
    ACCENT_PRIMARY_HOVER = "#388bfd"
    ACCENT_PRIMARY_PRESSED = "#0550ae"
    SUCCESS = "#238636"
    ACCENT_WARNING = "#d29922"
    ACCENT_DANGER = "#f85149"
    CHART_COLORS = ["#58a6ff", "#3fb950", "#d29922", "#f85149", "#a371f7", "#f778ba"]


class Fonts:
    """Standardized typography scales."""
    SIZE_SMALL = 11
    SIZE_NORMAL = 13
    SIZE_LARGE = 18
    SIZE_XLARGE = 24


class ThemeManager(QObject):
    """Pub/Sub Engine for dynamic theme switching."""
    
    # This signal will broadcast to the whole app when colors change
    theme_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.current_theme_name = "BioPro Default"

    def load_theme(self, theme_path: Path) -> bool:
        """Reads a theme.json and overwrites the Colors class globally."""
        if not theme_path.exists():
            logger.error(f"Theme file not found: {theme_path}")
            return False

        try:
            with open(theme_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.current_theme_name = data.get("name", theme_path.stem)

            # Dynamically overwrite the attributes in the Colors class
            for key, value in data.items():
                if hasattr(Colors, key):
                    setattr(Colors, key, value)

            logger.info(f"Successfully loaded theme: {self.current_theme_name}")
            
            # Broadcast to the app that it's time to redraw!
            self.theme_changed.emit()
            return True

        except Exception as e:
            logger.error(f"Failed to parse theme JSON {theme_path}: {e}")
            return False

# Global singleton instance so the whole app shares one engine
theme_manager = ThemeManager()