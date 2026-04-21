"""Tests for biopro.core.history_manager module."""

import pytest
from biopro.core.history_manager import ModuleHistory, HistoryManager


class TestModuleHistory:
    """Test ModuleHistory class."""
    
    def test_history_creation(self):
        history = ModuleHistory("test_module")
        assert history.module_id == "test_module"
        assert len(history.undo_stack) == 0
        assert len(history.redo_stack) == 0
    
    def test_push_state(self):
        history = ModuleHistory("test")
        state = {"value": 42}
        
        history.push(state)
        assert len(history.undo_stack) == 1
        assert history.undo_stack[0]["value"] == 42
    
    def test_push_duplicate_prevented(self):
        history = ModuleHistory("test")
        state = {"value": 42}
        
        history.push(state)
        history.push(state)  # Same state
        
        # Should not push duplicate
        assert len(history.undo_stack) == 1
    
    def test_undo_returns_previous_state(self):
        history = ModuleHistory("test")
        history.push({"value": 10})
        history.push({"value": 20})
        
        previous = history.undo()
        assert previous["value"] == 10
    
    def test_undo_moves_to_redo_stack(self):
        history = ModuleHistory("test")
        history.push({"value": 10})
        history.push({"value": 20})
        
        # Undo moves current state to redo
        history.undo()
        assert len(history.redo_stack) == 1
        assert history.redo_stack[0]["value"] == 20
    
    def test_redo_returns_next_state(self):
        history = ModuleHistory("test")
        history.push({"value": 10})
        history.push({"value": 20})
        
        history.undo()
        next_state = history.redo()
        
        assert next_state["value"] == 20
    
    def test_push_after_undo_clears_redo(self):
        history = ModuleHistory("test")
        history.push({"value": 10})
        history.push({"value": 20})
        history.undo()
        
        # Redo stack should have the undone state
        assert len(history.redo_stack) == 1
        
        # Push new state
        history.push({"value": 30})
        
        # Redo stack should be cleared
        assert len(history.redo_stack) == 0
    
    def test_serialize(self):
        history = ModuleHistory("test")
        history.push({"value": 10})
        history.push({"value": 20})
        
        serialized = history.serialize()
        assert "undo_stack" in serialized
        assert "redo_stack" in serialized
        assert len(serialized["undo_stack"]) == 2
    
    def test_load(self):
        history = ModuleHistory("test")
        data = {
            "undo_stack": [{"value": 10}, {"value": 20}],
            "redo_stack": [{"value": 30}]
        }
        
        history.load(data)
        assert len(history.undo_stack) == 2
        assert len(history.redo_stack) == 1
    
    def test_clear_empty(self):
        """Test clear on empty history."""
        history = ModuleHistory("test")
        history.clear()
        assert len(history.undo_stack) == 0
        assert len(history.redo_stack) == 0
    
    def test_clear_full(self):
        """Test clear removes all history."""
        history = ModuleHistory("test")
        history.push({"value": 10})
        history.push({"value": 20})
        history.undo()
        
        assert len(history.undo_stack) > 0
        assert len(history.redo_stack) > 0
        
        history.clear()
        assert len(history.undo_stack) == 0
        assert len(history.redo_stack) == 0
    
    def test_clear_keep_initial(self):
        """Test clear with keep_initial keeps first state."""
        history = ModuleHistory("test")
        initial_state = {"value": 0}
        history.push(initial_state)
        history.push({"value": 10})
        history.push({"value": 20})
        
        history.clear(keep_initial=True)
        
        assert len(history.undo_stack) == 1
        assert history.undo_stack[0]["value"] == 0
        assert len(history.redo_stack) == 0


