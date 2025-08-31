#!/usr/bin/env python3
import subprocess
import sys


def _run(cmd: list[str]) -> int:
    print("$", " ".join(cmd))
    try:
        return subprocess.call(cmd)
    except FileNotFoundError:
        print(f"Command not found: {' '.join(cmd)}", file=sys.stderr)
        return 127


def check() -> int:
    """Run lint (ruff) and tests (pytest)."""
    code = 0
    code |= _run(["ruff", "check", "."])
    code |= _run(["pytest"])  # uses pytest.ini options
    return code


def fix() -> int:
    """Autofix lint issues, then run tests."""
    code = 0
    code |= _run(["ruff", "check", ".", "--fix"])
    code |= _run(["pytest"])  # uses pytest.ini options
    return code


if __name__ == "__main__":
    # Allow running directly: `python tasks.py [check|fix]`
    if len(sys.argv) > 1 and sys.argv[1] == "fix":
        sys.exit(fix())
    sys.exit(check())

