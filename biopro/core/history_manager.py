"""History and State Management for Non-Destructive Editing."""

import logging

logger = logging.getLogger(__name__)

class ModuleHistory:
    """Manages the undo/redo stacks for a single, specific module."""
    
    def __init__(self, module_id: str):
        self.module_id = module_id
        self.undo_stack = []
        self.redo_stack = []

    def push(self, state: dict) -> None:
        """Saves a new state snapshot and clears the redo stack."""
        # Prevent spamming the exact same state twice in a row
        if self.undo_stack and self.undo_stack[-1] == state:
            return

        self.undo_stack.append(state)
        self.redo_stack.clear()
        logger.debug(f"[{self.module_id}] State pushed. Undo depth: {len(self.undo_stack)}")

    def undo(self) -> dict | None:
        """Moves current state to redo, returns the previous state to load."""
        # We need at least 2 states to perform an undo (the current one, and the one we revert to)
        if len(self.undo_stack) <= 1:
            return None  
            
        current_state = self.undo_stack.pop()
        self.redo_stack.append(current_state)
        
        logger.debug(f"[{self.module_id}] Undo. New depth: {len(self.undo_stack)}")
        # Return the new "top" of the undo stack so the plugin can render it
        return self.undo_stack[-1]

    def redo(self) -> dict | None:
        """Moves a state from redo back to undo and returns it."""
        if not self.redo_stack:
            return None
            
        state = self.redo_stack.pop()
        self.undo_stack.append(state)
        logger.debug(f"[{self.module_id}] Redo. Undo depth: {len(self.undo_stack)}")
        return state

    def serialize(self) -> dict:
        """Packages the history arrays so ProjectManager can write to project.json."""
        return {
            "undo_stack": self.undo_stack,
            "redo_stack": self.redo_stack
        }

    def load(self, data: dict) -> None:
        """Restores history from a loaded project.json file."""
        self.undo_stack = data.get("undo_stack", [])
        self.redo_stack = data.get("redo_stack", [])


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