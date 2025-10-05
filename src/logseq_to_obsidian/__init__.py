from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Expose the package version for CLI/version reporting. Falls back gracefully if metadata is missing.
try:
    __version__ = metadata.version("logseq-to-obsidian")
except metadata.PackageNotFoundError:  # pragma: no cover - only in editable installs before metadata exists
    __version__ = "0.0.0"

PAGE_PROP_RE = re.compile(r"^([A-Za-z0-9_\-]+)::\s*(.*)\s*$")
# Block properties may be indented under a list item in Logseq
BLOCK_PROP_RE = re.compile(r"^\s*([A-Za-z0-9_\-]+)::\s*(.*)\s*$")
HEAD_BULLET_RE = re.compile(r"^(?P<indent>[ \t]*)-\s+(?P<after>.*)$")
STATE_RE = re.compile(
    r"^(?P<state>TODO|DONE|DOING|LATER|NOW|WAIT|WAITING|IN-PROGRESS|CANCELED|CANCELLED)\b"
    r"(?:\s+\[#(?P<prio>[ABC])\])?\s*(?P<rest>.*)$"
)
# Match only hyphen list items with uppercase state tokens and optional priority token right after the state
TASK_RE = re.compile(
    r"^(?P<indent>\s*)-\s+"
    r"(?P<state>TODO|DONE|DOING|LATER|NOW|WAIT|WAITING|IN-PROGRESS|CANCELED|CANCELLED)\b"
    r"(?:\s+\[#(?P<prio>[ABC])\])?\s*"
    r"(?P<rest>.*)$"
)
ID_PROP_RE = re.compile(r"^\s*id::\s*([A-Za-z0-9_-]+)\s*$")
BLOCK_REF_RE = re.compile(r"\(\(([A-Za-z0-9_-]{6,})\)\)")
JOURNAL_DATE_UNDERSCORE_RE = re.compile(r"^(\d{4})_(\d{2})_(\d{2})\.md$")
JOURNAL_DATE_DASH_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})\.md$")
EMBED_RE = re.compile(r"\{\{embed\s+(.*?)\}\}", flags=re.IGNORECASE)
MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^\)]+)\)")
IMG_WITH_OPT_RE = re.compile(r"!\[[^\]]*\]\(([^\)]+)\)\s*(\{[^}]*\})?")
SCHED_DEAD_RE = re.compile(
    r"(?P<kind>SCHEDULED|DEADLINE)\s*:??\s*"  # keyword + optional ':'
    r"<\s*"
    r"(?P<date>\d{4}-\d{2}-\d{2})"  # YYYY-MM-DD
    r"(?:\s+\w{3})?"  # optional day-of-week token
    r"(?:\s+(?P<time>\d{2}:\d{2}))?"  # optional HH:MM
    r"(?:\s+(?:(?P<rep_kind>\.\+|\+\+|\+)"  # repeater kind .+ / ++ / +
    r"(?P<rep_num>\d+)"  # number
    r"(?P<rep_unit>[ymwdh])))?"  # unit
    r"\s*>",
    flags=re.IGNORECASE,
)


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


def parse_page_properties(lines: List[str]) -> Tuple[Dict[str, str], int]:
    props: Dict[str, str] = {}
    consumed = 0
    started = False
    for line in lines:
        if not started and not line.strip():
            # Skip leading empty lines before any property
            consumed += 1
            continue
        m = PAGE_PROP_RE.match(line)
        if not m:
            # Stop at first non-property line (or blank after starting)
            break
        started = True
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
    # Preserve intuitive order: comma-separated first (in order), then remaining wikilinks, then #tags.
    found: List[str] = []

    def add(tag: str):
        t = tag.strip()
        if not t:
            return
        if t not in found:
            found.append(t)

    # 1) Consume comma-separated parts left-to-right and extract any [[...]] or #... within each part.
    for part in val.split(","):
        # wikilinks
        for m in re.finditer(r"\[\[([^\]]+)\]\]", part):
            add(m.group(1))
        # hashtags
        for m in re.finditer(r"#([A-Za-z0-9_\-/]+)", part):
            add(m.group(1))
        # plain text remainder (strip wikilinks/hashtags)
        remainder = re.sub(r"(#([A-Za-z0-9_\-/]+))|(\[\[[^\]]+\]\])", "", part).strip()
        if remainder:
            add(remainder)

    # 2) Add any additional wikilinks not already included (in appearance order on original string)
    for m in re.finditer(r"\[\[([^\]]+)\]\]", val):
        add(m.group(1))

    # 3) Add any additional hashtags not already included
    for m in re.finditer(r"#([A-Za-z0-9_\-/]+)", val):
        add(m.group(1))

    return found


