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


@pytest.mark.req("REQ-PROPS-001")
def test_collapsed_property_is_filtered_on_block_level():
    src = (
        "title:: X\n"
        "\n"
        "- Item 1\n"
        "  collapsed:: true\n"
        "- Item 2\n"
    )
    out = l2o.transform_markdown(src, annotate_status=False)
    # Block-level collapsed line removed
    assert "collapsed::" not in out


@pytest.mark.req("REQ-EMBED-001")
@pytest.mark.req("REQ-LINKPATH-001")
def test_embed_block_ref_converts_to_obsidian_embed(tmp_path):
    text = "{{embed ((abc123))}}\n"
    src = Path(tmp_path / "pages/Foo.md")
    dst = Path(tmp_path / "Foo.md")
    index = {"abc123": src}
    in_to_out = {src: dst}
    replaced = l2o.replace_block_refs(text, index, in_to_out, tmp_path)
    embedded = l2o.replace_embeds(replaced)
    assert embedded.strip() == "![[Foo#^abc123]]"


@pytest.mark.req("REQ-EMBED-002")
def test_embed_page_link_converts_to_obsidian_embed():
    text = "{{embed [[Foo]]}}\n"
    embedded = l2o.replace_embeds(text)
    assert embedded.strip() == "![[Foo]]"


@pytest.mark.req("REQ-IMAGE-001")
def test_markdown_image_in_assets_converts_to_obsidian_embed(tmp_path):
    # paths relative to physical file location in Logseq pages
    text = "![alt](../assets/picture.png)\n"
    out = l2o.replace_asset_images(text)
    assert out.strip() == "![[picture.png]]"
    # Also support assets/picture.png form
    text2 = "![x](assets/picture.png)\n"
    out2 = l2o.replace_asset_images(text2)
    assert out2.strip() == "![[picture.png]]"


@pytest.mark.req("REQ-FRONTMATTER-005")
def test_only_leading_properties_become_yaml_frontmatter():
    src = (
        "title:: A\n"
        "\n"
        "Body\n"
        "\n"
        "title:: B\n"
    )
    out = l2o.transform_markdown(src, annotate_status=False)
    # Expect YAML front matter with title: A only
    assert out.startswith("---\n")
    parts = out.split("---\n")
    assert len(parts) >= 3
    yaml_section = parts[1]
    body = parts[2]
    assert "title: A" in yaml_section
    # Later 'title:: B' should remain in the body, not turned into YAML
    assert "title:: B" in body


@pytest.mark.req("REQ-TITLE-001")
def test_title_equal_to_output_path_is_suppressed():
    src = (
        "title:: folder/note\n"
        "\n"
        "Body\n"
    )
    out = l2o.transform_markdown(src, annotate_status=False, expected_title_path="folder/note")
    # No front matter should be present when the only property (title) is dropped
    assert not out.startswith("---\n")
    # And no title appears anywhere
    assert "title:" not in out


@pytest.mark.req("REQ-TITLE-001")
def test_title_mismatch_warns_and_title_dropped(capsys):
    src = (
        "title:: Display Name\n"
        "\n"
        "Body\n"
    )
    out = l2o.transform_markdown(
        src,
        annotate_status=False,
        expected_title_path="folder/note",
        rel_path_for_warn=Path("pages/note.md"),
    )
    # Title removed; does not appear in aliases; YAML may be omitted
    assert "title:" not in out
    assert "aliases:" not in out or "Display Name" not in out
    # Warning emitted
    captured = capsys.readouterr()
    assert "Title property mismatch" in captured.out
