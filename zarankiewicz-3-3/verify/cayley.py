"""`K_{s,s}`-freeness of bipartite Cayley graphs: the criterion, for all `s`.

See `CAYLEY.md` for the statement, the proof, and the literature position.
Summary of why this module exists:

Collins-Riasanovsky-Wallace-Radziszowski (arXiv:1604.01257, section 3) define
the bipartite Cayley graph `X(G,S)` -- rows and columns both indexed by a
group `G`, with `row_g = g*S` -- and prove (Proposition 5) that it is
`K_{2,2}`-free iff `S` is a Sidon set. They then use a `K_{3,3}`-free instance
in an example without giving any criterion for it. A literature survey found
no source stating the `s >= 3` criterion as a theorem; the general shape
appears only as an informal remark in Fueredi-Simonovits' survey
(arXiv:1306.5167, p. 35).

**Theorem.** `X(G,S)` is `K_{s,s}`-free **iff** for every `(s-1)`-tuple
`(a_1, ..., a_{s-1})` of *distinct non-identity* elements of `G`,

    | S ∩ a_1 S ∩ ... ∩ a_{s-1} S |  <=  s - 1 .

*Proof.* The columns adjacent to all of `g_1, ..., g_s` are
`∩_i g_i S`, so a `K_{s,s}` on those rows exists iff that intersection has
size `>= s`. Left translation by `g_1^{-1}` is a bijection of `G`, hence
preserves cardinality, and carries `∩_i g_i S` to
`S ∩ a_1 S ∩ ... ∩ a_{s-1} S` with `a_i = g_1^{-1} g_{i+1}`. The `g_i` are
distinct iff the `a_i` are distinct and non-identity, and every such tuple
arises (take `g_1 = e`, `g_{i+1} = a_i`). []

At `s = 2` the condition reads `|S ∩ aS| <= 1` for all `a != e`, i.e. every
non-identity "difference" has one representation -- so it specialises to
Proposition 5. `test_cayley.py` checks that specialisation against an
independent Sidon test, and checks the theorem itself by exhaustion over all
subsets of several small groups (including a non-abelian one) for
`s = 2, 3, 4`.

**Design-theoretic reading.** The condition says exactly that the development
`dev(S) = {gS : g in G}` is an `s-(n, d, s-1)` **packing**: every `s`-subset
of the `n` points lies in at most `s - 1` blocks. For `s = 3`: every 3-subset
in at most 2 blocks. The surrounding literature (difference families, optical
orthogonal codes, relative difference sets) is essentially all at strength
`t = 2`, which is why the condition has no established name.
"""

from __future__ import annotations

import itertools
from typing import Callable, Iterator

Mul = Callable[[int, int], int]


# --- groups, encoded with identity = 0 ----------------------------------

def cyclic(n: int) -> tuple[int, Mul]:
    """Z_n."""
    return n, (lambda g, h: (g + h) % n)


def product_cyclic(a: int, b: int) -> tuple[int, Mul]:
    """Z_a x Z_b, element `i*b + j` for i in Z_a, j in Z_b."""
    def mul(g: int, h: int) -> int:
        g1, g2 = divmod(g, b)
        h1, h2 = divmod(h, b)
        return ((g1 + h1) % a) * b + (g2 + h2) % b
    return a * b, mul


def symmetric_3() -> tuple[int, Mul]:
    """S_3, a NON-ABELIAN group, so the theorem is not only tested on
    abelian cases -- the proof uses left translation and never commutativity,
    and that distinction is worth exercising."""
    perms = sorted(itertools.permutations(range(3)), key=lambda p: p != (0, 1, 2))
    idx = {p: i for i, p in enumerate(perms)}

    def mul(g: int, h: int) -> int:
        p, q = perms[g], perms[h]
        return idx[tuple(p[q[i]] for i in range(3))]
    return 6, mul


# --- the construction --------------------------------------------------

def rows(n: int, mul: Mul, S: tuple[int, ...]) -> list[int]:
    """Row bitmasks of X(G,S): row_g = g*S."""
    return [sum(1 << mul(g, s) for s in S) for g in range(n)]


def matrix(n: int, mul: Mul, S: tuple[int, ...]) -> list[list[int]]:
    R = rows(n, mul, S)
    return [[(R[g] >> c) & 1 for c in range(n)] for g in range(n)]