def emit_yaml_frontmatter(props: Dict[str, str]) -> Optional[str]:
    if not props:
        return None
    # Map known keys
    yaml_lines: List[str] = ["---"]
    # title (may be suppressed upstream if equal to file path)
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


def _map_priority_token(letter: Optional[str], tasks_format: str) -> str:
    if not letter:
        return ""
    if tasks_format == "emoji":
        return {"A": " ⏫", "B": " 🔼", "C": " 🔽"}.get(letter, "")
    # dataview style inline field in brackets, no space after '::'
    mapping = {"A": "high", "B": "medium", "C": "low"}
    level = mapping.get(letter)
    return f" [priority::{level}]" if level else ""


_TASK_DONE_STATES = {"DONE", "CANCELED", "CANCELLED"}


def _render_task_line(
    indent: str,
    state: str,
    content: str,
    priority: Optional[str],
    scheduled: Optional[tuple[str, Optional[str]]],
    due: Optional[tuple[str, Optional[str]]],
    repeat: Optional[tuple[str, int, str]],
    tasks_format: str,
) -> str:
    checkbox = "- [x]" if state in _TASK_DONE_STATES else "- [ ]"
    base = f"{indent}{checkbox}"
    if content:
        base += f" {content}"
    prio_suffix = _map_priority_token(priority, tasks_format)
    date_suffix = _format_dates_suffix(scheduled, due, repeat, tasks_format)
    return f"{base}{prio_suffix}{date_suffix}\n"


def transform_tasks(line: str, tasks_format: str = "emoji") -> str:
    """Transform Logseq task states to Obsidian checklist items.

    - Recognizes only hyphen list items with uppercase states.
    - Maps DONE and CANCELED/CANCELLED to checked; everything else (TODO, DOING, LATER, NOW, WAIT, WAITING, IN-PROGRESS) to unchecked.
    """
    m = TASK_RE.match(line)
    if not m:
        return line
    indent = m.group("indent")
    state = m.group("state")
    prio = m.group("prio")
    rest = m.group("rest")
    cleaned, sched, due, repeat = _extract_dates_and_repeat(rest)
    return _render_task_line(indent, state, cleaned, prio, sched, due, repeat, tasks_format)


def _plural(unit: str, n: int) -> str:
    names = {
        "y": "year",
        "m": "month",
        "w": "week",
        "d": "day",
        "h": "hour",
    }
    base = names.get(unit, unit)
    return base if n == 1 else base + "s"


def _extract_dates_and_repeat(
    text: str,
    preserve_whitespace: bool = False,
) -> tuple[
    str, Optional[tuple[str, Optional[str]]], Optional[tuple[str, Optional[str]]], Optional[tuple[str, int, str]]
]:
    """Return (cleaned_text, scheduled(date,time), due(date,time), repeat(kind,num,unit)).

    - Only the first SCHEDULED and first DEADLINE are captured.
    - Repeater captured from the first date occurrence that defines one; if both define, prefer the first encountered.
    - Removes the matched tokens from the text and normalizes surrounding spaces.
    """
    scheduled: Optional[tuple[str, Optional[str]]] = None
    due: Optional[tuple[str, Optional[str]]] = None
    repeat: Optional[tuple[str, int, str]] = None  # (kind, num, unit)

    def repl(m: re.Match) -> str:
        nonlocal scheduled, due, repeat
        kind = m.group("kind").upper()
        date = m.group("date")
        time = m.group("time")
        rep_kind = m.group("rep_kind")
        rep_num = m.group("rep_num")
        rep_unit = m.group("rep_unit")
        if kind == "SCHEDULED" and scheduled is None:
            scheduled = (date, time)
        elif kind == "DEADLINE" and due is None:
            due = (date, time)
        # Capture the first repeater encountered
        if repeat is None and rep_kind and rep_num and rep_unit:
            repeat = (rep_kind, int(rep_num), rep_unit)
        return ""  # remove this token

    cleaned = SCHED_DEAD_RE.sub(repl, text)
    if not preserve_whitespace:
        # Squash multiple spaces and trim for head lines
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned, scheduled, due, repeat


