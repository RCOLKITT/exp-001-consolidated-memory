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
import re
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


RANKED_FUNCTIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "functions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "qualname": {"type": "string"}, "reason": {"type": "string"}},
                "required": ["path", "qualname", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["functions"],
    "additionalProperties": False,
}


def schema_key(schema: dict) -> str:
    """The top-level list the response must carry (`files` or `functions`)."""
    return (schema.get("required") or ["files"])[0]


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


class TransientError(RuntimeError):
    """Rate limit / upstream outage: retry, do not change response mode."""


TRANSIENT_HTTP = {408, 409, 425, 429, 500, 502, 503, 504, 529}


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


class OpenAICompatibleClient:
    """Chat-completions client for OpenAI-compatible endpoints (Together,
    Fireworks, Groq, OpenRouter, vLLM, Ollama…) — the path for open-weights
    models with documented training cutoffs (option A, docs/phase0-findings.md).

    Structured output: tries `response_format: json_schema`, then
    `json_object`, then plain text; the returned text is always validated as
    JSON with a `files` list before it is cached. Standard library only.
    """

    def __init__(self, base_url: str, api_key: str, timeout: float = 180.0, extra: Optional[dict] = None,
                 max_attempts: int = 6, backoff_s: float = 2.0, sleep=None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.extra = extra or {}          # e.g. {"seed": 0, "provider": {...}}
        self._mode: Optional[str] = None  # remembered after the first success
        self.max_attempts = max_attempts
        self.backoff_s = backoff_s
        self._sleep = sleep or __import__("time").sleep
        self.last_meta: dict = {}         # provider / model / usage of the last successful call

    def _post(self, body: dict) -> dict:
        import urllib.error
        import urllib.request
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode(),
            headers={"content-type": "application/json", "authorization": f"Bearer {self.api_key}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:500]
            if e.code in TRANSIENT_HTTP:
                raise TransientError(f"HTTP {e.code} from {self.base_url}: {body}") from None
            raise RuntimeError(f"HTTP {e.code} from {self.base_url}: {body}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise TransientError(f"network error to {self.base_url}: {e}") from None

    def _post_with_retry(self, body: dict) -> dict:
        delay = self.backoff_s
        for attempt in range(1, self.max_attempts + 1):
            try:
                return self._post(body)
            except TransientError:
                if attempt == self.max_attempts:
                    raise
                self._sleep(delay)
                delay = min(delay * 2, 60.0)
        raise AssertionError("unreachable")

    def _body(self, req: ModelRequest, mode: str) -> dict:
        body = {
            "model": req.model,
            "temperature": 0,
            "max_tokens": req.max_tokens,
            "messages": [{"role": "system", "content": req.system}, {"role": "user", "content": req.user}],
            **self.extra,
        }
        if mode == "json_schema":
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": f"ranked_{schema_key(req.schema)}", "schema": req.schema, "strict": True}}
        elif mode == "json_object":
            body["response_format"] = {"type": "json_object"}
            body["messages"][0]["content"] += "\nRespond with a single JSON object: " + json.dumps(req.schema)
        else:
            body["messages"][0]["content"] += "\nRespond with only a JSON object matching this schema, no prose: " + json.dumps(req.schema)
        return body

    @staticmethod
    def _meta(resp: dict) -> dict:
        u = resp.get("usage") or {}
        return {"provider": resp.get("provider"), "model": resp.get("model"),
                "prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens")}

    _PATH_RE = re.compile(r'"path"\s*:\s*"([^"\n]+)"')
    _FUNC_RE = re.compile(r'"path"\s*:\s*"([^"\n]+)"\s*,\s*"qualname"\s*:\s*"([^"\n]+)"')

    @classmethod
    def _extract(cls, resp: dict, key: str = "files") -> str:
        text = resp["choices"][0]["message"]["content"]
        if not isinstance(text, str):
            text = "".join(part.get("text", "") for part in text)
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            text = text[text.find("{"):]
        try:
            data = json.loads(text[text.find("{"): text.rfind("}") + 1])
            if not isinstance(data.get(key), list):
                raise ValueError(f"response has no {key} list")
        except (json.JSONDecodeError, ValueError):
            # Truncated or malformed output (e.g. max_tokens hit mid-string): keep every
            # completed item in order, drop reasons. Deterministic; recorded as salvaged.
            if key == "functions":
                items = [{"path": p, "qualname": q, "reason": ""} for p, q in cls._FUNC_RE.findall(text)]
            else:
                items = [{"path": p, "reason": ""} for p in cls._PATH_RE.findall(text)]
            if not items:
                raise
            data = {key: items, "salvaged": True}
        return json.dumps(data, sort_keys=True)

    def complete(self, req: ModelRequest) -> str:
        modes = [self._mode] if self._mode else ["json_schema", "json_object", "text"]
        last: Optional[Exception] = None
        last_text, finish = "", None
        for mode in modes:
            try:
                resp = self._post_with_retry(self._body(req, mode))   # TransientError propagates: not a mode problem
                out = self._extract(resp, schema_key(req.schema))
                self._mode = mode
                self.last_meta = self._meta(resp)
                return out
            except TransientError:
                raise
            except (RuntimeError, ValueError, KeyError, json.JSONDecodeError) as e:
                last = e
                try:    # keep the offending text so an unrecoverable shape can be diagnosed from errors.jsonl
                    raw = resp["choices"][0]["message"]["content"]
                    last_text = raw if isinstance(raw, str) else json.dumps(raw)
                    finish = resp["choices"][0].get("finish_reason")
                except Exception:
                    last_text, finish = "", None
                continue
        raise RuntimeError(f"all response modes failed: {last} | finish_reason={finish} | text={last_text[:400]!r}")


def make_client(provider: str, base_url: Optional[str] = None, api_key_env: Optional[str] = None, model_extra: str = "") -> ModelClient:
    """Provider factory used by every CLI. `anthropic` uses the SDK's own
    credential resolution; `openai-compatible` needs --base-url and the env
    var holding the key (default MODEL_API_KEY)."""
    if provider == "anthropic":
        return AnthropicClient()
    if provider == "openai-compatible":
        if not base_url:
            raise ValueError("--base-url is required for openai-compatible")
        key = os.environ.get(api_key_env or "MODEL_API_KEY", "")
        if not key:
            raise ValueError(f"environment variable {api_key_env or 'MODEL_API_KEY'} is empty")
        extra = json.loads(model_extra) if model_extra else {}
        return OpenAICompatibleClient(base_url, key, extra=extra)
    raise ValueError(f"unknown provider {provider!r}")


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
        self.last_meta: dict = {}
        self._mem: dict[str, str] = {}
        self._meta: dict[str, dict] = {}
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                if line.strip():
                    row = json.loads(line)
                    self._mem[row["key"]] = row["response"]
                    self._meta[row["key"]] = row.get("meta", {})

    def complete(self, req: ModelRequest) -> str:
        k = req.key()
        if k in self._mem:
            self.hits += 1
            self.last_meta = self._meta.get(k, {})
            return self._mem[k]
        if self.offline or self.inner is None:
            raise LookupError(f"cache miss in offline mode for request {k[:12]}")
        self.misses += 1
        out = self.inner.complete(req)
        meta = dict(getattr(self.inner, "last_meta", {}) or {})
        self._mem[k] = out
        self._meta[k] = meta
        self.last_meta = meta
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as f:
            f.write(json.dumps({"key": k, "model": req.model, "response": out, "meta": meta}) + "\n")
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
MAX_FILES = 4000          # ~80k tokens of paths; repos above this are truncated (recorded per task)
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".tox", ".eggs", "build", "dist", ".venv", "venv"}


def repo_file_tree(root: str | Path, suffixes: Sequence[str] = SOURCE_SUFFIXES, max_files: int = MAX_FILES) -> list[str]:
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


SYSTEM_PROMPT_FUNCTIONS = (
    "You are a defect localization verifier. Given a GitHub issue and, for a few "
    "candidate source files, the list of functions, methods and classes each file "
    "defines (with line ranges) at the commit where the issue was reported, identify "
    "the functions that must be modified to fix the issue. Rank them from most to "
    "least likely. Do not propose a patch. Only name entries that appear in the "
    "provided lists, exactly as written; use \"<module>\" for a file's module-level "
    "code. Prefer fewer, more certain entries; every wrong entry counts against you."
)


def render_function_prompt(problem_statement: str, index: Sequence[tuple[str, Sequence[tuple[str, int, int]]]], k: int, memories: Sequence[str] = ()) -> str:
    """Stage 2 of the v2 verifier. `index` = [(path, [(qualname, start, end), ...]), ...]
    for the stage-1 files, in rank order. Memory section identical to stage 1."""
    parts = ["## Issue", problem_statement.strip(), ""]
    for path, spans in index:
        parts += [f"## {path}", f"- <module>"] + [f"- {q}  (lines {a}-{b})" for q, a, b in spans] + [""]
    if memories:
        parts += ["## Relevant memory from prior defects in this repository", *[f"- {m}" for m in memories], ""]
    parts += [f"List at most {k} functions as path + qualname, most likely first."]
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
    meta: dict = None                     # provider / model / usage that served this request
    n_files: int = 0                      # size of the file list shown to the verifier

    def flags(self) -> tuple[Flag, ...]:
        return tuple(Flag(self.instance_id, file_location(p), reason) for p, reason in self.ranked)


@dataclass(frozen=True)
class FunctionLocalizationResult:
    """v2: stage-1 file ranking plus stage-2 function ranking."""
    instance_id: str
    files: LocalizationResult
    ranked: tuple[tuple[str, str, str], ...]     # (path, qualname, reason), most likely first
    request_key: str
    raw: str
    meta: dict = None
    function_flags: tuple[Flag, ...] = ()

    def flags(self) -> tuple[Flag, ...]:
        return self.function_flags

    def file_flags(self) -> tuple[Flag, ...]:
        return self.files.flags()


class Localizer:
    level = "file"

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
        return LocalizationResult(instance_id, tuple(ranked), req.key(), raw,
                                  dict(getattr(self.client, "last_meta", {}) or {}), len(files))


class LocalizerV2:
    """Two-stage verifier (v2 pre-registration §3): stage 1 is the v1 file
    ranking, unchanged (same prompt, same cache keys); stage 2 shows the
    function index of the stage-1 files and asks for up to k `path::qualname`
    flags. Both arms run both stages; memory is injected in both stages.
    `index_of(path) -> spans | None` comes from the task's checkout."""
    level = "function"

    def __init__(self, client: ModelClient, model: str, k: int = 3, effort: str = "high") -> None:
        self.stage1 = Localizer(client, model, k=k, effort=effort)
        self.client = client
        self.model = model
        self.k = k
        self.effort = effort

    def localize(self, instance_id: str, problem_statement: str, files: Sequence[str], memories: Sequence[str] = (), index_of=None) -> FunctionLocalizationResult:
        from phase0.functions import MODULE
        stage1 = self.stage1.localize(instance_id, problem_statement, files, memories)
        index: list[tuple[str, list[tuple[str, int, int]]]] = []
        spans_by_path: dict[str, dict[str, tuple[int, int]]] = {}
        for path, _ in stage1.ranked:
            spans = (index_of(path) if index_of else None) or ()
            index.append((path, [(sp.qualname, sp.start_line, sp.end_line) for sp in spans]))
            spans_by_path[path] = {sp.qualname: (sp.start_line, sp.end_line) for sp in spans}
        if not index:
            return FunctionLocalizationResult(instance_id, stage1, (), stage1.request_key, stage1.raw, stage1.meta)
        req = ModelRequest(model=self.model, system=SYSTEM_PROMPT_FUNCTIONS,
                           user=render_function_prompt(problem_statement, index, self.k, memories),
                           schema=RANKED_FUNCTIONS_SCHEMA, effort=self.effort)
        raw = self.client.complete(req)
        data = json.loads(raw)
        ranked: list[tuple[str, str, str]] = []
        flags: list[Flag] = []
        for item in data.get("functions", []):
            p, q = str(item.get("path", "")).strip(), str(item.get("qualname", "")).strip()
            if p not in spans_by_path or (p, q) in {(r[0], r[1]) for r in ranked}:
                continue
            if q == MODULE:
                loc = Location(p, 1, 10**9, MODULE)
            elif q in spans_by_path[p]:
                a, b = spans_by_path[p][q]
                loc = Location(p, a, b, q)
            else:
                continue          # not in the shown index: dropped, like an unknown path in v1
            reason = str(item.get("reason", ""))
            ranked.append((p, q, reason)); flags.append(Flag(instance_id, loc, reason))
            if len(ranked) >= self.k:
                break
        return FunctionLocalizationResult(instance_id, stage1, tuple(ranked), req.key(), raw, dict(getattr(self.client, "last_meta", {}) or {}), tuple(flags))
