"""Tests for verify/lower_bounds.py.

The module's whole job is to apply one lemma (row-deletion monotonicity)
without misapplying it. So the tests concentrate on the ways it could be
misapplied -- selecting columns, dropping the induced-subgraph requirement,
or trusting the "k largest degrees" shortcut -- rather than on re-checking
arithmetic the checker already covers.
"""

from __future__ import annotations

import itertools
import random
from pathlib import Path

import pytest

from checker import verify
import lower_bounds as lb


WITNESS_FILES = sorted(p for p in lb.WITNESS_DIR.glob("*.csv"))


def test_witness_directory_is_not_empty():
    """Guard against the tests below vacuously passing on zero witnesses."""
    assert WITNESS_FILES, f"no witness CSVs found in {lb.WITNESS_DIR}"


@pytest.mark.parametrize("path", WITNESS_FILES, ids=lambda p: p.name)
def test_every_subgraph_bound_is_backed_by_a_checked_subgraph(path):
    """The bounds are real: each one comes with a K33-free matrix of that size."""
    matrix = lb.load_matrix(path)
    if len(matrix[0]) != lb.N_COLS:
        pytest.skip(f"{path.name} has {len(matrix[0])} columns, not {lb.N_COLS}")
    info = lb.bounds_from_witness(path)
    for row in info["bounds"]:
        sub = [matrix[r] for r in row["rows"]]
        res = verify(sub, expected_edges=row["edges"])
        assert res["is_k33_free"]
        assert res["shape"] == (row["k"], lb.N_COLS)


@pytest.mark.parametrize("path", WITNESS_FILES, ids=lambda p: p.name)
def test_brute_force_agrees_with_largest_degrees_shortcut(path):
    """The optimality argument for 'take the k largest degrees' actually holds.

    `best_k_row_subgraph` brute-forces all C(m,k) subsets specifically so it
    does not depend on this argument. This test confirms the argument anyway,
    because if the two ever disagreed it would mean edges are not
    row-additive -- i.e. something is deeply wrong with how matrices are
    being read.
    """
    matrix = lb.load_matrix(path)
    degrees = sorted((sum(r) for r in matrix), reverse=True)
    for k in range(1, len(matrix) + 1):
        brute, _ = lb.best_k_row_subgraph(matrix, k)
        assert brute == sum(degrees[:k])


def test_monotonicity_holds_on_exhaustive_small_cases():
    """Row-deletion monotonicity, verified by exhaustion rather than by proof.

    Over every 4x4 0/1 matrix that is K33-free, every 3-row subgraph must
    also be K33-free. This is the lemma the whole module rests on, checked
    against the checker on 2^16 matrices instead of being taken on faith.
    """
    n = 4
    checked = 0
    for bits in range(1 << (n * n)):
        matrix = [
            [(bits >> (r * n + c)) & 1 for c in range(n)]
            for r in range(n)
        ]
        if verify(matrix)["has_k33"]:
            continue
        checked += 1
        for rows in itertools.combinations(range(n), 3):
            sub = [matrix[r] for r in rows]
            assert not verify(sub)["has_k33"], (
                f"row deletion created a K33: parent={matrix} rows={rows}"
            )
    assert checked > 0


def test_monotonicity_holds_on_random_larger_cases():
    """Same lemma on 12x17-shaped random matrices, where K33s are plentiful."""
    rng = random.Random(20260826)
    for _ in range(40):
        m, n = 12, 17
        matrix = [[1 if rng.random() < 0.35 else 0 for _ in range(n)] for _ in range(m)]
        if verify(matrix)["has_k33"]:
            continue
        for _ in range(5):
            k = rng.randint(3, m - 1)
            rows = rng.sample(range(m), k)
            assert not verify([matrix[r] for r in rows])["has_k33"]


