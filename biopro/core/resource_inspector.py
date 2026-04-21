"""Resource Inspection Engine for BioPro.

Utilities for identifying 'Heavy' resources (large arrays, tensors, figures)
within arbitrary object trees. Enables automatic memory management.
"""

import logging
import sys
import io
from typing import Any, List, Set, Dict, Tuple

logger = logging.getLogger(__name__)

class ResourceInspector:
    """Detects and categorizes heavy resources for memory management."""
    
    # Threshold for considering an array/object as 'Heavy' (in bytes)
    # Default: 1MB
    HEAVY_THRESHOLD_BYTES = 1024 * 1024 

    @classmethod
    def get_heavy_resources(cls, obj: Any) -> List[Tuple[str, Any]]:
        """Scans the attributes of an object for heavy resources.
        
        Args:
            obj: The object to inspect (typically a PluginBase or PluginState instance)
            
        Returns:
            List of (attribute_name, resource_object) tuples.
        """
        heavy = []
        
        # We check both the __dict__ and any public properties
        try:
            items = []
            if hasattr(obj, "__dict__"):
                items.extend(obj.__dict__.items())
            elif isinstance(obj, dict):
                items.extend(obj.items())

            for name, value in items:
                if cls.is_heavy(value):
                    heavy.append((name, value))
        except Exception as e:
            logger.debug(f"Failed to inspect object {type(obj)}: {e}")
            
        return heavy

    @classmethod
    def is_heavy(cls, obj: Any) -> bool:
        """Determines if a single object is considered a heavy resource."""
        if obj is None:
            return False
            
        # 1. Numpy Arrays
        try:
            import numpy as np
            if isinstance(obj, np.ndarray):
                return obj.nbytes >= cls.HEAVY_THRESHOLD_BYTES
        except ImportError:
            pass

        # 2. Torch Tensors
        try:
            import torch
            if isinstance(obj, torch.Tensor):
                # Tensors on GPU are ALWAYS considered heavy/critical to release
                if obj.is_cuda:
                    return True
                # Large CPU tensors
                return (obj.element_size() * obj.nelement()) >= cls.HEAVY_THRESHOLD_BYTES
        except ImportError:
            pass

        # 3. Matplotlib Figures
        try:
            import matplotlib.figure
            if isinstance(obj, matplotlib.figure.Figure):
                return True # Figures are light in bytes but leak easily in memory
        except ImportError:
            pass

        # 4. Open File Handles
        if isinstance(obj, io.IOBase):
            return True

        return False

    @classmethod
    def get_object_hash(cls, obj: Any) -> str | None:
        """Generates a pseudo-hash for identifying identical heavy resources.
        
        This is used for structural sharing in the HistoryManager.
        Note: We prioritize speed over cryptographic perfection.
        """
        if obj is None:
            return None

        try:
            # For Numpy
            import numpy as np
            if isinstance(obj, np.ndarray):
                # Use data pointer and metadata for extremely fast identification
                # if the array is modified in place, this hash might be stale, 
                # but BioPro discourages in-place state mutation.
                return f"np:{id(obj)}:{obj.shape}:{obj.dtype}"
                
            # For Torch
            import torch
            if isinstance(obj, torch.Tensor):
                return f"torch:{id(obj)}:{obj.shape}:{obj.device}"
        except ImportError:
            pass

        return None
