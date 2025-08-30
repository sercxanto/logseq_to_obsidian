#!/usr/bin/env python3
import argparse
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


PAGE_PROP_RE = re.compile(r"^([A-Za-z0-9_\-]+)::\s*(.*)\s*$")
TASK_RE = re.compile(r"^(?P<indent>\s*)([-*])\s+(?P<state>TODO|DONE|DOING|LATER|WAITING|CANCELLED)\s+(?P<rest>.*)$")
ID_PROP_RE = re.compile(r"^\s*id::\s*([A-Za-z0-9_-]+)\s*$")
BLOCK_REF_RE = re.compile(r"\(\(([A-Za-z0-9_-]{6,})\)\)")
JOURNAL_DATE_UNDERSCORE_RE = re.compile(r"^(\d{4})_(\d{2})_(\d{2})\.md$")
JOURNAL_DATE_DASH_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})\.md$")


@dataclass
class Options:
    input_dir: Path
    output_dir: Path
    rename_journals: bool
    daily_folder: Optional[str]
    flatten_pages: bool
    annotate_status: bool
    dry_run: bool


@dataclass
class FilePlan:
    in_path: Path
    out_path: Path
    is_markdown: bool


def parse_args(argv: List[str]) -> Options:
    p = argparse.ArgumentParser(description="Convert a Logseq vault to Obsidian-friendly Markdown.")
    p.add_argument("--input", required=True, help="Path to Logseq vault root")
    p.add_argument("--output", required=True, help="Path to destination Obsidian vault root")
    p.add_argument("--rename-journals", action="store_true", help="Rename journal files YYYY_MM_DD.md -> YYYY-MM-DD.md")
    p.add_argument("--daily-folder", default=None, help="Move journals into this folder name in output")
    p.add_argument("--flatten-pages", action="store_true", help="Move files in pages/ to output root (retains subfolders)")
    p.add_argument("--annotate-status", action="store_true", help="Annotate non-TODO/DONE statuses on tasks")
    p.add_argument("--dry-run", action="store_true", help="Do not write files; print plan only")
    args = p.parse_args(argv)
    return Options(
        input_dir=Path(args.input).resolve(),
        output_dir=Path(args.output).resolve(),
        rename_journals=bool(args.rename_journals),
        daily_folder=args.daily_folder,
        flatten_pages=bool(args.flatten_pages),
        annotate_status=bool(args.annotate_status),
        dry_run=bool(args.dry_run),
    )


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

        # Optionally rename journal files from underscores to dashes
        if opt.rename_journals and is_markdown(p):
            name = parts[-1]
            m = JOURNAL_DATE_UNDERSCORE_RE.match(name)
            if m:
                parts[-1] = f"{m.group(1)}-{m.group(2)}-{m.group(3)}.md"

    # Handle pages flattening
    if parts and parts[0] == "pages" and opt.flatten_pages:
        parts = list(parts[1:])  # drop the 'pages' segment

    return opt.output_dir.joinpath(*parts)


def collect_files(opt: Options) -> List[FilePlan]:
    plans: List[FilePlan] = []
    for root, dirs, files in os.walk(opt.input_dir):
        root_p = Path(root)
        for fname in files:
            in_path = root_p / fname
            out_path = plan_output_path(in_path, opt)
            plans.append(FilePlan(in_path=in_path, out_path=out_path, is_markdown=is_markdown(in_path)))
    return plans


def ensure_dir(p: Path, dry_run: bool = False):
    d = p.parent
    if not dry_run:
        d.mkdir(parents=True, exist_ok=True)


def parse_page_properties(lines: List[str]) -> Tuple[Dict[str, str], int]:
    props: Dict[str, str] = {}
    consumed = 0
    for line in lines:
        if not line.strip():
            # allow leading empty lines; do not count them as part of properties
            consumed += 1
            continue
        m = PAGE_PROP_RE.match(line)
        if not m:
            break
        key = m.group(1).strip().lower()
        val = m.group(2).strip()
        props[key] = val
        consumed += 1
    return props, consumed


