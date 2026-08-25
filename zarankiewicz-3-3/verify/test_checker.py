"""
Test suite for verify/checker.py.

This suite exists to earn trust in the checker BEFORE it is ever pointed
at a real Z(16,17,3,3) candidate matrix (see README.md, "Independent
verification": "no single script is allowed to both generate and certify
a result" -- the checker must be validated against cases whose answer is
already known by hand, independently of the checker itself).

Run with pytest:
    python -m pytest verify/test_checker.py -v

Or standalone (no pytest required):
    python verify/test_checker.py
"""

from __future__ import annotations

import itertools
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import checker  # noqa: E402


# ---------------------------------------------------------------------------
# A fourth, fully independent ground-truth implementation used ONLY in
# tests -- pure Python, no numpy, no networkx, operating on plain lists of
# lists. Its only job is to give us something to compare checker.py
# against that shares zero code with checker.py's three internal methods.
# ---------------------------------------------------------------------------

def _brute_force_ground_truth(rows: list[list[int]]) -> bool:
    """
    Pure-Python (no numpy, no networkx) brute-force K_{3,3} detector.
    Iterates over row-triples and, for each, does a plain Python set
    intersection over column indices. Independent of checker.py entirely.
    """
    m = len(rows)
    n = len(rows[0]) if m else 0
    for r0, r1, r2 in itertools.combinations(range(m), 3):
        cols0 = {j for j in range(n) if rows[r0][j]}
        cols1 = {j for j in range(n) if rows[r1][j]}
        cols2 = {j for j in range(n) if rows[r2][j]}
        common = cols0 & cols1 & cols2
        if len(common) >= 3:
            return True
    return False


def _brute_force_edge_count(rows: list[list[int]]) -> int:
    return sum(sum(row) for row in rows)


# ---------------------------------------------------------------------------
# Test 1: K_{3,3} itself must be flagged as containing K_{3,3}.
# ---------------------------------------------------------------------------

def test_k33_itself_is_detected():
    m = np.ones((3, 3), dtype=np.uint8)
    result = checker.verify(m, expected_edges=9)
    assert result["has_k33"] is True
    assert result["is_k33_free"] is False
    assert result["edges"] == 9
    assert result["methods"] == {"row_triples": True, "col_triples": True, "networkx": True}


# ---------------------------------------------------------------------------
# Test 2: K_{3,3} minus one edge (8 ones out of 9) must be K_{3,3}-free.
#
# Hand reasoning: with only 3 rows and 3 columns total, there is exactly
# one row-triple (all of them) and one column-triple (all of them) to
# check. Removing entry (0,0) means row 0 is missing column 0, so the
# columns common to all three rows are {1, 2} -- only 2, not 3. No
# K_{3,3} is possible with fewer than 3 fully-connected columns among the
# 3 rows. So this must be K_{3,3}-free.
# ---------------------------------------------------------------------------

def test_k33_minus_one_edge_is_free():
    m = np.ones((3, 3), dtype=np.uint8)
    m[0, 0] = 0
    assert int(m.sum()) == 8
    result = checker.verify(m, expected_edges=8)
    assert result["has_k33"] is False
    assert result["is_k33_free"] is True


# ---------------------------------------------------------------------------
# Test 3: K_{4,4} minus a perfect matching.
#
# Hand reasoning: rows 0..3, columns 0..3, with entry (i, i) removed for
# each i (the perfect matching). So row i is adjacent to every column
# except column i -- each row has degree 3, total edges = 4*3 = 12.
#
# Take any 3 of the 4 rows, say rows {a, b, c} (a<b<c, all distinct).
# Row a is missing only column a, row b only column b, row c only column
# c. Since a, b, c are pairwise distinct, the set of columns missing from
# at least one of these three rows is exactly {a, b, c} -- three distinct
# columns. Out of 4 columns total, the columns present in ALL THREE rows
# are the complement of {a, b, c} within {0,1,2,3}, which has exactly
# 4 - 3 = 1 element. So any 3-row subset has only 1 common column, never
# 3. This holds for all 4 choices of which 3 rows (by the symmetry of a
# perfect matching), so K_{4,4} minus a perfect matching contains NO
# K_{3,3}. (This is exactly why perfect-matching removal is a classic
# K_{3,3}-free construction technique for these problems.)
# ---------------------------------------------------------------------------

def test_k44_minus_perfect_matching_is_free():
    m = np.ones((4, 4), dtype=np.uint8)
    for i in range(4):
        m[i, i] = 0
    assert int(m.sum()) == 12
    result = checker.verify(m, expected_edges=12)
    assert result["has_k33"] is False
    assert result["is_k33_free"] is True

    # Cross-check with the independent pure-Python ground truth too.
    rows = m.tolist()
    assert _brute_force_ground_truth(rows) is False
    assert _brute_force_edge_count(rows) == 12


