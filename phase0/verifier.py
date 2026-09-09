"""Control-arm verifier: file-level defect localization with no memory.

Design (spec Phase 0 item 4, Phase 4 "same model, prompt scaffold, seeds"):
  - Input: the issue text + the repository's file tree at base_commit. No
    hints, no test patch, no gold patch (SWE-bench-Live protocol).
  - Output: a ranked list of up to k files the verifier believes must change,
    each with a one-line reason. Rendered as `Flag`s for the oracle.
  - Model access goes through the `ModelClient` seam. `CachedClient` stores
    every (request -> response) under sha256(request) so a rerun on identical
    inputs is byte-identical without touching the network (Gate 0 item 3).
    Sampling is not deterministic by itself; the cache is the mechanism, and
    the run manifest records it.
  - The treatment arm (Phase 4) adds retrieved memories to the prompt and
    changes nothing else. `render_prompt` takes `memories` for that reason and
    the control arm passes none.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol, Sequence

from adapters.code.oracle import Flag, Location

FILE_LEVEL = Location  # alias for readability


def file_location(path: str) -> Location:
    """Whole-file location: overlaps any hunk in the file."""
    return Location(path, 1, 10**9)


# --------------------------------------------------------------------------
# Model seam
# --------------------------------------------------------------------------
RANKED_FILES_SCHEMA = {
    "type": "object",
    "properties": {
        "files": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "reason": {"type": "string"}},
                "required": ["path", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["files"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class ModelRequest:
    model: str
    system: str
    user: str
    schema: dict
    max_tokens: int = 4096
    effort: str = "high"

    def key(self) -> str:
        return hashlib.sha256(json.dumps({
            "model": self.model, "system": self.system, "user": self.user,
            "schema": self.schema, "max_tokens": self.max_tokens, "effort": self.effort,
        }, sort_keys=True).encode()).hexdigest()


class ModelClient(Protocol):
    def complete(self, req: ModelRequest) -> str: ...


class AnthropicClient:
    """Claude via the official SDK with a JSON-schema output constraint."""

    def __init__(self, client=None) -> None:
        if client is None:
            import anthropic  # local import: kernel and tests stay dependency-free
            client = anthropic.Anthropic()
        self._client = client

    def complete(self, req: ModelRequest) -> str:
        resp = self._client.messages.create(
            model=req.model,
            max_tokens=req.max_tokens,
            system=req.system,
            messages=[{"role": "user", "content": req.user}],
            output_config={"effort": req.effort, "format": {"type": "json_schema", "schema": req.schema}},
        )
        if resp.stop_reason == "refusal":
            raise RuntimeError(f"model refused: {getattr(resp, 'stop_details', None)}")
        return next(b.text for b in resp.content if b.type == "text")


class CachedClient:
    """Content-addressed response cache in front of any ModelClient.

    Cache file: one JSON object per line {key, model, response}. `offline=True`
    raises on a miss, which is how a rerun proves it never touched the model.
    """

    def __init__(self, inner: Optional[ModelClient], cache_path: str | Path, offline: bool = False) -> None:
        self.inner = inner
        self.path = Path(cache_path)
        self.offline = offline
        self.hits = 0
        self.misses = 0
        self._mem: dict[str, str] = {}
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                if line.strip():
                    row = json.loads(line)
                    self._mem[row["key"]] = row["response"]

    def complete(self, req: ModelRequest) -> str:
        k = req.key()
        if k in self._mem:
            self.hits += 1
            return self._mem[k]
        if self.offline or self.inner is None:
            raise LookupError(f"cache miss in offline mode for request {k[:12]}")
        self.misses += 1
        out = self.inner.complete(req)
        self._mem[k] = out
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as f:
            f.write(json.dumps({"key": k, "model": req.model, "response": out}) + "\n")
        return out


class ScriptedClient:
    """Test double: maps request key (or '*') -> response."""

    def __init__(self, responses: dict[str, str]) -> None:
        self.responses = responses
        self.calls = 0

    def complete(self, req: ModelRequest) -> str:
        self.calls += 1
        return self.responses.get(req.key(), self.responses.get("*", '{"files": []}'))


# --------------------------------------------------------------------------
# Repository structure
# --------------------------------------------------------------------------
SOURCE_SUFFIXES = (".py",)
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".tox", ".eggs", "build", "dist", ".venv", "venv"}


def repo_file_tree(root: str | Path, suffixes: Sequence[str] = SOURCE_SUFFIXES, max_files: int = 4000) -> list[str]:
    root = Path(root)
    out: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fn in sorted(filenames):
            if fn.endswith(tuple(suffixes)):
                out.append(str(Path(dirpath, fn).relative_to(root)))
    return out[:max_files]


# --------------------------------------------------------------------------
# Prompt scaffold — frozen for the whole experiment (spec Phase 4)
# --------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are a defect localization verifier. Given a GitHub issue and the list of "
    "source files in the repository at the commit where the issue was reported, "
    "identify the files that must be modified to fix the issue. Rank them from most "
    "to least likely. Do not propose a patch. Only list paths that appear in the "
    "provided file list, exactly as written. Prefer fewer, more certain files; every "
    "wrong file counts against you."
)


def render_prompt(problem_statement: str, files: Sequence[str], k: int, memories: Sequence[str] = ()) -> str:
    parts = ["## Issue", problem_statement.strip(), "", "## Repository files", *files, ""]
    if memories:
        parts += ["## Relevant memory from prior defects in this repository", *[f"- {m}" for m in memories], ""]
    parts += [f"List at most {k} files, most likely first."]
    return "\n".join(parts)


# --------------------------------------------------------------------------
# Localizer
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class LocalizationResult:
    instance_id: str
    ranked: tuple[tuple[str, str], ...]   # (path, reason), most likely first
    request_key: str
    raw: str

    def flags(self) -> tuple[Flag, ...]:
        return tuple(Flag(self.instance_id, file_location(p), reason) for p, reason in self.ranked)


class Localizer:
    def __init__(self, client: ModelClient, model: str, k: int = 3, effort: str = "high") -> None:
        self.client = client
        self.model = model
        self.k = k
        self.effort = effort

    def localize(self, instance_id: str, problem_statement: str, files: Sequence[str], memories: Sequence[str] = ()) -> LocalizationResult:
        req = ModelRequest(
            model=self.model,
            system=SYSTEM_PROMPT,
            user=render_prompt(problem_statement, files, self.k, memories),
            schema=RANKED_FILES_SCHEMA,
            effort=self.effort,
        )
        raw = self.client.complete(req)
        data = json.loads(raw)
        known = set(files)
        ranked: list[tuple[str, str]] = []
        for item in data.get("files", []):
            p = str(item.get("path", "")).strip()
            if p in known and p not in {r[0] for r in ranked}:
                ranked.append((p, str(item.get("reason", ""))))
            if len(ranked) >= self.k:
                break
        return LocalizationResult(instance_id, tuple(ranked), req.key(), raw)
