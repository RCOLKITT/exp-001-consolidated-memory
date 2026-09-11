import csv
import json

from phase0.functions import function_index
from phase2.handcheck import indent_symbols, verify_functions

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


def test_indentation_symboliser_agrees_with_ast_on_spans():
    ast_spans = {(s.qualname, s.start_line, s.end_line) for s in function_index(SRC)}
    ind = set(indent_symbols(SRC))
    assert ind == ast_spans, (ind ^ ast_spans)


def test_verify_functions_scores_agreement(tmp_path):
    p = tmp_path / "hc.csv"
    with p.open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["instance_id", "path", "hunk_start", "hunk_end", "oracle", "manual", "context"])
        w.writerow(["o__r-1", "pkg/m.py", 16, 16, "Box.area", "", ""])
        w.writerow(["o__r-1", "pkg/m.py", 3, 3, "<module>", "", ""])
        w.writerow(["o__r-1", "pkg/m.py", 8, 8, "tail", "", ""])            # deliberately wrong oracle row
    rate, agree, n = verify_functions(str(p), str(tmp_path / "out.csv"), lambda iid, path: SRC)
    assert (agree, n) == (2, 3)
    rows = list(csv.DictReader(open(tmp_path / "out.csv")))
    assert [r["manual"] for r in rows] == ["Box.area", "<module>", "top"]
