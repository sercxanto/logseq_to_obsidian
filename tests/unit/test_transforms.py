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


@pytest.mark.req("REQ-FRONTMATTER-003")
def test_normalize_tags_handles_unicode_characters():
    tags = l2o.normalize_tags("#가나다, #마바사")
    assert tags == ["가나다", "마바사"]


@pytest.mark.req("REQ-FRONTMATTER-003")
def test_emit_yaml_frontmatter_handles_underscored_unicode_tags():
    yaml = l2o.emit_yaml_frontmatter({"tags": "#_가나다, #_마바사"})
    expected = "---\ntags:\n  - _가나다\n  - _마바사\n---\n\n"
    assert yaml == expected


@pytest.mark.req("REQ-FRONTMATTER-003")
def test_normalize_tags_ignores_embedded_property_tokens():
    tags = l2o.normalize_tags("tags:: #_가나다, #_마바사")
    assert tags == ["_가나다", "_마바사"]


@pytest.mark.req("REQ-TASKS-001")
@pytest.mark.req("REQ-TASKS-002")
@pytest.mark.req("REQ-TASKS-004")
@pytest.mark.req("REQ-TASKS-005")
@pytest.mark.req("REQ-TASKS-006")
def test_transform_tasks_all_states_simple_mapping():
    # Unchecked states
    assert l2o.transform_tasks("- TODO Work\n") == "- [ ] Work\n"
    assert l2o.transform_tasks("- DOING Work\n") == "- [ ] Work\n"
    assert l2o.transform_tasks("- LATER Soon\n") == "- [ ] Soon\n"
    assert l2o.transform_tasks("- NOW Now\n") == "- [ ] Now\n"
    assert l2o.transform_tasks("- WAIT Hold\n") == "- [ ] Hold\n"
    assert l2o.transform_tasks("- WAITING Hold\n") == "- [ ] Hold\n"
    assert l2o.transform_tasks("- IN-PROGRESS Going\n") == "- [ ] Going\n"
    # Checked states
    assert l2o.transform_tasks("- DONE Done\n") == "- [x] Done\n"
    assert l2o.transform_tasks("- CANCELED Skip\n") == "- [x] Skip\n"
    assert l2o.transform_tasks("- CANCELLED Skip\n") == "- [x] Skip\n"


@pytest.mark.req("REQ-TASKS-PRIO-001")
@pytest.mark.req("REQ-TASKS-PRIO-002")
def test_priority_mapping_emoji():
    assert l2o.transform_tasks("- TODO [#A] Alpha\n", tasks_format="emoji") == "- [ ] Alpha ⏫\n"
    assert l2o.transform_tasks("- DOING [#B] Beta\n", tasks_format="emoji") == "- [ ] Beta 🔼\n"
    assert l2o.transform_tasks("- DONE [#C] Gamma\n", tasks_format="emoji") == "- [x] Gamma 🔽\n"
    # No priority yields no emoji
    assert l2o.transform_tasks("- LATER Delta\n", tasks_format="emoji") == "- [ ] Delta\n"


@pytest.mark.req("REQ-TASKS-PRIO-001")
@pytest.mark.req("REQ-TASKS-PRIO-003")
def test_priority_mapping_dataview():
    assert l2o.transform_tasks("- TODO [#A] Alpha\n", tasks_format="dataview") == "- [ ] Alpha [priority::high]\n"
    assert l2o.transform_tasks("- DOING [#B] Beta\n", tasks_format="dataview") == "- [ ] Beta [priority::medium]\n"
    assert l2o.transform_tasks("- DONE [#C] Gamma\n", tasks_format="dataview") == "- [x] Gamma [priority::low]\n"
    # No priority means no field emitted
    assert l2o.transform_tasks("- LATER Delta\n", tasks_format="dataview") == "- [ ] Delta\n"


