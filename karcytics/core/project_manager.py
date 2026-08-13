"""Compatibility shim for ProjectManager.

Relocated to karcytics.core.projects.manager for SOLID compliance.
"""

from karcytics.core.projects.locking import ProjectLockedError
from karcytics.core.projects.manager import ProjectManager

__all__ = ["ProjectManager", "ProjectLockedError"]
