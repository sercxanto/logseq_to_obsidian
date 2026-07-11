# Agent instructions

Before changing anything in this repository, read `CONTRIBUTING.md`. It is the
canonical guide to the development workflow — running the CLI, linting with
Ruff, running the test suite with its 80% coverage gate, adding Towncrier
changelog fragments, and keeping requirements traceability in sync. Follow that
checklist for every contribution.

## Notes for agents

- When merging a Dependabot dependency-bump PR, remember to add a
  `<PR-number>.fixed.md` changelog fragment for it (Dependabot does not create
  one). This step is easy to miss because the bump PR itself touches no
  `.changelog/` files. See the changelog section of `CONTRIBUTING.md`.
