"""Build the placebo pool: promoted memories from kernels of repositories that
are outside the experiment (neither treatment nor negative control), so that
the placebo arm injects real defect-pattern text that cannot be relevant.

    python -m phase4.placebo_pool --kernels runs/rolling/streamlink__streamlink/kernel.json,runs/rolling/pvlib__pvlib-python/kernel.json --out placebo-pool.json

The file records each memory's content, source repository and id, and the
sha256 of the sorted contents so the pool can be pinned in a pre-registration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from memkernel.persist import _obj_from_dict


def build(kernel_paths: list[Path]) -> dict:
    pool = []
    for kp in kernel_paths:
        k = json.loads(kp.read_text())
        live = set(next((v for ver, v in k.get("versions", []) if ver == k.get("pinned_version")), []))
        for d in k.get("objects", []):
            o = _obj_from_dict(d)
            if o.kind == "promoted" and (not live or o.id in live):
                pool.append({"content": o.content, "source": kp.parent.name.replace("__", "/", 1), "id": o.id})
    pool.sort(key=lambda m: m["content"])
    digest = hashlib.sha256("\n".join(m["content"] for m in pool).encode()).hexdigest()
    return {"pool": pool, "n": len(pool), "sha256": digest, "sources": sorted({m["source"] for m in pool})}


def _main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kernels", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    res = build([Path(p) for p in a.kernels.split(",") if p])
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    sys.stdout.write(json.dumps({k: res[k] for k in ("n", "sha256", "sources")}) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
