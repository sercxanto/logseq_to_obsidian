# Contributing

Please carefully read the information and instructions in this file if you like
to contribute.

The package is intentionally kept free from runtime dependencies beyond the standard library.
Development/test dependencies (pytest, ruff, etc.) are managed by Poetry.

You can run the CLI via the installed console script or module entry point:

```shell
poetry run logseq-to-obsidian --help
# or
poetry run python -m logseq_to_obsidian --help
```

To install the development dependencies (and the package in editable mode) run:

```shell
poetry install --with dev
```

Routine automation lives in Poe (Poe the Poet) tasks. Run them via `poetry run poe <task>`.
Poe detects the Poetry environment automatically and runs commands inside the virtual
environment managed by poetry.

So to save typing, it is benefical to install poe:

```shell
pipx install poethepoet
```

The above example `poetry run poe <task>` could be written

```shell
poe <task>
```

## How to add new features

See below for details on the several items. It is not necessary to follow the list
in this specific order. Take it as reminder to not forget something:

- Add requirements for traceability
- Implement the change in the main script
- Add unit tests
- Add E2E tests if it makes sense
- Check that linting finds no issues and old and new tests are passing
- Adapt `README.md` to describe new behavior for users
- Add a Towncrier fragment in `.changelog/` describing the change

### Linting (Ruff)

To check if there are linting issues run:

```shell
poetry run ruff check .
```

or shorter:

```shell
poe lint
```

Some issues could be fixed automatically by:

```shell
poetry run ruff check . --fix
```

or shorter:

```shell
poe fixlint
```

Optional formatting:

```shell
poetry run ruff format .
```

or shorter:

```shell
poe format
```

### Testing

To run all tests (unit and E2E):

```shell
poetry run pytest
```

or shorter:

```shell
poe test
```

The unit tests are stored in `tests/unit`.
The e2e tests (starting the command line) are stored in `tests/e2e`.
The pytest run emits code coverage information and writes `coverage.xml` in the project root for IDE/CI integration.
Coverage must stay at or above 80% (the test run fails otherwise), and the CLI shim in `src/logseq_to_obsidian/__main__.py` is excluded from the report.

For E2E tests the input folder with an example logseq vault is stored in
`fixtures/logseq/basic`. This input folder is can be converted with multiple command
line options, see `e2e/test_golden_basic.py`.
The expected output is stored in subfolders of `tests/golden`.

To do linting and tests in one step run:

```shell
poe testandlint
```

This helper uses the same pytest configuration, so coverage is collected automatically.

### Changelog entries (Towncrier)

- Every user-visible change should come with a fragment file in `.changelog/`.
- Name each fragment `<number>.<type>.md`, where `<number>` is the tracking
  issue number or, if there is none, the pull request number (e.g.
  `123.added.md`). Towncrier turns this numeric prefix into a linked `(#123)`
  reference in the changelog via the `issue_format` setting. Avoid a purely
  descriptive name (e.g. `drop-python-39.removed.md`): Towncrier accepts it,
  but the prefix is rendered verbatim and yields no working link. If you only
  learn the PR number after opening the PR, rename the fragment then.
- Valid fragment types are `added`, `changed`, `deprecated`, `removed`,
  `fixed` and `security`.
- Dependency updates count too. When merging a Dependabot (or manual)
  dependency bump, add a `<PR-number>.fixed.md` fragment such as
  `Bump ruff from 0.15.2 to 0.15.21` — Dependabot does not create the fragment
  itself, so it has to be added by hand to keep the changelog consistent.
- Inspect pending fragments with `poetry run poe draftchangelog`.
- When preparing a release, run `poetry run poe changelog` or use the `release` task (see below) to fold fragments into `CHANGELOG.md`.

### Release workflow (Poe the Poet)

`poe release [patch|minor|major]` runs lint + tests, bumps the version, updates `CHANGELOG.md` via Towncrier, commits, and tags `v<version>`.

If you like to do single steps instead have a look at the defined tasks: `poe help`.

### Publish the release

Publishing is automated by the `Release` GitHub Actions workflow
(`.github/workflows/release.yml`). It is triggered by a new `v*` tag on the
release commit, which you can create in one of two ways:

- From the command line, push the release commit and its tag:

  ```shell
  git push && git push origin v$(poetry version -s)
  ```

- In the GitHub web UI (e.g. after merging the release commit through a pull
  request), open *Releases → Draft a new release*, enter the new tag
  `v<version>` with `main` as target, use `<version>` (without `v`) as title
  and publish the release. You can leave the description empty; the workflow
  fills it in from `CHANGELOG.md`. Saving
  only a draft does not create the tag and does not trigger the workflow.

The workflow:

1. checks that the tag matches the version in `pyproject.toml`,
2. runs lint and tests, builds the sdist and wheel, and smoke-tests the wheel
   (installs it into a fresh venv, checks `--version` and converts
   `tests/fixtures/logseq/basic`, comparing the result with `tests/golden/basic`),
3. publishes to PyPI via [trusted publishing](https://docs.pypi.org/trusted-publishers/)
   (OIDC, no API token needed) from the `pypi` GitHub environment,
4. creates the GitHub release (or updates the one published in the web UI)
   with the changelog section of that version as release notes and the built
   files attached. Release notes you wrote by hand are kept.

One-time setup: on PyPI, add a trusted publisher for the project with owner
`sercxanto`, repository `logseq_to_obsidian`, workflow `release.yml` and
environment `pypi`. On GitHub, create the environment `pypi` under
*Settings → Environments* (optionally with required reviewers and restricted
to `v*` tags).

### Requirements Traceability

- Spec file: `docs/spec/requirements.yml` lists requirement IDs and their status.
- Status meanings:
    - `active`: enforced; must be implemented and covered by tests.
    - `planned`/`draft`: defined but not required yet; coverage not enforced.
    - `deprecated`: no longer applicable; ignored by coverage.
    - `experimental`: optional/behind a flag; coverage not enforced.
- Tests link to requirements with `@pytest.mark.req("REQ-...")` and golden suites include a `manifest.yml` listing covered IDs.
- The test run validates that:
    - Every referenced requirement exists in the spec.
    - All `active` requirements are covered by at least one test or golden manifest.
