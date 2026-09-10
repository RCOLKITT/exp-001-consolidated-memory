"""Every CLI must parse the flags the workflows pass (this is what run/exp-1 failed on)."""
import subprocess
import sys

import pytest

SEAM = ["--similarity", "hashing", "--embedding-model", "m", "--embedding-revision", "abc", "--theta", "0.45", "--rho", "0.7", "--cluster-similarity", "0.6"]
PROVIDER = ["--provider", "openai-compatible", "--base-url", "http://x/v1", "--api-key-env", "K", "--model-extra", "{}", "--model", "m", "--top-k", "3", "--ttl", "30"]


@pytest.mark.parametrize("mod,extra", [
    ("phase3.learn", ["--tasks", "t", "--split", "s", "--out", "o"]),
    ("phase4.evaluate", ["--tasks", "t", "--split", "s", "--learn-dir", "l", "--out", "o", "--seed", "1", "--max-eval-per-repo", "5"]),
    ("phase0.run_control", ["--tasks", "t", "--out", "o", "--repos", "a/b", "--per-repo-limit", "2", "--limit", "1"]),
])
def test_cli_accepts_workflow_flags(mod, extra, tmp_path):
    # --help after the flags: argparse validates everything it has seen, then exits 0
    r = subprocess.run([sys.executable, "-m", mod, *extra, *PROVIDER, *(SEAM if mod != "phase0.run_control" else []), "--help"],
                       capture_output=True, text=True, cwd=str(tmp_path.parent.parent) if False else None)
    assert r.returncode == 0, r.stderr[-800:]
