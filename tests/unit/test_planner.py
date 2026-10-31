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


@pytest.mark.req("REQ-STRUCTURE-006")
def test_collect_files_skips_git_directory(tmp_path, capsys):
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    (input_dir / ".git").mkdir(parents=True)
    (input_dir / ".git" / "config").write_text("x", encoding="utf-8")
    (input_dir / "pages").mkdir(parents=True)
    (input_dir / "pages" / "Note.md").write_text("content", encoding="utf-8")

    opts = Options(
        input_dir=input_dir,
        output_dir=output_dir,
        daily_folder=None,
        dry_run=True,
        tasks_format="emoji",
        field_keys=[],
    )

    warnings = []
    plans = collect_files(opts, warn_collector=warnings)
    capsys.readouterr()

    assert all(".git" not in plan.in_path.parts for plan in plans)


def _opts(input_dir, output_dir):
    return Options(
        input_dir=input_dir,
        output_dir=output_dir,
        daily_folder=None,
        dry_run=True,
        tasks_format="emoji",
        field_keys=[],
    )


@pytest.mark.req("REQ-STRUCTURE-007")
@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("pages/a___b.md", "pages/a/b.md"),
        ("pages/Foo.md", "pages/foo.md"),
        ("journals/2024-01-01.md", "journals/2024_01_01.md"),
    ],
)
def test_collect_files_skips_output_collisions_with_warning(tmp_path, capsys, first, second):
    input_dir = tmp_path / "in"
    for rel in (second, first):  # creation order must not matter
        path = input_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rel, encoding="utf-8")

    warnings = []
    plans = collect_files(_opts(input_dir, tmp_path / "out"), warn_collector=warnings)
    out = capsys.readouterr().out

    assert [p.in_path.relative_to(input_dir).as_posix() for p in plans] == [first]
    assert len(warnings) == 1
    assert "Output path collision" in warnings[0]
    assert f"skipping {second}" in warnings[0]
    assert warnings[0] in out


@pytest.mark.req("REQ-STRUCTURE-007")
def test_collect_files_without_collisions_emits_no_warning(tmp_path, capsys):
    input_dir = tmp_path / "in"
    (input_dir / "pages").mkdir(parents=True)
    for name in ("b.md", "a.md", "a___b.md"):
        (input_dir / "pages" / name).write_text("x", encoding="utf-8")

    warnings = []
    plans = collect_files(_opts(input_dir, tmp_path / "out"), warn_collector=warnings)
    capsys.readouterr()

    assert warnings == []
    assert [p.in_path.name for p in plans] == ["a.md", "a___b.md", "b.md"]
