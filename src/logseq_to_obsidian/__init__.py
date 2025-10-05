from __future__ import annotations

from .cli import main, parse_args
from .planner import FilePlan, Options, collect_files, copy_or_write, plan_output_path
from .transformer import (
    attach_block_ids,
    build_block_index,
    emit_yaml_frontmatter,
    fix_heading_child_lists,
    normalize_aliases,
    normalize_tags,
    parse_page_properties,
    replace_asset_images,
    replace_block_refs,
    replace_embeds,
    replace_wikilinks_to_dv_fields,
    transform_markdown,
    transform_tasks,
)
from .version import __version__

__all__ = [
    "__version__",
    "FilePlan",
    "Options",
    "attach_block_ids",
    "build_block_index",
    "collect_files",
    "copy_or_write",
    "emit_yaml_frontmatter",
    "fix_heading_child_lists",
    "main",
    "normalize_aliases",
    "normalize_tags",
    "parse_args",
    "parse_page_properties",
    "plan_output_path",
    "replace_asset_images",
    "replace_block_refs",
    "replace_embeds",
    "replace_wikilinks_to_dv_fields",
    "transform_markdown",
    "transform_tasks",
]
