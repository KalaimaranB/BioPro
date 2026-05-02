import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

from biopro.core.history_manager import HistoryManager
from biopro.core.projects.locking import ProjectLock, ProjectLockedError
from biopro.core.projects.assets import AssetManager
from biopro.core.projects.workflows import WorkflowManager

logger = logging.getLogger(__name__)

class ProjectManager:
    """Orchestrates BioPro project operations by delegating to specialized managers."""

    def __init__(self, project_dir: Union[Path, str]):
        self.project_dir = Path(project_dir)
        self.project_file = self.project_dir / "project.biopro"
        self.assets_dir = self.project_dir / "assets"
        self.history_file = self.project_dir / "history.json"
        
        # Internal State
        self.data: Dict[str, Any] = {}
        self.history_manager = HistoryManager()
        
        # Specialized Managers
        self.locker = ProjectLock(self.project_dir)
        self.assets = AssetManager(self.project_dir, self.assets_dir)
        self.workflows = WorkflowManager(self.project_dir)

    @property
    def project_name(self) -> str:
        return self.data.get("project_name", self.project_dir.name)

    @property
    def config(self) -> dict:
        return self.data

    # ── Lifecycle ─────────────────────────────────────────────────────

    def create_new(self, project_name: str) -> None:
        if self.project_dir.exists():
            raise FileExistsError("Directory already exists.")
            
        self.project_dir.mkdir(parents=True)
        self.assets_dir.mkdir()

        self.data = {
            "project_name": project_name,
            "created_at": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat(),
            "assets": {},
            "analysis_state": {}
        }
        
        self.save()
        self.locker.acquire()
        logger.info(f"Created new project: {project_name}")

    def open_project(self) -> None:
        if not self.project_file.exists():
            raise FileNotFoundError(f"Not a valid BioPro project: {self.project_file}")

        self.locker.acquire()

        try:
            with open(self.project_file, "r") as f:
                self.data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"Project file corrupted or missing: {e}. Using default state.")
            if not self.data:
                self.data = {"project_name": self.project_dir.name, "assets": {}, "analysis_state": {}}
        
        if self.history_file.exists():
            try:
                with open(self.history_file, "r") as f:
                    self.history_manager.load_all(json.load(f))
            except Exception as e:
                logger.warning(f"Could not load history.json: {e}")
            
        self.validate_assets()
        logger.info(f"Opened project: {self.project_name}")

    def save(self) -> None:
        self.data["last_modified"] = datetime.now().isoformat()
        
        # Atomic Save for Project File
        temp_project = self.project_file.with_suffix(".tmp")
        with open(temp_project, "w") as f:
            json.dump(self.data, f, indent=4)
        os.replace(temp_project, self.project_file)
        
        # Atomic Save for History
        try:
            history_data = self.history_manager.serialize_all()
            temp_history = self.history_file.with_suffix(".tmp")
            with open(temp_history, "w") as f:
                json.dump(history_data, f, indent=4)
            os.replace(temp_history, self.history_file)
        except Exception as e:
            logger.error(f"Failed to save history.json: {e}")

    def close(self) -> None:
        self.save()
        self.locker.release()
        logger.info("Project closed and unlocked.")

    # ── Delegated Operations ──────────────────────────────────────────

    def add_image(self, filepath: Union[Path, str], copy_to_workspace: bool, subfolder: Optional[str] = None) -> str:
        h = self.assets.add_image(self.data, filepath, copy_to_workspace, subfolder)
        self.save()
        return h

    def batch_add_images(self, filepaths: List[Union[Path, str]], copy_to_workspace: bool, 
                          subfolder: Optional[str] = None) -> list[str]:
        hashes = [self.assets.add_image(self.data, fp, copy_to_workspace, subfolder) for fp in filepaths]
        self.save()
        return hashes

    def validate_assets(self) -> None:
        if self.assets.validate_assets(self.data):
            self.save()

    def get_asset_path(self, file_hash: str) -> Optional[Path]:
        return self.assets.get_asset_path(self.data, file_hash)
    
    def save_workflow(self, module_id: str, payload: dict, metadata: dict) -> str:
        return self.workflows.save(module_id, payload, metadata)

    def list_workflows(self) -> list[dict]:
        return self.workflows.list_all()

    def load_workflow_payload(self, filename: str) -> dict:
        return self.workflows.load_payload(filename)
        
    def delete_workflow(self, module_id: str, filename: str) -> bool:
        return self.workflows.delete(filename)