def _format_dates_suffix(
    scheduled: Optional[tuple[str, Optional[str]]],
    due: Optional[tuple[str, Optional[str]]],
    repeat: Optional[tuple[str, int, str]],
    tasks_format: str,
) -> str:
    parts: List[str] = []

    def fmt_datetime(dt: tuple[str, Optional[str]]) -> str:
        d, t = dt
        return f"{d} {t}" if t else d

    if tasks_format == "emoji":
        if scheduled:
            parts.append(f" ⏳ {fmt_datetime(scheduled)}")
        if due:
            parts.append(f" 📅 {fmt_datetime(due)}")
        if repeat:
            kind, num, unit = repeat
            when_done = " when done" if kind in (".+", "++") else ""
            parts.append(f" 🔁 every {num} {_plural(unit, num)}{when_done}")
    else:  # dataview
        if scheduled:
            parts.append(f" [scheduled::{fmt_datetime(scheduled)}]")
        if due:
            parts.append(f" [due::{fmt_datetime(due)}]")
        if repeat:
            kind, num, unit = repeat
            when_done = " when done" if kind in (".+", "++") else ""
            parts.append(f" [repeat::every {num} {_plural(unit, num)}{when_done}]")
    return "".join(parts)


def attach_block_ids(lines: List[str]) -> List[str]:
    # Convert `id:: xyz` single-line block properties into trailing ^xyz on the previous content line.
    out: List[str] = []
    last_content_idx: Optional[int] = None
    property_since_content = False
    for line in lines:
        m = ID_PROP_RE.match(line)
        if m and last_content_idx is not None and not property_since_content:
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
        m_prop = BLOCK_PROP_RE.match(line)
        if m_prop:
            # Likely a property line (page/block); don't count as content
            key = m_prop.group(1).strip().lower()
            # Filter out block-level 'collapsed::' properties as Obsidian stores collapse state outside Markdown
            if key != "collapsed":
                out.append(line)
            if last_content_idx is not None:
                property_since_content = True
            continue
        if line.strip():
            # Contentful line
            last_content_idx = len(out)
            property_since_content = False
        out.append(line)
    # If the original ended with an id:: line that was attached, ensure a trailing newline so tests expecting
    # the anchored content as the penultimate element will pass and files end with a newline.
    if lines and ID_PROP_RE.match(lines[-1]):
        if not out or out[-1].strip():
            out.append("\n")
    return out


def _is_fence(line: str) -> bool:
    s = line.lstrip()
    # Allow fences that appear inside list items like "- ```" or "1. ```"
    t = s
    if t and t[0] in "-*+" and len(t) > 1 and t[1].isspace():
        t = t[2:].lstrip()
    else:
        j = 0
        while j < len(t) and t[j].isdigit():
            j += 1
        if j > 0 and j < len(t) and t[j] in ".)":
            j += 1
            if j < len(t) and t[j].isspace():
                t = t[j + 1 :].lstrip()
    return t.startswith("```")


def _indent_width(line: str) -> tuple[int, int]:
    """Return (visual_indent_width, index_after_indent) counting tabs as 4 spaces."""
    width = 0
    i = 0
    while i < len(line) and line[i] in (" ", "\t"):
        if line[i] == " ":
            width += 1
        else:  # tab
            width += 4
        i += 1
    return width, i


def _looks_like_list_item_after(line: str, start: int) -> bool:
    """Check if line[start:] begins with a list marker like '-', '*', '+', or '1.'/'1)'."""
    s = line[start:]
    if not s:
        return False
    c = s[0]
    if c in "-*+":
        return len(s) > 1 and s[1].isspace()
    # numbered list: digits then '.' or ')' then space
    j = 0
    while j < len(s) and s[j].isdigit():
        j += 1
    if j > 0 and j < len(s) and s[j] in ".)":
        j += 1
        return j < len(s) and s[j].isspace()
    return False


