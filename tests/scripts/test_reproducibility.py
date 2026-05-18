"""Verification Script for Deterministic Build Mechanism (V2).

This script verifies which files differ between two PyInstaller builds.
"""

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path


def get_hash(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def build_mock(name, epoch):
    print(f"--- Starting Build: {name} (Epoch: {epoch}) ---")
    env = os.environ.copy()
    env["SOURCE_DATE_EPOCH"] = str(epoch)
    env["PYTHONHASHSEED"] = "0"

    # Create a tiny mock script
    script_path = Path("mock_app.py")  # Use same name for both
    with open(script_path, "w") as f:
        f.write("import sys\nprint('Hello Deterministic World')")

    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--name",
        "mock_app",
        str(script_path),
    ]

    subprocess.run(cmd, env=env, check=True, capture_output=True)

    # Move dist/mock_app to dist/mock_app_{name}
    res_dir = Path("dist_saved") / name
    res_dir.mkdir(parents=True, exist_ok=True)
    if res_dir.exists():
        shutil.rmtree(res_dir)
    shutil.move(Path("dist") / "mock_app", res_dir)

    # Cleanup
    script_path.unlink()
    shutil.rmtree("build")
    shutil.rmtree("dist")
    (Path("mock_app.spec")).unlink()

    return res_dir


def compare_dirs(dir1, dir2):
    files1 = set(p.relative_to(dir1) for p in dir1.rglob("*") if p.is_file())
    files2 = set(p.relative_to(dir2) for p in dir2.rglob("*") if p.is_file())

    if files1 != files2:
        print(f"Different file sets! {files1 ^ files2}")
        return False

    differing = []
    for f in sorted(files1):
        h1 = get_hash(dir1 / f)
        h2 = get_hash(dir2 / f)
        if h1 != h2:
            differing.append(f)
            print(f"File differs: {f}")

    return differing


def test_determinism():
    import pytest

    if shutil.which("pyinstaller") is None:
        pytest.skip("PyInstaller is not installed in this environment.")

    epoch = 1715800000

    if Path("dist_saved").exists():
        shutil.rmtree("dist_saved")

    dirA = build_mock("A", epoch)
    dirB = build_mock("B", epoch)

    differing = compare_dirs(dirA, dirB)

    if not differing:
        print("\n✅ SUCCESS: Builds are bit-for-bit identical!")
        sys.exit(0)
    else:
        print(f"\n❌ FAILURE: {len(differing)} files differ.")
        sys.exit(1)


if __name__ == "__main__":
    test_determinism()