# ---------------------------------------------------------------------------
# Test 3b: K_{4,4} minus a perfect matching, PLUS one extra edge put back,
# must become K_{3,3}-containing.
#
# Hand reasoning: restore edge (0,0). Now row 0 is adjacent to all 4
# columns, rows 1,2,3 are still missing only columns 1,2,3 respectively.
# Consider rows {0, 1, 2}: row 0 misses nothing, row 1 misses column 1,
# row 2 misses column 2. Columns missing from at least one of these three
# rows: {1, 2}. Common columns = complement = {0, 3} -- wait that's only
# 2. Let's instead consider rows {1, 2, 3}: unaffected by the restored
# edge (0,0) since row 0 isn't among them -- still only 1 common column,
# as in the base case. So we must check ALL 4 row-triples that include
# row 0: {0,1,2}: missing columns from the trio = {1,2} (row0 misses
# nothing extra), common = {0,3}, size 2 -- still not enough with only 4
# columns total (need to leave 3 free, but 2 other rows already forbid 2
# distinct columns, leaving only 4-2=2). So actually restoring ONE edge
# of a 4x4 grid is NOT enough to force a K_{3,3} -- 4 columns isn't wide
# enough for 3 rows to jointly free up 3 common columns unless at least
# two of the three chosen rows are matching-full. This sub-case instead
# checks a DIFFERENT known-by-hand positive control: extend to a 4x5
# grid (4 rows, 5 columns) built as [K_{4,4} minus matching] with a 5th
# column added that is all-ones. Now consider rows {1,2,3} (all missing
# their own diagonal column among 0..3, but all present in column 4):
# common columns among {1,2,3} = (complement of {1,2,3} within {0,1,2,3})
# UNION column 4 restricted to common = {0} plus column 4 = {0, 4}, size
# 2 still. Try rows {0,1,2}: common = {3} plus column 4 = {3,4}, size 2.
# Every 3-row subset still yields only 2 common columns (1 from the
# 4x4 part + the all-ones column), so THIS still doesn't contain K_{3,3}
# either -- it takes 3 wide-open columns. So instead we use the more
# direct positive control below (a full 3x3 all-ones submatrix planted
# inside a larger matrix), which by Test 1's reasoning obviously must be
# detected regardless of what surrounds it.
# ---------------------------------------------------------------------------

def test_planted_k33_inside_larger_matrix_is_detected():
    # 5x6 all-zero matrix with a K_{3,3} planted at rows {1,3,4}, cols {0,2,5}.
    m = np.zeros((5, 6), dtype=np.uint8)
    planted_rows = [1, 3, 4]
    planted_cols = [0, 2, 5]
    for r in planted_rows:
        for c in planted_cols:
            m[r, c] = 1
    assert int(m.sum()) == 9
    result = checker.verify(m, expected_edges=9)
    assert result["has_k33"] is True
    assert result["is_k33_free"] is False


# ---------------------------------------------------------------------------
# Test 4: edge count sanity check against a matrix with a known number of
# ones, built by an explicit, easy-to-hand-verify pattern.
# ---------------------------------------------------------------------------

def test_edge_count_known_value():
    # 6x7 matrix, ones on a simple diagonal-ish stripe pattern:
    # set m[i, j] = 1 iff (i + j) % 7 < 3. For each of the 6 rows, exactly
    # 3 of the 7 columns satisfy (i+j)%7 < 3 (since (i+j)%7 cycles through
    # all residues 0..6 exactly once as j ranges over 0..6), so total ones
    # = 6 rows * 3 = 18, by hand.
    m = np.zeros((6, 7), dtype=np.uint8)
    for i in range(6):
        for j in range(7):
            if (i + j) % 7 < 3:
                m[i, j] = 1
    assert checker.count_ones_numpy(m) == 18
    assert checker.count_ones_manual(m) == 18
    result = checker.verify(m, expected_edges=18)
    assert result["edges"] == 18


def test_edge_count_mismatch_raises():
    m = np.ones((3, 3), dtype=np.uint8)
    try:
        checker.verify(m, expected_edges=8)  # actual is 9
        assert False, "expected ValueError for mismatched expected_edges"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Test 5: random 16x17 matrices, many trials, all three internal methods
# cross-checked for agreement (verify() raises CheckerDisagreement if they
# don't), PLUS agreement against the independent pure-Python ground truth.
# This is a smoke test, not a proof -- it's here to catch a method
# disagreeing with the others across a wide variety of random inputs.
# ---------------------------------------------------------------------------

def test_random_16x17_many_trials_agree():
    rng = random.Random(20260825)  # fixed seed for reproducibility
    n_trials = 300
    # Edge probability chosen so these often (but not always) contain a
    # K_{3,3}: with p around 0.4-0.5 on a 16x17 bipartite graph, K_{3,3}s
    # are common but a nontrivial fraction of trials will still be free
    # (since 16x17 is comfortably above the K_{3,3}-free extremal edge
    # density but random graphs at these densities aren't guaranteed to
    # avoid it either) -- either way we just require self-consistency.
    saw_true = False
    saw_false = False
    for trial in range(n_trials):
        p = rng.choice([0.15, 0.3, 0.45, 0.6])
        rows = [[1 if rng.random() < p else 0 for _ in range(17)] for _ in range(16)]
        m = np.array(rows, dtype=np.uint8)

        result = checker.verify(m)  # raises CheckerDisagreement internally if methods disagree
        ground_truth = _brute_force_ground_truth(rows)
        assert result["has_k33"] == ground_truth, (
            f"trial {trial} (p={p}): checker.verify()={result['has_k33']} "
            f"but independent brute force={ground_truth}"
        )
        assert result["edges"] == _brute_force_edge_count(rows)

        if result["has_k33"]:
            saw_true = True
        else:
            saw_false = True

    # Sanity: with this mix of densities across 300 trials we should have
    # seen both outcomes at least once -- if not, the test isn't actually
    # exercising both branches and should be revisited.
    assert saw_true, "no trial produced a K_3,3-containing matrix -- check densities"
    assert saw_false, "no trial produced a K_3,3-free matrix -- check densities"


