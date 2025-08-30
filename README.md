Logseq → Obsidian Converter

Overview

- Converts a Logseq vault (Markdown flavor) to Obsidian-friendly Markdown.
- Handles page properties → YAML front matter, task statuses, block IDs, and block references.
- Preserves folder structure by default; configurable options for daily notes and pages.

Features

- Page properties (`key:: value`) at top → YAML front matter.
- Special mappings:
  - `alias::` or `aliases::` → `aliases: []` (array)
  - `tags::` → `tags: []` (array, without `#`)
  - `title::` → `title:`
- Task markers:
  - `- TODO Something` → `- [ ] Something`
  - `- DONE Something` → `- [x] Something`
  - Other states (`DOING`, `LATER`, `WAITING`, `CANCELLED`) → unchecked by default; optionally annotate.
- Block IDs:
  - `id:: <uuid>` lines are converted to Obsidian block anchors by appending `^<uuid>` to the owning block line.
- Block references:
  - `((<uuid>))` → `[[<FileName>#^<uuid>]]` (resolved by scanning all files first).
- Journals:
  - Option to rename `YYYY_MM_DD.md` → `YYYY-MM-DD.md` and/or move journals to a specific folder.
- Assets and other files are copied as-is.

Usage

```
python3 logseq_to_obsidian.py \
  --input /path/to/logseq-vault \
  --output /path/to/obsidian-vault \
  --rename-journals \
  --daily-folder "Daily Notes" \
  --flatten-pages \
  --annotate-status \
  --dry-run
```

Common options

- `--input`: Path to the Logseq vault root (folder containing `pages/`, `journals/`, etc.).
- `--output`: Destination Obsidian vault directory (created if not exists).
- `--rename-journals`: Convert journal filenames from `YYYY_MM_DD` to `YYYY-MM-DD`.
- `--daily-folder <name>`: Move `journals/` into this folder in the output. If omitted, keeps `journals/`.
- `--flatten-pages`: Move files from `pages/` to the output root (retains subfolders).
- `--annotate-status`: For non-`TODO/DONE` task states, append `(status: STATE)` after the task text.
- `--dry-run`: Print planned changes without writing files.

Notes and assumptions

- Only Markdown (`.md`) files are transformed; other files are copied.
- Block reference resolution requires that `id::` appears for referenced blocks in the source files.
- This tool is conservative: it preserves unknown page properties in YAML.

Limitations

- Does not parse or migrate the Logseq database; operates purely on Markdown files.
- Complex block property drawers beyond `id::` are not transformed (left in place).

Development

- Poetry setup (dev only; the script itself has no runtime deps):
  - `poetry install --with dev --no-root`
  - Run the script: `poetry run python logseq_to_obsidian.py --help`

Linting (Ruff)

- Check lint: `poetry run ruff check .`
- Auto-fix simple issues: `poetry run ruff check . --fix`
- Optional formatting: `poetry run ruff format .`

Testing

- Install dev deps: `poetry install --with dev --no-root`
- Run unit and E2E tests: `poetry run pytest`
