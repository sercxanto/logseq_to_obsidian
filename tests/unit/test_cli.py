from __future__ import annotations

import pytest

from logseq_to_obsidian import __version__, parse_args


@pytest.mark.req("REQ-CLI-001")
def test_version_flag_reports_package_version(capsys):
    with pytest.raises(SystemExit) as excinfo:
        parse_args(["--version"])

    assert excinfo.value.code == 0
    out = capsys.readouterr().out.strip()
    assert __version__ in out
