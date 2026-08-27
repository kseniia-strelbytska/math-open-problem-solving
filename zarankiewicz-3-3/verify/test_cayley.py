"""Tests for verify/cayley.py — the `K_{s,s}`-freeness criterion.

The theorem's proof is three lines. That is exactly the regime where an
off-by-one hides: "distinct non-identity" versus "non-identity", `<= s-1`
versus `< s-1`, or left- versus right-translation in a non-abelian group. So
the criterion is checked **by exhaustion against direct detection**, not
argued about.
"""

from __future__ import annotations

import csv
import itertools
from math import comb
from pathlib import Path

import pytest

import cayley as cy
from checker import verify


GROUPS = [
    ("Z_6", *cy.cyclic(6)),
    ("Z_7", *cy.cyclic(7)),
    ("Z_8", *cy.cyclic(8)),
    ("Z_9", *cy.cyclic(9)),
    ("Z_2xZ_4", *cy.product_cyclic(2, 4)),
    ("Z_3xZ_3", *cy.product_cyclic(3, 3)),
    ("S_3", *cy.symmetric_3()),
]


@pytest.mark.parametrize("name,n,mul", GROUPS, ids=[g[0] for g in GROUPS])
@pytest.mark.parametrize("s", [2, 3, 4])
def test_criterion_matches_direct_detection_exhaustively(name, n, mul, s):
    """THE theorem, over every subset of the group, for s = 2, 3, 4.

    `has_kss_direct` is the definition of `K_{s,s}` restated and shares no
    code with `criterion_holds`. Any disagreement falsifies the theorem.
    """
    if s > n:
        pytest.skip(f"s={s} exceeds |{name}|={n}")
    checked = 0
    for size in range(1, n + 1):
        for S in itertools.combinations(range(n), size):
            direct_free = not cy.has_kss_direct(cy.rows(n, mul, S), s)
            crit = cy.criterion_holds(n, mul, S, s)
            assert direct_free == crit, (
                f"{name}, s={s}, S={S}: direct says free={direct_free}, "
                f"criterion says {crit}"
            )
            checked += 1
    assert checked == 2 ** n - 1


def test_the_non_abelian_case_is_actually_exercised():
    """S_3 must really be non-abelian, else the parametrised sweep is weaker
    than it looks.

    The proof uses left translation and never commutativity. If the group
    encoded as S_3 were secretly abelian, the sweep would silently test only
    the abelian case.
    """
    n, mul = cy.symmetric_3()
    assert any(mul(g, h) != mul(h, g) for g in range(n) for h in range(n)), \
        "the 'non-abelian' group is abelian"
    # and it is a group: identity 0, closure, associativity, inverses
    for g in range(n):
        assert mul(0, g) == g and mul(g, 0) == g
        assert any(mul(g, h) == 0 for h in range(n)), f"{g} has no inverse"
    for g, h, k in itertools.product(range(n), repeat=3):
        assert mul(mul(g, h), k) == mul(g, mul(h, k))


@pytest.mark.parametrize("name,n,mul", GROUPS, ids=[g[0] for g in GROUPS])
def test_s2_specialisation_is_exactly_the_sidon_condition(name, n, mul):
    """At s=2 the theorem must reduce to Collins et al.'s Proposition 5.

    This is the normalisation check on the general statement: if the
    quantifiers or the bound were off by one, the s=2 case would stop
    agreeing with an independent Sidon test.
    """
    for size in range(1, n + 1):
        for S in itertools.combinations(range(n), size):
            assert cy.criterion_holds(n, mul, S, 2) == cy.is_sidon(n, mul, S), \
                f"{name}: s=2 criterion disagrees with Sidon on S={S}"


def test_criterion_rejects_s_below_2():
    n, mul = cy.cyclic(7)
    with pytest.raises(ValueError):
        cy.criterion_holds(n, mul, (0, 1), 1)


def test_construction_is_biregular():
    """row and column degrees both equal |S| -- the column half is the one
    that is easy to assume without checking."""
    for name, n, mul in GROUPS:
        for d in (2, 3):
            S = tuple(range(d))
            M = cy.matrix(n, mul, S)
            assert all(sum(r) == d for r in M)
            col = [sum(M[r][c] for r in range(n)) for c in range(n)]
            assert col == [d] * n, f"{name} not column-regular"


