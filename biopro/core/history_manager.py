"""History and State Management for Non-Destructive Editing."""

import logging
import copy
from .resource_inspector import ResourceInspector

logger = logging.getLogger(__name__)

class ModuleHistory:
    """Manages the undo/redo stacks for a single, specific module."""
    
    def __init__(self, module_id: str):
        self.module_id = module_id
        self.undo_stack = []
        self.redo_stack = []

    def push(self, state: dict) -> None:
        """Saves a new state snapshot and clears the redo stack.
        
        This implementation uses Structural Sharing for heavy resources (like numpy arrays)
        to prevent memory explosion during undo/redo storage.
        """
        # 1. Identify heavy objects in the state
        heavy_resources = {}
        cleaned_state = {}
        
        for key, value in state.items():
            if ResourceInspector.is_heavy(value):
                # Store by reference (No copy!)
                heavy_resources[key] = value
            else:
                # Deep copy light parameters (thresholds, strings)
                try:
                    cleaned_state[key] = copy.deepcopy(value)
                except Exception:
                    cleaned_state[key] = value

        # 2. Re-insert heavy resources into the snapshot by reference
        # This creates a "Shallow-Deep" hybrid that is safe for BioPro's patterns
        for key, ref in heavy_resources.items():
            cleaned_state[key] = ref

        # Prevent spamming the exact same state twice in a row
        if self.undo_stack and self._is_equal(self.undo_stack[-1], cleaned_state):
            return

        self.undo_stack.append(cleaned_state)
        self.redo_stack.clear()
        logger.debug(f"[{self.module_id}] State pushed with Structural Sharing. Depth: {len(self.undo_stack)}")

    def _is_equal(self, state_a: dict, state_b: dict) -> bool:
        """Optimized equality check that handles numpy arrays by identity."""
        if state_a.keys() != state_b.keys():
            return False
        
        for key in state_a:
            val_a = state_a[key]
            val_b = state_b[key]
            
            # For heavy resources, we check identity (address) for speed
            if ResourceInspector.is_heavy(val_a):
                if val_a is not val_b:
                    return False
                continue
                
            if val_a != val_b:
                return False
        return True

    def undo(self) -> dict | None:
        """Moves current state to redo, returns the previous state to load."""
        if len(self.undo_stack) <= 1:
            return None  
            
        current_state = self.undo_stack.pop()
        self.redo_stack.append(current_state)
        
        logger.debug(f"[{self.module_id}] Undo. New depth: {len(self.undo_stack)}")
        
        # 2. Return a copy of the state, preserving heavy references
        # We don't deepcopy again here because the state in the stack is already 
        # a hybrid snapshot created during push().
        return self.undo_stack[-1]

    def redo(self) -> dict | None:
        """Moves a state from redo back to undo and returns it."""
        if not self.redo_stack:
            return None
            
        state = self.redo_stack.pop()
        self.undo_stack.append(state)
        logger.debug(f"[{self.module_id}] Redo. Undo depth: {len(self.undo_stack)}")
        
        # 3. Return the state reference
        return state

    def serialize(self) -> dict:
        """Packages the history œarrays so ProjectManager can write to project.json."""
        return {
            "undo_stack": self.undo_stack,
            "redo_stack": self.redo_stack
        }

    def load(self, data: dict) -> None:
        """Restores history from a loaded project.json file."""
        self.undo_stack = data.get("undo_stack", [])
        self.redo_stack = data.get("redo_stack", [])

    def clear(self, keep_initial: bool = False) -> None:
        """Clears all undo/redo history for this module.
        
        Args:
            keep_initial: If True, keeps the first state in undo_stack as a checkpoint.
                         This is useful when resetting a module's analysis.
        """
        if keep_initial and self.undo_stack:
            initial_state = self.undo_stack[0]
            self.undo_stack = [initial_state]
        else:
            self.undo_stack.clear()
        self.redo_stack.clear()
        logger.debug(f"[{self.module_id}] History cleared. Keep initial: {keep_initial}")

class HistoryManager:
    """Central registry that holds independent histories for every module in a project."""
    
    def __init__(self):
        # Dictionary mapping: module_id -> ModuleHistory instance
        self.histories = {}

    def get_module_history(self, module_id: str) -> ModuleHistory:
        """Retrieves or creates the history tracker for a specific module."""
        if module_id not in self.histories:
            self.histories[module_id] = ModuleHistory(module_id)
        return self.histories[module_id]

    def serialize_all(self) -> dict:
        """Grabs the history from EVERY module to save the entire project."""
        output = {}
        for mod_id, mod_history in self.histories.items():
            output[mod_id] = mod_history.serialize()
        return output

    def load_all(self, data: dict) -> None:
        """Rebuilds the history registry when opening an existing project."""
        self.histories.clear()
        for mod_id, history_data in data.items():
            mod_history = ModuleHistory(mod_id)
            mod_history.load(history_data)
            self.histories[mod_id] = mod_history

    def clear_module_history(self, module_id: str, keep_initial: bool = False) -> None:
        """Clears history for a specific module.
        
        Args:
            module_id: The module whose history should be cleared.
            keep_initial: If True, keeps the first state as a checkpoint.
        """
        if module_id in self.histories:
            self.histories[module_id].clear(keep_initial=keep_initial)
            logger.debug(f"Cleared history for module: {module_id}")

    def clear_all(self, keep_initial: bool = False) -> None:
        """Clears all module histories.
        
        Args:
            keep_initial: If True, keeps first states as checkpoints for each module.
        """
        for module_history in self.histories.values():
            module_history.clear(keep_initial=keep_initial)
        logger.debug(f"Cleared all module histories. Keep initial: {keep_initial}")

    def remove_module(self, module_id: str) -> None:
        """Completely removes a module's history (e.g., when module is deleted)."""
        if module_id in self.histories:
            del self.histories[module_id]
            logger.debug(f"Removed history for module: {module_id}")