#!/usr/bin/env python3
"""Validate all Mermaid diagrams embedded in Markdown files across the repo.

Extracts every ```mermaid code block from every Markdown file in the repo,
writes each block to a temp .mmd file, and renders it via `mmdc` (mermaid-cli).
Exits non-zero if any diagram fails to render, printing the source file and
approximate line number for each failure.

Usage::

    python3 scripts/validate_mermaid.py [--root <dir>]

Dependencies (CI)::

    npm install -g @mermaid-js/mermaid-cli
"""

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

MERMAID_FENCE = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)


def find_markdown_files(root: Path) -> list[Path]:
    """Recursively find all Markdown files under *root*, excluding common noise dirs."""
    exclude = {".git", "node_modules", "__pycache__", ".venv"}
    files = []
    for path in root.rglob("*.md"):
        if not any(part in exclude for part in path.parts):
            files.append(path)
    return sorted(files)


def extract_diagrams(md_path: Path) -> list[tuple[int, str]]:
    """Return list of (start_line, diagram_source) for each mermaid block."""
    text = md_path.read_text(encoding="utf-8")
    results = []
    for match in MERMAID_FENCE.finditer(text):
        start_line = text[: match.start()].count("\n") + 1
        results.append((start_line, match.group(1).strip()))
    return results


def validate_diagram(source: str, label: str, puppeteer_config: str | None = None) -> str | None:
    """Render diagram via mmdc. Returns error message string on failure, None on success."""
    with tempfile.NamedTemporaryFile(suffix=".mmd", mode="w", delete=False, encoding="utf-8") as f:
        f.write(source)
        tmp_in = f.name

    tmp_out = tmp_in.replace(".mmd", ".svg")

    try:
        cmd = ["mmdc", "-i", tmp_in, "-o", tmp_out, "--quiet"]
        if puppeteer_config:
            cmd += ["--puppeteerConfigFile", puppeteer_config]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            stderr = (result.stderr or result.stdout).strip()
            return f"{label}\n    {stderr or 'Unknown render error'}"
        return None
    except FileNotFoundError:
        print(
            "::error::mmdc not found. Install with: npm install -g @mermaid-js/mermaid-cli",
            file=sys.stderr,
        )
        sys.exit(2)
    except subprocess.TimeoutExpired:
        return f"{label}\n    Timed out after 30s"
    finally:
        Path(tmp_in).unlink(missing_ok=True)
        Path(tmp_out).unlink(missing_ok=True)


def main() -> int:
    """Entry point: scan for Mermaid blocks, validate each, and report results."""
    parser = argparse.ArgumentParser(description="Validate Mermaid diagrams in Markdown files.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Root directory to scan (default: current directory)",
    )
    parser.add_argument(
        "--puppeteer-config",
        dest="puppeteer_config",
        default=None,
        help="Path to a Puppeteer JSON config file passed to mmdc (e.g. for --no-sandbox)",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    md_files = find_markdown_files(root)

    if not md_files:
        print("No Markdown files found.")
        return 0

    failures: list[str] = []
    total = 0

    for md_path in md_files:
        diagrams = extract_diagrams(md_path)
        for line_no, source in diagrams:
            total += 1
            rel = md_path.relative_to(root)
            label = f"{rel}:{line_no}"
            error = validate_diagram(source, label, puppeteer_config=args.puppeteer_config)
            if error:
                failures.append(error)
                print(f"::error file={rel},line={line_no}::Mermaid diagram failed to render")
            else:
                print(f"  ✓  {label}")

    print(f"\n{total - len(failures)}/{total} diagrams valid.")

    if failures:
        print("\nFailed diagrams:")
        for f in failures:
            print(f"  ✗  {f}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