@pytest.mark.req("REQ-TASKS-PRIO-001")
@pytest.mark.req("REQ-TASKS-PRIO-002")
def test_priority_precedes_attached_block_anchor():
    src = "- TODO [#A] Important task\nid:: prio123\n"
    out = l2o.transform_markdown(src, tasks_format="emoji")
    lines = out.splitlines()
    assert lines[0].endswith("⏫ ^prio123")


@pytest.mark.req("REQ-TASKS-PRIO-004")
def test_priority_only_recognized_when_after_state():
    # Priority appears later in the text, not directly after state → ignored
    src1 = "- TODO Do this [#A]\n"
    out1 = l2o.transform_tasks(src1, tasks_format="emoji")
    assert out1 == "- [ ] Do this [#A]\n"

    # Same for dataview format: no [priority::...] emitted
    out2 = l2o.transform_tasks(src1, tasks_format="dataview")
    assert out2 == "- [ ] Do this [#A]\n"


@pytest.mark.req("REQ-PROPS-002")
def test_collapsed_on_head_is_filtered_and_content_kept():
    src = "- collapsed:: true\n  Real content\n"
    out = l2o.transform_markdown(src)
    # Head property filtered; bullet synthesized from content
    assert out == "- Real content\n"


@pytest.mark.req("REQ-BLOCKID-003")
def test_id_on_head_attaches_to_first_content():
    src = "- id:: xyz789\n  First content line\n  Another\n"
    out = l2o.transform_markdown(src)
    lines = out.splitlines()
    assert lines[0].endswith("^xyz789")
    assert lines[0].startswith("- First content line")


@pytest.mark.req("REQ-TASKS-DATE-001")
@pytest.mark.req("REQ-TASKS-DATE-003")
def test_scheduled_with_time_and_repeat_emoji():
    src = "- TODO SCHEDULED: <2024-09-10 Tue 07:00 .+1d>\n"
    out = l2o.transform_tasks(src, tasks_format="emoji")
    assert out.strip() == "- [ ] ⏳ 2024-09-10 07:00 🔁 every 1 day when done"


@pytest.mark.req("REQ-TASKS-DATE-002")
@pytest.mark.req("REQ-TASKS-DATE-003")
def test_deadline_without_time_repeat_dataview():
    src = "- TODO DEADLINE: <2024-09-15 ++2w>\n"
    out = l2o.transform_tasks(src, tasks_format="dataview")
    assert out.strip() == "- [ ] [due::2024-09-15] [repeat::every 2 weeks when done]"


@pytest.mark.req("REQ-TASKS-001")
@pytest.mark.req("REQ-TASKS-DATE-001")
@pytest.mark.req("REQ-TASKS-DATE-002")
def test_transform_tasks_matches_transform_markdown():
    src = "- TODO Do thing SCHEDULED: <2025-01-01> DEADLINE: <2025-01-05>\n"
    emoji_line = l2o.transform_tasks(src, tasks_format="emoji")
    dataview_line = l2o.transform_tasks(src, tasks_format="dataview")
    assert emoji_line == l2o.transform_markdown(src, tasks_format="emoji")
    assert dataview_line == l2o.transform_markdown(src, tasks_format="dataview")


@pytest.mark.req("REQ-TASKS-DATE-004")
@pytest.mark.req("REQ-TASKS-DATE-005")
def test_dates_removed_and_appended_before_anchor():
    src = "- TODO [#A] Title SCHEDULED: <2024-09-20 Fri +1m>\nid:: aid123\n"
    out = l2o.transform_markdown(src, tasks_format="emoji")
    lines = out.splitlines()
    # Expect: checkbox, title, priority, scheduled, repeat, then anchor
    assert lines[0].startswith("- [ ] Title ⏫ ⏳ 2024-09-20")
    assert "🔁 every 1 month" in lines[0]
    assert lines[0].endswith("^aid123")


@pytest.mark.req("REQ-TASKS-DATE-006")
def test_both_scheduled_and_deadline_emitted():
    src = "- TODO SCHEDULED: <2024-09-10> and also DEADLINE: <2024-09-15>\n"
    out = l2o.transform_tasks(src, tasks_format="emoji")
    assert out.strip().endswith("⏳ 2024-09-10 📅 2024-09-15")