# --- the two sides of the theorem, kept deliberately separate ----------

def has_kss_direct(row_masks: list[int], s: int) -> bool:
    """Direct detection: are there `s` rows sharing `s` columns?

    This is the definition of `K_{s,s}` restated, and it is what the
    criterion is validated *against*. It must not use the criterion.
    """
    for rs in itertools.combinations(range(len(row_masks)), s):
        m = row_masks[rs[0]]
        for r in rs[1:]:
            m &= row_masks[r]
        if m.bit_count() >= s:
            return True
    return False


def criterion_holds(n: int, mul: Mul, S: tuple[int, ...], s: int) -> bool:
    """The theorem's condition, evaluated directly on `S`.

    Cost is `C(n-1, s-1)` intersections rather than the
    `C(n, s) * C(n, s)`-ish cost of scanning the whole matrix -- which is the
    practical point of the criterion, beyond its being a clean statement.
    """
    if s < 2:
        raise ValueError(f"s must be >= 2, got {s}")
    S_mask = sum(1 << x for x in S)
    translates = {a: sum(1 << mul(a, x) for x in S) for a in range(n)}
    for tup in itertools.combinations(range(1, n), s - 1):
        m = S_mask
        for a in tup:
            m &= translates[a]
        if m.bit_count() >= s:
            return False
    return True


def is_sidon(n: int, mul: Mul, S: tuple[int, ...]) -> bool:
    """Independent Sidon test, for checking the s=2 specialisation.

    `S` is Sidon iff every non-identity `a` has at most one pair
    `(x, y)` in `S x S` with `x = a*y`.
    """
    seen: set[int] = set()
    for x, y in itertools.permutations(S, 2):
        for a in range(1, n):
            if mul(a, y) == x:
                if a in seen:
                    return False
                seen.add(a)
                break
    return True


# --- searching for dense examples --------------------------------------

def search(n: int, mul: Mul, d: int, s: int = 3) -> Iterator[tuple[int, ...]]:
    """Every `S` of size `d` containing the identity with `X(G,S)` K_{s,s}-free.

    Restricting to `e in S` loses nothing: replacing `S` by `Sa^{-1}` gives an
    isomorphic graph (it permutes the columns), so every orbit has a
    representative containing the identity.
    """
    for rest in itertools.combinations(range(1, n), d - 1):
        S = (0,) + rest
        if criterion_holds(n, mul, S, s):
            yield S


def max_degree(n: int, mul: Mul, s: int = 3, cap: int | None = None
               ) -> tuple[int, tuple[int, ...] | None]:
    """Largest `d` admitting a K_{s,s}-free X(G,S), with a witness."""
    hi = cap if cap is not None else n
    for d in range(hi, 0, -1):
        S = next(search(n, mul, d, s), None)
        if S is not None:
            return d, S
    return 0, None


def counting_cap(n: int, s: int = 3) -> int:
    """Largest `d` a `d`-regular K_{s,s}-free n x n graph can have.

    From counting (row, column-`s`-subset) incidences: every `s`-subset of
    columns lies in at most `s-1` rows, so `n * C(d,s) <= (s-1) * C(n,s)`.
    """
    from math import comb
    best = 0
    for d in range(s, n + 1):
        if n * comb(d, s) <= (s - 1) * comb(n, s):
            best = d
    return best


def main() -> None:
    from math import comb
    print("Bipartite Cayley graphs X(G,S): max degree with K_{3,3}-freeness\n")
    print(f"{'n':>3} {'best d':>7} {'edges':>6} {'group':>12} {'reg. cap':>9} {'sharp?':>7}")
    for n in range(8, 21):
        cands = [(f"Z_{n}", *cyclic(n))]
        for a in range(2, n):
            if n % a == 0 and a <= n // a:
                cands.append((f"Z_{a}xZ_{n//a}", *product_cyclic(a, n // a)))
        cap = counting_cap(n, 3)
        bd, bname, bS = 0, "", None
        for name, m, mul in cands:
            d, S = max_degree(m, mul, 3, cap=cap)
            if d > bd:
                bd, bname, bS = d, name, S
        print(f"{n:>3} {bd:>7} {bd*n:>6} {bname:>12} {cap:>9} "
              f"{'YES' if bd == cap else '':>7}")


if __name__ == "__main__":
    main()
