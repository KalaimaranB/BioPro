import subprocess
import sys
import os

def run_step(name, command):
    print(f"\n>>> RUNNING: {name}")
    # Use the .venv python if it exists
    python_exe = ".venv/bin/python3"
    if not os.path.exists(python_exe):
        python_exe = "python3"
        
    cmd = command.replace("python3", python_exe)
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {name} PASSED")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {name} FAILED")
        print(e.stdout)
        print(e.stderr)
        return False

def main():
    print("--- BIOPRO SYSTEM QUALITY CHECK ---")
    
    steps = [
        ("Import Validity", "python3 verify_imports.py"),
        ("Resource Integrity", "python3 tests/test_resources.py"),
        ("Core Boot Tests", "python3 tests/test_boot.py"),
        ("UI Boot Tests", "python3 tests/test_ui.py")
    ]
    
    all_passed = True
    for name, cmd in steps:
        if not run_step(name, cmd):
            all_passed = False
            
    print("\n" + "="*40)
    if all_passed:
        print("🎉 ALL CHECKS PASSED. SYSTEM IS STABLE.")
        sys.exit(0)
    else:
        print("🔴 SYSTEM UNSTABLE. REVIEW ERRORS ABOVE.")
        sys.exit(1)

if __name__ == "__main__":
    main()
