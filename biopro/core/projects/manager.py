import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from biopro.core.event_bus import BioProEvent, event_bus
from biopro.core.history_manager import HistoryManager
from biopro.core.projects.assets import AssetManager
from biopro.core.projects.locking import ProjectLock
from biopro.core.projects.workflows import WorkflowManager
from biopro.core.utils import AtomicJsonFile

logger = logging.getLogger(__name__)


class ProjectManager:
    """Orchestrates BioPro project operations by delegating to specialized managers."""

    def __init__(self, project_dir: Path | str):
        self.project_dir = Path(project_dir)
        self.project_file = self.project_dir / "project.biopro"
        self.assets_dir = self.project_dir / "assets"
        self.history_file = self.project_dir / "history.json"

        # Internal State
        self.data: dict[str, Any] = {}
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

    def create_new(self, project_name: str, is_academy: bool = False) -> None:
        if self.project_dir.exists():
            raise FileExistsError("Directory already exists.")

        self.project_dir.mkdir(parents=True)
        self.assets_dir.mkdir()

        self.data = {
            "project_name": project_name,
            "is_academy": is_academy,
            "created_at": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat(),
            "assets": {},
            "analysis_state": {},
        }

        self.save()
        self.locker.acquire()
        logger.info(f"Created new project: {project_name}")

    def open_project(self) -> None:
        try:
            if not self.project_file.exists():
                raise FileNotFoundError(f"Not a valid BioPro project: {self.project_file}")

            self.locker.acquire()

            try:
                self.data = AtomicJsonFile.load(self.project_file, default=None)
                if self.data is None:
                    raise FileNotFoundError
            except Exception as e:
                logger.error(
                    f"Project file corrupted or missing: {e}. Using default state.", exc_info=True
                )
                if not self.data:
                    self.data = {
                        "project_name": self.project_dir.name,
                        "assets": {},
                        "analysis_state": {},
                    }

            if self.history_file.exists():
                try:
                    history_data = AtomicJsonFile.load(self.history_file)
                    if history_data:
                        self.history_manager.load_all(history_data)
                except Exception as e:
                    logger.error(f"Could not load history.json: {e}", exc_info=True)

            self.validate_assets()
            logger.info(f"Opened project: {self.project_name}")
        except Exception as e:
            logger.error(f"Failed to open project: {e}", exc_info=True)
            raise e

    def save(self) -> None:
        try:
            self.data["last_modified"] = datetime.now().isoformat()

            # Atomic Save for Project File
            if not AtomicJsonFile.save(self.project_file, self.data):
                raise OSError("Failed to atomically save project data.")

            # Atomic Save for History
            try:
                history_data = self.history_manager.serialize_all()
                if not AtomicJsonFile.save(self.history_file, history_data):
                    raise OSError("Failed to atomically save history.")
            except Exception as e:
                logger.error(f"Failed to save history.json: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Failed to save project: {e}", exc_info=True)
            from biopro.core.diagnostics import diagnostics

            diagnostics.report_error(f"Failed to save project: {e}")
            raise e

    def close(self) -> None:
        self.save()
        self.locker.release()
        logger.info("Project closed and unlocked.")

    # ── Delegated Operations ──────────────────────────────────────────

    def add_image(
        self, filepath: Path | str, copy_to_workspace: bool, subfolder: str | None = None
    ) -> str:
        h = self.assets.add_image(self.data, filepath, copy_to_workspace, subfolder)
        self.save()
        return h

    def batch_add_images(
        self, filepaths: list[Path | str], copy_to_workspace: bool, subfolder: str | None = None
    ) -> list[str]:
        hashes = [
            self.assets.add_image(self.data, fp, copy_to_workspace, subfolder) for fp in filepaths
        ]
        self.save()
        return hashes

    def validate_assets(self) -> None:
        if self.assets.validate_assets(self.data):
            self.save()

    def get_asset_path(self, file_hash: str) -> Path | None:
        return self.assets.get_asset_path(self.data, file_hash)

    def save_workflow(
        self,
        module_id: str,
        payload: dict,
        metadata: dict,
        filename: str | None = None,
        attachments: list[dict] | None = None,
    ) -> str:
        result = self.workflows.save(module_id, payload, metadata, filename, attachments)
        event_bus.emit(BioProEvent.WORKFLOW_SAVED, result)
        return result

    def attach_workflow_file(
        self,
        wf_filename: str,
        source_path: Path | str,
        key: str,
        description: str = "",
        mime_hint: str = "application/octet-stream",
    ) -> dict:
        return self.workflows.attach_file(wf_filename, source_path, key, description, mime_hint)

    def get_attachment_path(self, wf_filename: str, key: str) -> Path | None:
        attachments = self.workflows.load_attachments(wf_filename)
        for att in attachments:
            if att.get("key") == key:
                rel_path = att.get("relative_path")
                if rel_path:
                    path = self.project_dir / rel_path
                    if path.exists():
                        return path
        return None

    def list_workflows(self) -> list[dict]:
        return self.workflows.list_all()

    def load_workflow_payload(self, filename: str) -> dict:
        return self.workflows.load_payload(filename)

    def get_workflow_hash(self, filename: str) -> str | None:
        return self.workflows.get_hash(filename)

    def delete_workflow(self, module_id: str, filename: str) -> bool:
        return self.workflows.delete(filename)

    def delete_workflow_attachment(self, filename: str, key: str) -> bool:
        return self.workflows.delete_attachment(filename, key)
