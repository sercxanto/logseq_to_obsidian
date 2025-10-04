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

## How to add new features

See below for details on the several items. It is not necessary to follow the list
in this specific order. Take it as reminder to not forget something:

- Add requirements for traceability
- Implement the change in the main script
- Add unit tests
- Add E2E tests if it makes sense
- Check that linting finds no issues and old and new tests are passing
- Adapt `README.md` to describe new behavior for users

### Linting (Ruff)

To check if there are linting issues run:

```shell
poetry run ruff check .
```

Some issues could be fixed automatically by:

```shell
poetry run ruff check . --fix
```
Optional formatting:

```shell
poetry run ruff format .
```

### Testing

To run all tests (unit and E2E):

```shell
poetry run pytest
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
poetry run python -m tasks
```
This helper uses the same pytest configuration, so coverage is collected automatically.

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
