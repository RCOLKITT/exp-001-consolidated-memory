"""learn -> evaluate -> paired at function granularity through the real CLIs:
a local git repo stands in for GitHub, a stub server for the model."""
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

SRC = "def parse(s):\n    return s\n\n\ndef dump(s):\n    return s\n"


class Model(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        user = body["messages"][1]["content"]
        name = body["response_format"]["json_schema"]["name"]
        if name == "ranked_files":
            content = {"files": [{"path": "pkg/parser.py", "reason": "r"}]}
        elif "Relevant memory" in user:
            content = {"functions": [{"path": "pkg/parser.py", "qualname": "parse", "reason": "memory"}]}
        else:
            content = {"functions": [{"path": "pkg/parser.py", "qualname": "dump", "reason": "guess"}, {"path": "pkg/parser.py", "qualname": "parse", "reason": "r"}]}
        out = json.dumps({"choices": [{"message": {"content": json.dumps(content)}}], "provider": "stub"}).encode()
        self.send_response(200); self.send_header("content-type", "application/json"); self.end_headers(); self.wfile.write(out)

    def log_message(self, *a):
        pass


@pytest.fixture
def model_url():
    srv = HTTPServer(("127.0.0.1", 0), Model)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}/v1"
    srv.shutdown()


def _git_repo(root: Path) -> str:
    d = root / "repos" / "o__r"; (d / "pkg").mkdir(parents=True)
    (d / "pkg" / "parser.py").write_text(SRC)
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"}
    for cmd in (["git", "init", "-q"], ["git", "add", "."], ["git", "commit", "-q", "-m", "base"]):
        subprocess.run(cmd, cwd=d, check=True, env=env)
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=d, capture_output=True, text=True, check=True).stdout.strip()


def _patch(start):
    return f"diff --git a/pkg/parser.py b/pkg/parser.py\n--- a/pkg/parser.py\n+++ b/pkg/parser.py\n@@ -{start},1 +{start},1 @@\n-a\n+b\n"


def test_function_level_cli_end_to_end(tmp_path, model_url):
    sha = _git_repo(tmp_path)
    tasks = tmp_path / "tasks.jsonl"
    with tasks.open("w") as f:
        for i in range(1, 9):   # 4 build + 4 eval; gold = parse (line 1) throughout, and one negative-control task
            f.write(json.dumps({"instance_id": f"o__r-{i}", "repo": "o/r", "base_commit": sha, "created_at": f"2025-08-{i:02d}T00:00:00Z",
                                "problem_statement": f"crash in parse {i}", "patch": _patch(1)}) + "\n")
        f.write(json.dumps({"instance_id": "n__c-1", "repo": "n/c", "base_commit": sha, "created_at": "2025-08-01T00:00:00Z", "problem_statement": "x", "patch": _patch(1)}) + "\n")
    split = tmp_path / "split.json"; split.write_text(json.dumps({"o/r": 4, "n/c": 0}))
    env = {**os.environ, "MODEL_API_KEY": "k"}
    common = ["--tasks", str(tasks), "--split", str(split), "--repos-dir", str(tmp_path / "repos"), "--provider", "openai-compatible", "--base-url", model_url,
              "--model", "m", "--top-k", "2", "--similarity", "hashing", "--granularity", "function", "--consolidation", "function", "--tau", "0.0",
              "--min-occurrences", "2", "--min-distinct-inputs", "2", "--negative-control", "n/c"]
    r = subprocess.run([sys.executable, "-m", "phase3.learn", *common, "--out", str(tmp_path / "learn")], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr[-1500:]
    g3 = json.loads((tmp_path / "learn" / "o__r" / "gate3.json").read_text())
    assert g3["promoted"] == 1 and g3["granularity"] == "function" and g3["consolidation"].startswith("function-keyed")
    assert (tmp_path / "learn" / "o__r" / "functions.jsonl").exists()
    r = subprocess.run([sys.executable, "-m", "phase4.evaluate", *common, "--learn-dir", str(tmp_path / "learn"), "--out", str(tmp_path / "eval"), "--seed", "3",
                        "--arms", "control,treatment,ungated"], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr[-1500:]
    g4 = json.loads((tmp_path / "eval" / "gate4.json").read_text())
    assert g4["control"]["n_tasks"] == 4 and g4["localization_lift_pts"] == 0.0 and g4["false_positive_rise_pts"] == -50.0
    assert g4["secondary_arms"]["ungated"]["localization_lift_pts"] == 0.0 and g4["file_level_secondary"]["control"]["localization_rate"] == 1.0
    assert g4["negative_control_lift"] == {"localization_lift_pts": 0.0, "false_positive_rise_pts": 0.0}
    arms = json.loads((tmp_path / "eval" / "o__r" / "arms.json").read_text())
    assert set(arms["arms"]) == {"control", "treatment", "ungated"} and all(arms["arms"]["treatment"]["hits"].values())
    assert arms["arms"]["control"]["flags"]["o__r-5"] == ["pkg/parser.py::dump", "pkg/parser.py::parse"]
    # paired analysis needs no corpus for v2 files; secondary arm gets its own report
    ev = tmp_path / "evaldir"; ev.mkdir()
    for d in (tmp_path / "eval").iterdir():
        if (d / "arms.json").exists():
            (ev / f"{d.name}.arms.json").write_text((d / "arms.json").read_text())
    r = subprocess.run([sys.executable, "-m", "phase4.paired", "--eval-dir", str(ev), "--out", str(tmp_path / "paired"), "--negative-control", "n/c"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-1500:]
    pj = json.loads((tmp_path / "paired" / "paired.json").read_text())
    assert pj["primary"]["n_tasks"] == 4 and pj["primary"]["flags_differed"] == 4 and pj["primary"]["retrieved_any"] == 4
    assert (tmp_path / "paired" / "paired-ungated.md").exists()
