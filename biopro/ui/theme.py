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
    DNA_PRIMARY = "#00f2ff"  # Default Cyan
    DNA_SECONDARY = "#a371f7"  # Default Purple
    FG_DISABLED = "#484f58"
    BORDER = "#30363d"
    BORDER_FOCUS = "#58a6ff"
    ACCENT_PRIMARY = "#2f81f7"
    ACCENT_PRIMARY_HOVER = "#388bfd"
    ACCENT_PRIMARY_PRESSED = "#0550ae"
    ACCENT_SUCCESS = "#238636"
    ACCENT_WARNING = "#d29922"
    ACCENT_DANGER = "#f85149"
    ACCENT_CRITICAL = "#f85149"  # Aliased to Danger for now
    BORDER = "#30363d"
    BORDER_DARK = "#21262d"  # Aliased to Medium
    BORDER_LIGHT = "#484f58"
    BORDER_FOCUS = "#58a6ff"
    BG_DARKER = "#0d1117"  # Aliased to Darkest
    CHART_COLORS = ["#58a6ff", "#3fb950", "#d29922", "#f85149", "#a371f7", "#f778ba"]

    # --- NEW: Enhanced Theme Properties ---
    GLOW_COLOR = "transparent"
    SCANLINE_OPACITY = 0.0
    # --------------------------------------


class _Fonts:
    """Standardized typography scales."""

    SIZE_SMALL = 11
    SIZE_NORMAL = 13
    SIZE_LARGE = 18
    SIZE_XLARGE = 24

    # --- NEW: Font Families ---
    FAMILY_HEADINGS = "Arial, sans-serif"
    FAMILY_UI = "Arial, sans-serif"
    FAMILY_MONO = "Monaco, 'Courier New', monospace"
    # ---------------------------

    # Standardized QFont Objects (initialized on first access or manually)
    @property
    def H1(self):
        from PyQt6.QtGui import QFont

        f = QFont(self.FAMILY_HEADINGS, self.SIZE_XLARGE, QFont.Weight.Bold)
        return f

    @property
    def H2(self):
        from PyQt6.QtGui import QFont

        f = QFont(self.FAMILY_HEADINGS, self.SIZE_LARGE, QFont.Weight.Bold)
        return f

    @property
    def H3(self):
        from PyQt6.QtGui import QFont

        f = QFont(self.FAMILY_HEADINGS, self.SIZE_NORMAL, QFont.Weight.Bold)
        return f

    @property
    def BODY(self):
        from PyQt6.QtGui import QFont

        f = QFont(self.FAMILY_UI, self.SIZE_NORMAL)
        return f

    @property
    def CAPTION(self):
        from PyQt6.QtGui import QFont

        f = QFont(self.FAMILY_UI, self.SIZE_SMALL)
        return f


# Create singleton instances for static-like access
Fonts = _Fonts()


class Strings:
    """Theme-dependent text values."""

    TAGLINE = "Bio Analysis Made Simple"
    APP_TITLE = "BioPro — Bio Analysis"
    GREETING = "Good morning"  # Will be adjusted by time of day if default