def test_deleting_columns_is_not_what_this_module_does():
    """Selecting rows must leave the column count intact.

    A transposition bug -- selecting columns while believing they are rows --
    would still produce K33-free subgraphs and plausible-looking edge counts,
    so the checker alone would not catch it. What it would change is the
    shape, and hence which z(k,n;3) cell the bound applies to. This pins the
    shape.
    """
    matrix = lb.load_matrix(WITNESS_FILES[0])
    m = len(matrix)
    n = len(matrix[0])
    for k in (1, m // 2, m):
        _, rows = lb.best_k_row_subgraph(matrix, k)
        sub = [matrix[r] for r in rows]
        assert len(sub) == k
        assert all(len(r) == n for r in sub), "column count changed -- transposition bug"


def test_bounds_are_monotone_in_k():
    """z(k,17;3) >= b_k with b_k nondecreasing: adding a row cannot lose edges."""
    for path in WITNESS_FILES:
        matrix = lb.load_matrix(path)
        if len(matrix[0]) != lb.N_COLS:
            continue
        info = lb.bounds_from_witness(path)
        edges = [row["edges"] for row in info["bounds"]]
        assert edges == sorted(edges)


def test_recorded_bounds_match_the_committed_log():
    """The numbers quoted in LOWER_BOUNDS.md are what the code produces.

    This is the anti-drift test: a documented result that no test pins can
    silently become false when the witness set changes.
    """
    expected = {11: 94, 12: 102, 13: 110, 14: 118, 15: 126}
    best = lb.best_known_lower_bounds()
    for k, v in expected.items():
        assert best[k] == v, f"z({k},17;3) lower bound is {best[k]}, log says {v}"


def _density_chain_step(prev_bound: int, m: int) -> int:
    """Largest e with e - floor(e/m) <= prev_bound.

    This is the density lemma (Collins-Riasanovsky-Wallace-Radziszowski 2016,
    Lemma 3) in contrapositive form. Its hypotheses, checked here: the graph
    is K33-free on m rows (so deleting a row leaves a K33-free (m-1)-row
    graph), and the minimum row degree is at most the average floor(e/m)
    because a minimum is at most a mean and degrees are integers.
    """
    best = None
    for e in range(prev_bound, prev_bound + 64):
        if e - e // m <= prev_bound:
            best = e
    if best is None:
        raise AssertionError(f"no e found for prev={prev_bound} m={m}")
    return best


def test_density_chain_table_in_the_log_is_correct():
    """Pins the 'if z(11,17;3) = v then z(16,17;3) <= w' table in LOWER_BOUNDS.md.

    Arithmetic quoted in prose is exactly the kind of thing that rots. The
    table drives a strategic decision (whether the k=11 route can reach 134
    at all), so it is asserted rather than trusted.
    """
    expected = {94: 134, 95: 135, 96: 136, 97: 137}
    for start, target in expected.items():
        v = start
        for m in range(12, 17):
            v = _density_chain_step(v, m)
        assert v == target, f"chain from f(11)={start} gives {v}, log says {target}"


def test_chain_propagation_is_one_to_one_in_this_range():
    """Each edge saved at k=11 is worth exactly one at k=16 -- no cliff here.

    The chain's divisor is 8 throughout k=12..16 for these values, so the
    propagation is 1:1. This is asserted because elsewhere in the project a
    single edge at k=9 was worth *eight* at k=16 (the divisor changed from 9
    to 8), and assuming 1:1 without checking is how that gets missed.
    """
    starts = sorted({94, 95, 96, 97})
    ends = []
    for start in starts:
        v = start
        for m in range(12, 17):
            v = _density_chain_step(v, m)
        ends.append(v)
    diffs = [b - a for a, b in zip(ends, ends[1:])]
    assert diffs == [1, 1, 1], f"propagation is not 1:1: {ends}"


def test_lower_bound_forbids_refutation_at_that_target():
    """The operational claim: --decide 94 at k=11 cannot legitimately be UNSAT.

    A 94-edge K33-free 11x17 graph exists and is checked above, so any
    exhaustive search reporting 'no 94-edge graph' has a bug. Asserting the
    witness exists is the guard.
    """
    best = lb.best_known_lower_bounds()
    assert best[11] >= 94
    # And exhibit the matrix, so the claim is not merely a cached number.
    for path in WITNESS_FILES:
        matrix = lb.load_matrix(path)
        if len(matrix[0]) != lb.N_COLS or len(matrix) < 11:
            continue
        edges, rows = lb.best_k_row_subgraph(matrix, 11)
        if edges >= 94:
            res = verify([matrix[r] for r in rows], expected_edges=edges)
            assert res["is_k33_free"] and res["shape"] == (11, 17)
            return
    pytest.fail("no witness exhibited an 11-row subgraph with >= 94 edges")


def test_lower_bound_is_known_to_be_loose_at_k_11():
    """Records, as a test, that these bounds are NOT tight.

    The comparison value 96 is CITED, not derived here: Collins-Riasanovsky-
    Wallace-Radziszowski arXiv:1604.01257 Table 4, row m=11 column n=17, in
    boldface (their legend: "a boldfaced entry is an exact value"), and
    independently boldface in Tan arXiv:2203.02283 Table 3, row 11 column 17.

    An earlier version of this test asserted the gap at k=10 against the
    value 90, described as "proved by this project". A reviewer correctly
    pointed out that no artifact supporting 90 is reachable from this PR --
    it was proved on a branch this series never carried over -- so the test
    was baking an unverifiable number into an assert. It is replaced with the
    k=11 comparison, whose comparison value at least has a precise citation
    a reader can check.

    Asserted so that if a future witness closes the gap, the suite fails and
    the tightness question is re-opened deliberately rather than absorbed.
    """
    CITED_Z_11_17 = 96
    best = lb.best_known_lower_bounds()
    assert best[11] == 94
    assert best[11] < CITED_Z_11_17, (
        "row deletion now reaches the cited value at k=11 -- re-read the docs "
        "before treating any of these bounds as tight"
    )


def test_no_unlanded_value_is_asserted_as_fact():
    """Guard: this module must not hardcode values it cannot support.

    Specifically 81 and 90 (z(9,17) and z(10,17)), which are proved elsewhere
    in this project but on a branch not present in this PR series. They may
    appear in prose as explicitly-labelled unlanded claims, but must not be
    the subject of an assert -- which is exactly the defect a reviewer found
    in the previous version of this file.
    """
    src = (Path(__file__).parent / "test_lower_bounds.py").read_text()
    body = src.split("def test_no_unlanded_value_is_asserted_as_fact")[0]
    for forbidden in ("== 81", "== 90", "assert best[9] ==", "assert best[10] =="):
        assert forbidden not in body, (
            f"found {forbidden!r} asserted in this file -- that value is not "
            "verifiable from this PR"
        )
