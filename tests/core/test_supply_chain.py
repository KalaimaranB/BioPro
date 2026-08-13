"""Supply Chain Integrity Tests for Karcytics.

Ensures that all production dependencies are pinned with SHA-256 hashes
to prevent dependency hijacking and ensure hermetic builds using uv.lock.
"""

import tomllib
from pathlib import Path


def test_requirements_integrity():
    """Verify that uv.lock uses strict hash-verification."""
    lock_path = Path(__file__).parent.parent.parent / "uv.lock"

    assert lock_path.exists(), "uv.lock is missing!"

    with open(lock_path, "rb") as f:
        lock_data = tomllib.load(f)

    # For each package, ensure there is at least one hash
    unhashed = []
    for pkg in lock_data.get("package", []):
        has_hash = False
        if "sdist" in pkg and "hash" in pkg["sdist"]:
            has_hash = True
        if "wheels" in pkg:
            for wheel in pkg["wheels"]:
                if "hash" in wheel:
                    has_hash = True
        if not has_hash and pkg["name"] not in ["karcytics", "biopro-sdk"]:
            unhashed.append(pkg["name"])

    assert not unhashed, (
        f"The following dependencies are missing integrity hashes: {unhashed}. "
        "uv should generate hashes automatically."
    )


def test_no_unpinned_dependencies():
    """Verify that all dependencies have exact versions."""
    lock_path = Path(__file__).parent.parent.parent / "uv.lock"

    with open(lock_path, "rb") as f:
        lock_data = tomllib.load(f)

    unpinned = []
    for pkg in lock_data.get("package", []):
        if "version" not in pkg:
            unpinned.append(pkg["name"])

    assert not unpinned, (
        f"The following dependencies are not pinned to an exact version: {unpinned}"
    )
