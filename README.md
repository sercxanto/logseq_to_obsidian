Logseq → Obsidian Converter

Overview

- Converts a Logseq vault (Markdown flavor) to Obsidian-friendly Markdown.
- Handles page properties → YAML front matter, task statuses, block IDs, and block references.
- Preserves non-page folders; moves `pages/` content to the vault root.

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
- Embeds:
  - `{{embed ((<uuid>))}}` → `![[<FileName>#^<uuid>]]`
  - `{{embed [[Some Page]]}}` → `![[Some Page]]`
- Images in assets:
  - `![alt](../assets/image.png)` or `![alt](assets/image.png)` → `![[image.png]]` (alt text is not preserved)
- Journals:
  - Renames `YYYY_MM_DD.md` → `YYYY-MM-DD.md` and can move journals to a specific folder.
- Assets and other files are copied as-is.

Usage

```
python3 logseq_to_obsidian.py \
  --input /path/to/logseq-vault \
  --output /path/to/obsidian-vault \
  --daily-folder "Daily Notes" \
  --annotate-status \
  --dry-run
```

Common options

- `--input`: Path to the Logseq vault root (folder containing `pages/`, `journals/`, etc.).
- `--output`: Destination Obsidian vault directory (created if not exists).
- `--daily-folder <name>`: Move `journals/` into this folder in the output. If omitted, keeps `journals/`.
- Pages are always flattened to the vault root; see "File placement rules" below.
- `--annotate-status`: For non-`TODO/DONE` task states, append `(status: STATE)` after the task text.
- `--dry-run`: Print planned changes without writing files.

Notes and assumptions

- Only Markdown (`.md`) files are transformed; other files are copied.
- Block reference resolution requires that `id::` appears for referenced blocks in the source files.
- This tool is conservative: it preserves unknown page properties in YAML.
- Block-level `collapsed::` properties are ignored; Obsidian stores list collapse state outside Markdown.

Limitations

- Does not parse or migrate the Logseq database; operates purely on Markdown files.
- Complex block property drawers beyond `id::` are not transformed (left in place).
- Skips Logseq's internal `logseq/` metadata folder.
- Skips Logseq whiteboards (`whiteboards/`); a warning is emitted since Obsidian cannot read Logseq's whiteboard format.

File placement rules

- Pages: All files from Logseq's `pages/` are placed at the root of the Obsidian vault.
- Nested paths: Logseq encodes subfolders in page filenames using three underscores `___`.
  - Example: `pages/a___b.md` becomes `a/b.md`.

Journals

- Journal filenames are always renamed from `YYYY_MM_DD.md` to `YYYY-MM-DD.md`.
- Logseq already displays journal page links using dashes (e.g., `[[2024-08-30]]`), so link text does not need conversion.

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

Checks

- Lint + tests: `poetry run python -m tasks`
- Autofix + tests: `poetry run python -m tasks fix`

Requirements Traceability

- Spec file: `docs/spec/requirements.yml` lists requirement IDs and their status.
- Status meanings:
  - `active`: enforced; must be implemented and covered by tests.
  - `planned`/`draft`: defined but not required yet; coverage not enforced.
  - `deprecated`: no longer applicable; ignored by coverage.
  - `experimental`: optional/behind a flag; coverage not enforced.
- Tests link to requirements with `@pytest.mark.req("REQ-…")` and golden suites include a `manifest.yml` listing covered IDs.
- The test run validates that:
  - Every referenced requirement exists in the spec.
  - All `active` requirements are covered by at least one test or golden manifest.
