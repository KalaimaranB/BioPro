"""BioPro Project Management and Asset Tracking."""

import hashlib
import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from biopro.core.history_manager import HistoryManager

logger = logging.getLogger(__name__)

class ProjectLockedError(Exception):
    """Raised when trying to open a project that is currently in use."""
    pass

class ProjectManager:
    """Manages the BioPro project workspace, assets, and application state."""

    def __init__(self, project_dir: Path | str):
        self.project_dir = Path(project_dir)
        self.project_file = self.project_dir / "project.biopro"
        self.assets_dir = self.project_dir / "assets"
        self.lock_file = self.project_dir / ".biopro.lock"
        self.history_file = self.project_dir / "history.json"
        
        self.history_manager = HistoryManager()
        self.data: Dict[str, Any] = {} # Keep just the type-hinted one!

    # ── Project Lifecycle ─────────────────────────────────────────────

    def create_new(self, project_name: str) -> None:
        """Initialize a new project workspace."""
        if self.project_dir.exists():
            raise FileExistsError("Directory already exists.")
            
        self.project_dir.mkdir(parents=True)
        self.assets_dir.mkdir()

        self.data = {
            "project_name": project_name,
            "created_at": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat(),
            "assets": {},  # Format: { file_hash: { asset_metadata } }
            "analysis_state": {} # For saving UI/Pipeline state later
        }
        
        self.save()
        self._acquire_lock()
        logger.info(f"Created new project: {project_name}")

    def open_project(self) -> None:
        """Open an existing project and lock it."""
        if not self.project_file.exists():
            raise FileNotFoundError(f"Not a valid BioPro project: {self.project_file}")

        self._acquire_lock()

        with open(self.project_file, "r") as f:
            self.data = json.load(f)
        
        if self.history_file.exists():
            try:
                with open(self.history_file, "r") as f:
                    history_data = json.load(f)
                self.history_manager.load_all(history_data)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Could not load history.json: {e}")
            
        logger.info(f"Opened project: {self.data.get('project_name')}")

    def save(self) -> None:
        """Save current data to the project.biopro file."""
        self.data["last_modified"] = datetime.now().isoformat()
        with open(self.project_file, "w") as f:
            json.dump(self.data, f, indent=4)
        try:
            history_data = self.history_manager.serialize_all()
            with open(self.history_file, "w") as f:
                json.dump(history_data, f, indent=4)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to save history.json: {e}")

    def close(self) -> None:
        """Save and safely release the project lock."""
        self.save()
        self._release_lock()
        logger.info("Project closed and unlocked.")

    # ── Concurrency & Locking ─────────────────────────────────────────

    def _acquire_lock(self) -> None:
        """Create a lock file containing the current Process ID (PID)."""
        if self.lock_file.exists():
            # Check if the process that locked it is actually still running
            try:
                with open(self.lock_file, "r") as f:
                    pid = int(f.read().strip())
                # os.kill with signal 0 does not kill, just checks if process exists
                os.kill(pid, 0) 
                raise ProjectLockedError(f"Project is currently open in another BioPro instance (PID: {pid}).")
            except (OSError, ValueError):
                # The process crashed or PID is invalid. It's safe to steal the lock.
                logger.warning("Found stale lock file. Overriding.")
                self.lock_file.unlink()

        with open(self.lock_file, "w") as f:
            f.write(str(os.getpid()))

    def _release_lock(self) -> None:
        """Remove the lock file."""
        if self.lock_file.exists():
            self.lock_file.unlink()

    # ── Asset Management ──────────────────────────────────────────────

    def compute_hash(self, filepath: Path, chunk_size: int = 8192) -> str:
        """Compute SHA-256 hash of a file efficiently."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(chunk_size):
                sha256.update(chunk)
        return sha256.hexdigest()

    def add_image(self, filepath: Path | str, copy_to_workspace: bool) -> str:
        """
        Add an image to the project.
        Returns the hash of the file so the UI can reference it.
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Cannot find image: {filepath}")

        file_hash = self.compute_hash(filepath)

        # If we already have this exact file registered, just return its hash
        if file_hash in self.data["assets"]:
            logger.info("File already exists in project assets.")
            return file_hash

        local_path = None
        if copy_to_workspace:
            # Create a safe filename inside the assets folder
            dest_filename = f"{filepath.stem}_{file_hash[:8]}{filepath.suffix}"
            dest_path = self.assets_dir / dest_filename
            shutil.copy2(filepath, dest_path)
            
            # Store relative path for portability (the USB drive test)
            local_path = f"./assets/{dest_filename}"
            logger.info(f"Copied asset to workspace: {local_path}")
        else:
            logger.warning(f"Referencing external asset: {filepath}. If moved, the project may break.")

        self.data["assets"][file_hash] = {
            "original_path": str(filepath.absolute()),
            "local_path": local_path,
            "filename": filepath.name,
            "added_at": datetime.now().isoformat(),
            "copied_to_workspace": copy_to_workspace
        }

        self.save()
        return file_hash

    def get_asset_path(self, file_hash: str) -> Optional[Path]:
        """Resolve the best path to load an asset, preferring the local workspace copy."""
        asset = self.data["assets"].get(file_hash)
        if not asset:
            return None

        # 1. Try local workspace copy first
        if asset.get("local_path"):
            local = self.project_dir / asset["local_path"]
            if local.exists():
                return local

        # 2. Fallback to original external path
        original = Path(asset["original_path"])
        if original.exists():
            # If the user initially refused the copy but the external file is still there
            return original

        # 3. File is missing.
        logger.error(f"Asset missing! Hash: {file_hash}, File: {asset['filename']}")
        return None