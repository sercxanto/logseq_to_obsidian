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


@pytest.mark.req("REQ-EMBED-003")
def test_video_and_youtube_macros_convert_to_markdown_embeds():
    video = "{{video https://www.youtube.com/watch?v=Aq5WXmQQooo}}\n"
    youtube = "{{youtube https://www.youtube.com/watch?v=Aq5WXmQQooo}}\n"

    assert l2o.replace_embeds(video).strip() == "![](https://www.youtube.com/watch?v=Aq5WXmQQooo)"
    assert l2o.replace_embeds(youtube).strip() == "![](https://www.youtube.com/watch?v=Aq5WXmQQooo)"


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


@pytest.mark.req("REQ-IMAGE-001")
def test_image_replacement_keeps_following_newline():
    text = "- ![alt](../assets/picture.png)\n- Next line\n"
    out = l2o.replace_asset_images(text)
    assert out == "- ![[picture.png]]\n- Next line\n"


@pytest.mark.req("REQ-IMAGE-001")
def test_image_replacement_keeps_following_text():
    text = "- ![alt](../assets/picture.png) - Same line\n"
    out = l2o.replace_asset_images(text)
    assert out == "- ![[picture.png]] - Same line\n"


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


# --- Org-mode block conversion ---


@pytest.mark.req("REQ-ORGBLOCK-001")
def test_quote_block_to_blockquote():
    src = "#+BEGIN_QUOTE\nsome text\nmore text\n#+END_QUOTE\n"
    out = l2o.transform_markdown(src)
    assert "> some text\n" in out
    assert "> more text\n" in out
    assert "#+BEGIN" not in out
    assert "#+END" not in out


@pytest.mark.req("REQ-ORGBLOCK-002")
def test_note_block_to_callout():
    src = "#+BEGIN_NOTE\ncontent line\n#+END_NOTE\n"
    out = l2o.transform_markdown(src)
    assert "> [!note]\n" in out
    assert "> content line\n" in out


@pytest.mark.req("REQ-ORGBLOCK-002")
def test_tip_block_to_callout():
    src = "#+BEGIN_TIP\ntip content\n#+END_TIP\n"
    out = l2o.transform_markdown(src)
    assert "> [!tip]\n" in out
    assert "> tip content\n" in out


@pytest.mark.req("REQ-ORGBLOCK-002")
def test_warning_block_to_callout():
    src = "#+BEGIN_WARNING\ndanger ahead\n#+END_WARNING\n"
    out = l2o.transform_markdown(src)
    assert "> [!warning]\n" in out
    assert "> danger ahead\n" in out


@pytest.mark.req("REQ-ORGBLOCK-002")
def test_example_block_to_callout():
    src = "#+BEGIN_EXAMPLE\nexample code\n#+END_EXAMPLE\n"
    out = l2o.transform_markdown(src)
    assert "> [!example]\n" in out


@pytest.mark.req("REQ-ORGBLOCK-002")
def test_unknown_block_type_defaults_to_note():
    src = "#+BEGIN_CENTER\ncentered text\n#+END_CENTER\n"
    out = l2o.transform_markdown(src)
    assert "> [!note]\n" in out
    assert "> centered text\n" in out


@pytest.mark.req("REQ-ORGBLOCK-003")
def test_bold_title_extraction():
    src = "#+BEGIN_NOTE\n**My Title**\ncontent here\n#+END_NOTE\n"
    out = l2o.transform_markdown(src)
    assert "> [!note] My Title\n" in out
    assert "> content here\n" in out
    assert "**My Title**" not in out


@pytest.mark.req("REQ-ORGBLOCK-003")
def test_no_title_extraction_for_quote():
    src = "#+BEGIN_QUOTE\n**bold text**\nmore\n#+END_QUOTE\n"
    out = l2o.transform_markdown(src)
    assert "> **bold text**\n" in out
    assert "[!quote]" not in out


@pytest.mark.req("REQ-ORGBLOCK-004")
def test_comment_block_to_obsidian_comment():
    src = "#+BEGIN_COMMENT\nhidden text\nanother line\n#+END_COMMENT\n"
    out = l2o.transform_markdown(src)
    assert "%%\n" in out
    assert "hidden text\n" in out
    assert "#+BEGIN" not in out


