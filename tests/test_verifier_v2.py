"""v2 two-stage verifier: file stage unchanged, function stage validated
against the shown index, `<module>` allowed, salvage covers qualnames."""
import json

import pytest

from adapters.code.oracle import Location
from phase0.functions import MODULE, Span
from phase0.verifier import (RANKED_FILES_SCHEMA, RANKED_FUNCTIONS_SCHEMA, Localizer, LocalizerV2, ModelRequest,
                             OpenAICompatibleClient, render_function_prompt, render_prompt, schema_key)

FILES = ["pkg/a.py", "pkg/b.py", "pkg/c.py"]
INDEX = {"pkg/a.py": (Span("f", "function", 1, 5), Span("K", "class", 7, 20), Span("K.m", "function", 8, 12)),
         "pkg/b.py": ()}


class TwoStage:
    def __init__(self):
        self.requests = []

    def complete(self, req: ModelRequest) -> str:
        self.requests.append(req)
        if schema_key(req.schema) == "files":
            return json.dumps({"files": [{"path": "pkg/a.py", "reason": "r"}, {"path": "pkg/b.py", "reason": "r"}]})
        return json.dumps({"functions": [{"path": "pkg/a.py", "qualname": "K.m", "reason": "method"},
                                         {"path": "pkg/a.py", "qualname": "ghost", "reason": "not in index"},
                                         {"path": "pkg/b.py", "qualname": "<module>", "reason": "module code"},
                                         {"path": "pkg/zzz.py", "qualname": "f", "reason": "unknown file"},
                                         {"path": "pkg/a.py", "qualname": "K.m", "reason": "dup"}]})


def test_stage1_is_v1_and_stage2_flags_carry_symbol_and_span():
    client = TwoStage()
    v2 = LocalizerV2(client, "m", k=3)
    res = v2.localize("i1", "issue text", FILES, index_of=lambda p: INDEX.get(p))
    assert client.requests[0].user == render_prompt("issue text", FILES, 3) and client.requests[0].schema == RANKED_FILES_SCHEMA
    assert client.requests[0].key() == Localizer(TwoStage(), "m", k=3).localize("i1", "issue text", FILES).request_key   # same cache key as v1
    assert [f.location for f in res.flags()] == [Location("pkg/a.py", 8, 12, "K.m"), Location("pkg/b.py", 1, 10**9, MODULE)]
    assert [f.location for f in res.file_flags()] == [Location("pkg/a.py", 1, 10**9), Location("pkg/b.py", 1, 10**9)]
    assert "- K.m  (lines 8-12)" in client.requests[1].user and "## pkg/b.py\n- <module>\n" in client.requests[1].user
    assert client.requests[1].schema == RANKED_FUNCTIONS_SCHEMA


def test_memory_section_in_both_stages_only_when_given():
    client = TwoStage()
    LocalizerV2(client, "m").localize("i1", "t", FILES, memories=["sym => pkg / a # K.m :: why"], index_of=lambda p: INDEX.get(p))
    assert all("Relevant memory" in r.user for r in client.requests)
    client2 = TwoStage()
    LocalizerV2(client2, "m").localize("i1", "t", FILES, index_of=lambda p: INDEX.get(p))
    assert not any("Relevant memory" in r.user for r in client2.requests)


def test_salvage_recovers_path_qualname_pairs_in_order():
    resp = {"choices": [{"message": {"content": '{"functions": [{"path": "pkg/a.py", "qualname": "K.m", "reason": "x"}, {"path": "pkg/b.py", "qualname": "f", "reason": "trunc'}}]}
    out = json.loads(OpenAICompatibleClient._extract(resp, "functions"))
    assert [(f["path"], f["qualname"]) for f in out["functions"]] == [("pkg/a.py", "K.m"), ("pkg/b.py", "f")] and out["salvaged"] is True
    with pytest.raises(json.JSONDecodeError):
        OpenAICompatibleClient._extract({"choices": [{"message": {"content": '{"files": [{"path": "x"}]'}}]}, "functions")   # wrong key: no salvage


def test_no_stage2_when_stage1_returns_nothing():
    class Empty:
        def complete(self, req):
            return '{"files": []}'
    res = LocalizerV2(Empty(), "m").localize("i1", "t", FILES, index_of=lambda p: ())
    assert res.flags() == () and res.ranked == ()