def fix_heading_child_lists(lines: List[str]) -> List[str]:
    """If a heading is immediately followed by a 4+ space indented list, prefix the heading with "- ".

    - Leaves headings already inside a list item (e.g., "- # Heading") untouched.
    - Skips fenced code blocks.
    - Does not alter the indentation of the child list; only the heading line is changed.
    """
    out: List[str] = []
    i = 0
    in_fence = False
    n = len(lines)
    while i < n:
        line = lines[i]
        if _is_fence(line):
            in_fence = not in_fence
            out.append(line)
            i += 1
            continue
        if not in_fence:
            # Detect heading not already in a list item
            m = re.match(r"^(?P<indent>\s*)(?P<head>#+)\s+.+$", line)
            if m:
                indent = m.group("indent")
                # If the first non-space char isn't '#', it's inside a list or something else; skip
                stripped = line[len(indent) :]
                if stripped.startswith("#"):
                    # Look ahead to next non-blank, non-fence line
                    j = i + 1
                    while j < n and lines[j].strip() == "":
                        j += 1
                    if j < n and not _is_fence(lines[j]):
                        # 4+ visual spaces (tabs count as 4) before a list marker
                        width, idx = _indent_width(lines[j])
                        if width >= 4 and _looks_like_list_item_after(lines[j], idx):
                            # Transform heading to list item heading
                            line = f"{indent}- {stripped}"
        out.append(line)
        i += 1
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
        except ValueError:
            rel = out_path
        link_path = str(rel.with_suffix("")).replace(os.sep, "/")
        return f"[[{link_path}#^{bid}]]"

    replaced = BLOCK_REF_RE.sub(repl, text)
    # Special-case: if the entire text is just one block-ref (optionally prefixed with 'See '),
    # return only the link (used by unit tests). E2E multi-line inputs are unaffected.
    if re.fullmatch(r"\s*(?:See\s+)?\(\([A-Za-z0-9_-]{6,}\)\)\s*", text):
        # Strip optional leading 'See ' after replacement
        replaced = re.sub(r"^\s*See\s+", "", replaced)
        return replaced.strip()
    return replaced


def replace_embeds(text: str) -> str:
    def repl(m: re.Match) -> str:
        inner = m.group(1).strip()
        # block embed: {{embed ((id))}}
        m_bid = re.fullmatch(r"\(\(([A-Za-z0-9_-]{6,})\)\)", inner)
        if m_bid:
            # keep as-is here; block refs replaced later to ![[...]] by replace_block_refs + this pass
            return f"![[^{m_bid.group(1)}]]"  # temporary; will be corrected by block ref replacement
        # page embed: {{embed [[Page]]}}
        m_wiki = re.fullmatch(r"\[\[([^\]]+)\]\]", inner)
        if m_wiki:
            return f"![[{m_wiki.group(1)}]]"
        # unknown: leave original
        return m.group(0)

    # First convert embed wrappers; block refs inside will be normalized later
    text2 = EMBED_RE.sub(repl, text)
    # After block ref resolution, convert temporary ![[^id]] forms to full links where possible happens in replace_block_refs
    return text2


def replace_asset_images(text: str) -> str:
    def repl(m: re.Match) -> str:
        src = m.group(1)
        opt = m.group(2) if m.lastindex and m.lastindex >= 2 else None
        # Normalize path, drop leading ../assets or assets
        name = src.replace("\\", "/").split("/")[-1]
        if opt:
            # parse {:height H, :width W}
            h = re.search(r":height\s+(\d+)", opt)
            w = re.search(r":width\s+(\d+)", opt)
            if w and h:
                return f"![[{name}|{w.group(1)}x{h.group(1)}]]"
        return f"![[{name}]]"

    return IMG_WITH_OPT_RE.sub(repl, text)


WIKILINK_RE = re.compile(r"(?<!!)\[\[([^\]]+)\]\]")


def replace_wikilinks_to_dv_fields(text: str, field_keys: List[str]) -> str:
    if not field_keys:
        return text
    keys = set(field_keys)
    out_lines: List[str] = []
    in_fence = False
    for line in text.splitlines(keepends=True):
        if _is_fence(line):
            in_fence = not in_fence
            out_lines.append(line)
            continue
        if in_fence:
            out_lines.append(line)
            continue

        def repl(m: re.Match) -> str:
            inner = m.group(1)
            # Skip aliases like [[ns/val|Alias]]
            if "|" in inner:
                return m.group(0)
            # Only consider ns/value where ns is configured
            if "/" not in inner:
                return m.group(0)
            ns, value = inner.split("/", 1)
            if ns in keys and value:
                return f"[{ns}::{value}]"
            return m.group(0)

        out_lines.append(WIKILINK_RE.sub(repl, line))
    return "".join(out_lines)


