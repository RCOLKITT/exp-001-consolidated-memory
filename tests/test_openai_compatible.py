"""OpenAICompatibleClient against a local stub server: json_schema mode
first, fallback to json_object when the provider rejects it, validation."""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from phase0.verifier import ModelRequest, OpenAICompatibleClient, RANKED_FILES_SCHEMA, make_client


class Stub(BaseHTTPRequestHandler):
    reject_json_schema = False
    seen: list = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        Stub.seen.append(body)
        fmt = body.get("response_format", {}).get("type")
        if fmt == "json_schema" and Stub.reject_json_schema:
            self.send_response(400); self.end_headers(); self.wfile.write(b'{"error":"json_schema unsupported"}'); return
        content = json.dumps({"files": [{"path": "pkg/a.py", "reason": "r"}]})
        if fmt is None:
            content = "```json\n" + content + "\n```"
        out = json.dumps({"choices": [{"message": {"content": content}}]}).encode()
        self.send_response(200); self.send_header("content-type", "application/json"); self.end_headers(); self.wfile.write(out)

    def log_message(self, *a):  # quiet
        pass


@pytest.fixture
def server():
    srv = HTTPServer(("127.0.0.1", 0), Stub)
    t = threading.Thread(target=srv.serve_forever, daemon=True); t.start()
    Stub.seen = []; Stub.reject_json_schema = False
    yield f"http://127.0.0.1:{srv.server_port}/v1"
    srv.shutdown()


def _req():
    return ModelRequest("llama-4-maverick", "sys", "user", RANKED_FILES_SCHEMA)


def test_json_schema_mode_and_canonical_output(server):
    c = OpenAICompatibleClient(server, "k")
    out = c.complete(_req())
    assert json.loads(out) == {"files": [{"path": "pkg/a.py", "reason": "r"}]}
    assert Stub.seen[0]["response_format"]["type"] == "json_schema" and Stub.seen[0]["temperature"] == 0
    assert Stub.seen[0]["messages"][0]["role"] == "system"


def test_falls_back_when_provider_rejects_json_schema(server):
    Stub.reject_json_schema = True
    c = OpenAICompatibleClient(server, "k")
    c.complete(_req())
    assert [b.get("response_format", {}).get("type") for b in Stub.seen] == ["json_schema", "json_object"]
    c.complete(_req())                       # remembered mode: no retry of json_schema
    assert Stub.seen[-1]["response_format"]["type"] == "json_object" and len(Stub.seen) == 3


def test_text_mode_strips_fences(server):
    c = OpenAICompatibleClient(server, "k"); c._mode = "text"
    assert "pkg/a.py" in c.complete(_req())


def test_factory(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "x")
    assert isinstance(make_client("openai-compatible", "http://h/v1"), OpenAICompatibleClient)
    with pytest.raises(ValueError):
        make_client("openai-compatible", None)
    monkeypatch.delenv("MODEL_API_KEY")
    with pytest.raises(ValueError):
        make_client("openai-compatible", "http://h/v1")
    with pytest.raises(ValueError):
        make_client("nope")


def test_transient_429_is_retried_then_succeeds(server):
    class Flaky(Stub):
        pass
    calls = {"n": 0}
    orig = Stub.do_POST
    def do_POST(self):
        calls["n"] += 1
        if calls["n"] <= 2:
            self.send_response(429); self.end_headers(); self.wfile.write(b'{"error":{"code":429,"message":"rate-limited upstream"}}'); return
        orig(self)
    Stub.do_POST = do_POST
    try:
        slept = []
        c = OpenAICompatibleClient(server, "k", max_attempts=4, backoff_s=1.0, sleep=slept.append)
        out = c.complete(_req())
        assert "pkg/a.py" in out and slept == [1.0, 2.0] and c._mode == "json_schema"   # mode not abandoned on 429
        assert c.last_meta["provider"] is None  # stub sends no provider field
    finally:
        Stub.do_POST = orig


def test_transient_exhausted_raises_transient(server):
    from phase0.verifier import TransientError
    orig = Stub.do_POST
    def do_POST(self):
        self.send_response(503); self.end_headers(); self.wfile.write(b'{}')
    Stub.do_POST = do_POST
    try:
        c = OpenAICompatibleClient(server, "k", max_attempts=2, backoff_s=0.0, sleep=lambda s: None)
        with pytest.raises(TransientError):
            c.complete(_req())
    finally:
        Stub.do_POST = orig


def test_cache_records_provider_meta(server, tmp_path):
    from phase0.verifier import CachedClient
    orig = Stub.do_POST
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        content = json.dumps({"files": [{"path": "pkg/a.py", "reason": "r"}]})
        out = json.dumps({"provider": "Crusoe", "model": "m", "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                          "choices": [{"message": {"content": content}}]}).encode()
        self.send_response(200); self.send_header("content-type", "application/json"); self.end_headers(); self.wfile.write(out)
    Stub.do_POST = do_POST
    try:
        cc = CachedClient(OpenAICompatibleClient(server, "k"), tmp_path / "c.jsonl")
        cc.complete(_req()); assert cc.last_meta["provider"] == "Crusoe" and cc.last_meta["prompt_tokens"] == 10
        cc2 = CachedClient(None, tmp_path / "c.jsonl", offline=True)
        cc2.complete(_req()); assert cc2.last_meta["provider"] == "Crusoe"          # provenance survives the cache
    finally:
        Stub.do_POST = orig


def test_truncated_json_is_salvaged_in_order():
    resp = {"choices": [{"message": {"content": '{"files": [{"path": "pkg/a.py", "reason": "x"}, {"path": "pkg/b.py", "reason": "unterminated'}}]}
    out = json.loads(OpenAICompatibleClient._extract(resp))
    assert [f["path"] for f in out["files"]] == ["pkg/a.py", "pkg/b.py"] and out["salvaged"] is True
    with pytest.raises(json.JSONDecodeError):
        OpenAICompatibleClient._extract({"choices": [{"message": {"content": "no json at all"}}]})
