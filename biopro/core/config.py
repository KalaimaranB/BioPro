"""Global application configuration and recent project tracking."""

import json
from pathlib import Path
from typing import List

class AppConfig:
    """Manages global settings stored in the user's home directory."""
    
    def __init__(self):
        self.config_dir = Path.home() / ".biopro"
        self.config_file = self.config_dir / "config.json"
        self.data = {"recent_projects": []}
        self._load()

    def _load(self) -> None:
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    self.data = json.load(f)
            except Exception:
                pass

    def save(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w") as f:
            json.dump(self.data, f, indent=4)

    def add_recent_project(self, project_path: Path | str) -> None:
        """Push a project to the top of the recents list."""
        path_str = str(Path(project_path).absolute())
        recent: List[str] = self.data.get("recent_projects", [])
        
        # If it's already in the list, remove it so we can push it to the top
        if path_str in recent:
            recent.remove(path_str)
            
        recent.insert(0, path_str)
        
        # Keep only the top 10 recent projects
        self.data["recent_projects"] = recent[:10]
        self.save()

    def get_recent_projects(self) -> List[str]:
        """Return a list of absolute paths to recent projects."""
        return self.data.get("recent_projects", [])