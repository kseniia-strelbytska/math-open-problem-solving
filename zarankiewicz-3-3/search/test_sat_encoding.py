"""
Validation tests for search/sat_encoding.py.

This file is the actual load-bearing justification referenced in
sat_encoding.py's module docstring for the "double lex" symmetry-breaking
clauses -- that docstring is explicit that its own hand-wave argument has
a gap, and that what actually licenses trusting the symmetry-breaking
clauses is an EXHAUSTIVE empirical check on small cases, done here, not
the informal argument. Per README.md's working discipline ("ground the
riskiest step in something checkable"), this must be built and run BEFORE
the symmetry-breaking clauses are trusted on the real 16x17 target.

Two things are checked:

  1. `test_lex_ge_gadget`: the `lex_ge_clauses` gadget in total isolation.
     For bit-lengths 2, 3, and 4, build a CNF containing ONLY the lex_ge
     clauses over a pair of free literal sequences (a_lits, b_lits), with
     no other constraints. For EVERY possible bit assignment of a and b
     (full enumeration, not sampling -- 2^n * 2^n pairs, all small enough
     to enumerate completely), confirm the gadget is satisfiable exactly
     when "a >=_lex b" holds, as computed independently in plain Python
     (a simple, from-scratch loop, sharing no code with lex_ge_clauses).

  2. `test_symmetry_breaking_preserves_sat_status_*`: the full pipeline's
     symmetry-breaking clauses (`symmetry_breaking_clauses`, used via
     `build_instance(..., symmetry_breaking=True)`) on small (m, n, K)
     instances. Solve WITH and WITHOUT symmetry breaking and confirm they
     agree on SAT/UNSAT.
       - For the smallest cases (m, n in {3,4}, m*n <= 16) this is checked
         against an actual brute-force ground truth over ALL 2^(m*n)
         possible 0/1 matrices (a from-scratch, independent K_{3,3} check,
         sharing no code with sat_encoding.py or verify/checker.py) -- so
         this incidentally also re-validates the K_{3,3}-freeness clauses
         on those sizes, not just the symmetry-breaking clauses.
       - For larger cases (m, n up to 5, m*n up to 25) full enumeration is
         too slow, so only WITH-vs-WITHOUT solver agreement is checked,
         across several K values spanning sparse/mid/dense/full.
     Whenever a SAT verdict is produced, the decoded witness is ALSO run
     through the real, independent `verify/checker.py` (never trusted
     directly from the SAT model) to confirm it is genuinely a valid
     K-edge, K_{3,3}-free matrix.

If ANY case here shows symmetry breaking flipping SAT to UNSAT (or vice
versa) relative to the unconstrained instance, that is a stop-everything
finding: it would mean the symmetry-breaking clauses are unsound and any
downstream UNSAT result obtained with symmetry_breaking=True cannot be
trusted as a real proof. See SAT_LOG.md for the actual results of running
this suite.

Run with pytest:
    .venv/bin/python -m pytest search/test_sat_encoding.py -v
Or standalone (no pytest required):
    .venv/bin/python search/test_sat_encoding.py
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent
for p in (_HERE, _REPO_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from pysat.formula import CNF, IDPool
from pysat.solvers import Cadical153

import sat_encoding as se  # noqa: E402
from verify import checker  # noqa: E402


# ---------------------------------------------------------------------------
# Part 1: lex_ge_clauses in isolation
# ---------------------------------------------------------------------------

def _lex_ge_python(a_bits: tuple[int, ...], b_bits: tuple[int, ...]) -> bool:
    """
    Independent, from-scratch ground truth for "a >=_lex b" over equal-
    length 0/1 bit tuples, MSB-first (index 0 = most significant), matching
    the convention documented in lex_ge_clauses(). Shares no code with
    lex_ge_clauses() itself -- this is a plain scan for the first
    differing position.
    """
    for a, b in zip(a_bits, b_bits):
        if a != b:
            return a > b
    return True  # equal everywhere -> a >=_lex b holds (non-strict)


def test_lex_ge_gadget():
    for n_bits in (2, 3, 4):
        vpool = IDPool()
        a_lits = [vpool.id(("a", n_bits, i)) for i in range(n_bits)]
        b_lits = [vpool.id(("b", n_bits, i)) for i in range(n_bits)]
        clauses = se.lex_ge_clauses(a_lits, b_lits, vpool, ("test", n_bits))

        cnf = CNF()
        cnf.extend(clauses)

        with Cadical153(bootstrap_with=cnf.clauses) as solver:
            for a_bits in itertools.product((0, 1), repeat=n_bits):
                for b_bits in itertools.product((0, 1), repeat=n_bits):
                    assumptions = [
                        (lit if bit else -lit)
                        for lit, bit in zip(a_lits, a_bits)
                    ] + [
                        (lit if bit else -lit)
                        for lit, bit in zip(b_lits, b_bits)
                    ]
                    sat = solver.solve(assumptions=assumptions)
                    expected = _lex_ge_python(a_bits, b_bits)
                    assert sat == expected, (
                        f"lex_ge_clauses gadget disagreement at n_bits={n_bits}: "
                        f"a={a_bits} b={b_bits} solver_sat={sat} "
                        f"expected(a>=_lex b)={expected}"
                    )


# ---------------------------------------------------------------------------
# Part 2: full-pipeline symmetry-breaking SAT/UNSAT agreement
# ---------------------------------------------------------------------------

def _brute_force_max_k33_free(m: int, n: int) -> int:
    """
    Full enumeration over ALL 2^(m*n) possible m x n 0/1 matrices (encoded
    as a tuple of m row-bitmasks, each in range(2**n)). Returns the
    maximum edge count among matrices that are K_{3,3}-free.

    K_{3,3}-freeness check here is a from-scratch, independent
    implementation of the same underlying (and elementary/definitional)
    lemma used elsewhere in this project: 3 rows host a K_{3,3} iff their
    bitwise-AND (the set of columns they all three hit) has popcount >= 3.
    Shares no code with sat_encoding.py's k33_clauses or with
    verify/checker.py.

    Note: the set of achievable edge counts among K_{3,3}-free matrices is
    downward-closed (removing any single edge from a K_{3,3}-free graph
    cannot create a K_{3,3}), so "a K-edge K_{3,3}-free matrix exists" is
    exactly "K <= this function's return value" -- we don't need to
    separately enumerate every achievable K.
    """
    best = 0
    for row_vals in itertools.product(range(1 << n), repeat=m):
        ok = True
        for r1, r2, r3 in itertools.combinations(row_vals, 3):
            if bin(r1 & r2 & r3).count("1") >= 3:
                ok = False
                break
        if ok:
            edges = sum(bin(r).count("1") for r in row_vals)
            if edges > best:
                best = edges
    return best


def _solve(m: int, n: int, K: int, symmetry_breaking: bool):
    cnf, x, vpool = se.build_instance(m, n, K, symmetry_breaking=symmetry_breaking)
    with Cadical153(bootstrap_with=cnf.clauses) as solver:
        sat = solver.solve()
        model = solver.get_model() if sat else None
    matrix = se.model_to_matrix(model, x, m, n) if sat else None
    return sat, matrix


def _check_witness_if_sat(sat, matrix, K, context):
    """Never trust a SAT model directly -- always re-verify decoded
    witnesses with the real, independent checker before treating a SAT
    result as confirmed."""
    if sat:
        result = checker.verify(matrix, expected_edges=K)
        assert result["is_k33_free"], f"{context}: decoded witness is NOT K33-free"
        assert result["edges"] == K, f"{context}: decoded witness has wrong edge count"


# Smallest cases: full brute-force ground truth available (m*n <= 16).
TINY_CASES = [
    (3, 3),  # m*n = 9
    (3, 4),  # m*n = 12
    (3, 5),  # m*n = 15
    (4, 4),  # m*n = 16
]

# Larger cases: full enumeration is too slow; only WITH-vs-WITHOUT solver
# agreement is checked (still exhaustive over several boundary-spanning K
# values per case, and still witness-verified via checker.py on every SAT).
LARGER_CASES = [
    (4, 5),  # m*n = 20
    (5, 5),  # m*n = 25
]


def test_symmetry_breaking_preserves_sat_status_tiny():
    for m, n in TINY_CASES:
        mn = m * n
        max_edges = _brute_force_max_k33_free(m, n)
        candidates = sorted(set(
            k for k in (0, 1, max_edges - 1, max_edges, max_edges + 1, mn)
            if 0 <= k <= mn
        ))
        for K in candidates:
            expected_sat = K <= max_edges

            sat_off, mat_off = _solve(m, n, K, symmetry_breaking=False)
            assert sat_off == expected_sat, (
                f"UNCONSTRAINED instance disagrees with brute-force ground "
                f"truth at m={m} n={n} K={K} (max={max_edges}): "
                f"solver_sat={sat_off} expected={expected_sat} -- this would "
                f"mean the K33 clauses or cardinality encoding are wrong, "
                f"not (only) symmetry breaking"
            )
            _check_witness_if_sat(sat_off, mat_off, K, f"m={m} n={n} K={K} sym=False")

            sat_on, mat_on = _solve(m, n, K, symmetry_breaking=True)
            assert sat_on == expected_sat, (
                f"SYMMETRY BREAKING flips SAT status relative to ground "
                f"truth at m={m} n={n} K={K} (max={max_edges}): "
                f"solver_sat_with_symmetry={sat_on} expected={expected_sat} "
                f"unconstrained_solver_sat={sat_off} -- STOP: symmetry "
                f"breaking clauses are unsound"
            )
            _check_witness_if_sat(sat_on, mat_on, K, f"m={m} n={n} K={K} sym=True")


def test_symmetry_breaking_preserves_sat_status_larger():
    for m, n in LARGER_CASES:
        mn = m * n
        candidates = sorted(set(
            k for k in (0, 1, int(mn * 0.4), int(mn * 0.6), mn - 1, mn)
            if 0 <= k <= mn
        ))
        for K in candidates:
            sat_off, mat_off = _solve(m, n, K, symmetry_breaking=False)
            _check_witness_if_sat(sat_off, mat_off, K, f"m={m} n={n} K={K} sym=False")

            sat_on, mat_on = _solve(m, n, K, symmetry_breaking=True)
            _check_witness_if_sat(sat_on, mat_on, K, f"m={m} n={n} K={K} sym=True")

            assert sat_off == sat_on, (
                f"SYMMETRY BREAKING disagreement (no ground truth available "
                f"at this size, but the two configurations of the SAME "
                f"instance disagree with each other) at m={m} n={n} K={K}: "
                f"sym_off={sat_off} sym_on={sat_on} -- STOP: symmetry "
                f"breaking clauses are unsound"
            )


# ---------------------------------------------------------------------------
# Standalone runner (no pytest dependency required) -- mirrors
# verify/test_checker.py's style.
# ---------------------------------------------------------------------------

def _all_test_functions():
    mod = sys.modules[__name__]
    return [
        getattr(mod, name)
        for name in sorted(dir(mod))
        if name.startswith("test_") and callable(getattr(mod, name))
    ]


if __name__ == "__main__":
    import time

    tests = _all_test_functions()
    failures = []
    for fn in tests:
        t0 = time.time()
        try:
            fn()
            dt = time.time() - t0
            print(f"PASS  {fn.__name__}  ({dt:.1f}s)")
        except Exception as e:  # noqa: BLE001
            dt = time.time() - t0
            failures.append((fn.__name__, e))
            print(f"FAIL  {fn.__name__}  ({dt:.1f}s): {e!r}")

    print(f"\n{len(tests) - len(failures)}/{len(tests)} tests passed")
    if failures:
        sys.exit(1)
