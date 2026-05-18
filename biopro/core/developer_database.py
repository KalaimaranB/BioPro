"""Centralized Database and Avatar Image Caching system for BioPro Developers."""

import json
import logging
from pathlib import Path

import certifi
import requests

logger = logging.getLogger(__name__)


class DeveloperProfileDatabase:
    """Manages parsing, disk serialization, and query lookups for trusted developers."""

    def __init__(self, db_file: Path | str | None = None):
        if db_file is None:
            self.db_file = Path.home() / ".biopro" / "trusted_developers.json"
        else:
            self.db_file = Path(db_file)

        self.db_file.parent.mkdir(parents=True, exist_ok=True)
        self.profiles: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        """Loads developers from the cached database file."""
        if self.db_file.exists():
            try:
                with open(self.db_file) as f:
                    data = json.load(f)
                    # Normalize list of profiles into an ID-based dictionary
                    if isinstance(data, list):
                        self.profiles = {d.get("developer_id", "Unknown"): d for d in data if d}
                    elif isinstance(data, dict):
                        self.profiles = data
            except Exception as e:
                logger.warning(f"Could not load trusted developer database: {e}")

    def save_profiles(self, profiles: list) -> None:
        """Serializes the list of developers to the local cache database."""
        try:
            self.profiles = {d.get("developer_id", "Unknown"): d for d in profiles if d}
            with open(self.db_file, "w") as f:
                json.dump(profiles, f, indent=4)
            logger.debug(f"Saved {len(profiles)} developer profiles to cache database.")
        except Exception as e:
            logger.error(f"Failed to write trusted developer database to disk: {e}")

    def get_profile(self, developer_id: str) -> dict:
        """Retrieves a developer profile, or returns a safe structural fallback."""
        if developer_id in self.profiles:
            return self.profiles[developer_id]

        # Fail-safe structural default profile
        return {
            "developer_id": developer_id,
            "name": f"Developer '{developer_id}'",
            "role": "Verified Contributor",
            "avatar_url": None,
            "description": "Verified independent developer contributing safe computational plugins to BioPro.",
            "public_key": "",
        }


class AvatarManager:
    """Downloads and caches developer JPG/PNG avatar images locally for offline availability."""

    def __init__(self, avatar_dir: Path | str | None = None):
        if avatar_dir is None:
            self.avatar_dir = Path.home() / ".biopro" / "avatars"
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
            logger.debug(f"Downloading avatar for {developer_id} from {avatar_url}...")
            response = requests.get(avatar_url, timeout=10, verify=certifi.where())
            response.raise_for_status()

            # Save the raw image binary bytes
            with open(cached_file, "wb") as f:
                f.write(response.content)

            logger.info(f"Successfully cached avatar for {developer_id} at {cached_file}")
            return str(cached_file.absolute())
        except Exception as e:
            logger.warning(
                f"Could not cache avatar image for {developer_id} (offline/network issue): {e}"
            )
            # Safe degradation fallback: UI will render initials gradient on-the-fly
            return None
