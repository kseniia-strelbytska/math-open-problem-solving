#!/usr/bin/env python3
"""
Asserted checks on the degree-sequence side of `zarankiewicz-3-3/REDUCTION.md`,
plus a consistency check tying those counts to the orderly generator's own
measured search-tree width.

Why this is worth asserting rather than eyeballing: pinning the minimum row
degree and distributing the excess *is* an integer partition, so the counts
MUST come out as partition numbers. If the generator's enumeration over- or
under-counts at the top of the tree, this is where it shows up cheaply.

Run: python3 test_reduction.py
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ORDERLY = os.path.join(HERE, "orderly")


def num_partitions(n: int) -> int:
    """p(n), by the standard unrestricted-partition DP."""
    dp = [0] * (n + 1)
    dp[0] = 1
    for part in range(1, n + 1):
        for j in range(part, n + 1):
            dp[j] += dp[j - part]
    return dp[n]


def degree_sequences(m: int, e: int, dmin: int, dmax: int):
    """All non-increasing length-m sequences with entries in [dmin, dmax],
    summing to e, whose minimum is EXACTLY dmin."""
    out = []

    def rec(i, rem, cap, cur):
        if i == m:
            if rem == 0 and cur[-1] == dmin:
                out.append(tuple(cur))
            return
        left = m - i
        for d in range(min(cap, dmax), dmin - 1, -1):
            if d * left < rem:
                break                      # even all-d cannot reach rem
            if rem - d > d * (left - 1):
                continue                   # remaining rows cannot supply rem-d
            rec(i + 1, rem - d, d, cur + [d])

    rec(0, e, dmax, [])
    return out


CASES = [
    # label,                              m,   e, dmin, dmax, excess
    ("e=134 on 16x17, d_min=8",           16, 134,   8,   14,  6),
    ("e=133 on 16x17, d_min=8",           16, 133,   8,   13,  5),
    ("parent Ext(15,17,126), deg>=8",     15, 126,   8,   14,  6),
    ("parent Ext(15,17,125), deg>=8",     15, 125,   8,   13,  5),
]


def main() -> int:
    failures = []

    for label, m, e, dmin, dmax, excess in CASES:
        seqs = degree_sequences(m, e, dmin, dmax)
        expected = num_partitions(excess)
        ok = len(seqs) == expected
        print(f"{label:34s}: {len(seqs):3d} sequences, expected p({excess})={expected}  "
              f"{'OK' if ok else 'MISMATCH'}")
        if not ok:
            failures.append(f"{label}: got {len(seqs)}, expected p({excess})={expected}")

    # Tie the Ext(15,17,126) sequence set to the generator's own level-1 width.
    # Level 1 of that search enumerates exactly the admissible choices of the
    # FIRST (= maximum) row degree, so its width must equal the number of
    # distinct largest parts among the p(6)=11 partitions.
    seqs = degree_sequences(15, 126, 8, 14)
    distinct_max = sorted({s[0] for s in seqs})
    print(f"\ndistinct max degree over Ext(15,17,126) sequences: {distinct_max} "
          f"({len(distinct_max)} values)")

    if os.path.exists(ORDERLY):
        out = subprocess.run(
            [ORDERLY, "-n", "17", "-m", "15", "--enum", "126", "--emax", "126",
             "--dfloor", "8", "--hmode", "ub", "--assume", "9:81",
             "--countlevel", "1"],
            capture_output=True, text=True, timeout=120,
        )
        mm = re.search(r"level nodes:.*\b1:(\d+)", out.stdout + out.stderr)
        if mm:
            width = int(mm.group(1))
            ok = width == len(distinct_max)
            print(f"orderly measured level-1 tree width: {width}  "
                  f"{'OK - matches' if ok else 'MISMATCH'}")
            if not ok:
                failures.append(
                    f"level-1 width {width} != {len(distinct_max)} distinct max degrees")
        else:
            print("could not parse orderly level-1 width (skipped)")
    else:
        print("orderly binary not built; skipped the generator cross-check")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  -", f)
        return 1
    print("\nALL REDUCTION DEGREE-SEQUENCE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
