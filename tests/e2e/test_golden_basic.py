from pathlib import Path

from tests.helpers import compare_trees, run_converter


def test_golden_basic(tmp_path: Path):
    src = Path("tests/fixtures/logseq/basic").resolve()
    out = tmp_path / "out"
    expected = Path("tests/golden/basic").resolve()

    code = run_converter(src, out)
    assert code == 0

    ok, msg = compare_trees(out, expected)
    assert ok, msg


def test_golden_with_options(tmp_path: Path):
    src = Path("tests/fixtures/logseq/basic").resolve()
    out = tmp_path / "out"
    expected = Path("tests/golden/basic_opts").resolve()

    code = run_converter(
        src,
        out,
        "--rename-journals",
        "--daily-folder",
        "Daily Notes",
        "--flatten-pages",
        "--annotate-status",
    )
    assert code == 0

    ok, msg = compare_trees(out, expected)
    assert ok, msg
