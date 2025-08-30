from pathlib import Path

import logseq_to_obsidian as l2o


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


def test_transform_tasks_all_states():
    assert l2o.transform_tasks("- TODO Work\n", False) == "- [ ] Work\n"
    assert l2o.transform_tasks("- DONE Done\n", False) == "- [x] Done\n"
    # Other state without annotate
    assert l2o.transform_tasks("- LATER Soon\n", False) == "- [ ] Soon\n"
    # Other state with annotate
    assert l2o.transform_tasks("- LATER Soon\n", True) == "- [ ] Soon (status: LATER)\n"


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


def test_replace_block_refs_builds_vault_relative_links(tmp_path):
    text = "See ((abc123))\n"
    index = {"abc123": Path(tmp_path / "pages/Foo.md")}
    in_to_out = {Path(tmp_path / "pages/Foo.md"): Path(tmp_path / "pages/Foo.md")}
    out = l2o.replace_block_refs(text, index, in_to_out, tmp_path)
    assert out.strip() == "[[pages/Foo#^abc123]]"