@pytest.mark.req("REQ-TASKS-DATE-007")
def test_scheduled_on_following_line_same_indent():
    src = "- TODO Do stuff\n  SCHEDULED: <2024-12-23 Mon>\n"
    out = l2o.transform_markdown(src, tasks_format="emoji")
    lines = out.splitlines()
    assert lines[0] == "- [ ] Do stuff ⏳ 2024-12-23"
    # The continuation line only included the date; it should be removed entirely
    assert len(lines) == 1


@pytest.mark.req("REQ-TASKS-006")
@pytest.mark.req("REQ-TASKS-001")
def test_task_recognized_at_nested_indentation():
    src = "  \t  - TODO Nested\n"  # mix of spaces and tab before '-'
    out = l2o.transform_markdown(src)
    assert out == "  \t  - [ ] Nested\n"


@pytest.mark.req("REQ-TASKS-DATE-007")
def test_deeper_indent_is_not_continuation():
    src = "  - TODO Parent\n  SCHEDULED: <2024-01-02>\n    - Child bullet\n"
    out = l2o.transform_markdown(src, tasks_format="emoji")
    lines = out.splitlines()
    assert lines[0] == "  - [ ] Parent ⏳ 2024-01-02"
    # Child bullet remains as is on its own line
    assert lines[1] == "    - Child bullet"


@pytest.mark.req("REQ-TASKS-006")
@pytest.mark.req("REQ-TASKS-DATE-001")
def test_nested_task_under_heading_with_scheduled_on_its_own_line():
    src = (
        "- ## [[2025-05-25]]\n"
        "    - Indentation level 1\n"
        "        - Indentation level 2\n"
        "        - DONE My task\n"
        "          SCHEDULED: <2025-05-27 Tue>\n"
    )
    out = l2o.transform_markdown(src, tasks_format="emoji")
    lines = out.splitlines()
    assert lines[0] == "- ## [[2025-05-25]]"
    # The scheduled date must be attached to the DONE task, not the parent
    assert any(line.strip() == "- [x] My task ⏳ 2025-05-27" for line in lines)


@pytest.mark.req("REQ-HEADCHILD-001")
@pytest.mark.req("REQ-PROPS-001")
def test_heading_followed_by_collapsed_then_indented_list_becomes_list_heading():
    src = "## Tag 1\ncollapsed:: true\n    - Indentation\n"
    out = l2o.transform_markdown(src, tasks_format="emoji")
    lines = out.splitlines()
    assert lines[0].startswith("- ## Tag 1")
    assert lines[1] == "    - Indentation"


@pytest.mark.req("REQ-LINKNS-001")
@pytest.mark.req("REQ-LINKNS-002")
@pytest.mark.req("REQ-LINKNS-003")
def test_wikilink_to_dataview_field_conversion():
    # No config → unchanged
    assert l2o.replace_wikilinks_to_dv_fields("X [[a/b]] Y\n", []) == "X [[a/b]] Y\n"
    # Single key
    assert l2o.replace_wikilinks_to_dv_fields("X [[a/b]] Y\n", ["a"]) == "X [a::b] Y\n"
    # Nested value remains
    assert l2o.replace_wikilinks_to_dv_fields("[[a/b/c]]\n", ["a"]) == "[a::b/c]\n"
    # Embed not converted
    assert l2o.replace_wikilinks_to_dv_fields("![[a/b]]\n", ["a"]) == "![[a/b]]\n"
    # Aliased link not converted
    assert l2o.replace_wikilinks_to_dv_fields("[[a/b|Alias]]\n", ["a"]) == "[[a/b|Alias]]\n"
    # Inside fenced code not converted
    src = "```\n[[a/b]]\n```\n"
    assert l2o.replace_wikilinks_to_dv_fields(src, ["a"]) == src


