from pathlib import Path

import pytest

from tests.helpers import run_converter


def _mtime_s(p: Path) -> int:
    return int(p.stat().st_mtime)


@pytest.mark.req("REQ-MTIME-001")
def test_preserve_times_for_markdown_and_assets(tmp_path: Path):
    src = Path("tests/fixtures/logseq/basic").resolve()
    out = tmp_path / "out"
    code = run_converter(src, out)
    assert code == 0

    # Markdown files
    assert _mtime_s(out / "Foo.md") == _mtime_s(src / "pages/Foo.md")
    assert _mtime_s(out / "a/b.md") == _mtime_s(src / "pages/a___b.md")

    # Assets
    assert _mtime_s(out / "assets/picture.png") == _mtime_s(src / "assets/picture.png")
    assert _mtime_s(out / "assets/img.txt") == _mtime_s(src / "assets/img.txt")
