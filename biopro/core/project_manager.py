"""Compatibility shim for ProjectManager.
Relocated to biopro.core.projects.manager for SOLID compliance.
"""

from biopro.core.projects.locking import ProjectLockedError
from biopro.core.projects.manager import ProjectManager

__all__ = ["ProjectManager", "ProjectLockedError"]
