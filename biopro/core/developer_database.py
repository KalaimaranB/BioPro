"""Centralized Database and Avatar Image Caching system for BioPro Developers."""

import logging
from pathlib import Path

import certifi
import requests

from biopro.core.config import AppConfig
from biopro.core.utils import AtomicJsonFile

logger = logging.getLogger(__name__)


class DeveloperProfileDatabase:
    """Manages parsing, disk serialization, and query lookups for trusted developers."""

    def __init__(self, db_file: Path | str | None = None):
        """
        Initialize the developer profile database and load cached profiles from disk.
        
        Parameters:
        	db_file (Path | str | None): Optional path to the profile database file. Defaults to the application's trusted developer cache.
        """
        if db_file is None:
            self.db_file = AppConfig.APP_DATA_DIR / "trusted_developers.json"
        else:
            self.db_file = Path(db_file)

        self.db_file.parent.mkdir(parents=True, exist_ok=True)
        self.profiles: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        """Loads developers from the cached database file."""
        data = AtomicJsonFile.load(self.db_file)
        if data:
            if isinstance(data, list):
                self.profiles = {d.get("developer_id", "Unknown"): d for d in data if d}
            elif isinstance(data, dict):
                self.profiles = data

    def save_profiles(self, profiles: list) -> None:
        """Serializes the list of developers to the local cache database."""
        self.profiles = {d.get("developer_id", "Unknown"): d for d in profiles if d}
        if AtomicJsonFile.save(self.db_file, profiles):
            logger.debug(f"Saved {len(profiles)} developer profiles to cache database.")
        else:
            logger.error("Failed to write trusted developer database to disk.")

    def get_profile(self, developer_id: str) -> dict:
        """
        Retrieve a developer profile by identifier, providing a safe default profile when no match exists.
        
        Parameters:
        	developer_id (str): Identifier of the developer to retrieve.
        
        Returns:
        	dict: The matching profile, or a fallback profile containing the identifier and safe default metadata.
        """
        if developer_id in self.profiles:
            return self.profiles[developer_id]

        # Fail-safe structural default profile
        return {
            "developer_id": developer_id,
            "name": f"Developer '{developer_id}'",
            "role": "Verified Contributor",
            "avatar_url": None,
            "description": "Verified independent developer contributing safe computational plugins to BioPro.",  # noqa: E501
            "public_key": "",
        }


class AvatarManager:
    """Downloads and caches developer JPG/PNG avatar images locally for offline availability."""

    def __init__(self, avatar_dir: Path | str | None = None):
        """
        Initialize the avatar storage directory.
        
        Parameters:
        	avatar_dir (Path | str | None): Directory for cached avatars. Defaults to the application's avatar directory.
        """
        if avatar_dir is None:
            self.avatar_dir = AppConfig.APP_DATA_DIR / "avatars"
        else:
            self.avatar_dir = Path(avatar_dir)

        self.avatar_dir.mkdir(parents=True, exist_ok=True)

    def fetch_and_cache_avatar(self, developer_id: str, avatar_url: str | None) -> str | None:
        """Asynchronously downloads remote image binaries and saves them locally."""
        if not avatar_url:
            return None

        # Clean filename matching the developer's unique ID
        file_ext = avatar_url.split(".")[-1].split("?")[0].lower()
        if file_ext not in ["png", "jpg", "jpeg", "webp"]:
            file_ext = "png"  # Default fallback extension

        cached_file = self.avatar_dir / f"{developer_id}.{file_ext}"

        try:
            import shutil

            logger.debug("Downloading avatar image from remote source...")
            response = requests.get(avatar_url, stream=True, timeout=10, verify=certifi.where())
            response.raise_for_status()

            # Save the raw image binary bytes
            with open(cached_file, "wb") as f:
                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, f)

            logger.info("Successfully cached avatar image locally.")
            return str(cached_file.absolute())
        except Exception:
            logger.warning("Could not cache avatar image (offline/network issue)", exc_info=True)
            # Safe degradation fallback: UI will render initials gradient on-the-fly
            return None