def normalize_aliases(val: str) -> List[str]:
    # Supports comma-separated, or [[Alias]] styles
    aliases: List[str] = []
    # Extract [[...]] first
    for m in re.finditer(r"\[\[([^\]]+)\]\]", val):
        aliases.append(m.group(1).strip())
    # Remove wikilinks and split remaining by comma
    remainder = re.sub(r"\[\[[^\]]+\]\]", "", val)
    for part in remainder.split(","):
        s = part.strip()
        if s:
            aliases.append(s)
    # Deduplicate preserving order
    seen = set()
    uniq = []
    for a in aliases:
        if a not in seen:
            uniq.append(a)
            seen.add(a)
    return uniq


def normalize_tags(val: str) -> List[str]:
    tags: List[str] = []
    # Capture #tags and [[tags]] and comma-separated
    for m in re.finditer(r"#([A-Za-z0-9_\-/]+)", val):
        tags.append(m.group(1))
    for m in re.finditer(r"\[\[([^\]]+)\]\]", val):
        tags.append(m.group(1).strip())
    remainder = re.sub(r"(#([A-Za-z0-9_\-/]+))|(\[\[[^\]]+\]\])", "", val)
    for part in remainder.split(","):
        s = part.strip()
        if s:
            tags.append(s)
    seen = set()
    uniq = []
    for t in tags:
        if t not in seen:
            uniq.append(t)
            seen.add(t)
    return uniq


def emit_yaml_frontmatter(props: Dict[str, str]) -> Optional[str]:
    if not props:
        return None
    # Map known keys
    yaml_lines: List[str] = ["---"]
    # title
    if "title" in props:
        yaml_lines.append(f"title: {props['title']}")
    # aliases
    aliases_src = props.get("aliases") or props.get("alias")
    if aliases_src:
        aliases = normalize_aliases(aliases_src)
        if aliases:
            yaml_lines.append("aliases:")
            for a in aliases:
                yaml_lines.append(f"  - {a}")
    # tags
    tags_src = props.get("tags")
    if tags_src:
        tags = normalize_tags(tags_src)
        if tags:
            yaml_lines.append("tags:")
            for t in tags:
                yaml_lines.append(f"  - {t}")
    # Include other props (excluding those already handled)
    handled = {"title", "aliases", "alias", "tags"}
    for k, v in props.items():
        if k in handled:
            continue
        # simple scalars; leave as-is
        if v:
            yaml_lines.append(f"{k}: {v}")
    yaml_lines.append("---")
    return "\n".join(yaml_lines) + "\n\n"


def transform_tasks(line: str, annotate_status: bool) -> str:
    m = TASK_RE.match(line)
    if not m:
        return line
    indent = m.group("indent")
    state = m.group("state")
    rest = m.group("rest")
    if state == "TODO":
        return f"{indent}- [ ] {rest}\n"
    if state == "DONE":
        return f"{indent}- [x] {rest}\n"
    # Other states
    if annotate_status:
        return f"{indent}- [ ] {rest} (status: {state})\n"
    return f"{indent}- [ ] {rest}\n"


def attach_block_ids(lines: List[str]) -> List[str]:
    # Convert `id:: xyz` single-line block properties into trailing ^xyz on the previous content line.
    out: List[str] = []
    last_content_idx: Optional[int] = None
    last_content_indent: int = 0
    for idx, line in enumerate(lines):
        m = ID_PROP_RE.match(line)
        if m and last_content_idx is not None:
            block_id = m.group(1)
            # Append anchor to the last content line
            base = out[last_content_idx].rstrip("\n")
            if not base.strip():
                # No content to attach to; keep the id line as-is
                out.append(line)
                continue
            if re.search(rf"\^\b{re.escape(block_id)}\b$", base):
                # already has anchor
                continue
            out[last_content_idx] = base + f" ^{block_id}\n"
            # Drop the id:: line by not appending it
            continue

        # Track last content line (non-empty, not a property-only line)
        if PAGE_PROP_RE.match(line):
            # Likely a property line (page/block); don't count as content
            out.append(line)
            continue
        if line.strip():
            # Contentful line
            last_content_idx = len(out)
            # track indent width for potential future heuristics (unused for now)
            last_content_indent = len(line) - len(line.lstrip(" "))
        out.append(line)
    return out


