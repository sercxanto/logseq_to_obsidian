# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!-- towncrier release notes start -->

## [0.2.0] - 2026-07-25

### Added

- Remove remaining `logseq.*` namespaced block properties (e.g., `logseq.toc::`). ([#41](https://github.com/sercxanto/logseq_to_obsidian/issues/41))
- Convert `{{tweet URL}}` embeds to Markdown `![](URL)`. ([#41](https://github.com/sercxanto/logseq_to_obsidian/issues/41))
- Convert task date properties (created/completed/done/cancelled/canceled) to Obsidian Tasks emoji suffixes (➕/✅/❌), with or without a leading dot and with or without `[[]]` around the date. ([#41](https://github.com/sercxanto/logseq_to_obsidian/issues/41))
- Remove `:LOGBOOK:` ... `:END:` time-tracker blocks from the text. ([#41](https://github.com/sercxanto/logseq_to_obsidian/issues/41))
- Convert Logseq ^^highlight^^ syntax to Obsidian ==highlight== syntax, skipping fenced code blocks. ([#41](https://github.com/sercxanto/logseq_to_obsidian/issues/41))
- Convert Logseq org-mode blocks (#+BEGIN/END) to Obsidian format: QUOTE to blockquotes, NOTE/TIP/WARNING/IMPORTANT/CAUTION/EXAMPLE to callouts, COMMENT to %% syntax. Supports nested blocks, bold title extraction, and indented blocks inside list items. ([#41](https://github.com/sercxanto/logseq_to_obsidian/issues/41))
- Convert Logseq numbered lists (logseq.order-list-type:: number property) to standard Markdown numbered lists (1. 2. 3.) with proper sequential numbering and nesting support. ([#41](https://github.com/sercxanto/logseq_to_obsidian/issues/41))
- Test and advertise support for Python 3.13 and 3.14. ([#56](https://github.com/sercxanto/logseq_to_obsidian/issues/56))

### Fixed

- Quote wiki-link references in YAML front matter so Obsidian recognizes them as links. Single references like `[[Page]]` are wrapped in double quotes; comma-separated references are expanded into a YAML list of quoted items. ([#41](https://github.com/sercxanto/logseq_to_obsidian/issues/41))
- Bump pytest-cov from 7.0.0 to 7.1.0 ([#44](https://github.com/sercxanto/logseq_to_obsidian/issues/44))
- Bump ruff from 0.15.2 to 0.15.21 ([#52](https://github.com/sercxanto/logseq_to_obsidian/issues/52))
- Bump poethepoet from 0.37.0 to 0.48.0 ([#57](https://github.com/sercxanto/logseq_to_obsidian/issues/57))
- Bump pytest from 8.4.2 to 9.1.1 ([#58](https://github.com/sercxanto/logseq_to_obsidian/issues/58))
- Bump ruff from 0.15.21 to 0.16.0 ([#59](https://github.com/sercxanto/logseq_to_obsidian/issues/59))

### Removed

- Drop support for Python 3.9 (end-of-life since October 2025); the minimum supported version is now Python 3.10. Beyond the end-of-life, the 3.9 CI job had also started failing at environment setup: `pipx` could no longer install Poetry under 3.9 because a transitive dependency now uses `dataclass(slots=...)`, which is only available on Python 3.10+. ([#53](https://github.com/sercxanto/logseq_to_obsidian/issues/53))


## [0.1.3] - 2026-03-01

### Fixed

- Convert Logseq `{{video ...}}` and `{{youtube ...}}` macros to Markdown embeds for Obsidian (#33)
- Ignore top-level .git folders in input vaults during conversion (#37)
- Bump ruff from 0.14.14 to 0.15.2 (#38)


## [0.1.2] - 2026-01-25

### Fixed

- Fix images followed by an indentation (#26)
- Warn and collect planner warnings (percent-encoded filenames and whiteboards) for clearer conversion output. (#27)
- Bump ruff from 0.14.7 to 0.14.13 (#30)


## [0.1.1] - 2025-12-07

### Fixed

- Fixed alias link conversion with syntax `[Display Name]([[Page Name]])` (#10)
- Fixed tags with unicode characters (#11)
- Bump ruff from 0.13.3 to 0.14.5 (#15)
- Bump ruff from 0.14.5 to 0.14.6 (#20)
- Bump ruff from 0.14.6 to 0.14.7 (#22)
- Fixed developer documentation


## [0.1.0] - 2025-10-05

First public version.
