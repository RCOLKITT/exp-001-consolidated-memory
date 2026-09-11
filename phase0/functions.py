"""Function index of a Python source file at a commit (v2 pre-registration §3).

`function_index(source)` lists every `def` / `async def` / `class` with its
qualified name and PRE-image line span, so that

  - a gold hunk can be mapped to the enclosing symbol (function-level ground
    truth; module-level hunks map to `<module>`), and
  - a verifier flag `path::qualname` can be turned into a `Location` with the
    symbol's line range and `symbol` set (adapters.code.oracle).

Nesting: a method is `Class.method`; a nested function is folded into its
enclosing def (`outer.inner` is never a target, `outer` is). The innermost
*indexed* span containing a line wins; class bodies outside any method map to
the class itself.

`FunctionIndexCache` memoises spans by (repo, commit, path) in a JSONL file
saved with the run, so a replay never needs the checkout again.
"""
from __future__ import annotations

import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Optional

from memkernel.canon import digest

MODULE = "<module>"


@dataclass(frozen=True)
class Span:
    qualname: str
    kind: str          # "function" | "class"
    start_line: int
    end_line: int

    def contains(self, line: int) -> bool:
        return self.start_line <= line <= self.end_line


def _start(node: ast.AST) -> int:
    decos = getattr(node, "decorator_list", None) or []
    return min([node.lineno] + [d.lineno for d in decos])


def function_index(source: str) -> tuple[Span, ...]:
    """Spans for top-level functions, classes and their methods. Unparseable
    source (pre-image syntax the running interpreter rejects) yields ()."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return ()
    out: list[Span] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append(Span(node.name, "function", _start(node), node.end_lineno or node.lineno))
        elif isinstance(node, ast.ClassDef):
            out.append(Span(node.name, "class", _start(node), node.end_lineno or node.lineno))
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out.append(Span(f"{node.name}.{sub.name}", "function", _start(sub), sub.end_lineno or sub.lineno))
    return tuple(out)


def enclosing(index: tuple[Span, ...], line: int) -> Optional[Span]:
    """Innermost indexed span containing `line` (method before class); None at module level."""
    best: Optional[Span] = None
    for s in index:
        if s.contains(line) and (best is None or (s.end_line - s.start_line) < (best.end_line - best.start_line)):
            best = s
    return best


def enclosing_range(index: tuple[Span, ...], start_line: int, end_line: int) -> tuple[str, ...]:
    """Symbols touched by a line range: the enclosing symbol of every line in
    it (deduplicated, in order); `<module>` where no span applies. A zero-width
    insertion hunk (start 0) is module-level unless it falls inside a span."""
    seen: list[str] = []
    for line in range(max(start_line, 1), max(end_line, start_line, 1) + 1):
        s = enclosing(index, line)
        name = s.qualname if s else MODULE
        if name not in seen:
            seen.append(name)
    return tuple(seen) or (MODULE,)


class FunctionIndexCache:
    """(repo, commit, path) -> spans, memoised in a JSONL file. `read_source`
    is called on a miss and returns the file's text at that commit, or None
    when the file does not exist there (a pure-addition patch)."""

    def __init__(self, read_source: Callable[[str, str, str], Optional[str]], path: Optional[str | Path] = None) -> None:
        self._read = read_source
        self._path = Path(path) if path else None
        self._mem: dict[str, Optional[tuple[Span, ...]]] = {}
        self.hits = 0
        self.misses = 0
        if self._path and self._path.exists():
            for line in self._path.read_text().splitlines():
                if line.strip():
                    row = json.loads(line)
                    self._mem[row["key"]] = None if row["spans"] is None else tuple(Span(**s) for s in row["spans"])

    def spans(self, repo: str, commit: str, path: str) -> Optional[tuple[Span, ...]]:
        key = digest({"repo": repo, "commit": commit, "path": path})
        if key in self._mem:
            self.hits += 1
            return self._mem[key]
        self.misses += 1
        src = self._read(repo, commit, path)
        spans = None if src is None else function_index(src)
        self._mem[key] = spans
        if self._path:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a") as f:
                f.write(json.dumps({"key": key, "repo": repo, "commit": commit, "path": path,
                                    "spans": None if spans is None else [asdict(s) for s in spans]}) + "\n")
        return spans


def checkout_reader(repos_dir: str | Path):
    """`read_source` backed by the Phase 0 checkout (`run_control.ensure_checkout`)."""
    from phase0.corpus import Task
    from phase0.run_control import ensure_checkout

    def read(repo: str, commit: str, path: str) -> Optional[str]:
        d = ensure_checkout(Path(repos_dir), Task(instance_id="", repo=repo, base_commit=commit, created_at="", problem_statement="", patch=""))
        p = d / path
        if not p.is_file():
            return None
        try:
            return p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
    return read