@pytest.mark.req("REQ-ORGBLOCK-005")
def test_nested_blocks():
    src = "#+BEGIN_NOTE\n**Outer**\nouter content\n#+BEGIN_QUOTE\ninner quote\n#+END_QUOTE\nmore outer\n#+END_NOTE\n"
    out = l2o.transform_markdown(src)
    assert "> [!note] Outer\n" in out
    assert "> outer content\n" in out
    assert "> > inner quote\n" in out
    assert "> more outer\n" in out


@pytest.mark.req("REQ-ORGBLOCK-006")
def test_orgblock_inside_indented_list():
    src = "- bullet\n  #+BEGIN_NOTE\n  **Title**\n  content\n  #+END_NOTE\n"
    out = l2o.transform_markdown(src)
    assert "  > [!note] Title\n" in out
    assert "  > content\n" in out


@pytest.mark.req("REQ-ORGBLOCK-001")
def test_empty_quote_block():
    src = "#+BEGIN_QUOTE\n#+END_QUOTE\n"
    out = l2o.transform_markdown(src)
    assert "#+BEGIN" not in out
    assert "#+END" not in out


# --- Highlights ---


@pytest.mark.req("REQ-HIGHLIGHT-001")
def test_highlight_conversion():
    src = "- Text with ^^a highlight^^ in the middle\n"
    out = l2o.transform_markdown(src)
    assert "==a highlight==" in out
    assert "^^" not in out


@pytest.mark.req("REQ-HIGHLIGHT-001")
def test_multiple_highlights_on_one_line():
    src = "- ^^first^^ and ^^second^^\n"
    out = l2o.transform_markdown(src)
    assert "==first==" in out
    assert "==second==" in out


@pytest.mark.req("REQ-HIGHLIGHT-002")
def test_highlights_inside_code_fence_are_skipped():
    src = "```\n^^not a highlight^^\n```\n"
    out = l2o.transform_markdown(src)
    assert "^^not a highlight^^" in out
    assert "==" not in out


# --- Numbered lists ---


@pytest.mark.req("REQ-NUMLIST-001")
def test_numbered_list_basic():
    src = (
        "- one\n"
        "  logseq.order-list-type:: number\n"
        "- two\n"
        "  logseq.order-list-type:: number\n"
        "- three\n"
        "  logseq.order-list-type:: number\n"
    )
    out = l2o.transform_markdown(src)
    lines = out.splitlines()
    assert lines[0] == "1. one"
    assert lines[1] == "2. two"
    assert lines[2] == "3. three"
    assert "logseq.order-list-type" not in out


@pytest.mark.req("REQ-NUMLIST-002")
def test_numbered_list_resets_after_non_numbered():
    src = (
        "- a\n"
        "  logseq.order-list-type:: number\n"
        "- b\n"
        "  logseq.order-list-type:: number\n"
        "- regular bullet\n"
        "- c\n"
        "  logseq.order-list-type:: number\n"
    )
    out = l2o.transform_markdown(src)
    lines = out.splitlines()
    assert lines[0] == "1. a"
    assert lines[1] == "2. b"
    assert lines[2] == "- regular bullet"
    assert lines[3] == "1. c"


@pytest.mark.req("REQ-NUMLIST-001")
@pytest.mark.req("REQ-NUMLIST-002")
def test_nested_numbered_lists():
    src = (
        "- outer one\n"
        "  logseq.order-list-type:: number\n"
        "    - inner a\n"
        "      logseq.order-list-type:: number\n"
        "    - inner b\n"
        "      logseq.order-list-type:: number\n"
        "- outer two\n"
        "  logseq.order-list-type:: number\n"
        "    - inner c\n"
        "      logseq.order-list-type:: number\n"
    )
    out = l2o.transform_markdown(src)
    lines = out.splitlines()
    assert lines[0] == "1. outer one"
    assert lines[1] == "    1. inner a"
    assert lines[2] == "    2. inner b"
    assert lines[3] == "2. outer two"
    assert lines[4] == "    1. inner c"


# --- Logbook removal ---


@pytest.mark.req("REQ-LOGBOOK-001")
def test_logbook_removal():
    src = (
        "- TODO task\n"
        "  :LOGBOOK:\n"
        "  CLOCK: [2024-01-15 Mon 09:00]--[2024-01-15 Mon 10:30] =>  01:30\n"
        "  :END:\n"
        "- next item\n"
    )
    out = l2o.transform_markdown(src)
    assert ":LOGBOOK:" not in out
    assert ":END:" not in out
    assert "CLOCK:" not in out
    assert "next item" in out


