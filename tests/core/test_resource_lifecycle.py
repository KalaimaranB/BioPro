"""Tests for Phase 5: Resource Lifecycle & RAII."""

import pytest
import numpy as np
import os
from biopro.core.resource_inspector import ResourceInspector
from biopro.core.history_manager import ModuleHistory

class TestResourceInspector:
    def test_detect_heavy_numpy(self):
        # 2MB array (Heavy)
        heavy_arr = np.zeros(1024 * 1024 // 4 * 2, dtype=np.float32)
        # 1KB array (Light)
        light_arr = np.zeros(1024 // 4, dtype=np.float32)
        
        assert ResourceInspector.is_heavy(heavy_arr) is True
        assert ResourceInspector.is_heavy(light_arr) is False

    def test_inspect_object(self):
        class MockPlugin:
            def __init__(self):
                self.image = np.zeros((1000, 1000)) # ~8MB
                self.threshold = 0.5 # Light
        
        plugin = MockPlugin()
        heavy_resources = ResourceInspector.get_heavy_resources(plugin)
        
        assert len(heavy_resources) == 1
        assert heavy_resources[0][0] == "image"

class TestHistoryDeduplication:
    """Verifies that the HistoryManager uses structural sharing to save RAM."""
    
    def test_automatic_deduplication(self):
        history = ModuleHistory("test_module")
        
        # 4MB image
        image_data = np.random.rand(1000, 500).astype(np.float32)
        
        # Scenario: User moves a slider, threshold changes but image stays the same
        state_1 = {"id": "test", "threshold": 0.1, "img": image_data}
        state_2 = {"id": "test", "threshold": 0.2, "img": image_data}
        
        history.push(state_1)
        history.push(state_2)
        
        # Verify both states are in history
        assert len(history.undo_stack) == 2
        
        # Verify the 'img' object is IDENTICAL in both history steps 
        # (Structural Sharing / Deduplication)
        # Note: If we used deepcopy (the old way), these would be different objects.
        h1 = history.undo_stack[0]["img"]
        h2 = history.undo_stack[1]["img"]
        
        assert h1 is h2 # Same memory address

    def test_rehydration_on_undo(self):
        history = ModuleHistory("test_module")
        image_data = np.zeros((10, 10)) # Mock heavy for test
        # Set a low threshold for the test to ensure it treats this as heavy
        ResourceInspector.HEAVY_THRESHOLD_BYTES = 10 
        
        state = {"img": image_data, "val": 1}
        history.push(state)
        history.push({"img": image_data, "val": 2})
        
        # Step back
        restored = history.undo()
        
        assert restored["val"] == 1
        assert restored["img"] is image_data
        assert isinstance(restored["img"], np.ndarray)
