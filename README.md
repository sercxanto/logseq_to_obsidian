# Logseq → Obsidian Converter

![tests](https://github.com/sercxanto/logseq_to_obsidian/actions/workflows/tests.yml/badge.svg)
![lint](https://github.com/sercxanto/logseq_to_obsidian/actions/workflows/lint.yml/badge.svg)
[![codecov](https://codecov.io/gh/sercxanto/logseq_to_obsidian/graph/badge.svg?token=bTE5A3niNf)](https://codecov.io/gh/sercxanto/logseq_to_obsidian)

## Overview

- Converts a Logseq vault (Markdown flavor) to Obsidian-friendly Markdown.
- Handles page properties → YAML front matter, task statuses, block IDs, and block references.
- Preserves non-page folders; moves `pages/` content to the vault root.

## Features

- Page properties (`key:: value`) at top → YAML front matter.
- Special mappings:
    - `alias::` or `aliases::` → `aliases: []` (array)
    - `tags::` → `tags: []` (array, without `#`)
    - `title::` → omitted (Obsidian only uses the filename as the note name). If the Logseq title mismatches the vault-relative output path, a warning is emitted so you can tidy it up.
- Task markers:
    - Recognized at the start of a list item (`- STATE ...`, uppercase only):
        - `TODO`, `DOING`, `LATER`, `NOW`, `WAIT`, `WAITING`, `IN-PROGRESS` → `- [ ] ...`
        - `DONE`, `CANCELED`, `CANCELLED` → `- [x] ...`
    - Priorities right after state (`[#A|#B|#C]`):
        - Emoji: A→`⏫`, B→`🔼`, C→`🔽` (appended at end)
        - Dataview: `[priority::high|medium|low]` (appended at end; omitted if none)
    - Dates anywhere after the state:
        - `SCHEDULED: <YYYY-MM-DD [Dow] [HH:MM] [repeater]>` → Emoji: `⏳ YYYY-MM-DD[ HH:MM]`; Dataview: `[scheduled::YYYY-MM-DD[ HH:MM]]`
        - `DEADLINE: <YYYY-MM-DD [Dow] [HH:MM] [repeater]>` → Emoji: `📅 YYYY-MM-DD[ HH:MM]`; Dataview: `[due::YYYY-MM-DD[ HH:MM]]`
        - Repeaters: `. +N<u>` or `++N<u>` → “every N <unit> when done”; `+N<u>` → “every N <unit>”
        - Units: `y`=year(s), `m`=month(s), `w`=week(s), `d`=day(s), `h`=hour(s); pluralized when N ≠ 1
        - Ordering: append priority, then scheduled, then due, then repeat; block anchors (e.g., `^id`) remain last
- Block IDs:
    - `id:: <uuid>` lines are converted to Obsidian block anchors by appending `^<uuid>` to the owning block line.
- Block references:
    - `((<uuid>))` → `[[<FileName>#^<uuid>]]` (resolved by scanning all files first).
    - Optional: convert configured wikilinks `[[key/value]]` to Dataview inline fields `[key::value]` (non-embed, no alias, not inside code blocks).
- Embeds:
    - `{{embed ((<uuid>))}}` → `![[<FileName>#^<uuid>]]`
    - `{{embed [[Some Page]]}}` → `![[Some Page]]`
- Images in assets:
    - `![alt](../assets/image.png)` or `![alt](assets/image.png)` → `![[image.png]]` (alt text is not preserved)
    - With size attributes: `![alt](../assets/image.png){:height H, :width W}` → `![[image.png|WxH]]` (width × height)
- Headings followed by indented lists:
    - If a heading line is immediately followed by an indented list (≥4 spaces or tabs), prefix the heading with `- ` (i.e., `- # Heading`).
    - Rationale: Logseq treats such lists as children of the heading; Obsidian otherwise renders them as quoted/code blocks. This keeps folding behavior aligned.
- Journals:
    - Renames `YYYY_MM_DD.md` → `YYYY-MM-DD.md` and can move journals to a specific folder.
- Assets and other files are copied as-is.

## Installation

- pipx (recommended): `pipx install logseq-to-obsidian`
- pip: `pip install logseq-to-obsidian`
- From Git (development version): `pipx install "git+https://github.com/sercxanto/logseq_to_obsidian.git@main"`

## Usage

```
logseq-to-obsidian \
  --input /path/to/logseq-vault \
  --output /path/to/obsidian-vault \
  --daily-folder "Daily Notes" \
  --tasks-format emoji \
  --field-key project \
  --field-key topic \
  --dry-run
```

Alternatively (no console script), you can run:

```
python -m logseq_to_obsidian \
  --input /path/to/logseq-vault \
  --output /path/to/obsidian-vault \
  --dry-run
```

## Options

- `--input`: Path to the Logseq vault root (folder containing `pages/`, `journals/`, etc.).
- `--output`: Destination Obsidian vault directory (created if not exists).
- `--daily-folder <name>`: Move `journals/` into this folder in the output. If omitted, keeps `journals/`.
- `--tasks-format {emoji|dataview}`: Choose output format for Tasks metadata (priorities now; dates later). Default: `emoji`.
- `--field-key <key>`: Convert wikilinks of the form `[[key/value]]` to Dataview inline fields `[key::value]`. Repeatable for multiple keys.
- Pages are always flattened to the vault root; see "File placement rules" below.
- `--dry-run`: Print planned changes without writing files.

## Notes and assumptions

- Only Markdown (`.md`) files are transformed; other files are copied.
- Block reference resolution requires that `id::` appears for referenced blocks in the source files.
- This tool is conservative: it preserves unknown page properties in YAML.
- Block-level `collapsed::` properties are ignored; Obsidian stores list collapse state outside Markdown.

## Limitations

- Does not parse or migrate the Logseq database; operates purely on Markdown files.
- Complex block property drawers beyond `id::` are not transformed (left in place).
- Skips Logseq's internal `logseq/` metadata folder.
- Skips Logseq whiteboards (`whiteboards/`); a warning is emitted since Obsidian cannot read Logseq's whiteboard format.
    - Only normalizes heading + indented list patterns outside fenced code blocks; headings already inside list items are left unchanged.
- File times are preserved: output files keep the original source modification time (mtime) for both transformed Markdown and copied assets.

## File placement rules

- Pages: All files from Logseq's `pages/` are placed at the root of the Obsidian vault.
- Nested paths: Logseq encodes subfolders in page filenames using three underscores `___`.
    - Example: `pages/a___b.md` becomes `a/b.md`.

## Journals

- Journal filenames are always renamed from `YYYY_MM_DD.md` to `YYYY-MM-DD.md`.
- Logseq already displays journal page links using dashes (e.g., `[[2024-08-30]]`), so link text does not need conversion.

## Development / Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)