@pytest.mark.req("REQ-LOGBOOK-001")
def test_empty_logbook_removal():
    src = "- item\n  :LOGBOOK:\n  :END:\n"
    out = l2o.transform_markdown(src)
    assert ":LOGBOOK:" not in out
    assert ":END:" not in out


# --- LogSeq property cleanup ---


@pytest.mark.req("REQ-LOGSEQPROP-001")
def test_logseq_property_removal():
    src = "- item\n  logseq.toc:: true\n  logseq.table.version:: 2\n"
    out = l2o.transform_markdown(src)
    assert "logseq.toc" not in out
    assert "logseq.table" not in out
    assert "item" in out


# --- Tweet embeds ---


@pytest.mark.req("REQ-EMBED-004")
def test_tweet_embed_conversion():
    text = "{{tweet https://twitter.com/user/status/123456}}\n"
    out = l2o.replace_embeds(text)
    assert out.strip() == "![](https://twitter.com/user/status/123456)"


# --- Task date properties ---


@pytest.mark.req("REQ-TASKDATE-001")
def test_created_property_to_emoji():
    src = "- TODO some task\n  .created:: [[2024-01-15]]\n"
    out = l2o.transform_markdown(src)
    assert "➕ 2024-01-15" in out
    assert ".created::" not in out


@pytest.mark.req("REQ-TASKDATE-001")
def test_completed_property_to_emoji():
    src = "- DONE finished task\n  .completed:: [[2024-01-20]]\n"
    out = l2o.transform_markdown(src)
    assert "✅ 2024-01-20" in out
    assert ".completed::" not in out


@pytest.mark.req("REQ-TASKDATE-001")
def test_cancelled_property_to_emoji():
    src = "- CANCELLED skipped task\n  .cancelled:: [[2024-02-01]]\n"
    out = l2o.transform_markdown(src)
    assert "❌ 2024-02-01" in out
    assert ".cancelled::" not in out


@pytest.mark.req("REQ-TASKDATE-001")
def test_multiple_date_properties_combined():
    src = "- DONE task\n  .created:: [[2024-01-01]]\n  .completed:: [[2024-01-10]]\n"
    out = l2o.transform_markdown(src)
    assert "➕ 2024-01-01" in out
    assert "✅ 2024-01-10" in out


@pytest.mark.req("REQ-TASKDATE-001")
def test_date_property_before_block_anchor():
    src = "- TODO task\n  .created:: [[2024-01-15]]\nid:: abc123\n"
    out = l2o.transform_markdown(src)
    line = out.splitlines()[0]
    assert line.endswith("^abc123")
    assert "➕ 2024-01-15" in line


@pytest.mark.req("REQ-TASKDATE-001")
def test_date_property_without_dot_prefix():
    src = "- TODO some task\n  created:: [[2024-03-01]]\n"
    out = l2o.transform_markdown(src)
    assert "➕ 2024-03-01" in out
    assert "created::" not in out


@pytest.mark.req("REQ-TASKDATE-001")
def test_date_property_bare_date_without_brackets():
    src = "- DONE finished task\n  .completed:: 2024-02-15\n"
    out = l2o.transform_markdown(src)
    assert "✅ 2024-02-15" in out
    assert ".completed::" not in out


@pytest.mark.req("REQ-TASKDATE-001")
def test_date_property_done_alias():
    src = "- DONE task\n  done:: [[2024-04-10]]\n"
    out = l2o.transform_markdown(src)
    assert "✅ 2024-04-10" in out
    assert "done::" not in out


@pytest.mark.req("REQ-TASKDATE-001")
def test_date_property_canceled_alias():
    src = "- CANCELLED task\n  canceled:: 2024-05-20\n"
    out = l2o.transform_markdown(src)
    assert "❌ 2024-05-20" in out
    assert "canceled::" not in out


@pytest.mark.req("REQ-TASKDATE-001")
def test_date_property_no_dot_no_brackets_combined():
    src = "- DONE task\n  created:: 2024-01-01\n  completed:: 2024-01-10\n"
    out = l2o.transform_markdown(src)
    assert "➕ 2024-01-01" in out
    assert "✅ 2024-01-10" in out
