import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class AppConfig:
    """Manages global settings stored in the user's home directory."""

    from biopro import __version__ as CORE_VERSION

    REGISTRY_URL = (
        "https://raw.githubusercontent.com/KalaimaranB/BioPro-Distribution/main/registry.json"
    )
    AUTHORITY_REGISTRY_URL = (
        "https://raw.githubusercontent.com/KalaimaranB/BioPro-Distribution/main/authorities.json"
    )

    def __init__(self):
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
            try:
                with open(self.config_file) as f:
                    self.data = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}")
                try:
                    from biopro.core.diagnostics import diagnostics

                    diagnostics.report_error(f"Failed to load app config: {e}", exception=e)
                except Exception:
                    pass

    def save(self) -> None:
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save config file: {e}")
            try:
                from biopro.core.diagnostics import diagnostics

                diagnostics.report_error(f"Failed to save app config: {e}", exception=e)
            except Exception:
                pass

    def add_recent_project(self, project_path: Path | str) -> None:
        """Push a project to the top of the recents list."""
        path_str = str(Path(project_path).absolute())
        recent: list[str] = self.data.get("recent_projects", [])

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

    def get_skipped_update_version(self) -> str | None:
        """Return the version string the user last chose to skip, or None."""
        return self.data.get("skipped_update_version")

    def set_skipped_update_version(self, version: str) -> None:
        """Persist the version the user wants to skip so the banner won't re-appear."""
        self.data["skipped_update_version"] = version
        self.save()
