from __future__ import annotations

import pytest

from logseq_to_obsidian.planner import Options, collect_files


@pytest.mark.req("REQ-STRUCTURE-005")
def test_collect_files_warns_on_percent_encoded_filenames(tmp_path, capsys):
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    (input_dir / "pages").mkdir(parents=True)
    encoded = input_dir / "pages" / "Topic%3AName.md"
    encoded.write_text("content", encoding="utf-8")

    opts = Options(
        input_dir=input_dir,
        output_dir=output_dir,
        daily_folder=None,
        dry_run=True,
        tasks_format="emoji",
        field_keys=[],
    )

    warnings = []
    collect_files(opts, warn_collector=warnings)
    out = capsys.readouterr().out
    assert "percent-encoded filename" in out
    assert "pages/Topic%3AName.md" in out
    assert any("pages/Topic%3AName.md" in msg for msg in warnings)


@pytest.mark.req("REQ-STRUCTURE-005")
def test_collect_files_skips_warning_for_plain_filenames(tmp_path, capsys):
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    (input_dir / "assets").mkdir(parents=True)
    normal = input_dir / "assets" / "image.png"
    normal.write_text("x", encoding="utf-8")

    opts = Options(
        input_dir=input_dir,
        output_dir=output_dir,
        daily_folder=None,
        dry_run=True,
        tasks_format="emoji",
        field_keys=[],
    )

    warnings = []
    collect_files(opts, warn_collector=warnings)
    out = capsys.readouterr().out
    assert "percent-encoded filename" not in out
    assert warnings == []


@pytest.mark.req("REQ-STRUCTURE-004")
def test_collect_files_warns_on_whiteboards_directory(tmp_path, capsys):
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    (input_dir / "whiteboards").mkdir(parents=True)
    (input_dir / "whiteboards" / "board.edn").write_text("x", encoding="utf-8")

    opts = Options(
        input_dir=input_dir,
        output_dir=output_dir,
        daily_folder=None,
        dry_run=True,
        tasks_format="emoji",
        field_keys=[],
    )

    warnings = []
    collect_files(opts, warn_collector=warnings)
    out = capsys.readouterr().out
    assert "whiteboards" in out
    assert any("whiteboards" in msg for msg in warnings)
