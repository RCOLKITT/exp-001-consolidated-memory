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
