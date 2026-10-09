"""Section-tree ("vectorless") navigation over statute headings. Y.3172 node: PP. Priority P2."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass
class TreeNode:
    label: str
    chunk_ids: list[str] = field(default_factory=list)
    children: dict[str, "TreeNode"] = field(default_factory=dict)

    def add(self, path: Sequence[str], chunk_id: str) -> None:
        if not path:
            self.chunk_ids.append(chunk_id)
            return
        head, *rest = path
        self.children.setdefault(head, TreeNode(label=head)).add(rest, chunk_id)


class SectionTree:
    """instrument -> section -> chunk ids, navigated by lexical overlap at each level."""
    def __init__(self, root: TreeNode, texts: dict[str, str]):
        self.root = root
        self.texts = texts

    @classmethod
    def from_chunks(cls, chunks) -> "SectionTree":
        root = TreeNode(label="corpus")
        texts = {}
        for c in chunks:
            root.add([c.jurisdiction, c.instrument, c.section], c.chunk_id)
            texts[c.chunk_id] = c.text
        return cls(root, texts)

    @staticmethod
    def _overlap(query: str, label: str) -> float:
        from .retrieve import tokenize
        q, l = set(tokenize(query)), set(tokenize(label))
        return len(q & l) / len(q) if q else 0.0

    def navigate(self, query: str, k: int = 5, beam: int = 3) -> list[tuple[str, float]]:
        """Descend the tree keeping the `beam` best branches per level; score leaves on text overlap."""
        frontier: list[tuple[TreeNode, float]] = [(self.root, 0.0)]
        while any(n.children for n, _ in frontier):
            nxt: list[tuple[TreeNode, float]] = []
            for n, s in frontier:
                if not n.children:
                    nxt.append((n, s))
                    continue
                scored = [(c, s + self._overlap(query, c.label)) for c in n.children.values()]
                scored.sort(key=lambda p: -p[1])
                nxt.extend(scored[:beam])
            frontier = sorted(nxt, key=lambda p: -p[1])[: beam * beam]
        leaves: list[tuple[str, float]] = []
        for n, s in frontier:
            for cid in n.chunk_ids:
                leaves.append((cid, s + self._overlap(query, self.texts.get(cid, ""))))
        leaves.sort(key=lambda p: -p[1])
        return leaves[:k]
