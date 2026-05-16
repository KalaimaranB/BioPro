"""Tests for Phase 5: Resource Lifecycle & RAII."""

from unittest.mock import patch

import numpy as np

from biopro.core.history_manager import ModuleHistory
from biopro.core.resource_inspector import ResourceInspector


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
                self.image = np.zeros((1000, 1000))  # ~8MB
                self.threshold = 0.5  # Light

        plugin = MockPlugin()
        heavy_resources = ResourceInspector.get_heavy_resources(plugin)

        assert len(heavy_resources) == 1
        assert heavy_resources[0][0] == "image"

    def test_custom_checker(self):
        def my_checker(obj):
            return hasattr(obj, "is_special")

        ResourceInspector.register_heavy_checker(my_checker)

        class Special:
            is_special = True

        assert ResourceInspector.is_heavy(Special()) is True
        assert ResourceInspector.is_heavy(123) is False

    def test_torch_tensors(self):
        import torch

        # Large CPU tensor (Default threshold 1MB, float32 is 4 bytes/elem)
        t_cpu = torch.zeros(1024 * 1024 // 4 * 2)
        assert ResourceInspector.is_heavy(t_cpu) is True

        # Small CPU tensor
        t_small = torch.zeros(10)
        assert ResourceInspector.is_heavy(t_small) is False

        # Mock GPU tensor check if no GPU
        t_mock_gpu = torch.zeros(10)
        with patch.object(torch.Tensor, "is_cuda", True):
            assert ResourceInspector.is_heavy(t_mock_gpu) is True

    def test_matplotlib_figures(self):
        import matplotlib.pyplot as plt

        fig = plt.figure()
        assert ResourceInspector.is_heavy(fig) is True
        plt.close(fig)

    def test_io_base(self):
        import io

        f = io.BytesIO(b"data")
        assert ResourceInspector.is_heavy(f) is True

    def test_get_object_hash(self):
        arr = np.zeros((10, 10))
        h = ResourceInspector.get_object_hash(arr)
        assert h is not None
        assert h.startswith("np:")

        import torch

        t = torch.zeros(5)
        h2 = ResourceInspector.get_object_hash(t)
        assert h2 is not None
        assert h2.startswith("torch:")

        assert ResourceInspector.get_object_hash(None) is None
        assert ResourceInspector.get_object_hash("string") is None

    def test_get_heavy_resources_dict_and_fallback(self):
        # Test dict inspection
        data = {"big": np.zeros(1024 * 1024), "small": 1}
        heavy = ResourceInspector.get_heavy_resources(data)
        assert len(heavy) == 1
        assert heavy[0][0] == "big"

        # Test fallback/exception path
        class Uninspectable:
            def __getattr__(self, name):
                if name == "__dict__":
                    raise Exception("Cannot touch this")
                raise AttributeError(name)

        # Should return empty list and not crash
        assert ResourceInspector.get_heavy_resources(Uninspectable()) == []

    def test_checker_exception_handling(self):
        def bad_checker(obj):
            raise Exception("Boom")

        ResourceInspector.register_heavy_checker(bad_checker)
        # Should not raise, just move on to next checks
        assert ResourceInspector.is_heavy(None) is False
        assert ResourceInspector.is_heavy("test") is False


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

        assert h1 is h2  # Same memory address

    def test_rehydration_on_undo(self):
        history = ModuleHistory("test_module")
        image_data = np.zeros((10, 10))  # Mock heavy for test
        # Set a low threshold for the test to ensure it treats this as heavy
        ResourceInspector.HEAVY_THRESHOLD_BYTES = 10

        state = {"img": image_data, "val": 1}
        history.push(state)
        history.push({"img": image_data, "val": 2})

        # Step back
        restored = history.undo()
        assert restored is not None
        assert restored["val"] == 1
        assert restored["img"] is image_data
        assert isinstance(restored["img"], np.ndarray)
