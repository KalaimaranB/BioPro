import hashlib
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Union, Dict, Any

logger = logging.getLogger(__name__)

class AssetManager:
    """Manages project assets, hashing, and workspace consistency."""
    
    def __init__(self, project_dir: Path, assets_dir: Path):
        self.project_dir = project_dir
        self.assets_dir = assets_dir

    def compute_hash(self, filepath: Path, chunk_size: int = 8192) -> str:
        """Compute SHA-256 hash of a file efficiently."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(chunk_size):
                sha256.update(chunk)
        return sha256.hexdigest()

    def add_image(self, data: Dict[str, Any], filepath: Union[Path, str], copy_to_workspace: bool, subfolder: Optional[str] = None) -> str:
        """Add an image to the project data and return its hash."""
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Cannot find image: {filepath}")

        file_hash = self.compute_hash(filepath)

        # Skip if already exists and no upgrade needed
        if file_hash in data["assets"]:
            asset = data["assets"][file_hash]
            if not (copy_to_workspace and not asset.get("copied_to_workspace", False)):
                logger.info("File already exists in project assets.")
                return file_hash

        local_path = None
        if copy_to_workspace:
            target_dir = self.assets_dir
            if subfolder:
                target_dir = self.assets_dir / subfolder
                target_dir.mkdir(parents=True, exist_ok=True)

            dest_filename = f"{filepath.stem}_{file_hash[:8]}{filepath.suffix}"
            dest_path = target_dir / dest_filename
            shutil.copy2(filepath, dest_path)
            local_path = str(dest_path.relative_to(self.project_dir))
            logger.info(f"Copied asset to workspace: {local_path}")

        data["assets"][file_hash] = {
            "original_path": str(filepath.absolute()),
            "local_path": local_path,
            "filename": filepath.name,
            "added_at": datetime.now().isoformat(),
            "copied_to_workspace": copy_to_workspace
        }
        return file_hash

    def validate_assets(self, data: Dict[str, Any]) -> bool:
        """Checks all registered assets and removes records for missing files."""
        if "assets" not in data:
            return False

        to_remove = []
        for file_hash, asset in data["assets"].items():
            has_local = False
            if asset.get("local_path"):
                if (self.project_dir / asset["local_path"]).exists():
                    has_local = True
            
            has_original = False
            if asset.get("original_path"):
                if Path(asset["original_path"]).exists():
                    has_original = True
            
            if not has_local and not has_original:
                logger.warning(f"Removing record for missing asset: {asset.get('filename')}")
                to_remove.append(file_hash)
        
        for h in to_remove:
            del data["assets"][h]
            
        return len(to_remove) > 0

    def get_asset_path(self, data: Dict[str, Any], file_hash: str) -> Optional[Path]:
        """Resolve the best path to load an asset."""
        asset = data["assets"].get(file_hash)
        if not asset: return None

        if asset.get("local_path"):
            local = self.project_dir / asset["local_path"]
            if local.exists(): return local

        original = Path(asset["original_path"])
        if original.exists(): return original

        logger.error(f"Asset missing! Hash: {file_hash}")
        return None
