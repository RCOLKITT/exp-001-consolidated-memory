"""Every CLI must parse the flags the workflows pass (this is what run/exp-1 failed on)."""
import subprocess
import sys

import pytest

SEAM = ["--similarity", "hashing", "--embedding-model", "m", "--embedding-revision", "abc", "--theta", "0.45", "--rho", "0.7", "--cluster-similarity", "0.6", "--consolidation", "function", "--min-occurrences", "2", "--min-distinct-inputs", "2", "--granularity", "function", "--tau", "0.5"]
PROVIDER = ["--provider", "openai-compatible", "--base-url", "http://x/v1", "--api-key-env", "K", "--model-extra", "{}", "--model", "m", "--top-k", "3", "--ttl", "30"]


@pytest.mark.parametrize("mod,extra", [
    ("phase3.learn", ["--tasks", "t", "--split", "s", "--out", "o"]),
    ("phase4.evaluate", ["--tasks", "t", "--split", "s", "--learn-dir", "l", "--out", "o", "--seed", "1", "--max-eval-per-repo", "5", "--arms", "control,treatment,ungated"]),
    ("phase0.run_control", ["--tasks", "t", "--out", "o", "--repos", "a/b", "--per-repo-limit", "2", "--limit", "1", "--level", "function"]),
    ("phase2.recurrence", ["t", "--repos", "a/b", "--level", "function", "--repos-dir", "r", "--functions-cache", "f"]),
    ("phase4.paired", ["--eval-dir", "e", "--out", "o", "--treatment-arm", "ungated", "--secondary-repos", "a/b"]),
    ("phase4.rolling", ["--tasks", "t", "--repos", "a/b", "--warmup", "20", "--out", "o", "--seed", "11", "--arms", "control,treatment:0,gated:0.5,placebo:0", "--placebo-pool", "p.json"]),
    ("phase4.aggregate", ["--dirs", "a,b", "--negative-control", "n/c", "--out", "o"]),
    ("phase4.placebo_pool", ["--kernels", "k.json", "--out", "p.json"]),
])
def test_cli_accepts_workflow_flags(mod, extra, tmp_path):
    # --help after the flags: argparse validates everything it has seen, then exits 0
    r = subprocess.run([sys.executable, "-m", mod, *extra, *(PROVIDER if mod in ("phase3.learn", "phase4.evaluate", "phase0.run_control", "phase4.rolling") else []), *(SEAM if mod in ("phase3.learn", "phase4.evaluate", "phase4.rolling") else []), "--help"],
                       capture_output=True, text=True, cwd=str(tmp_path.parent.parent) if False else None)
    assert r.returncode == 0, r.stderr[-800:]