class TestHistoryManager:
    """Test HistoryManager class."""
    
    def test_manager_creation(self):
        manager = HistoryManager()
        assert len(manager.histories) == 0
    
    def test_get_module_history_creates_new(self):
        manager = HistoryManager()
        history = manager.get_module_history("module1")
        
        assert history is not None
        assert history.module_id == "module1"
        assert "module1" in manager.histories
    
    def test_get_module_history_reuses_existing(self):
        manager = HistoryManager()
        history1 = manager.get_module_history("module1")
        history2 = manager.get_module_history("module1")
        
        assert history1 is history2
    
    def test_serialize_all(self):
        manager = HistoryManager()
        history1 = manager.get_module_history("module1")
        history2 = manager.get_module_history("module2")
        
        history1.push({"value": 10})
        history2.push({"value": 20})
        
        serialized = manager.serialize_all()
        
        assert "module1" in serialized
        assert "module2" in serialized
        assert len(serialized["module1"]["undo_stack"]) == 1
        assert len(serialized["module2"]["undo_stack"]) == 1
    
    def test_load_all(self):
        manager = HistoryManager()
        data = {
            "module1": {
                "undo_stack": [{"value": 10}],
                "redo_stack": []
            },
            "module2": {
                "undo_stack": [{"value": 20}],
                "redo_stack": []
            }
        }
        
        manager.load_all(data)
        
        assert len(manager.histories) == 2
        assert "module1" in manager.histories
        assert "module2" in manager.histories
    
    def test_clear_module_history(self):
        """Test clearing a specific module's history."""
        manager = HistoryManager()
        history1 = manager.get_module_history("module1")
        history2 = manager.get_module_history("module2")
        
        history1.push({"value": 10})
        history1.push({"value": 20})
        history2.push({"value": 30})
        
        manager.clear_module_history("module1")
        
        # Module 1 cleared
        assert len(history1.undo_stack) == 0
        # Module 2 untouched
        assert len(history2.undo_stack) == 1
    
    def test_clear_module_history_keep_initial(self):
        """Test clear_module_history with keep_initial."""
        manager = HistoryManager()
        history = manager.get_module_history("module1")
        
        initial = {"value": 0}
        history.push(initial)
        history.push({"value": 10})
        
        manager.clear_module_history("module1", keep_initial=True)
        
        assert len(history.undo_stack) == 1
        assert history.undo_stack[0]["value"] == 0
    
    def test_clear_all(self):
        """Test clearing all module histories."""
        manager = HistoryManager()
        history1 = manager.get_module_history("module1")
        history2 = manager.get_module_history("module2")
        
        history1.push({"value": 10})
        history2.push({"value": 20})
        
        manager.clear_all()
        
        assert len(history1.undo_stack) == 0
        assert len(history2.undo_stack) == 0
    
    def test_clear_all_keep_initial(self):
        """Test clear_all with keep_initial."""
        manager = HistoryManager()
        history1 = manager.get_module_history("module1")
        history2 = manager.get_module_history("module2")
        
        state1 = {"value": 0}
        state2 = {"value": 100}
        history1.push(state1)
        history1.push({"value": 10})
        history2.push(state2)
        history2.push({"value": 200})
        
        manager.clear_all(keep_initial=True)
        
        assert len(history1.undo_stack) == 1
        assert len(history2.undo_stack) == 1
        assert history1.undo_stack[0]["value"] == 0
        assert history2.undo_stack[0]["value"] == 100
    
    def test_remove_module(self):
        """Test removing a module's history."""
        manager = HistoryManager()
        manager.get_module_history("module1")
        manager.get_module_history("module2")
        
        assert len(manager.histories) == 2
        
        manager.remove_module("module1")
        
        assert len(manager.histories) == 1
        assert "module2" in manager.histories
        assert "module1" not in manager.histories
    
    def test_remove_nonexistent_module(self):
        """Test removing a module that doesn't exist."""
        manager = HistoryManager()
        
        # Should not raise
        manager.remove_module("nonexistent")
        assert len(manager.histories) == 0


class TestHistoryManagerIntegration:
    """Integration tests for HistoryManager."""
    
    def test_undo_redo_workflow(self):
        """Test typical undo/redo workflow."""
        manager = HistoryManager()
        history = manager.get_module_history("analysis")
        
        # Simulate analysis steps
        history.push({"step": "load_image"})
        history.push({"step": "detect_lanes"})
        history.push({"step": "detect_bands"})
        
        assert len(history.undo_stack) == 3
        
        # Undo twice
        state = history.undo()
        assert state["step"] == "detect_lanes"
        state = history.undo()
        assert state["step"] == "load_image"
        
        # Redo once
        state = history.redo()
        assert state["step"] == "detect_lanes"
        
        # Push new state (clears redo)
        history.push({"step": "analyze_alternative"})
        assert len(history.redo_stack) == 0
    
    def test_multiple_modules_independence(self):
        """Test that multiple modules have independent histories."""
        manager = HistoryManager()
        
        module1_history = manager.get_module_history("module1")
        module2_history = manager.get_module_history("module2")
        
        # Module 1 history
        module1_history.push({"value": 1})
        module1_history.push({"value": 2})
        
        # Module 2 history
        module2_history.push({"value": 10})
        module2_history.push({"value": 20})
        
        # Clear module 1 only
        manager.clear_module_history("module1")
        
        assert len(module1_history.undo_stack) == 0
        assert len(module2_history.undo_stack) == 2
    
    def test_save_load_cycle(self):
        """Test saving and loading history."""
        manager1 = HistoryManager()
        history1 = manager1.get_module_history("module1")
        history1.push({"data": "first"})
        history1.push({"data": "second"})
        
        # Serialize
        serialized = manager1.serialize_all()
        
        # Create new manager and load
        manager2 = HistoryManager()
        manager2.load_all(serialized)
        
        # Verify
        history2 = manager2.get_module_history("module1")
        assert len(history2.undo_stack) == 2
        assert history2.undo_stack[0]["data"] == "first"
        assert history2.undo_stack[1]["data"] == "second"