@pytest.mark.req("REQ-LINKNS-001")
@pytest.mark.req("REQ-LINKNS-003")
def test_wikilink_after_codeblock_is_converted():
    src = "- ```\n  [[a/b]]\n  ```\n- [[a/c]]\n"
    out = l2o.replace_wikilinks_to_dv_fields(src, ["a"])
    assert out.endswith("[a::c]\n")


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
    src = "title:: X\n\n- Item 1\n  collapsed:: true\n- Item 2\n"
    out = l2o.transform_markdown(src)
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


@pytest.mark.req("REQ-LINKALIAS-001")
def test_markdown_alias_links_convert_to_obsidian_alias():
    text = "Before [Display Name]([[Page Name]]) after [Docs](https://example.com)\n"
    out = l2o.replace_page_alias_links(text)
    assert "[[Page Name|Display Name]]" in out
    assert "[Docs](https://example.com)" in out


@pytest.mark.req("REQ-LINKALIAS-001")
def test_alias_links_inside_code_fence_are_ignored():
    text = "```\n[Display Name]([[Page Name]])\n```\n"
    out = l2o.replace_page_alias_links(text)
    assert out == text


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


@pytest.mark.req("REQ-IMAGE-002")
def test_markdown_image_with_size_attrs_converts_to_size_suffix():
    text = "![alt](../assets/picture.png){:height 424, :width 675}"
    out = l2o.replace_asset_images(text)
    assert out.strip() == "![[picture.png|675x424]]"


@pytest.mark.req("REQ-FRONTMATTER-005")
def test_only_leading_properties_become_yaml_frontmatter():
    src = "title:: A\n\nBody\n\ntitle:: B\n"
    out = l2o.transform_markdown(src)
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
    src = "title:: folder/note\n\nBody\n"
    out = l2o.transform_markdown(src, expected_title_path="folder/note")
    # No front matter should be present when the only property (title) is dropped
    assert not out.startswith("---\n")
    # And no title appears anywhere
    assert "title:" not in out


@pytest.mark.req("REQ-TITLE-001")
def test_title_mismatch_warns_and_title_dropped(capsys):
    src = "title:: Display Name\n\nBody\n"
    out = l2o.transform_markdown(
        src,
        expected_title_path="folder/note",
        rel_path_for_warn=Path("pages/note.md"),
    )
    # Title removed; does not appear in aliases; YAML may be omitted
    assert "title:" not in out
    assert "aliases:" not in out or "Display Name" not in out
    # Warning emitted
    captured = capsys.readouterr()
    assert "Title property mismatch" in captured.out


@pytest.mark.req("REQ-HEADCHILD-001")
@pytest.mark.req("REQ-HEADCHILD-002")
@pytest.mark.req("REQ-HEADCHILD-003")
def test_heading_followed_by_indented_list_becomes_list_heading():
    src = "# Heading without '-' at the beginning\n\t- list item 1\n\t- list item 2\n"
    out = l2o.transform_markdown(src)
    lines = out.splitlines()
    assert lines[0].startswith("- # Heading without '-'")
    assert lines[1] == "\t- list item 1"
    assert lines[2] == "\t- list item 2"


@pytest.mark.req("REQ-HEADCHILD-001")
def test_heading_followed_by_tab_indented_list_becomes_list_heading():
    src = "# Heading with tabs\n\t- item A\n\t\t- item B\n"
    out = l2o.transform_markdown(src)
    lines = out.splitlines()
    assert lines[0].startswith("- # Heading with tabs")
    # Child lines remain with tabs; we only prefix the heading
    assert lines[1].startswith("\t- item A")
    assert lines[2].startswith("\t\t- item B")


@pytest.mark.req("REQ-HEADCHILD-002")
def test_heading_already_inside_list_is_unchanged():
    src = "- # Already a list heading\n\t- child\n"
    out = l2o.transform_markdown(src)
    assert out.startswith("- # Already a list heading")


@pytest.mark.req("REQ-HEADCHILD-003")
def test_no_change_inside_code_fence():
    src = "```\n# Not a real heading\n\t- list item\n```\n"
    out = l2o.transform_markdown(src)
    # Fenced block should remain untouched
    assert out == src
