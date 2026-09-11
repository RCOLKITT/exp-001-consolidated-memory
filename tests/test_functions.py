"""Function index, symbolised ground truth, and the oracle's symbol clause."""
from adapters.code.oracle import Location
from phase0.corpus import Task
from phase0.functions import MODULE, FunctionIndexCache, Span, enclosing, enclosing_range, function_index
from phase0.ground_truth import function_ground_truth_from_tasks, gold_symbols, symbolise_hunks

SRC = '''import os

CONST = 1


def top(a):
    def inner():
        return a
    return inner()


class Box:
    size = 0

    @property
    def area(self):
        return self.size ** 2

    async def fetch(self):
        pass


def tail():
    pass
'''


def test_index_lists_top_level_functions_classes_and_methods_with_spans():
    idx = function_index(SRC)
    names = [s.qualname for s in idx]
    assert names == ["top", "Box", "Box.area", "Box.fetch", "tail"]        # nested `inner` folded into `top`
    area = next(s for s in idx if s.qualname == "Box.area")
    assert (area.start_line, area.end_line) == (15, 17)                    # decorator line starts the span
    assert enclosing(idx, 8).qualname == "top"
    assert enclosing(idx, 13).qualname == "Box"                             # class body outside any method
    assert enclosing(idx, 3) is None                                        # module level


def test_range_maps_to_every_symbol_touched_and_module_where_none():
    idx = function_index(SRC)
    assert enclosing_range(idx, 3, 3) == (MODULE,)
    assert enclosing_range(idx, 8, 16) == ("top", MODULE, "Box", "Box.area")
    assert enclosing_range(idx, 0, 0) == (MODULE,)                          # pure insertion at 0
    assert function_index("def broken(:\n") == ()                          # unparseable -> empty


def _task(iid, patch):
    return Task(instance_id=iid, repo="o/r", base_commit="c1", created_at="2025-01-01T00:00:00Z", problem_statement="p", patch=patch)


PATCH = """diff --git a/pkg/m.py b/pkg/m.py
--- a/pkg/m.py
+++ b/pkg/m.py
@@ -16,2 +16,2 @@
-x
+y
@@ -3 +3 @@
-CONST = 1
+CONST = 2
diff --git a/pkg/new.py b/pkg/new.py
--- /dev/null
+++ b/pkg/new.py
@@ -0,0 +1,2 @@
+a
"""


def test_symbolised_ground_truth_and_cache(tmp_path):
    reads = []

    def read(repo, commit, path):
        reads.append(path)
        return SRC if path == "pkg/m.py" else None
    cache = FunctionIndexCache(read, tmp_path / "functions.jsonl")
    t = _task("o__r-1", PATCH)
    gt = function_ground_truth_from_tasks([t], cache)
    locs = gt.locations("o__r-1")
    assert Location("pkg/m.py", 15, 17, "Box.area") in locs
    assert Location("pkg/m.py", 3, 3, MODULE) in locs
    assert Location("pkg/new.py", 0, 0, MODULE) in locs                    # file absent at base_commit
    assert gold_symbols(t, cache) == ("pkg/m.py::Box.area", "pkg/m.py::<module>", "pkg/new.py::<module>")
    assert gt.locations("o__r-1") is locs                                   # memoised
    # a fresh cache object reads the JSONL and never calls the checkout again
    cache2 = FunctionIndexCache(lambda *a: (_ for _ in ()).throw(AssertionError("no read")), tmp_path / "functions.jsonl")
    assert cache2.spans("o/r", "c1", "pkg/m.py") == cache.spans("o/r", "c1", "pkg/m.py") and cache2.spans("o/r", "c1", "pkg/new.py") is None


def test_oracle_symbol_clause():
    gold_fn = Location("pkg/m.py", 15, 17, "Box.area")
    gold_mod = Location("pkg/m.py", 3, 3, MODULE)
    assert Location("pkg/m.py", 15, 17, "Box.area").overlaps(gold_fn)
    assert not Location("pkg/m.py", 15, 17, "Box.fetch").overlaps(gold_fn)       # right lines, wrong symbol
    assert not Location("pkg/m.py", 1, 10**9, MODULE).overlaps(gold_fn)          # "<module>" earns no function credit
    assert Location("pkg/m.py", 1, 10**9, MODULE).overlaps(gold_mod)             # ...but does match a module-level hunk
    assert Location("pkg/m.py", 1, 10**9).overlaps(gold_fn)                      # file-level flag: unchanged v1 semantics
    assert gold_fn.file_level == Location("pkg/m.py", 1, 10**9)
