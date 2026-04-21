import os
import sys
import importlib.util
from pathlib import Path

def verify_imports(start_path="biopro"):
    """
    Recursively walks the directory and attempts to import each Python file.
    Helps find missing imports, syntax errors, and undefined names.
    """
    print(f"--- STARTING IMPORT VALIDATION: {start_path} ---")
    
    # Add current directory to path so relative imports work
    sys.path.append(os.getcwd())
    
    error_count = 0
    checked_count = 0
    
    for root, dirs, files in os.walk(start_path):
        # Skip __pycache__ and hidden folders
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
        
        for file in files:
            if file.endswith(".py") and file != "setup.py":
                checked_count += 1
                full_path = Path(root) / file
                
                # Convert path to module name (e.g., biopro/core/trust_manager.py -> biopro.core.trust_manager)
                module_name = str(full_path.with_suffix("")).replace(os.path.sep, ".")
                
                try:
                    # Attempt to import the module
                    importlib.import_module(module_name)
                    print(f"✅ [PASS] {module_name}")
                except Exception as e:
                    error_count += 1
                    print(f"❌ [FAIL] {module_name}")
                    print(f"    ERROR: {type(e).__name__}: {str(e)}")
                    # For deeper info, we can print the traceback if needed
                    # import traceback; traceback.print_exc()

    print(f"\n--- VALIDATION SUMMARY ---")
    print(f"Total Modules Checked: {checked_count}")
    print(f"Success: {checked_count - error_count}")
    print(f"Failures: {error_count}")
    
    if error_count > 0:
        print("\nACTION REQUIRED: Please fix the errors above before pushing.")
        sys.exit(1)
    else:
        print("\nSUCCESS: All modules are healthy and importable.")
        sys.exit(0)

if __name__ == "__main__":
    verify_imports()
