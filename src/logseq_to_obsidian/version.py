from __future__ import annotations

from importlib import metadata

try:
    __version__ = metadata.version("logseq-to-obsidian")
except metadata.PackageNotFoundError:  # pragma: no cover - only in editable installs before metadata exists
    __version__ = "0.0.0"

__all__ = ["__version__"]
