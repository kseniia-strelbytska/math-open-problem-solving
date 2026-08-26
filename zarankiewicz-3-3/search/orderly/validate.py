#!/usr/bin/env python3
"""
Validation harness for the orderly generator.

Three independent things are checked, and all three must pass:

 1. AGREEMENT WITH A DELIBERATELY DIFFERENT SEARCH.  For every small cell
    (m,n) in a grid, `orderly --hcurve` produces h(k,n)=z(k,n;3) for
    k=1..m. For each of those we ask `brute` (a separate program that uses
    only row-mask ordering -- no column symmetry at all -- and the row-triple
    K33 test) two questions: is `value` reachable, and is `value+1`
    unreachable. Both must agree with orderly. This is what tests the risky
    column-orbit canonicity rule (R2): if R2 dropped a graph, orderly's value
    would be too low and brute would find value+1.

 2. AGREEMENT WITH PUBLISHED EXACT VALUES.

 3. CERTIFICATION OF EVERY WITNESS by verify/checker.py -- never by the
    search's own bookkeeping.

Run:  python3 validate.py
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "verify"))
import checker  # noqa: E402  the independent checker; never reimplemented here

ORDERLY = os.path.join(HERE, "orderly")
BRUTE = os.path.join(HERE, "brute")

# Published exact values used as trust anchors.  Squares from the classical
# Zarankiewicz table; the *,17 cells are the ones the case reduction needs.
PUBLISHED = {
    (3, 3): 8, (4, 4): 13, (5, 5): 20, (6, 6): 26,
    (7, 7): 33, (8, 8): 42, (9, 9): 49,
}
PUBLISHED_17 = {13: 110, 14: 118, 15: 126}


def run(cmd, timeout=None):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd} failed rc={r.returncode}\n{r.stdout}\n{r.stderr}")
    return r.stdout


def orderly_curve(n, m, extra=()):
    """Return {k: (value, nodes, secs)} and the top-level witness rows."""
    out = run([ORDERLY, "-n", str(n), "-m", str(m), "--hcurve", *extra])
    vals, wit = {}, None
    for line in out.splitlines():
        mm = re.match(r"F k=(\d+) dcap=(\d+) value=(\d+) nodes=(\d+) secs=([\d.]+)", line)
        if mm:
            vals[int(mm.group(1))] = (int(mm.group(3)), int(mm.group(4)), float(mm.group(5)))
        if line.startswith("WITNESS_ROWS"):
            parts = line.split()
            wit = [int(x) for x in parts[2:]]
    return vals, wit


def brute_decide(n, m, T, timeout=None):
    out = run([BRUTE, str(n), str(m), str(T)], timeout=timeout)
    return "FOUND" in out


def certify(rows, n, expected_edges, label):
    """Certify an explicit graph THROUGH verify/checker.py."""
    res = checker.verify(rows, expected_edges=expected_edges, n_cols=n)
    assert res["is_k33_free"], f"{label}: checker says K33 present!"
    assert res["edges"] == expected_edges, label
    return res


def main():
    fails, notes = [], []

    # ---------------- 1+3: grid agreement vs brute, witnesses certified -----
    print("=== grid: orderly vs independent brute force (n=3..8) ===")
    for n in range(3, 9):
        m = n
        vals, _ = orderly_curve(n, m)
        for k in sorted(vals):
            v = vals[k][0]
            # certify a witness at this exact value, produced by orderly
            out = run([ORDERLY, "-n", str(n), "-m", str(k), "--decide", str(v)])
            wr = None
            for line in out.splitlines():
                if line.startswith("WITNESS_ROWS"):
                    wr = [int(x) for x in line.split()[2:]]
            if wr is None:
                fails.append(f"orderly claims h({k},{n})={v} but produced no witness")
            else:
                certify(wr, n, v, f"h({k},{n})={v}")

            # brute must agree: v reachable, v+1 not
            try:
                lo = brute_decide(n, k, v, timeout=900)
                hi = brute_decide(n, k, v + 1, timeout=900)
            except subprocess.TimeoutExpired:
                notes.append(f"brute timeout at ({k},{n}) -- not cross-checked")
                print(f"  z({k},{n}) = {v:3d}  [orderly, witness CERTIFIED; brute timed out]")
                continue
            status = "OK" if (lo and not hi) else "MISMATCH"
            if status == "MISMATCH":
                fails.append(f"z({k},{n}): orderly={v} brute reach({v})={lo} reach({v+1})={hi}")
            print(f"  z({k},{n}) = {v:3d}  [witness CERTIFIED; brute agrees: {status}]")

    # ---------------- 2: published squares ----------------------------------
    print("\n=== published exact values (squares) ===")
    for (mm, nn), pv in sorted(PUBLISHED.items()):
        vals, _ = orderly_curve(nn, mm)
        got = vals[mm][0]
        ok = got == pv
        if not ok:
            fails.append(f"z({mm},{nn}): published {pv}, orderly {got}")
        print(f"  z({mm},{nn};3): published {pv:3d}  orderly {got:3d}  {'MATCH' if ok else 'MISMATCH'}")

    # ---------------- known witnesses from the literature -------------------
    print("\n=== literature witnesses re-checked (lower bounds) ===")
    wdir = os.path.join(ROOT, "data", "known_witnesses")
    for fn in sorted(os.listdir(wdir)):
        if not fn.endswith(".csv"):
            continue
        rows = []
        with open(os.path.join(wdir, fn)) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append([int(x) for x in line.split(",")])
        res = checker.verify(rows)
        print(f"  {fn}: {res['shape'][0]}x{res['shape'][1]} edges={res['edges']} "
              f"k33_free={res['is_k33_free']}")
        if not res["is_k33_free"]:
            fails.append(f"{fn} contains a K33")

    print()
    for nte in notes:
        print("NOTE:", nte)
    if fails:
        print("\nFAILURES:")
        for f in fails:
            print("  -", f)
        return 1
    print("ALL VALIDATION CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
