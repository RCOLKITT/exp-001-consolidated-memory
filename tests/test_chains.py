from phase0.chains import build_chains, markdown_report, stats
from phase0.corpus import Task


def _t(repo, iid, day):
    return Task(instance_id=iid, repo=repo, base_commit="abc", created_at=f"2025-01-{day:02d}T00:00:00Z",
                problem_statement="p", patch="diff --git a/x b/x\n")


def test_chains_are_chronological_and_sorted_by_length():
    tasks = [_t("a/a", "a3", 3), _t("b/b", "b1", 1), _t("a/a", "a1", 1), _t("a/a", "a2", 2)]
    chains = build_chains(tasks)
    assert [c.repo for c in chains] == ["a/a", "b/b"]
    assert [t.instance_id for t in chains[0].tasks] == ["a1", "a2", "a3"]
    assert chains[0].span_days == 2
    build, ev = chains[0].split(2)
    assert [t.instance_id for t in build] == ["a1", "a2"] and [t.instance_id for t in ev] == ["a3"]


def test_stats_and_eligibility():
    tasks = [_t("a/a", f"a{i}", i) for i in range(1, 8)] + [_t("b/b", "b1", 1)]
    chains = build_chains(tasks)
    s = stats(chains, min_build=4, min_eval=2)
    assert s.n_repos == 2 and s.n_tasks == 8 and s.eligible_repos == ("a/a",)
    assert s.count_at_least(5) == 1
    md = markdown_report(chains, 4, 2)
    assert "| a/a | 7 |" in md and "eligible" in md


def test_recurrence_report_counts_gold_files_and_dirs():
    from phase2.recurrence import analyse
    def patch(*paths):
        return "".join(f"diff --git a/{p} b/{p}\n--- a/{p}\n+++ b/{p}\n@@ -1,1 +1,1 @@\n-a\n+b\n" for p in paths)
    tasks = [Task(instance_id=f"o__r-{i}", repo="o/r", base_commit="c", created_at=f"2025-01-{i+1:02d}", problem_statement="p",
                  patch=patch("pkg/a.py" if i % 2 == 0 else f"pkg/b{i}.py")) for i in range(8)]
    res = analyse(tasks, ["o/r"], [4])
    r4 = res["o/r"]["rows"][0]
    assert r4["prefix"] == 4 and r4["files_ge3"] == 0 and r4["files_ge2"] == 1 and r4["dirs_ge3"] == 1
    assert r4["eval_file_seen1"] == 0.5 and r4["eval_dir_seen3"] == 1.0
