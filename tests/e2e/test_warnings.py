from pathlib import Path

import pytest

from tests.helpers import run_converter


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.mark.req("REQ-BLOCKREF-003")
@pytest.mark.req("REQ-EMBED-005")
@pytest.mark.req("REQ-EMBED-001")
def test_unresolved_block_refs_are_kept_and_reported(tmp_path: Path, capsys):
    src = tmp_path / "in"
    out = tmp_path / "out"
    _write(src, "pages/Target.md", "- Known block\n  id:: known01\n")
    _write(
        src,
        "pages/Source.md",
        "- See ((known01)) and ((missing1))\n- {{embed ((known01))}}\n- {{embed ((missing2))}}\n- ((missing1))\n",
    )

    assert run_converter(src, out) == 0
    stdout = capsys.readouterr().out

    assert (out / "Source.md").read_text(encoding="utf-8") == (
        "- See [[Target#^known01]] and ((missing1))\n- ![[Target#^known01]]\n- {{embed ((missing2))}}\n- ((missing1))\n"
    )
    assert "[WARN] Unresolved block reference(s) in pages/Source.md: missing1, missing2 (left unchanged)" in stdout
    assert "Target.md: " not in stdout
    assert "Conversion completed with 1 warning(s)" in stdout


@pytest.mark.req("REQ-STRUCTURE-007")
def test_output_collision_keeps_first_file(tmp_path: Path, capsys):
    src = tmp_path / "in"
    out = tmp_path / "out"
    _write(src, "pages/a/b.md", "- from folder\n")
    _write(src, "pages/a___b.md", "- from namespace\n")

    assert run_converter(src, out) == 0
    stdout = capsys.readouterr().out

    assert (out / "a" / "b.md").read_text(encoding="utf-8") == "- from namespace\n"
    assert "skipping pages/a/b.md" in stdout
