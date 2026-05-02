import json
import os
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class WorkflowManager:
    """Manages scientific workflows stored as JSON in the project workspace."""
    
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.wf_dir = self.project_dir / "workflows"

    def save(self, module_id: str, payload: dict, metadata: dict) -> str:
        """Saves an aggregated module payload as a JSON workflow."""
        self.wf_dir.mkdir(exist_ok=True)

        safe_name = "".join([c for c in metadata["name"] if c.isalnum() or c == ' '])
        safe_name = safe_name.replace(" ", "_").lower() or "untitled_workflow"

        filepath = self.wf_dir / f"{safe_name}.json"
        counter = 1
        while filepath.exists():
            filepath = self.wf_dir / f"{safe_name}_{counter}.json"
            counter += 1

        metadata["module"] = module_id
        workflow_data = {"metadata": metadata, "payload": payload}

        with open(filepath, 'w') as f:
            json.dump(workflow_data, f, indent=4)
            
        return str(filepath.name)

    def list_all(self) -> List[dict]:
        """Scans the workflows directory and returns metadata."""
        if not self.wf_dir.exists():
            return []
            
        workflows = []
        for file in self.wf_dir.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    meta = data.get("metadata", {})
                    meta["filename"] = file.name
                    workflows.append(meta)
            except: pass
                
        workflows.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return workflows

    def load_payload(self, filename: str) -> dict:
        """Extracts the exact scientific payload."""
        filepath = self.wf_dir / filename
        if not filepath.exists(): return {}
            
        with open(filepath, 'r') as f:
            data = json.load(f)
            return data.get("payload", {})
        
    def delete(self, filename: str) -> bool:
        """Deletes a saved workflow JSON file."""
        file_path = self.wf_dir / os.path.basename(filename)
        try:
            if file_path.exists() and file_path.is_file():
                os.remove(file_path)
                return True
        except Exception as e:
            logger.error(f"Failed to delete workflow {filename}: {e}")
        return False
