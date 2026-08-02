"""Verification Script for Deterministic Build Mechanism (V2).

This script verifies which files differ between two PyInstaller builds.
"""

import hashlib
import os
import shutil
import subprocess
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
    with open(script_path, "w", encoding="utf-8") as f:
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
    """
    Compare the files and contents of two directories.

    Parameters:
        dir1 (Path): First directory to compare.
        dir2 (Path): Second directory to compare.

    Returns:
        False if the directories contain different file paths; otherwise, a list of relative paths whose file contents differ.
    """
    files1 = set(p.relative_to(dir1) for p in dir1.rglob("*") if p.is_file())  # noqa: C401
    files2 = set(p.relative_to(dir2) for p in dir2.rglob("*") if p.is_file())  # noqa: C401

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

    dirA = build_mock("A", epoch)  # noqa: N806
    dirB = build_mock("B", epoch)  # noqa: N806

    differing = compare_dirs(dirA, dirB)

    if not differing:
        print("\n✅ SUCCESS: Builds are bit-for-bit identical!")
        return

    assert not differing, f"FAILURE: {len(differing)} files differ."


if __name__ == "__main__":
    test_determinism()
