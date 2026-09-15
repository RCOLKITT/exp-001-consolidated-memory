import json
import os
import subprocess
from pathlib import Path

from phase0.repo_corpus import build, clean_message


def _run(d, *cmd):
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"}
    subprocess.run(["git", "-C", str(d), *cmd], check=True, env=env, capture_output=True)


def test_build_tasks_from_commits(tmp_path: Path):
    d = tmp_path / "r"; d.mkdir(); _run(d, "init", "-q", "-b", "main")
    (d / "src").mkdir(); (d / "src" / "a.ts").write_text("export const a = 1;\n"); (d / "README.md").write_text("x\n")
    _run(d, "add", "."); _run(d, "commit", "-q", "-m", "feat: initial (#1)")
    (d / "src" / "a.ts").write_text("export const a = 2;\n"); (d / "src" / "a.test.ts").write_text("test\n")
    _run(d, "add", "."); _run(d, "commit", "-q", "-m", "fix(core): a returns 2 (#2)\n\nLong body here.\n\nCo-Authored-By: someone <x@y>")
    (d / "README.md").write_text("y\n"); _run(d, "add", "."); _run(d, "commit", "-q", "-m", "docs: readme (#3)")
    tasks, trees, summary = build(str(d), "o/r", "main", (".ts",))
    assert summary["commits"] == 3 and summary["tasks"] == 1                      # root has no parent; docs-only dropped
    t = tasks[0]
    assert t["problem_statement"] == "fix(core): a returns 2\n\nLong body here." and "Co-Authored" not in t["problem_statement"]
    assert "src/a.ts" in t["patch"] and "a.test.ts" not in t["patch"]               # test hunks stripped from the stored patch
    assert trees[0]["files"] == ["src/a.ts"] and trees[0]["instance_id"] == t["instance_id"]
    assert clean_message("x (#9)", "") == "x"
