from pathlib import Path

import pytest

import logseq_to_obsidian as l2o


@pytest.mark.req("REQ-FRONTMATTER-001")
@pytest.mark.req("REQ-FRONTMATTER-002")
@pytest.mark.req("REQ-FRONTMATTER-003")
def test_parse_page_properties_basic():
    lines = [
        "title:: My Note\n",
        "tags:: a, [[b]] #c\n",
        "aliases:: [[Alt]], Other\n",
        "\n",
        "Body starts here\n",
    ]
    props, consumed = l2o.parse_page_properties(lines)
    assert consumed == 3
    assert props["title"] == "My Note"
    assert props["tags"].startswith("a")
    assert props["aliases"].startswith("[[Alt]]")


@pytest.mark.req("REQ-FRONTMATTER-001")
@pytest.mark.req("REQ-FRONTMATTER-002")
@pytest.mark.req("REQ-FRONTMATTER-003")
@pytest.mark.req("REQ-FRONTMATTER-004")
def test_emit_yaml_frontmatter_mapping():
    props = {
        "title": "Foo",
        "tags": "x, [[y]] #z",
        "aliases": "[[A]], B",
        "custom": "value",
    }
    yaml = l2o.emit_yaml_frontmatter(props)
    assert yaml is not None
    assert "title: Foo" in yaml
    assert "aliases:\n  - A\n  - B" in yaml
    assert "tags:\n  - x\n  - y\n  - z" in yaml
    assert "custom: value" in yaml


@pytest.mark.req("REQ-TASKS-001")
@pytest.mark.req("REQ-TASKS-002")
@pytest.mark.req("REQ-TASKS-003")
def test_transform_tasks_all_states():
    assert l2o.transform_tasks("- TODO Work\n", False) == "- [ ] Work\n"
    assert l2o.transform_tasks("- DONE Done\n", False) == "- [x] Done\n"
    # Other state without annotate
    assert l2o.transform_tasks("- LATER Soon\n", False) == "- [ ] Soon\n"
    # Other state with annotate
    assert l2o.transform_tasks("- LATER Soon\n", True) == "- [ ] Soon (status: LATER)\n"


@pytest.mark.req("REQ-BLOCKID-001")
@pytest.mark.req("REQ-BLOCKID-002")
def test_attach_block_ids_attaches_to_previous_content():
    lines = [
        "Some text\n",
        "id:: abc123\n",
        "source:: url\n",
        "id:: def456\n",
        "\n",
        "Another line\n",
        "id:: ghi789\n",
    ]
    out = l2o.attach_block_ids(lines)
    assert "Some text ^abc123\n" in out[0]
    # id after a property line should not attach
    assert "id:: def456\n" in out[2]
    # attaches to 'Another line'
    assert out[-2].startswith("Another line") and out[-2].rstrip("\n").endswith("^ghi789")


@pytest.mark.req("REQ-BLOCKREF-001")
@pytest.mark.req("REQ-LINKPATH-001")
@pytest.mark.req("REQ-STRUCTURE-001")
def test_replace_block_refs_builds_vault_relative_links(tmp_path):
    text = "See ((abc123))\n"
    src = Path(tmp_path / "pages/Foo.md")
    dst = Path(tmp_path / "Foo.md")  # flattened
    index = {"abc123": src}
    in_to_out = {src: dst}
    out = l2o.replace_block_refs(text, index, in_to_out, tmp_path)
    assert out.strip() == "[[Foo#^abc123]]"


@pytest.mark.req("REQ-BLOCKREF-002")
def test_unresolved_block_refs_are_left_unchanged(tmp_path):
    text = "Ref ((unknownid)) end\n"
    index = {}
    in_to_out = {}
    out = l2o.replace_block_refs(text, index, in_to_out, tmp_path)
    assert out == text
