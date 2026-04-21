"""Local Trust Overrides for BioPro.

Allows users to manually 'Verify' and trust locally modified plugins
on their specific machine, overriding standard signature checks.
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Optional, Set

class LocalTrustRegistry:
    """Manages a registry of user-approved plugin snapshots."""
    
    def __init__(self):
        self.config_dir = Path.home() / ".biopro"
        self.storage_path = self.config_dir / "trust_overrides.json"
        self._data: Dict[str, Dict[str, str]] = {}
        self._load()

    def _load(self):
        """Load stored overrides from disk."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r") as f:
                    self._data = json.load(f)
            except Exception:
                self._data = {}

    def save(self):
        """Persist overrides to disk."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w") as f:
            json.dump(self._data, f, indent=4)

    def is_locally_trusted(self, plugin_id: str, current_hashes: Dict[str, str]) -> bool:
        """Check if the current state of a plugin matches a trusted local snapshot."""
        if plugin_id not in self._data:
            return False
            
        stored_snapshot = self._data[plugin_id]
        
        # All files in the snapshot must match the current state
        if stored_snapshot != current_hashes:
            return False
            
        return True

    def trust_current_state(self, plugin_id: str, current_hashes: Dict[str, str]):
        """Record the current state as trusted for this machine."""
        self._data[plugin_id] = current_hashes
        self.save()

    def remove_trust(self, plugin_id: str):
        """Remove a local trust override."""
        if plugin_id in self._data:
            del self._data[plugin_id]
            self.save()
