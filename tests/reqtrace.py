from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Set

import pytest
import yaml

SPEC_PATH = Path("docs/spec/requirements.yml")


def _load_requirement_sets() -> tuple[Set[str], Set[str]]:
    """Return (all_ids, active_ids) from the spec.

    - all_ids: every requirement id present in the spec
    - active_ids: only ids with status: active (enforced coverage)
    """
    if not SPEC_PATH.exists():
        return set(), set()
    data = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8")) or []
    all_ids: Set[str] = set()
    active_ids: Set[str] = set()
    for entry in data:
        if not isinstance(entry, dict):
            continue
        rid = entry.get("id")
        if not isinstance(rid, str):
            continue
        all_ids.add(rid)
        status = str(entry.get("status", "active")).lower()
        if status == "active":
            active_ids.add(rid)
    return all_ids, active_ids


def _load_manifest_ids() -> Dict[Path, Set[str]]:
    ids_by_manifest: Dict[Path, Set[str]] = {}
    for p in Path("tests/golden").rglob("manifest.yml"):
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        reqs = data.get("requirements") or []
        ids_by_manifest[p] = {r for r in reqs if isinstance(r, str)}
    return ids_by_manifest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "req(id): Link this test to a requirement id from the spec")
    all_ids, active_ids = _load_requirement_sets()
    config._req_all_ids = all_ids  # type: ignore[attr-defined]
    config._req_active_ids = active_ids  # type: ignore[attr-defined]
    config._req_used_ids: Set[str] = set()  # type: ignore[attr-defined]
    config._req_tests_without: List[str] = []  # type: ignore[attr-defined]


def pytest_collection_modifyitems(session: pytest.Session, config: pytest.Config, items: List[pytest.Item]) -> None:  # noqa: D401
    spec_ids: Set[str] = getattr(config, "_req_all_ids", set())
    used_ids: Set[str] = getattr(config, "_req_used_ids", set())
    tests_without: List[str] = getattr(config, "_req_tests_without", [])

    for item in items:
        req_ids: List[str] = []
        for m in item.iter_markers(name="req"):
            for arg in m.args:
                if isinstance(arg, str):
                    req_ids.append(arg)
        if not req_ids:
            tests_without.append(item.nodeid)
        used_ids.update(req_ids)

    # Also treat golden manifests as coverage
    for ids in _load_manifest_ids().values():
        used_ids.update(ids)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    config = session.config
    all_ids: Set[str] = getattr(config, "_req_all_ids", set())
    active_ids: Set[str] = getattr(config, "_req_active_ids", set())
    used_ids: Set[str] = getattr(config, "_req_used_ids", set())
    tests_without: List[str] = getattr(config, "_req_tests_without", [])

    unknown = sorted(id_ for id_ in used_ids if id_ not in all_ids)
    uncovered = sorted(id_ for id_ in active_ids if id_ not in used_ids)

    problems: List[str] = []
    if unknown:
        problems.append("Unknown requirement ids referenced: " + ", ".join(unknown))
    if uncovered:
        problems.append("Uncovered requirements: " + ", ".join(uncovered))
    if tests_without:
        problems.append(f"Tests missing @pytest.mark.req: {len(tests_without)} (e.g., {tests_without[:3]})")

    if problems:
        for p in problems:
            print("[REQTRACE] " + p)
        session.exitstatus = 1
