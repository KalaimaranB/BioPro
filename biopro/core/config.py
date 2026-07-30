"""Core module."""

import logging
from pathlib import Path

from biopro.core.utils import AtomicJsonFile

logger = logging.getLogger(__name__)


class AppConfig:
    """Manages global settings stored in the user's home directory."""

    from biopro import __version__ as CORE_VERSION  # noqa: N812

    REGISTRY_URL = (
        "https://raw.githubusercontent.com/KalaimaranB/BioPro-Distribution/main/registry.json"
    )
    AUTHORITY_REGISTRY_URL = (
        "https://raw.githubusercontent.com/KalaimaranB/BioPro-Distribution/main/authorities.json"
    )

    APP_DATA_DIR = Path.home() / ".biopro"

    def __init__(self) -> None:
        """Documentation."""
        # We re-evaluate Path.home() here so that pytest monkeypatching works correctly.
        self.config_dir = Path.home() / ".biopro"
        self.config_file = self.config_dir / "config.json"
        self.data = {"recent_projects": [], "ai_enabled": True}
        self._load()

    @staticmethod
    def get_docs_dir() -> Path:
        """Returns the absolute path to the core docs directory."""
        return Path(__file__).parents[2] / "docs"

    def _load(self) -> None:
        if self.config_file.exists():
            data = AtomicJsonFile.load(self.config_file, default=None)
            if data is None:
                from biopro.core.diagnostics import diagnostics

                diagnostics.report_error(f"Failed to load config from {self.config_file}")
            else:
                # Merge the loaded data with defaults instead of overwriting completely
                self.data.update(data)

    def save(self) -> None:
        """Documentation."""
        if not AtomicJsonFile.save(self.config_file, self.data):
            from biopro.core.diagnostics import diagnostics

            diagnostics.report_error(f"Failed to save config to {self.config_file}")

    def add_recent_project(self, project_path: Path | str) -> None:
        """Push a project to the top of the recents list."""
        path_str = str(Path(project_path).absolute())
        from typing import cast

        recent: list[str] = cast(list[str], self.data.get("recent_projects", []))

        # If it's already in the list, remove it so we can push it to the top
        if path_str in recent:
            recent.remove(path_str)

        recent.insert(0, path_str)

        # Keep only the top 10 recent projects
        self.data["recent_projects"] = recent[:10]
        self.save()

    def get_recent_projects(self) -> list[str]:
        """Return a list of absolute paths to recent projects."""
        from typing import cast

        return cast(list[str], self.data.get("recent_projects", []))

    def remove_recent_project(self, project_path: Path | str) -> None:
        """Remove a project from the recents list."""
        path_str = str(Path(project_path).absolute())
        from typing import cast

        recent: list[str] = cast(list[str], self.data.get("recent_projects", []))
        if path_str in recent:
            recent.remove(path_str)
            self.data["recent_projects"] = recent
            self.save()

    def get_skipped_update_version(self) -> str | None:
        """Return the version string the user last chose to skip, or None."""
        from typing import cast

        return cast(str | None, self.data.get("skipped_update_version"))

    def set_skipped_update_version(self, version: str) -> None:
        """Persist the version the user wants to skip so the banner won't re-appear."""
        self.data["skipped_update_version"] = version
        self.save()
