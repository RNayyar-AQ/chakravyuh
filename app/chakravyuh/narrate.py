"""Human-readable narration of a run. Y.3172 node: SINK.

Narration is output only. It reads the ledger an ordinary run already wrote and says, in
sentences, what each entry means. Nothing here decides anything, so turning it on cannot
change a result -- the run narrated is byte-for-byte the run that would have happened anyway.
"""
from __future__ import annotations

import os
import re
import sys
from typing import IO, Optional

from .y3172 import node

ANSI = re.compile(r"\x1b\[[0-9;]*m")

# Y.3172 node letter -> (label, colour). The same letters the deck and docs/y3172_map.md use.
NODES = {
    "SRC": ("SRC ", "38;5;75"),    # data source: the world, the scenario, the fuzzer
    "C":   ("C   ", "38;5;80"),    # collection: ingest
    "PP":  ("PP  ", "38;5;79"),    # pre-processing: chunking, retrieval, pack compilation
    "M":   ("M   ", "38;5;141"),   # model: the agents
    "P":   ("P   ", "38;5;179"),   # policy: the deontic engine
    "D":   ("D   ", "38;5;209"),   # distribution: the Game Master, the world
    "SINK": ("SINK", "38;5;204"),  # sink: the ledger, the properties
}

DECISION_COLOUR = {"ALLOW": "38;5;78", "BLOCK": "38;5;203", "NEEDS_HUMAN": "38;5;221"}


def want_colour(choice: str, stream: IO[str]) -> bool:
    if choice == "always":
        return True
    if choice == "never" or os.environ.get("NO_COLOR"):
        return False
    return bool(getattr(stream, "isatty", lambda: False)())


def strip_ansi(text: str) -> str:
    return ANSI.sub("", text)


@node("SINK")
class Narrator:
    """Writes the story of a run to a stream, and keeps a plain-text copy of every line."""

    def __init__(self, stream: Optional[IO[str]] = None, colour: str = "auto",
                 keep: bool = True):
        self.stream = stream or sys.stdout
        self.colour = want_colour(colour, self.stream)
        self.lines: list[str] = []
        self.keep = keep
        self._stage = 0

    # ------------------------------------------------------------------ writing

    def _c(self, text: str, code: str) -> str:
        return f"\x1b[{code}m{text}\x1b[0m" if self.colour else text

    def write(self, text: str = "") -> None:
        if self.keep:
            self.lines.append(strip_ansi(text))
        print(text, file=self.stream, flush=True)

    def blank(self) -> None:
        self.write("")

    def rule(self, char: str = "─", width: int = 86) -> None:
        self.write(self._c(char * width, "38;5;240"))

    # ------------------------------------------------------------------ structure

    def banner(self, title: str, subtitle: str = "") -> None:
        self.blank()
        self.rule("═")
        self.write(self._c(f"  {title}", "1;38;5;51"))
        if subtitle:
            self.write(self._c(f"  {subtitle}", "38;5;244"))
        self.rule("═")

    def stage(self, title: str, why: str = "") -> None:
        """A numbered pipeline stage. `why` says, in one sentence, what it is for."""
        self._stage += 1
        self.blank()
        self.write(self._c(f"━━━ STAGE {self._stage}  {title} ", "1;38;5;51")
                   + self._c("━" * max(4, 70 - len(title)), "38;5;240"))
        if why:
            self.write(self._c(f"    {why}", "38;5;244"))
        self.blank()

    def step(self, node_letter: str, text: str) -> None:
        """One pipeline event, tagged with the Y.3172 node that produced it."""
        label, colour = NODES.get(node_letter, (node_letter.ljust(4), "38;5;244"))
        self.write(f"  {self._c('[' + label + ']', colour)} {text}")

    def detail(self, text: str, indent: int = 10) -> None:
        self.write(" " * indent + self._c(text, "38;5;247"))

    def faint(self, text: str, indent: int = 10) -> None:
        self.write(" " * indent + self._c(text, "38;5;240"))

    def kv(self, key: str, value: str, width: int = 26, indent: int = 4) -> None:
        self.write(" " * indent + self._c(key.ljust(width), "38;5;244") + str(value))

    def bullet(self, text: str, indent: int = 4) -> None:
        self.write(" " * indent + self._c("• ", "38;5;240") + text)

    def tick(self, t: int, clock: str) -> None:
        self.blank()
        self.write(self._c(f"  T+{t:<6d}", "1;38;5;252") + self._c(f"  {clock}", "38;5;244"))

    # ------------------------------------------------------------------ emphasis

    def decision(self, value: str) -> str:
        return self._c(value, DECISION_COLOUR.get(value, "38;5;252"))

    def good(self, text: str) -> str:
        return self._c(text, "38;5;78")

    def bad(self, text: str) -> str:
        return self._c(text, "38;5;203")

    def warn(self, text: str) -> str:
        return self._c(text, "38;5;221")

    def muted(self, text: str) -> str:
        return self._c(text, "38;5;244")

    def dim(self, text: str) -> str:
        return self._c(text, "38;5;240")

    def hash_(self, digest: str, keep: int = 12) -> str:
        """A digest, shortened for reading but never silently: the ellipsis is part of the text."""
        return self._c(f"{digest[:keep]}…", "38;5;109")

    def quote(self, text: str, width: int = 76, indent: int = 10, lines: int = 3) -> None:
        """Print verbatim source text, wrapped, so a citation can be read and not just counted."""
        import textwrap  # noqa: PLC0415
        wrapped = textwrap.wrap(" ".join(text.split()), width=width)
        for line in wrapped[:lines]:
            self.write(" " * indent + self._c("│ ", "38;5;240") + self._c(line, "38;5;251"))
        if len(wrapped) > lines:
            self.faint(f"│ … {len(wrapped) - lines} more line(s) of this clause", indent)
