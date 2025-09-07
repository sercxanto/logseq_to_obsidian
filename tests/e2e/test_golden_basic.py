from pathlib import Path

import pytest

from tests.helpers import compare_trees, run_converter


@pytest.mark.req("REQ-FRONTMATTER-001")
@pytest.mark.req("REQ-FRONTMATTER-002")
@pytest.mark.req("REQ-FRONTMATTER-003")
@pytest.mark.req("REQ-SPACING-001")
@pytest.mark.req("REQ-TASKS-001")
@pytest.mark.req("REQ-TASKS-002")
@pytest.mark.req("REQ-BLOCKID-001")
@pytest.mark.req("REQ-BLOCKREF-001")
@pytest.mark.req("REQ-LINKPATH-001")
@pytest.mark.req("REQ-STRUCTURE-001")
@pytest.mark.req("REQ-STRUCTURE-002")
def test_golden_basic(tmp_path: Path):
    src = Path("tests/fixtures/logseq/basic").resolve()
    out = tmp_path / "out"
    expected = Path("tests/golden/basic").resolve()

    code = run_converter(src, out)
    assert code == 0

    ok, msg = compare_trees(out, expected)
    assert ok, msg


@pytest.mark.req("REQ-FRONTMATTER-001")
@pytest.mark.req("REQ-FRONTMATTER-002")
@pytest.mark.req("REQ-FRONTMATTER-003")
@pytest.mark.req("REQ-SPACING-001")
@pytest.mark.req("REQ-TASKS-001")
@pytest.mark.req("REQ-TASKS-002")
@pytest.mark.req("REQ-TASKS-004")
@pytest.mark.req("REQ-TASKS-005")
@pytest.mark.req("REQ-BLOCKID-001")
@pytest.mark.req("REQ-BLOCKREF-001")
@pytest.mark.req("REQ-LINKPATH-001")
@pytest.mark.req("REQ-STRUCTURE-001")
@pytest.mark.req("REQ-STRUCTURE-002")
@pytest.mark.req("REQ-JOURNALS-001")
@pytest.mark.req("REQ-JOURNALS-002")
def test_golden_with_options(tmp_path: Path):
    src = Path("tests/fixtures/logseq/basic").resolve()
    out = tmp_path / "out"
    expected = Path("tests/golden/basic_opts").resolve()

    code = run_converter(
        src,
        out,
        "--daily-folder",
        "Daily Notes",
    )
    assert code == 0

    ok, msg = compare_trees(out, expected)
    assert ok, msg