class ThemeManager(QObject):
    """Pub/Sub Engine for dynamic theme switching."""

    # This signal will broadcast to the whole app when colors change
    theme_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.current_theme_name = "BioPro Default"
        self._last_color_map = self._get_current_color_map()

    def _get_current_color_map(self) -> dict[str, str]:
        """Snapshots all hex codes from the Colors class."""
        return {
            name: getattr(Colors, name).lower()
            for name in dir(Colors)
            if not name.startswith("_")
            and isinstance(getattr(Colors, name), str)
            and getattr(Colors, name).startswith("#")
        }

    def load_theme(self, theme_path: Path) -> bool:
        """Reads a theme.json and overwrites the Colors class globally.

        This method triggers a global style migration, scanning all active QWidgets
        and updating their stylesheets to reflect the new color palette.

        Args:
            theme_path (Path): Path to the JSON theme definition file.

        Returns:
            bool: True if the theme was loaded and applied successfully.
        """
        if not theme_path.exists():
            logger.error(f"Theme file not found: {theme_path}")
            return False

        try:
            with open(theme_path, encoding="utf-8") as f:
                data = json.load(f)

            # Snapshot BEFORE update
            old_map = self._get_current_color_map()

            self.current_theme_name = data.get("name", theme_path.stem)

            # Dynamically overwrite the attributes in the Colors and Fonts classes
            for key, value in data.items():
                if hasattr(Colors, key):
                    setattr(Colors, key, value)
                elif hasattr(Fonts, key):
                    setattr(Fonts, key, value)
                elif hasattr(Strings, key):
                    setattr(Strings, key, value)

            new_map = self._get_current_color_map()

            logger.info(f"Successfully loaded theme: {self.current_theme_name}")

            # Perform Global Smart Refresh
            # theme_changed is emitted inside the migration, after the last chunk finishes
            self._apply_global_style_migration(
                old_map, new_map, on_complete=self.theme_changed.emit
            )
            return True

        except Exception as e:
            logger.error(f"Failed to parse theme JSON {theme_path}: {e}")
            return False

    def discover_themes(self) -> list[tuple[str, Path]]:
        """Scans both user-space and internal themes directories, returning (Name, Path) tuples."""
        from biopro.core.resource_manager import resource_path

        user_themes_dir = Path.home() / ".biopro" / "themes"
        user_themes_dir.mkdir(parents=True, exist_ok=True)

        internal_themes_dir = resource_path("themes")

        themes = []
        seen_paths = set()

        # Scan directories
        for directory in [user_themes_dir, internal_themes_dir]:
            if directory and directory.exists():
                for theme_file in directory.glob("*.json"):
                    resolved = theme_file.resolve()
                    if resolved in seen_paths:
                        continue
                    seen_paths.add(resolved)
                    try:
                        with open(theme_file, encoding="utf-8") as f:
                            data = json.load(f)
                            name = data.get("name", theme_file.stem)
                            themes.append((name, theme_file))
                    except Exception:
                        pass

        # Ensure default is first if found
        themes.sort(key=lambda x: 0 if "Default" in x[0] else 1)
        return themes

    def _apply_global_style_migration(self, old_map: dict, new_map: dict, on_complete=None) -> None:
        """Recursively finds all widgets and replaces old hex codes with new ones.

        This 'Smart Refresh' mechanism allows for hot-swapping themes without
        restarting the application. It uses regex to precisely swap hex codes
        within existing QSS strings.

        Args:
            old_map (dict): The mapping of color names to hex codes before the change.
            new_map (dict): The mapping of color names to hex codes after the change.
        """
        import re

        from PyQt6.QtWidgets import QApplication, QWidget

        app = QApplication.instance()
        if not app:
            return

        # Prepare translation table (Case insensitive search)
        translations = []
        for name, old_hex in old_map.items():
            new_hex = new_map.get(name)
            if new_hex and old_hex != new_hex:
                # Compile regex for the hex code, ensuring it's not part of a larger word
                # but allowing for shorthand/longhand if we wanted (keeping it simple for now)
                pattern = re.compile(re.escape(old_hex), re.IGNORECASE)
                translations.append((pattern, new_hex))

        if not translations:
            return

        logger.info(f"Migrating styles for {len(translations)} color changes...")

        from biopro.ui.components.overlays import BioLoadingOverlay

        main_window = app.activeWindow()
        overlay = None
        if main_window:
            overlay = BioLoadingOverlay(main_window)
            overlay.set_text("Applying Theme...")
            overlay.start()
            app.processEvents()

        all_widgets = app.allWidgets()
        total_widgets = len(all_widgets)
        from PyQt6.QtCore import QTimer

        def process_chunk(start_idx):
            chunk_size = 30  # Process 30 widgets per frame to guarantee 60fps responsiveness
            end_idx = min(start_idx + chunk_size, total_widgets)

            for i in range(start_idx, end_idx):
                widget = all_widgets[i]

                try:
                    if not isinstance(widget, QWidget) or widget is overlay:
                        continue

                    qss = widget.styleSheet()
                    if not qss:
                        continue

                    original_qss = qss
                    for pattern, new_hex in translations:
                        qss = pattern.sub(new_hex, qss)

                    if qss != original_qss:
                        widget.setStyleSheet(qss)
                except RuntimeError:
                    # Widget was deleted in the middle of the async migration (e.g. tooltip, popup)
                    continue

            if end_idx < total_widgets:
                # Yield back to the main event loop, allowing the OS to breathe and the overlay to animate
                QTimer.singleShot(15, lambda: process_chunk(end_idx))
            else:
                if overlay:
                    overlay.stop()
                    overlay.deleteLater()

                # Re-inject app-level styles (QToolTip, QPalette) so they also reflect the new theme
                try:
                    from biopro_sdk.plugin.components import _apply_global_sdk_styles

                    _apply_global_sdk_styles()
                except Exception:
                    pass

                # Broadcast theme_changed AFTER migration is fully complete so all signal
                # handlers (e.g. _apply_styles) run while the overlay is already visible
                if on_complete:
                    on_complete()

        # Give the UI 50ms to render the overlay onto the screen before we start the heavy migration chunks
        QTimer.singleShot(50, lambda: process_chunk(0))


# Global singleton instance so the whole app shares one engine
theme_manager = ThemeManager()
