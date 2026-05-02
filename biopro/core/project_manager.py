"""Compatibility shim for ProjectManager.
Relocated to biopro.core.projects.manager for SOLID compliance.
"""

from biopro.core.projects.manager import ProjectManager
from biopro.core.projects.locking import ProjectLockedError

__all__ = ["ProjectManager", "ProjectLockedError"]