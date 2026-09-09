from adapters.code.oracle import Location
from phase0.ground_truth import gold_files, ground_truth_from_tasks, is_test_path, parse_patch

PATCH = """diff --git a/pkg/core.py b/pkg/core.py
index 1..2 100644
--- a/pkg/core.py
+++ b/pkg/core.py
@@ -10,7 +10,8 @@ def f():
-    x = 1
+    x = 2
+    y = 3
@@ -40 +41,2 @@ def g():
+    pass
diff --git a/tests/test_core.py b/tests/test_core.py
--- a/tests/test_core.py
+++ b/tests/test_core.py
@@ -1,3 +1,4 @@
+import x
diff --git a/pkg/new.py b/pkg/new.py
new file mode 100644
--- /dev/null
+++ b/pkg/new.py
@@ -0,0 +1,3 @@
+a
"""


def test_parse_files_and_hunks():
    s = parse_patch(PATCH)
    assert s.files == ("pkg/core.py", "tests/test_core.py", "pkg/new.py")
    assert Location("pkg/core.py", 10, 16) in s.hunks
    assert Location("pkg/core.py", 40, 40) in s.hunks
    assert Location("pkg/new.py", 0, 0) in s.hunks          # pure addition: zero-width at 0


def test_tests_excluded_by_default():
    assert gold_files(PATCH) == ("pkg/core.py", "pkg/new.py")
    assert gold_files(PATCH, exclude_tests=False) == ("pkg/core.py", "tests/test_core.py", "pkg/new.py")
    assert is_test_path("tests/unit/test_x.py") and is_test_path("pkg/conftest.py")
    assert not is_test_path("pkg/core.py")


def test_ground_truth_table():
    class T:
        instance_id = "r__p-1"
        patch = PATCH
    gt = ground_truth_from_tasks([T()])
    locs = gt.locations("r__p-1")
    assert locs is not None and all(not l.path.startswith("tests/") for l in locs)
    assert gt.locations("nope") is None
