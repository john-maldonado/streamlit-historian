"""Utilities for building and rendering the historian tag tree."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, MutableMapping, Sequence

import copy
import streamlit as st

Tree = MutableMapping[str, "Tree"]


@dataclass
class TagTree:
    """Represents a hierarchical tree of historian tag paths."""

    root: Tree = field(default_factory=dict)

    @classmethod
    def from_paths(cls, paths: Iterable[str]) -> "TagTree":
        tree: Tree = {}
        for path in sorted({p.strip() for p in paths if p}):
            if not path:
                continue
            current = tree
            for part in path.split("/"):
                current = current.setdefault(part, {})
            current.setdefault("__leaf__", {})
        return cls(tree)

    def filtered(self, query: str) -> "TagTree":
        if not query:
            return TagTree(copy.deepcopy(self.root))

        lowered = query.lower()

        def include_subtree(node: Tree, prefix: Sequence[str]) -> Tree:
            filtered_node: Tree = {}
            for key, child in node.items():
                if key == "__leaf__":
                    continue
                new_prefix = (*prefix, key)
                child_filtered = include_subtree(child, new_prefix)
                path = "/".join(new_prefix)
                if lowered in path.lower() or child_filtered:
                    filtered_node[key] = child_filtered or {"__leaf__": {}}
            if "__leaf__" in node and (lowered in "/".join(prefix).lower()):
                filtered_node.setdefault("__leaf__", {})
            return filtered_node

        return TagTree(include_subtree(self.root, ()))


def render_tag_tree(tag_tree: TagTree, selected: Iterable[str]) -> List[str]:
    """Render the tag tree and return the updated selection."""

    selected_set = set(selected)

    def render_node(name: str, node: Tree, path: List[str]) -> None:
        current_path = path + [name]
        full_path = "/".join(current_path)
        children = {k: v for k, v in node.items() if k != "__leaf__"}

        if children:
            expander = st.expander(name, expanded=False)
            with expander:
                if "__leaf__" in node:
                    checked = st.checkbox(
                        full_path,
                        value=full_path in selected_set,
                        key=f"tag_leaf_{full_path.replace('/', '__')}",
                    )
                    if checked:
                        selected_set.add(full_path)
                    else:
                        selected_set.discard(full_path)
                for child_name in sorted(children):
                    render_node(child_name, children[child_name], current_path)
        else:
            checked = st.checkbox(
                name,
                value=full_path in selected_set,
                key=f"tag_leaf_{full_path.replace('/', '__')}",
            )
            if checked:
                selected_set.add(full_path)
            else:
                selected_set.discard(full_path)

    for top_name in sorted(k for k in tag_tree.root.keys() if k != "__leaf__"):
        render_node(top_name, tag_tree.root[top_name], [])

    return sorted(selected_set)
