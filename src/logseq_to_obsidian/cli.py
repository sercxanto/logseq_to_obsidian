from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List

from .planner import Options, collect_files, copy_or_write
from .transformer import (
    build_block_index,
    replace_asset_images,
    replace_block_refs,
    replace_embeds,
    replace_page_alias_links,
    replace_wikilinks_to_dv_fields,
    transform_markdown,
)
from .version import __version__

__all__ = ["main", "parse_args"]


def parse_args(argv: List[str]) -> Options:
    p = argparse.ArgumentParser(description="Convert a Logseq vault to Obsidian-friendly Markdown.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("--input", required=True, help="Path to Logseq vault root")
    p.add_argument("--output", required=True, help="Path to destination Obsidian vault root")
    p.add_argument("--daily-folder", default=None, help="Move journals into this folder name in output")
    p.add_argument(
        "--tasks-format",
        choices=["emoji", "dataview"],
        default="emoji",
        help="Format for Tasks plugin metadata (priority, dates)",
    )
    p.add_argument(
        "--field-key",
        action="append",
        default=[],
        help="Convert wikilinks of the form [[key/value]] to Dataview inline fields [key::value] for the given key(s).",
    )
    p.add_argument("--dry-run", action="store_true", help="Do not write files; print plan only")
    args = p.parse_args(argv)
    return Options(
        input_dir=Path(args.input).resolve(),
        output_dir=Path(args.output).resolve(),
        daily_folder=args.daily_folder,
        dry_run=bool(args.dry_run),
        tasks_format=str(args.tasks_format),
        field_keys=list(args.field_key or []),
    )


def main(argv: List[str]) -> int:
    opt = parse_args(argv)
    if not opt.input_dir.exists():
        print(f"Input directory not found: {opt.input_dir}", file=sys.stderr)
        return 1
    opt.output_dir.mkdir(parents=True, exist_ok=True)

    print("[START] Logseq → Obsidian conversion")
    print(f"[CONFIG] input={opt.input_dir}")
    print(f"[CONFIG] output={opt.output_dir}")
    print(
        f"[CONFIG] daily_folder={opt.daily_folder or '-'} tasks_format={opt.tasks_format} field_keys={','.join(opt.field_keys) or '-'} dry_run={opt.dry_run}"
    )

    plans = collect_files(opt)
    total = len(plans)
    md_total = sum(1 for p in plans if p.is_markdown)
    other_total = total - md_total
    print(f"[SCAN] Discovered {total} files ({md_total} markdown, {other_total} other)")

    # First pass: read markdown files and pre-transform to attach ids, etc., to allow building index
    pre_texts: Dict[Path, str] = {}
    in_to_out: Dict[Path, Path] = {pl.in_path: pl.out_path for pl in plans}

    warn_messages: List[str] = []
    for pl in plans:
        if not pl.is_markdown:
            continue
        try:
            rel = pl.in_path.relative_to(opt.input_dir)
        except ValueError:
            rel = pl.in_path
        print(f"[TRANSFORM] {rel}")
        raw = pl.in_path.read_text(encoding="utf-8")
        # Compute the expected title as the vault-relative output path without extension
        try:
            rel_out = pl.out_path.relative_to(opt.output_dir)
        except ValueError:
            rel_out = pl.out_path
        expected_title = rel_out.with_suffix("").as_posix()
        transformed = transform_markdown(
            raw,
            expected_title_path=expected_title,
            rel_path_for_warn=rel,
            warn_collector=warn_messages,
            tasks_format=opt.tasks_format,
        )
        pre_texts[pl.in_path] = transformed

    block_index = build_block_index(pre_texts)
    print(f"[INDEX] Resolved {len(block_index)} block id(s)")

    # Second pass: write files, replacing block refs using the index
    writes = 0
    copies = 0
    for pl in plans:
        if pl.is_markdown:
            text = pre_texts.get(pl.in_path, pl.in_path.read_text(encoding="utf-8"))
            text = replace_block_refs(text, block_index, in_to_out, opt.output_dir)
            text = replace_embeds(text)
            text = replace_page_alias_links(text)
            text = replace_wikilinks_to_dv_fields(text, opt.field_keys)
            text = replace_asset_images(text)
            # Ensure a trailing newline at EOF to match golden outputs
            if not text.endswith("\n"):
                text += "\n"
            copy_or_write(pl.out_path, text, pl.in_path, opt.dry_run)
            writes += 1
        else:
            # Copy assets and others
            copy_or_write(pl.out_path, None, pl.in_path, opt.dry_run)
            copies += 1

    print(f"[DONE] Wrote {writes} markdown file(s), copied {copies} other file(s)")
    if warn_messages:
        print(f"[WARN] Conversion completed with {len(warn_messages)} warning(s). Review the messages above.")
    if opt.dry_run:
        print("[INFO] Dry run complete. No files were written.")
    return 0
