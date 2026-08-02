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
        """Initialize application configuration paths and load persisted settings."""
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
        """Load persisted configuration data and merge it with the current defaults.

        If the configuration file cannot be loaded, an error is reported.
        """
        if self.config_file.exists():
            data = AtomicJsonFile.load(self.config_file, default=None)
            if data is None or not isinstance(data, dict):
                from biopro.core.diagnostics import diagnostics

                diagnostics.report_error(f"Failed to load config from {self.config_file}")
            else:
                # Normalize loaded fields before merging
                recent = data.get("recent_projects", [])
                data["recent_projects"] = (
                    [x for x in recent if isinstance(x, str)] if isinstance(recent, list) else []
                )

                if "skipped_update_version" in data:
                    skipped = data.get("skipped_update_version")
                    data["skipped_update_version"] = skipped if isinstance(skipped, str) else None

                self.data.update(data)

    def save(self) -> None:
        """Persist the application configuration to disk."""
        if not AtomicJsonFile.save(self.config_file, self.data):
            from biopro.core.diagnostics import diagnostics

            diagnostics.report_error(f"Failed to save config to {self.config_file}")

    def add_recent_project(self, project_path: Path | str) -> None:
        """Add a project to the recent-projects list.

        The project path is stored as an absolute path, moved to the front of the list, and the
        list is limited to 10 entries.

        Parameters:
            project_path (Path | str): Path of the project to add.
        """
        path_str = str(Path(project_path).absolute())

        recent = self.data.get("recent_projects", [])
        if not isinstance(recent, list):
            recent = []

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

        recent = self.data.get("recent_projects", [])
        return cast(list[str], recent) if isinstance(recent, list) else []

    def remove_recent_project(self, project_path: Path | str) -> None:
        """Remove a project from the recent projects list and persist the updated configuration.

        Parameters:
            project_path (Path | str): Path of the project to remove.
        """
        path_str = str(Path(project_path).absolute())

        recent = self.data.get("recent_projects", [])
        if not isinstance(recent, list):
            return

        if path_str in recent:
            recent.remove(path_str)
            self.data["recent_projects"] = recent
            self.save()

    def get_skipped_update_version(self) -> str | None:
        """Get the version string the user chose to skip.

        Returns:
            str | None: The skipped update version, or None if no version is set.
        """
        skipped = self.data.get("skipped_update_version")
        return skipped if isinstance(skipped, str) else None

    def set_skipped_update_version(self, version: str) -> None:
        """Persist the update version to skip."""
        self.data["skipped_update_version"] = version
        self.save()
