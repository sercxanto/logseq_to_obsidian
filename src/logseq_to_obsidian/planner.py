from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

JOURNAL_DATE_UNDERSCORE_RE = re.compile(r"^(\d{4})_(\d{2})_(\d{2})\.md$")


@dataclass
class Options:
    input_dir: Path
    output_dir: Path
    daily_folder: Optional[str]
    dry_run: bool
    tasks_format: str  # 'emoji' or 'dataview'
    field_keys: List[str]


@dataclass
class FilePlan:
    in_path: Path
    out_path: Path
    is_markdown: bool


__all__ = [
    "FilePlan",
    "Options",
    "collect_files",
    "copy_or_write",
    "plan_output_path",
]


def is_markdown(path: Path) -> bool:
    return path.suffix.lower() == ".md"


def plan_output_path(p: Path, opt: Options) -> Path:
    rel = p.relative_to(opt.input_dir)
    parts = list(rel.parts)

    # Handle journals folder name and file rename
    if parts and parts[0] == "journals":
        # Optionally move journals into a custom folder
        out_base = opt.daily_folder if opt.daily_folder else "journals"
        parts[0] = out_base

        # Always rename journal files from underscores to dashes
        if is_markdown(p):
            name = parts[-1]
            m = JOURNAL_DATE_UNDERSCORE_RE.match(name)
            if m:
                parts[-1] = f"{m.group(1)}-{m.group(2)}-{m.group(3)}.md"

    # Handle pages flattening (always) and expand "___" to folder separators for markdown files
    was_pages = parts and parts[0] == "pages"
    if was_pages:
        parts = list(parts[1:])  # drop the 'pages' segment
        if is_markdown(p) and parts:
            name = parts[-1]
            stem, ext = os.path.splitext(name)
            if "___" in stem:
                segs = stem.split("___")
                parts = parts[:-1] + segs[:-1] + [segs[-1] + ext]

    return opt.output_dir.joinpath(*parts)


def collect_files(opt: Options) -> List[FilePlan]:
    plans: List[FilePlan] = []
    for root, dirs, files in os.walk(opt.input_dir):
        root_p = Path(root)
        # Do not descend into certain top-level metadata/content folders not useful in Obsidian
        if root_p == opt.input_dir:
            for skip in ("logseq", "whiteboards"):
                if skip in dirs:
                    dirs.remove(skip)
                    if skip == "whiteboards":
                        print(
                            "[WARN] Skipping top-level 'whiteboards/' directory (Logseq whiteboards are not supported)"
                        )
                    elif skip == "logseq":
                        # We keep warning behavior concise; logseq folder is silently skipped as metadata
                        pass
        for fname in files:
            in_path = root_p / fname
            # Defensive skip: ignore any files under top-level `logseq/`
            try:
                rel_first = (in_path.relative_to(opt.input_dir).parts or [None])[0]
            except ValueError:
                rel_first = None
            if rel_first in {"logseq", "whiteboards"}:
                continue
            out_path = plan_output_path(in_path, opt)
            plans.append(FilePlan(in_path=in_path, out_path=out_path, is_markdown=is_markdown(in_path)))
    return plans


def ensure_dir(p: Path, dry_run: bool = False):
    d = p.parent
    if not dry_run:
        d.mkdir(parents=True, exist_ok=True)


def copy_or_write(out_path: Path, content: Optional[str], src: Path, dry_run: bool):
    ensure_dir(out_path, dry_run)
    if content is not None:
        if dry_run:
            print(f"[DRY-WRITE] {out_path}")
            return
        print(f"[WRITE] {out_path}")
        out_path.write_text(content, encoding="utf-8")
        # Preserve timestamps from source when available
        try:
            shutil.copystat(src, out_path)
        except Exception as e:
            print(f"[WARN] Could not preserve times for {out_path}: {e}")
    else:
        if dry_run:
            print(f"[DRY-COPY] {src} -> {out_path}")
            return
        print(f"[COPY] {src} -> {out_path}")
        shutil.copy2(src, out_path)
        # Reinforce metadata copy in case of platform quirks
        try:
            shutil.copystat(src, out_path)
        except Exception as e:
            print(f"[WARN] Could not preserve times for {out_path}: {e}")
