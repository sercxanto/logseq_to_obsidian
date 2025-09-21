from __future__ import annotations

import sys

from . import main as _main


def main() -> int:
    """Console entry point: dispatch to package `main(argv)`.

    Returns process exit code.
    """
    return _main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())

