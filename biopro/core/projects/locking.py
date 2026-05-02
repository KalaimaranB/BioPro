import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ProjectLockedError(Exception):
    """Raised when trying to open a project that is currently in use."""
    pass

class ProjectLock:
    """Handles project-level file locking to prevent concurrent access."""
    
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.lock_file = self.project_dir / ".biopro.lock"

    def acquire(self) -> None:
        """Create a lock file containing the current Process ID (PID)."""
        if self.lock_file.exists():
            try:
                with open(self.lock_file, "r") as f:
                    pid = int(f.read().strip())
                # Check if process is alive
                os.kill(pid, 0) 
                raise ProjectLockedError(f"Project is currently open in another BioPro instance (PID: {pid}).")
            except (OSError, ValueError):
                logger.warning("Found stale lock file. Overriding.")
                self.lock_file.unlink()

        with open(self.lock_file, "w") as f:
            f.write(str(os.getpid()))

    def release(self) -> None:
        """Remove the lock file."""
        if self.lock_file.exists():
            self.lock_file.unlink()
