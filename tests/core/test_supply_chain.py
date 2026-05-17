"""Supply Chain Integrity Tests for BioPro.

Ensures that all production dependencies are pinned with SHA-256 hashes
to prevent dependency hijacking and ensure hermetic builds.
"""

import re
from pathlib import Path


def test_requirements_integrity():
    """Verify that requirements.txt uses strict hash-verification."""
    req_path = Path(__file__).parent.parent.parent / "requirements.txt"

    assert req_path.exists(), "requirements.txt is missing!"

    with open(req_path) as f:
        content = f.read()

    # pip-compile blocks are separated by blank lines (or at least start with the package name)
    # We look for lines that look like 'package==version \'
    package_pattern = re.compile(r"^([a-zA-Z0-9\-_\[\]]+==[0-9.a-z]+) \s*\\", re.MULTILINE)
    hash_pattern = re.compile(r"--hash=sha256:[a-f0-9]{64}")

    # Find all packages defined in the file
    packages = package_pattern.findall(content)

    # For each package, ensure there is at least one hash following it until the next package or end of file
    unhashed = []
    for pkg in packages:
        # Get the content starting from this package line
        start_idx = content.find(pkg)
        # Find where the next package starts or end of file
        next_matches = list(package_pattern.finditer(content, start_idx + len(pkg)))
        end_idx = next_matches[0].start() if next_matches else len(content)

        block = content[start_idx:end_idx]
        if not hash_pattern.search(block):
            unhashed.append(pkg)

    assert not unhashed, (
        f"The following dependencies are missing integrity hashes: {unhashed}. "
        "Run 'pip-compile --generate-hashes' to harden the supply chain."
    )


def test_no_unpinned_dependencies():
    """Verify that all dependencies have exact versions and no loose requirements."""
    req_path = Path(__file__).parent.parent.parent / "requirements.txt"

    with open(req_path) as f:
        lines = f.readlines()

    unpinned = []
    for line in lines:
        line = line.strip()
        # Skip comments, blank lines, hashes, and 'via' lines
        if not line or line.startswith("#") or line.startswith("--hash") or line.startswith("-"):
            continue

        # If a line doesn't have == and isn't a hash/comment, it might be unpinned
        # In pip-compile, the package lines look like 'pkg==1.2.3 \'
        if (
            "==" not in line
            and not line.startswith(" ")
            and re.match(r"^[a-zA-Z0-9\-_\[\]]+$", line.split()[0])
        ):
            unpinned.append(line)

    assert not unpinned, (
        f"The following dependencies are not pinned to an exact version: {unpinned}"
    )