def build_block_index(file_texts: Dict[Path, str]) -> Dict[str, Path]:
    # Map id -> file path where the id anchor will live
    index: Dict[str, Path] = {}
    for p, text in file_texts.items():
        for m in re.finditer(r"^\s*id::\s*([A-Za-z0-9_-]+)\s*$", text, flags=re.MULTILINE):
            index[m.group(1)] = p
        # Also pick up already-anchored lines (^id)
        for m in re.finditer(r"\^([A-Za-z0-9_-]+)\s*$", text, flags=re.MULTILINE):
            index[m.group(1)] = p
    return index


def replace_block_refs(text: str, index: Dict[str, Path], in_to_out: Dict[Path, Path], output_root: Path) -> str:
    def repl(m: re.Match) -> str:
        bid = m.group(1)
        target = index.get(bid)
        if not target:
            return m.group(0)  # leave as-is
        out_path = in_to_out.get(target, target)
        # Use a vault-relative path without extension for better disambiguation
        try:
            rel = out_path.relative_to(output_root)
        except Exception:
            rel = out_path
        link_path = str(rel.with_suffix("")).replace(os.sep, "/")
        return f"[[{link_path}#^{bid}]]"

    return BLOCK_REF_RE.sub(repl, text)


def transform_markdown(text: str, annotate_status: bool) -> str:
    # Page frontmatter
    lines = text.splitlines(keepends=True)
    props, consumed = parse_page_properties(lines)
    yaml = emit_yaml_frontmatter(props)

    body_lines = lines[consumed:]
    # tasks
    body_lines = [transform_tasks(ln, annotate_status) for ln in body_lines]
    # block ids
    body_lines = attach_block_ids(body_lines)

    out = (yaml or "") + "".join(body_lines)
    return out


def copy_or_write(out_path: Path, content: Optional[str], src: Optional[Path], dry_run: bool):
    ensure_dir(out_path, dry_run)
    if content is not None:
        if dry_run:
            print(f"[DRY-WRITE] {out_path}")
            return
        print(f"[WRITE] {out_path}")
        out_path.write_text(content, encoding="utf-8")
    else:
        assert src is not None
        if dry_run:
            print(f"[DRY-COPY] {src} -> {out_path}")
            return
        print(f"[COPY] {src} -> {out_path}")
        shutil.copy2(src, out_path)


def main(argv: List[str]) -> int:
    opt = parse_args(argv)
    if not opt.input_dir.exists():
        print(f"Input directory not found: {opt.input_dir}", file=sys.stderr)
        return 1
    opt.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[START] Logseq → Obsidian conversion")
    print(f"[CONFIG] input={opt.input_dir}")
    print(f"[CONFIG] output={opt.output_dir}")
    print(
        f"[CONFIG] rename_journals={opt.rename_journals} daily_folder={opt.daily_folder or '-'} flatten_pages={opt.flatten_pages} annotate_status={opt.annotate_status} dry_run={opt.dry_run}"
    )

    plans = collect_files(opt)
    total = len(plans)
    md_total = sum(1 for p in plans if p.is_markdown)
    other_total = total - md_total
    print(f"[SCAN] Discovered {total} files ({md_total} markdown, {other_total} other)")

    # First pass: read markdown files and pre-transform to attach ids, etc., to allow building index
    pre_texts: Dict[Path, str] = {}
    in_to_out: Dict[Path, Path] = {pl.in_path: pl.out_path for pl in plans}

    for pl in plans:
        if not pl.is_markdown:
            continue
        try:
            rel = pl.in_path.relative_to(opt.input_dir)
        except Exception:
            rel = pl.in_path
        print(f"[TRANSFORM] {rel}")
        raw = pl.in_path.read_text(encoding="utf-8")
        transformed = transform_markdown(raw, annotate_status=opt.annotate_status)
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
            copy_or_write(pl.out_path, text, None, opt.dry_run)
            writes += 1
        else:
            # Copy assets and others
            copy_or_write(pl.out_path, None, pl.in_path, opt.dry_run)
            copies += 1

    print(f"[DONE] Wrote {writes} markdown file(s), copied {copies} other file(s)")
    if opt.dry_run:
        print("[INFO] Dry run complete. No files were written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
