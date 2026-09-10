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