# --- the numbers quoted in CAYLEY.md -----------------------------------

DOCUMENTED = {  # n -> (best degree, edges)
    14: (7, 98), 15: (8, 120), 16: (8, 128),
    17: (8, 136), 18: (8, 144), 19: (8, 152), 20: (9, 180),
}


@pytest.mark.parametrize("n", sorted(DOCUMENTED))
def test_documented_lower_bounds_are_achieved_and_verified(n):
    """Each table row in CAYLEY.md: the degree is achievable, and the
    resulting matrix passes the independent three-detector checker."""
    d, edges = DOCUMENTED[n]
    assert d * n == edges
    found = None
    cands = [cy.cyclic(n)]
    for a in range(2, n):
        if n % a == 0 and a <= n // a:
            cands.append(cy.product_cyclic(a, n // a))
    for m, mul in cands:
        S = next(cy.search(m, mul, d, 3), None)
        if S is not None:
            found = (m, mul, S)
            break
    assert found, f"no K33-free X(G,S) of degree {d} at n={n}"
    m, mul, S = found
    res = verify(cy.matrix(m, mul, S), expected_edges=edges)
    assert res["is_k33_free"] and res["shape"] == (n, n)


@pytest.mark.parametrize("n", sorted(DOCUMENTED))
def test_documented_degree_is_maximal_for_the_groups_searched(n):
    """No larger degree works, over the groups this module searches.

    Scoped exactly: this is maximality within the searched family, NOT a
    claim about all K33-free graphs, and not even about all groups of order n
    (only cyclic and Z_a x Z_b are enumerated here).
    """
    d, _ = DOCUMENTED[n]
    cap = cy.counting_cap(n, 3)
    cands = [cy.cyclic(n)]
    for a in range(2, n):
        if n % a == 0 and a <= n // a:
            cands.append(cy.product_cyclic(a, n // a))
    for bigger in range(d + 1, cap + 1):
        for m, mul in cands:
            assert next(cy.search(m, mul, bigger, 3), None) is None, (
                f"n={n}: degree {bigger} IS achievable -- CAYLEY.md understates "
                f"the bound and must be updated"
            )


def test_counting_cap_and_where_the_construction_attains_it():
    """The self-contained sharpness claim.

    n*C(d,3) <= 2*C(n,3) caps the degree of any d-regular K33-free n x n
    graph. At n=17 that forces d <= 8 and at n=20 it forces d <= 9, and the
    construction attains both -- so no d-regular K33-free graph beats it
    there, with no citation involved.
    """
    assert cy.counting_cap(17, 3) == 8
    assert cy.counting_cap(20, 3) == 9
    # the arithmetic behind those two, spelled out
    assert 17 * comb(9, 3) > 2 * comb(17, 3)   # 9-regular impossible at n=17
    assert 17 * comb(8, 3) <= 2 * comb(17, 3)
    assert 20 * comb(10, 3) > 2 * comb(20, 3)  # 10-regular impossible at n=20
    assert 20 * comb(9, 3) <= 2 * comb(20, 3)
    attained = {n for n in range(8, 21)
                if DOCUMENTED.get(n, (0,))[0] == cy.counting_cap(n, 3)}
    assert {17, 20} <= attained


def test_novelty_caveats_are_stated_not_buried():
    """CAYLEY.md must keep the caveats that make the claim honest.

    Specifically: that n=15,16 only MATCH closed exact values, that n=14
    FALLS SHORT, and that the known optima at n=13,14,16 are irregular and
    beat the circulant baseline. Dropping any of those would turn an honest
    table into an overclaim.
    """
    doc = (Path(__file__).resolve().parent.parent / "CAYLEY.md").read_text()
    for phrase in ("falls 7 short", "closed at 128", "closed at 120",
                   "irregular", "quadratic-residue"):
        assert phrase in doc, f"CAYLEY.md no longer states: {phrase!r}"
