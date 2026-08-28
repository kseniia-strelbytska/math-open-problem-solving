"""Algebraic constructions of dense `K_{3,3}`-free bipartite graphs.

## Why this module exists

The chain-ceiling result in `CHAIN_CEILING.md` had a column-deletion half
(Theorem B) that was **conditional** on `z(16,16;3) >= 127`. This project
could not establish it: the best `16x16` lower bound obtainable by deleting a
column from the verified 132-edge `16x17` witness is exactly **126** — one
edge short of what the theorem needs — and greedy edge augmentation with 60
randomised restarts on each of the 17 possible column deletions (1,020 runs)
saturated at 126 every time.

Searching harder was the wrong response. `z(16,16;3) = 128 = 8 * 16` suggests
an **8-regular** extremal graph, and regular structures of that kind usually
come from a group. So instead of searching the space, this module searches a
*family*: graphs whose rows are the translates of a single subset under a
group acting on the columns.

That turned a failed search into a one-line construction.

## The construction

Index both rows and columns by a group `G` of order `n`. Fix a subset
`S ⊆ G` of size `d`. Define

    row_g  =  { g + s  :  s in S }        (the translate of S by g)

This is `d`-regular in rows and, since every column `c` lies in `row_g`
exactly when `g in c - S`, also `d`-regular in columns. The whole graph is
determined by `S`, so the search space is `C(n, d)` rather than `2^(n*n)`.

**Result for `(16,16)` at `d = 8`:**

| group | 8-regular `K_{3,3}`-free translates found |
|---|---|
| `Z_16` (circulant) | **0** |
| `(Z_2)^4` (XOR translates) | **0** |
| **`Z_4 x Z_4`** | **96** |

So the group matters decisively, and the two obvious choices both fail. All
96 solutions are re-verified by `verify/checker.py` (three independent
`K_{3,3}` detectors, which must agree or the run raises).

`Z_16` does admit 7-regular solutions (112 edges) — the failure at `d = 8` is
specific to the density, not a defect in the family.

## What this establishes, and what it does not

**Establishes:** `z(16,16;3) >= 128`, by explicit construction, verified here,
with no citation anywhere in the derivation.

**Consequence:** Theorem B's hypothesis `z(16,16;3) >= 127` is **discharged**,
so both Theorem B and the corollary about the 2016 paper's `z_bound` algorithm
become **unconditional**.

**Does not establish:** `z(16,16;3) <= 128`. The exact value therefore still
rests on a citation, and `-n 16 -m 16 --decide 129` is running to close that
half. Until it returns, this module supports only the lower bound, and
`CHAIN_CEILING.md` says so.

**Also worth being precise about:** the published value for this cell was
never sourced in this project — it is the same `z(16,16;3) = 128` that
`CHAIN_CEILING.md` previously carried as `UNVERIFIED_ASSUMED_16_16` after a
reviewer pointed out it had no citation. This construction does not "confirm
the literature"; it independently establishes the lower bound, and the
literature's own status for that cell remains unread here.
"""

from __future__ import annotations

import itertools
from typing import Callable, Iterator

# --- group actions on {0, ..., n-1} -------------------------------------

def cyclic(n: int) -> Callable[[int, int], int]:
    """Z_n: translation is addition mod n."""
    return lambda g, s: (g + s) % n


def elementary_abelian_2(n: int) -> Callable[[int, int], int]:
    """(Z_2)^k for n = 2^k: translation is XOR."""
    if n & (n - 1):
        raise ValueError(f"n={n} is not a power of two")
    return lambda g, s: g ^ s


def product_cyclic(a: int, b: int) -> Callable[[int, int], int]:
    """Z_a x Z_b, elements encoded as `i*b + j` for i in Z_a, j in Z_b."""
    def act(g: int, s: int) -> int:
        g1, g2 = divmod(g, b)
        s1, s2 = divmod(s, b)
        return ((g1 + s1) % a) * b + (g2 + s2) % b
    return act


GROUPS_16 = {
    "Z_16": (16, cyclic(16)),
    "(Z_2)^4": (16, elementary_abelian_2(16)),
    "Z_4 x Z_4": (16, product_cyclic(4, 4)),
}


# --- the construction and its test --------------------------------------

def translate_rows(n: int, subset: tuple[int, ...],
                   act: Callable[[int, int], int]) -> list[int]:
    """Row bitmasks for the translate construction: row_g = act(g, S)."""
    return [sum(1 << act(g, s) for s in subset) for g in range(n)]


def is_k33_free(rows: list[int]) -> bool:
    """No three rows share three columns.

    This is the definition, not a shortcut: a `K_{3,3}` is exactly three rows
    and three columns with all nine pairs present, i.e. three rows whose
    neighbourhood intersection has size >= 3. Written here from the definition
    rather than importing the checker, so that a construction and its
    verification do not share an implementation; `checker.py` is then applied
    as an independent second opinion by the tests.
    """
    m = len(rows)
    for a, b, c in itertools.combinations(range(m), 3):
        if (rows[a] & rows[b] & rows[c]).bit_count() >= 3:
            return False
    return True


def search_translates(n: int, degree: int,
                      act: Callable[[int, int], int]) -> Iterator[tuple[int, ...]]:
    """Yield every subset S of size `degree` whose translates are K33-free."""
    for subset in itertools.combinations(range(n), degree):
        if is_k33_free(translate_rows(n, subset, act)):
            yield subset


def rows_to_matrix(rows: list[int], n: int) -> list[list[int]]:
    return [[(r >> c) & 1 for c in range(n)] for r in rows]


def survey_16x16(degree: int = 8) -> dict[str, list[tuple[int, ...]]]:
    """The headline survey: which groups of order 16 admit a d-regular solution."""
    out: dict[str, list[tuple[int, ...]]] = {}
    for name, (n, act) in GROUPS_16.items():
        out[name] = list(search_translates(n, degree, act))
    return out


def main() -> None:
    print("Translate constructions for 16x16, degree 8 (=> 128 edges)\n")
    survey = survey_16x16(8)
    for name, sols in survey.items():
        print(f"  {name:12s}: {len(sols):4d} K33-free 8-regular translates")
    winner = max(survey, key=lambda k: len(survey[k]))
    if survey[winner]:
        S = survey[winner][0]
        n, act = GROUPS_16[winner]
        rows = translate_rows(n, S, act)
        edges = sum(r.bit_count() for r in rows)
        print(f"\n  {winner}, S = {S}: {edges} edges, "
              f"K33-free = {is_k33_free(rows)}")
        print(f"  => z(16,16;3) >= {edges}")

    print("\nFor contrast, Z_16 at lower degrees:")
    for d in (8, 7, 6):
        first = next(search_translates(16, d, cyclic(16)), None)
        print(f"  degree {d} ({d*16:3d} edges): "
              f"{'e.g. ' + str(first) if first else 'none'}")


if __name__ == "__main__":
    main()
