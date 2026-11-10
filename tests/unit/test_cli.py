from __future__ import annotations

import pytest

from logseq_to_obsidian import __version__, parse_args


@pytest.mark.req("REQ-CLI-001")
def test_non_utf8_markdown_is_copied_unchanged(tmp_path, capsys):
    import logseq_to_obsidian as l2o

    vault = tmp_path / "vault"
    (vault / "pages").mkdir(parents=True)
    raw = "caf\xe9 \xfcnicode\n- TODO item\n".encode("latin-1")
    (vault / "pages" / "latin.md").write_bytes(raw)
    (vault / "pages" / "ok.md").write_text("# hello\nplain ascii\n", encoding="utf-8")
    out = tmp_path / "out"

    code = l2o.main(["--input", str(vault), "--output", str(out)])

    assert code == 0
    assert (out / "latin.md").read_bytes() == raw
    assert "non-UTF-8" in capsys.readouterr().out


@pytest.mark.req("REQ-CLI-001")
def test_version_flag_reports_package_version(capsys):
    with pytest.raises(SystemExit) as excinfo:
        parse_args(["--version"])

    assert excinfo.value.code == 0
    out = capsys.readouterr().out.strip()
    assert __version__ in out
