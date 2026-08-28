"""Tests for verify/constructions.py.

The module makes one load-bearing claim — `z(16,16;3) >= 128` by explicit
construction — which discharges a previously-conditional theorem. So the tests
attack the two ways that claim could be wrong: the graph might not be what is
claimed, or the group action might not be a group action.
"""

from __future__ import annotations

import csv
import itertools
from pathlib import Path

import pytest

from checker import verify
import constructions as ct

WITNESS = Path(__file__).resolve().parent.parent / "data" / "our_witnesses" / "z16_16_128.csv"


# --- the group actions really are actions -------------------------------

@pytest.mark.parametrize("name", sorted(ct.GROUPS_16))
def test_action_is_a_group_action(name):
    """Closure, identity, and bijectivity of each translation map.

    If `act` were not a genuine action, "translates of S" would not be a
    well-defined orbit and the regularity argument in the docstring would be
    unfounded — the construction could silently produce a non-regular graph
    that happens to pass the K33 test, and the reasoning would be wrong even
    where the object is fine.
    """
    n, act = ct.GROUPS_16[name]
    # identity element is 0 in all three encodings
    for g in range(n):
        assert act(g, 0) == g, f"{name}: 0 is not the identity"
        assert act(0, g) == g
    # each translation is a bijection of the column set
    for s in range(n):
        images = {act(g, s) for g in range(n)}
        assert images == set(range(n)), f"{name}: translation by {s} is not a bijection"
    # associativity of the action, via the induced binary operation
    for g, s, t in itertools.product(range(n), repeat=3):
        assert act(act(g, s), t) == act(g, act(s, t)), f"{name}: not associative"


@pytest.mark.parametrize("name", sorted(ct.GROUPS_16))
def test_translate_construction_is_biregular(name):
    """Row AND column degrees must both equal |S|.

    Column-regularity is the half that is easy to assume and not check: it
    holds because column `c` lies in `row_g` exactly when `g` is in the
    preimage of `c` under translation by some element of S. Asserted rather
    than argued.
    """
    n, act = ct.GROUPS_16[name]
    for degree in (3, 5, 8):
        S = tuple(range(degree))
        rows = ct.translate_rows(n, S, act)
        assert all(r.bit_count() == degree for r in rows), "row degree wrong"
        matrix = ct.rows_to_matrix(rows, n)
        col_deg = [sum(matrix[r][c] for r in range(n)) for c in range(n)]
        assert col_deg == [degree] * n, f"{name}: not column-regular"


# --- the K33 test in this module agrees with the checker ----------------

def test_module_k33_test_agrees_with_checker_on_random_graphs():
    """`is_k33_free` here is written from the definition; cross-check it.

    The module deliberately does not import the checker, so that a
    construction and its verification do not share an implementation. This
    test is where the two are compared.
    """
    import random
    rng = random.Random(20260827)
    n = 16
    for _ in range(60):
        rows = [rng.getrandbits(n) for _ in range(8)]
        mine = ct.is_k33_free(rows)
        theirs = not verify(ct.rows_to_matrix(rows, n))["has_k33"]
        assert mine == theirs


def test_module_k33_test_agrees_with_checker_exhaustively_on_small_cases():
    """All 2^12 three-row, four-column graphs."""
    for bits in range(1 << 12):
        rows = [(bits >> (4 * r)) & 0xF for r in range(3)]
        mine = ct.is_k33_free(rows)
        theirs = not verify(ct.rows_to_matrix(rows, 4))["has_k33"]
        assert mine == theirs, (bits, rows)


# --- the survey result --------------------------------------------------

def test_survey_reproduces_the_documented_counts():
    """0 / 0 / 96 for Z_16, (Z_2)^4, Z_4xZ_4 at degree 8.

    The two zeros matter as much as the 96: they are what makes the choice of
    group a real finding rather than an arbitrary one. A bug that made the K33
    test permissive would turn the zeros positive.
    """
    survey = ct.survey_16x16(8)
    assert len(survey["Z_16"]) == 0
    assert len(survey["(Z_2)^4"]) == 0
    assert len(survey["Z_4 x Z_4"]) == 96


def test_every_z4xz4_solution_is_a_verified_128_edge_k33_free_graph():
    """All 96, through the independent checker -- not just the one we saved."""
    n, act = ct.GROUPS_16["Z_4 x Z_4"]
    sols = list(ct.search_translates(n, 8, act))
    assert len(sols) == 96
    for S in sols:
        rows = ct.translate_rows(n, S, act)
        res = verify(ct.rows_to_matrix(rows, n), expected_edges=128)
        assert res["is_k33_free"]
        assert res["shape"] == (16, 16)


def test_z16_admits_degree_7_but_not_degree_8():
    """The Z_16 failure is about density, not a broken family."""
    _, act = ct.GROUPS_16["Z_16"]
    assert next(ct.search_translates(16, 8, act), None) is None
    assert next(ct.search_translates(16, 7, act), None) is not None


# --- the landed witness ------------------------------------------------

def test_saved_witness_matches_the_construction():
    """The CSV on disk is one of the 96, not something else."""
    with open(WITNESS, newline="") as fh:
        matrix = [[int(x) for x in row] for row in csv.reader(fh) if row]
    res = verify(matrix, expected_edges=128)
    assert res["is_k33_free"]
    assert res["shape"] == (16, 16)
    rows = [sum(1 << c for c in range(16) if matrix[r][c]) for r in range(16)]
    n, act = ct.GROUPS_16["Z_4 x Z_4"]
    produced = {tuple(sorted(ct.translate_rows(n, S, act)))
                for S in ct.search_translates(n, 8, act)}
    assert tuple(sorted(rows)) in produced, (
        "the saved witness is not one of the Z_4 x Z_4 translate solutions"
    )


def test_witness_discharges_theorem_b_hypothesis():
    """128 >= 127, which is the whole point.

    Theorem B in CHAIN_CEILING.md needs z(16,16;3) >= 127 to rule out the
    column-deletion route to 133. This asserts the discharge explicitly so
    that if the witness ever regressed, the theorem's status would fail loudly
    rather than silently becoming conditional again.
    """
    with open(WITNESS, newline="") as fh:
        matrix = [[int(x) for x in row] for row in csv.reader(fh) if row]
    edges = verify(matrix, expected_edges=128)["edges"]
    REQUIRED_BY_THEOREM_B = 127
    assert edges >= REQUIRED_BY_THEOREM_B


def test_upper_bound_is_not_claimed():
    """Guard against overclaiming: this establishes only the LOWER bound.

    z(16,16;3) <= 128 is NOT established by a construction, and the exact
    value therefore still needs a refutation at 129. If a future edit starts
    asserting the exact value on the strength of this module, this test fails.
    """
    src = (Path(__file__).resolve().parent / "constructions.py").read_text()
    for bad in ("z(16,16;3) = 128", "z(16,16;3)=128"):
        idx = src.find(bad)
        while idx != -1:
            window = src[max(0, idx - 300):idx + 300]
            assert any(h in window for h in
                       ("does not establish", "still rests on a citation",
                        "suggests", "never sourced", "= 128 = 8 * 16")), (
                f"constructions.py asserts {bad!r} as established; only the "
                "lower bound is"
            )
            idx = src.find(bad, idx + 1)