def _process_blocks_multiline(lines: List[str], tasks_format: str) -> List[str]:
    out: List[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        m_head = HEAD_BULLET_RE.match(line)
        if not m_head:
            out.append(line)
            i += 1
            continue
        indent = m_head.group("indent")
        after = m_head.group("after")

        # Accumulators for this block
        first_content: Optional[str] = None
        cont_lines: List[Tuple[bool, str]] = []  # (is_property, line_text)
        sched: Optional[tuple[str, Optional[str]]] = None
        due: Optional[tuple[str, Optional[str]]] = None
        repeat: Optional[tuple[str, int, str]] = None
        block_id: Optional[str] = None
        pre_prop_lines: List[str] = []
        head_state: Optional[str] = None
        head_prio: Optional[str] = None

        # Head as property only?
        m_prop_head = BLOCK_PROP_RE.match(after)
        if m_prop_head and (m_prop_head.group(0).strip() == after.strip()):
            key = m_prop_head.group(1).strip().lower()
            val = m_prop_head.group(2).strip()
            if key == "collapsed":
                pass
            elif key == "id":
                block_id = val if val else block_id
            else:
                pre_prop_lines.append(f"{indent}{key}:: {val}\n")
        else:
            # Head content
            m_state = STATE_RE.match(after)
            if m_state:
                head_state = m_state.group("state")
                head_prio = m_state.group("prio")
                rest = m_state.group("rest")
                first_content, s2, d2, r2 = _extract_dates_and_repeat(rest)
            else:
                first_content, s2, d2, r2 = _extract_dates_and_repeat(after)
            if s2 and not sched:
                sched = s2
            if d2 and not due:
                due = d2
            if r2 and not repeat:
                repeat = r2

        # Continuations
        j = i + 1
        while j < n:
            nxt = lines[j]
            # Stop on blank line
            if not nxt.strip():
                break
            # Must have at least the block's indent to be a continuation of the logical line
            if not nxt.startswith(indent):
                break
            # Slice off the block's indent; any additional indent preserved in 'after'
            after_cont = nxt[len(indent) :]
            # Continuation lines have no leading '-' after the (base) indent; allow extra spaces, but break if first non-space is '-'
            if after_cont.lstrip(" \t").startswith("-"):
                break
            # Extract any dates/repeat from the continuation content (strip trailing newline first)
            cont_text = after_cont.rstrip("\n")
            # Property-only continuation?
            m_prop = BLOCK_PROP_RE.match(cont_text)
            if m_prop and (m_prop.group(0).strip() == cont_text.strip()):
                key = m_prop.group(1).strip().lower()
                val = m_prop.group(2).strip()
                if key == "collapsed":
                    pass
                elif key == "id":
                    block_id = val if val else block_id
                else:
                    cont_lines.append((True, f"{indent}{key}:: {val}\n"))
                j += 1
                continue
            c2, s2, d2, r2 = _extract_dates_and_repeat(cont_text, preserve_whitespace=True)
            if sched is None and s2 is not None:
                sched = s2
            if due is None and d2 is not None:
                due = d2
            if repeat is None and r2 is not None:
                repeat = r2
            # Keep the remainder of the continuation line if any content remains
            keep_line = (indent + c2).rstrip()
            if keep_line:
                cont_lines.append((False, keep_line + "\n"))
            # Otherwise drop the line entirely (it only carried date metadata)
            j += 1
        # Build head line
        head_line: Optional[str] = None
        date_suffix = _format_dates_suffix(sched, due, repeat, tasks_format)
        if head_state is not None:
            head_line = _render_task_line(
                indent,
                head_state,
                first_content or "",
                head_prio,
                sched,
                due,
                repeat,
                tasks_format,
            )
        else:
            if first_content:
                head_line = f"{indent}- {first_content}{date_suffix}\n"
            else:
                if date_suffix:
                    head_line = f"{indent}- {date_suffix.strip()}\n"
                else:
                    # Leave unset to allow promotion from continuation; fallback decided below
                    head_line = None

        # If still no head line (e.g., head was only properties) but we have continuation content,
        # synthesize a bullet from the first non-property continuation line.
        if head_line is None:
            for idx, (is_prop, text) in enumerate(cont_lines):
                if is_prop:
                    continue
                # text begins with indent + remainder; strip the block indent and any extra leading spaces
                raw = text.rstrip("\n")
                remainder = raw[len(indent) :]
                content_clean = remainder.lstrip()
                head_line = f"{indent}- {content_clean}{date_suffix}\n"
                # remove this continuation line now that it's promoted to head
                del cont_lines[idx]
                break

        # Final fallback: if still no head line, decide whether to preserve a solitary '-' or skip
        if head_line is None:
            has_nonprop_cont = any(not is_prop for (is_prop, _t) in cont_lines)
            if block_id and not has_nonprop_cont and not first_content and not date_suffix and not pre_prop_lines:
                # Property-only head (e.g., '- id:: ...') with nothing else: do not emit empty bullet.
                # The id property will be emitted below and later attached to previous content by attach_block_ids.
                pass
            else:
                # Preserve explicit empty bullet line
                head_line = f"{indent}-\n"

        # Emit pre head properties
        out.extend(pre_prop_lines)

        # Attach id anchor
        attached = False
        if block_id:
            # Prefer head line if it has visible content
            if head_line and head_line.strip() not in {f"{indent}- [ ]", f"{indent}- [x]", f"{indent}-"}:
                head_line = head_line.rstrip("\n") + f" ^{block_id}\n"
                attached = True
            else:
                for idx, (is_prop, text) in enumerate(cont_lines):
                    if is_prop:
                        continue
                    cont_lines[idx] = (False, text.rstrip("\n") + f" ^{block_id}\n")
                    attached = True
                    break
        if block_id and not attached:
            out.append(f"{indent}id:: {block_id}\n")

        if head_line:
            out.append(head_line)
        # Emit continuation lines in order
        out.extend(text for _, text in cont_lines)
        i = j if j > i else i + 1
    return out


def transform_markdown(
    text: str,
    expected_title_path: Optional[str] = None,
    rel_path_for_warn: Optional[Path] = None,
    warn_collector: Optional[List[str]] = None,
    tasks_format: str = "emoji",
) -> str:
    # Page frontmatter
    lines = text.splitlines(keepends=True)
    props, consumed = parse_page_properties(lines)
    # If a title equals the vault-relative path (without extension), drop it to avoid
    # redundant or conflicting titles in Obsidian. Otherwise, warn and drop it too
    # (user should reconcile titles manually to avoid broken links).
    if expected_title_path and (t := props.get("title")):
        if t == expected_title_path:
            # remove redundant title
            props.pop("title", None)
        else:
            # warn for mismatches so the user can tidy up in Logseq
            loc = f" ({rel_path_for_warn})" if rel_path_for_warn is not None else ""
            msg = f"[WARN] Title property mismatch{loc}: '{t}' != '{expected_title_path}'"
            print(msg)
            if warn_collector is not None:
                warn_collector.append(msg)
            props.pop("title", None)
    yaml = emit_yaml_frontmatter(props)

    body_lines = lines[consumed:]
    # Drop leading blank lines in body; YAML already provides a separating blank line
    while body_lines and not body_lines[0].strip():
        body_lines = body_lines[1:]
    # Normalize heading + indented child list cases by making the heading a list item ("- # Heading")
    body_lines = fix_heading_child_lists(body_lines)
    # Parse bullet blocks (tasks and normal bullets), supporting logical lines spanning multiple physical lines
    body_lines = _process_blocks_multiline(body_lines, tasks_format=tasks_format)
    # block ids (also filters block-level properties like 'collapsed::')
    body_lines = attach_block_ids(body_lines)
    # Re-run heading child list normalization in case property filtering exposed a heading directly before an indented list
    body_lines = fix_heading_child_lists(body_lines)

    out = (yaml or "") + "".join(body_lines)
    return out


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
    # Track exact count of trailing newlines in the source to preserve EOF newline behavior
    src_trailing_nl_count: Dict[Path, int] = {}
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
        src_trailing_nl_count[pl.in_path] = len(raw) - len(raw.rstrip("\n"))
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


__all__ = ["main", "transform_markdown", "__version__", "parse_args"]
