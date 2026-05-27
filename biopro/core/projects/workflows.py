import json
import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


class WorkflowManager:
    """Manages scientific workflows stored as JSON in the project workspace."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.wf_dir = self.project_dir / "workflows"

    def save(
        self,
        module_id: str,
        payload: dict,
        metadata: dict,
        filename: str | None = None,
        attachments: list[dict] | None = None,
    ) -> str:
        """Saves an aggregated module payload as a JSON workflow."""
        self.wf_dir.mkdir(exist_ok=True)

        if filename:
            filepath = self.wf_dir / filename
            safe_name = filepath.stem
        else:
            safe_name = "".join([c for c in metadata["name"] if c.isalnum() or c == " "])
            safe_name = safe_name.replace(" ", "_").lower() or "untitled_workflow"

            filepath = self.wf_dir / f"{safe_name}.json"
            counter = 1
            while filepath.exists():
                filepath = self.wf_dir / f"{safe_name}_{counter}.json"
                counter += 1
                safe_name = filepath.stem

        metadata["module"] = module_id

        import typing

        workflow_data: dict[str, typing.Any] = {"metadata": metadata, "payload": payload}
        if attachments is not None:
            workflow_data["attachments"] = attachments

        temp_filepath = filepath.with_suffix(".tmp")
        with open(temp_filepath, "w") as f:
            json.dump(workflow_data, f, indent=4)

        temp_filepath.replace(filepath)

        return str(filepath.name)

    def attach_file(
        self,
        wf_filename: str,
        source_path: Path | str,
        key: str,
        description: str = "",
        mime_hint: str = "application/octet-stream",
    ) -> dict:
        """Copies an auxiliary file into the workflow's attachment folder and returns its record."""
        source_path = Path(source_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Attachment source not found: {source_path}")

        wf_filepath = self.wf_dir / wf_filename
        wf_stem = wf_filepath.stem
        att_dir = self.wf_dir / f"{wf_stem}_attachments"
        att_dir.mkdir(parents=True, exist_ok=True)

        dest_path = att_dir / source_path.name

        # Handle filename collisions within attachments directory
        counter = 1
        while dest_path.exists():
            dest_path = att_dir / f"{source_path.stem}_{counter}{source_path.suffix}"
            counter += 1

        shutil.copy2(source_path, dest_path)

        import hashlib

        sha256 = hashlib.sha256()
        with open(dest_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)

        rel_path = dest_path.relative_to(self.project_dir).as_posix()

        return {
            "key": key,
            "filename": dest_path.name,
            "relative_path": rel_path,
            "mime_hint": mime_hint,
            "description": description,
            "size_bytes": dest_path.stat().st_size,
            "sha256": sha256.hexdigest(),
        }

    def list_all(self) -> list[dict]:
        """Scans the workflows directory and returns metadata."""
        if not self.wf_dir.exists():
            return []

        workflows = []
        for file in self.wf_dir.glob("*.json"):
            try:
                with open(file) as f:
                    data = json.load(f)
                    meta = data.get("metadata", {})
                    meta["filename"] = file.name
                    workflows.append(meta)
            except:
                pass

        workflows.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return workflows

    def load_payload(self, filename: str) -> dict:
        """Extracts the exact scientific payload."""
        filepath = self.wf_dir / filename
        if not filepath.exists():
            return {}

        with open(filepath) as f:
            data = json.load(f)
            return data.get("payload", {})

    def load_attachments(self, filename: str) -> list[dict]:
        """Extracts the attachments manifest."""
        filepath = self.wf_dir / filename
        if not filepath.exists():
            return []

        with open(filepath) as f:
            data = json.load(f)
            return data.get("attachments", [])

    def delete(self, filename: str) -> bool:
        """Deletes a saved workflow JSON file."""
        file_path = self.wf_dir / os.path.basename(filename)
        att_dir = self.wf_dir / f"{file_path.stem}_attachments"

        try:
            if file_path.exists() and file_path.is_file():
                os.remove(file_path)

                # Delete attachments folder if it exists
                if att_dir.exists() and att_dir.is_dir():
                    shutil.rmtree(att_dir)

                return True
        except Exception as e:
            logger.error(f"Failed to delete workflow {filename}: {e}")
        return False

    def delete_attachment(self, filename: str, key: str) -> bool:
        """Deletes a specific attachment from a workflow and updates its manifest."""
        filepath = self.wf_dir / os.path.basename(filename)
        if not filepath.exists():
            return False

        try:
            with open(filepath) as f:
                data = json.load(f)

            attachments = data.get("attachments", [])
            target_att = None

            for att in attachments:
                if att.get("key") == key:
                    target_att = att
                    break

            if not target_att:
                return False

            # Remove from json and save
            attachments.remove(target_att)
            if not attachments:
                data.pop("attachments", None)
            else:
                data["attachments"] = attachments

            with open(filepath, "w") as f:
                json.dump(data, f, indent=4)

            # Delete physical file
            rel_path = target_att.get("relative_path")
            if rel_path:
                phys_path = self.project_dir / rel_path
                if phys_path.exists() and phys_path.is_file():
                    os.remove(phys_path)
            return True

        except Exception as e:
            logger.error(f"Failed to delete attachment {key} from {filename}: {e}")
            return False