# ---------------------------------------------------------------------------
# Test 6: smaller random matrices (8x9) checked against the independent
# brute-force ground truth too, as a second density/shape regime.
# ---------------------------------------------------------------------------

def test_random_8x9_many_trials_agree():
    rng = random.Random(3141592)
    for trial in range(200):
        p = rng.choice([0.2, 0.4, 0.5, 0.7])
        rows = [[1 if rng.random() < p else 0 for _ in range(9)] for _ in range(8)]
        m = np.array(rows, dtype=np.uint8)
        result = checker.verify(m)
        assert result["has_k33"] == _brute_force_ground_truth(rows), (
            f"trial {trial} (p={p}) disagreement"
        )


# ---------------------------------------------------------------------------
# Input handling / normalization tests.
# ---------------------------------------------------------------------------

def test_row_bitmask_input():
    # 3x4 matrix:
    # row0: 1 0 1 1  -> bits (LSB=col0): col0=1,col1=0,col2=1,col3=1 -> 0b1101 = 13
    # row1: 0 1 1 0  -> 0b0110 = 6
    # row2: 1 1 0 0  -> 0b0011 = 3
    rows_listlist = [
        [1, 0, 1, 1],
        [0, 1, 1, 0],
        [1, 1, 0, 0],
    ]
    bitmasks = [13, 6, 3]

    result_list = checker.verify(rows_listlist)
    result_bits = checker.verify(bitmasks, n_cols=4)

    assert result_list["edges"] == result_bits["edges"]
    assert result_list["has_k33"] == result_bits["has_k33"]
    # Row sums by hand: row0=3 ones, row1=2 ones, row2=2 ones -> 7 total.
    assert result_bits["edges"] == 7


def test_bitmask_without_n_cols_raises():
    try:
        checker.verify([13, 6, 3])
        assert False, "expected ValueError without n_cols"
    except ValueError:
        pass


def test_non_binary_entries_raise():
    m = np.array([[0, 1, 2], [1, 0, 1], [1, 1, 0]])
    try:
        checker.verify(m)
        assert False, "expected ValueError for non-0/1 entries"
    except ValueError:
        pass


def test_convenience_wrappers():
    m = np.ones((3, 3), dtype=np.uint8)
    assert checker.is_k33_free(m) is False
    assert checker.edge_count(m) == 9

    m2 = np.zeros((3, 3), dtype=np.uint8)
    assert checker.is_k33_free(m2) is True
    assert checker.edge_count(m2) == 0


# ---------------------------------------------------------------------------
# check_against_known_exact_value: basic behavior (real literature witness
# cross-checks live in test_known_witnesses.py, not here).
# ---------------------------------------------------------------------------

def test_known_exact_value_accepts_matching_matrix():
    m = np.ones((3, 3), dtype=np.uint8)
    m[0, 0] = 0  # 8 edges, K_3,3-free (see test_k33_minus_one_edge_is_free)
    result = checker.check_against_known_exact_value(m, published_value=8)
    assert result["edges"] == 8
    assert result["is_k33_free"] is True


def test_known_exact_value_rejects_wrong_edge_count():
    m = np.ones((3, 3), dtype=np.uint8)
    m[0, 0] = 0  # 8 edges
    try:
        checker.check_against_known_exact_value(m, published_value=9)
        assert False, "expected ValueError for edge-count mismatch"
    except ValueError:
        pass


def test_known_exact_value_rejects_matrix_containing_k33():
    m = np.ones((3, 3), dtype=np.uint8)  # 9 edges, but IS K_3,3
    try:
        checker.check_against_known_exact_value(m, published_value=9)
        assert False, "expected CheckerDisagreement -- matrix contains K_3,3"
    except checker.CheckerDisagreement:
        pass


# ---------------------------------------------------------------------------
# Standalone runner (no pytest dependency required).
# ---------------------------------------------------------------------------

def _all_test_functions():
    mod = sys.modules[__name__]
    return [
        getattr(mod, name)
        for name in sorted(dir(mod))
        if name.startswith("test_") and callable(getattr(mod, name))
    ]


if __name__ == "__main__":
    tests = _all_test_functions()
    failures = []
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except Exception as e:  # noqa: BLE001
            failures.append((fn.__name__, e))
            print(f"FAIL  {fn.__name__}: {e!r}")

    print(f"\n{len(tests) - len(failures)}/{len(tests)} tests passed")
    if failures:
        sys.exit(1)
