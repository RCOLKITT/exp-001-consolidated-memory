"""Build a task corpus from a repository's own history (Memory Value Report).

    python -m phase0.repo_corpus --clone /path/to/repo --repo owner/name --branch main \
        --suffixes .ts,.tsx,.js,.py --cutoff 2023-12-31 --model meta-llama/llama-3.3-70b-instruct --out corpus/

Each non-merge commit on the branch becomes a task, in chronological order:
  problem_statement = commit subject + body (PR trailers and sign-offs stripped)
  base_commit       = the commit's parent (the tree the verifier sees)
  patch             = diff parent..commit restricted to source files
Commits whose patch touches no non-test source file are dropped (nothing to
localize). `filelists.jsonl` carries the source tree at each base_commit so
the harness never needs to clone the repository (private repos). Nothing is
read from GitHub; only the local clone.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from phase0.ground_truth import is_test_path, parse_patch

TRAILER = re.compile(r"^(co-authored-by|signed-off-by|claude-session|reviewed-by|see-also):", re.I)
PR_REF = re.compile(r"\s*\(#\d+\)\s*$")


def _git(clone: str, *args: str) -> str:
    return subprocess.run(["git", "-C", clone, *args], capture_output=True, text=True, check=True).stdout


def clean_message(subject: str, body: str) -> str:
    lines = [l.rstrip() for l in body.splitlines() if not TRAILER.match(l.strip())]
    text = "\n".join(lines).strip()
    return (PR_REF.sub("", subject).strip() + ("\n\n" + text if text else "")).strip()


def build(clone: str, repo: str, branch: str, suffixes: tuple[str, ...], min_words: int = 0) -> tuple[list[dict], list[dict], dict]:
    hashes = _git(clone, "rev-list", "--no-merges", "--reverse", branch).split()
    tasks, trees, dropped = [], [], {"no_parent": 0, "no_source_gold": 0, "short_message": 0}
    for h in hashes:
        parents = _git(clone, "log", "-1", "--format=%P", h).split()
        if not parents:
            dropped["no_parent"] += 1; continue
        parent = parents[0]
        subject = _git(clone, "log", "-1", "--format=%s", h).strip()
        body = _git(clone, "log", "-1", "--format=%b", h)
        date = _git(clone, "log", "-1", "--format=%cI", h).strip()
        patch = _git(clone, "diff", f"{parent}..{h}", "--")
        gold = [f for f in parse_patch(patch).files if f.endswith(suffixes) and not is_test_path(f)]
        if not gold:
            dropped["no_source_gold"] += 1; continue
        msg = clean_message(subject, body)
        if len(msg.split()) < min_words:
            dropped["short_message"] += 1; continue
        # keep only the hunks of source files in the stored patch (tests and docs are noise for the oracle)
        keep = set(gold); out_lines = []; cur = None
        for line in patch.splitlines():
            m = re.match(r"^diff --git a/(.+?) b/(.+)$", line)
            if m:
                cur = m.group(2)
            if cur in keep:
                out_lines.append(line)
        iid = f"{repo.replace('/', '__')}-{h[:10]}"
        tasks.append({"instance_id": iid, "repo": repo, "base_commit": parent, "created_at": date, "problem_statement": msg, "patch": "\n".join(out_lines) + "\n"})
        files = [f for f in _git(clone, "ls-tree", "-r", "--name-only", parent).split("\n") if f.endswith(suffixes)]
        trees.append({"instance_id": iid, "files": sorted(files)})
    return tasks, trees, {"commits": len(hashes), "tasks": len(tasks), "dropped": dropped}


def _main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--clone", required=True); ap.add_argument("--repo", required=True); ap.add_argument("--branch", default="main")
    ap.add_argument("--suffixes", default=".ts,.tsx,.js,.mjs,.py"); ap.add_argument("--min-words", type=int, default=0)
    ap.add_argument("--cutoff", required=True, help="verifier training cutoff YYYY-MM-DD (freshness gate)"); ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    suffixes = tuple(x.strip() for x in a.suffixes.split(",") if x.strip())
    tasks, trees, summary = build(a.clone, a.repo, a.branch, suffixes, a.min_words)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / "tasks.jsonl").write_text("".join(json.dumps(t) + "\n" for t in tasks))
    (out / "filelists.jsonl").write_text("".join(json.dumps(t) + "\n" for t in trees))
    (out / "models.json").write_text(json.dumps({a.model: a.cutoff}) + "\n")
    summary.update({"repo": a.repo, "branch": a.branch, "suffixes": list(suffixes), "median_tree_size": sorted(len(t["files"]) for t in trees)[len(trees) // 2] if trees else 0})
    (out / "corpus-summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    sys.stdout.write(json.dumps(summary) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
