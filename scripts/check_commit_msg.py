"""Pre-commit commit-msg hook: enforce Conventional Commits format.

Real enforcement lives in the enforce-workflow CI job (checks PR titles on a
protected branch); this is local, fast feedback only, bypassable with --no-verify.
"""

import re
import sys

_PATTERN = re.compile(r"^(feat|fix|chore|docs|refactor|test|ci)(\(.+\))?!?: .+")


def main() -> int:
    """Validate that the commit message file's first line follows Conventional Commits."""
    commit_msg_path = sys.argv[1]
    with open(commit_msg_path, encoding="utf-8") as f:
        first_line = f.readline().strip()

    if not _PATTERN.match(first_line):
        print(
            'Commit message must follow Conventional Commits, e.g. "fix: handle empty file". '
            f"Got: {first_line!r}"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
