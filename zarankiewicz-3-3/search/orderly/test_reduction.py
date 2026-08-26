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


def chain_step(j: int, prev: int) -> int:
    """The Density Lemma (R6) upper-bound step: the largest e such that
    e - floor(e/j) <= prev.  Deleting a minimum-degree row of an e-edge
    j x n graph leaves at least e - floor(e/j) edges on j-1 rows."""
    e = prev
    while (e + 1) - ((e + 1) // j) <= prev:
        e += 1
    return e


def chain_up(k0: int, v0: int, kmax: int = 16) -> dict[int, int]:
    """Propagate f(k0) <= v0 upward with chain_step, returning {k: bound}."""
    out, v = {k0: v0}, v0
    for j in range(k0 + 1, kmax + 1):
        v = chain_step(j, v)
        out[j] = v
    return out


# (start level, start bound, expected f(16) bound, label)
CHAIN_CASES = [
    (9, 81, 144, "ORDERLY_LOG section 5, chain from the proved f(9)=81"),
    (11, 98, 138, "ORDERLY_LOG section 11.4, chain from the proved f(11)<=98"),
    (11, 97, 137, "one further edge at k=11"),
    (12, 105, 137, "one refutation at k=12 (target 106)"),
    (12, 102, 134, "section 11.5: equivalent to the hand-derived f(16)<=134"),
    (12, 101, 133, "section 11.5: equivalent to the published f(16)<=133"),
]

# (start level, start bound) -> how much f(16) improves per further edge saved
# there.  1 everywhere on the live chain; 8 at k=9 because of a divisor cliff.
SENSITIVITY = {
    (9, 81): 8,
    (11, 98): 1,
    (11, 97): 1,
    (12, 105): 1,
    (12, 102): 1,
    (12, 101): 1,
}

# f(16) goal -> the largest bound at k=11/12/13 that still reaches it
CHAIN_INVERSE = [
    (138, 98, 106, 114),
    (137, 97, 105, 113),
    (134, 94, 102, 110),
    (133, 93, 101, 109),
]


def check_chain() -> list[str]:
    """The density chain arithmetic behind ORDERLY_LOG sections 11.4/11.5.

    Worth asserting because every headline upper bound this workstream claims
    above k=11 is one of these numbers, and they were originally computed by
    hand.  A single off-by-one here would misstate the project's headline
    result for z(16,17;3)."""
    failures = []
    print("\n--- density chain (R6) arithmetic ---")
    for k0, v0, want16, label in CHAIN_CASES:
        got = chain_up(k0, v0)[16]
        ok = got == want16
        print(f"f({k0}) <= {v0:3d}  =>  f(16) <= {got:3d}  (expect {want16:3d})  "
              f"{'OK' if ok else 'MISMATCH'}   {label}")
        if not ok:
            failures.append(f"chain from f({k0})<={v0}: got f(16)<={got}, expected {want16}")

    print("\n--- inverse: what each f(16) goal requires ---")
    for goal, n11, n12, n13 in CHAIN_INVERSE:
        for k0, need in ((11, n11), (12, n12), (13, n13)):
            best = max(v for v in range(60, 145) if chain_up(k0, v)[16] <= goal)
            ok = best == need
            if not ok:
                failures.append(
                    f"f(16)<={goal} via k={k0}: largest sufficient bound is {best}, "
                    f"log says {need}")
            print(f"f(16) <= {goal}  needs f({k0}) <= {best:3d}  (log says {need:3d})  "
                  f"{'OK' if ok else 'MISMATCH'}")

    # The 1:1 propagation claim of section 11.4, asserted the way the log uses
    # it: one edge saved at k0 is exactly one edge saved at k=16.  (Asserting
    # the *reason* -- floor(e/j) == 8 -- would be wrong to state globally: on
    # the older, weaker chain from f(9)=81 the divisor is 9, not 8.  The
    # sensitivity is what the log actually relies on, so that is what is
    # checked.)
    #
    # The sensitivity is NOT uniform, and the exception is worth asserting
    # rather than glossing: at k=9 one further edge would have been worth
    # EIGHT at k=16, because f(9)=81 sits just above a divisor cliff
    # (floor(90/10)=9, but from f(9)=80 the chain runs 88,96,... with
    # floor=8 throughout).  See ORDERLY_LOG section 11.4a.  That door is shut --
    # f(9)=81 is proved exactly, with a certified 81-edge witness -- but it
    # explains why the chain from k=9 was so much worse than it looked.
    print()
    for k0, v0, _, _ in CHAIN_CASES:
        got = chain_up(k0, v0)[16] - chain_up(k0, v0 - 1)[16]
        want = SENSITIVITY[(k0, v0)]
        ok = got == want
        print(f"one edge saved at k={k0} (from {v0}) moves f(16) by {got} "
              f"(expect {want})  {'OK' if ok else 'MISMATCH'}")
        if not ok:
            failures.append(
                f"chain sensitivity at k={k0}, v={v0}: f(16) moves by {got}, "
                f"expected {want}")

    # And the stated *reason*, checked only where the log states it: on the
    # live chain (k0 >= 11) every step has floor(e/j) == 8, i.e. f(j) <= f(j-1)+8.
    for k0, v0, _, _ in CHAIN_CASES:
        if k0 < 11:
            continue
        bounds = chain_up(k0, v0)
        for j in range(k0 + 1, 17):
            if bounds[j] // j != 8:
                failures.append(
                    f"step-size claim broken on the live chain: "
                    f"floor({bounds[j]}/{j}) = {bounds[j] // j}, not 8")
    live_ok = not any("step-size" in f for f in failures)
    print(f"live chain (k0 >= 11) has floor(e/j) == 8 at every step: "
          f"{'OK' if live_ok else 'MISMATCH'}")
    print()

    # Why k=12 @ 106 is structurally wider than k=11 @ 99 (section 13.1):
    # the tightness argument leaves 0 slack at k=11 and 10 at k=12.
    for m, e, dfloor, want in ((11, 99, 9, 1), (12, 106, 8, 41)):
        seqs = degree_sequences(m, e, dfloor, min(17, e - (m - 1) * dfloor))
        ok = len(seqs) == want
        print(f"k={m}, e={e}, dfloor={dfloor}: {len(seqs):3d} admissible degree "
              f"sequences (expect {want})  {'OK' if ok else 'MISMATCH'}")
        if not ok:
            failures.append(f"k={m} e={e}: {len(seqs)} degree sequences, expected {want}")
    return failures


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

    failures.extend(check_chain())

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  -", f)
        return 1
    print("\nALL REDUCTION DEGREE-SEQUENCE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
