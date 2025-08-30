from __future__ import annotations

import filecmp
import os
from pathlib import Path
from typing import Iterable, Tuple

import logseq_to_obsidian as l2o


def run_converter(input_dir: Path, output_dir: Path, *args: str) -> int:
    argv = [
        "--input",
        str(input_dir),
        "--output",
        str(output_dir),
        *args,
    ]
    return l2o.main(argv)


def _iter_files(root: Path) -> Iterable[Path]:
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            p = Path(dirpath) / name
            yield p.relative_to(root)


def compare_trees(actual: Path, expected: Path) -> Tuple[bool, str]:
    actual_set = {p for p in _iter_files(actual)}
    expected_set = {p for p in _iter_files(expected)}
    if actual_set != expected_set:
        only_actual = sorted(str(p) for p in (actual_set - expected_set))
        only_expected = sorted(str(p) for p in (expected_set - actual_set))
        return False, f"Tree mismatch. Only in actual: {only_actual}; Only in expected: {only_expected}"

    for rel in sorted(actual_set):
        a = actual / rel
        e = expected / rel
        if a.suffix.lower() in {".md", ".txt"}:
            a_text = a.read_text(encoding="utf-8")
            e_text = e.read_text(encoding="utf-8")
            if a_text != e_text:
                return False, f"Content mismatch for {rel}:\n--- actual ---\n{a_text}\n--- expected ---\n{e_text}"
        else:
            # Binary/other: compare by bytes
            if not filecmp.cmp(a, e, shallow=False):
                return False, f"Binary mismatch for {rel}"
    return True, ""

