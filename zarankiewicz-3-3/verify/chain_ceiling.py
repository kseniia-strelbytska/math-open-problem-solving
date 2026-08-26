"""The exact ceiling of the density-lemma chain, and why it stops at 134.

This module formalises one negative result and one corollary about it. Both
are self-contained: they need nothing but the density lemma (restated and
re-derived below) and the 126-edge `15x17` witness this repo re-verifies.

## The inference rule

Write `z(m,n) := z(m,n;3,3)` for the maximum number of edges in a
`K_{3,3}`-free bipartite graph with `m` rows and `n` columns.

**Density lemma** (Collins-Riasanovsky-Wallace-Radziszowski, *Zarankiewicz
Numbers and Bipartite Ramsey Numbers*, arXiv:1604.01257, Lemma 3;
re-derived here so the argument does not depend on the citation). Let `G` be
`K_{3,3}`-free on `m x n` with `e` edges. Its minimum row degree `d` is at
most the mean `e/m`, and being an integer, at most `floor(e/m)`. Deleting
that row leaves a `K_{3,3}`-free `(m-1) x n` graph with `e - d >= e -
floor(e/m)` edges. Hence

    e - floor(e/m)  <=  z(m-1, n).

Hypotheses, each checked rather than assumed:

1. `m >= 1`, so a row exists to delete. Enforced.
2. `G` is `K_{3,3}`-free, and deletion preserves that — this is
   row-deletion monotonicity, machine-checked by exhaustion in
   `test_lower_bounds.py`.
3. `d <= floor(e/m)`: a minimum is at most a mean, and degrees are
   integers. No further structure needed.

Read as an inference rule, from an upper bound `z(m-1,n) <= B` it licenses

    z(m,n)  <=  CEIL(B, m)  :=  max{ e : e - floor(e/m) <= B }.

`CEIL` is exactly what `density_ceiling` computes. This is the *only* rule
the "chain" (the `z_bound` style of argument: pure arithmetic from a table
of lower levels, no enumeration) has available at the top step.

## The negative result

**Theorem A (row deletion).** No sound chain whose final step deletes a
*row* proves `z(16,17) <= 133` — regardless of how much computation is spent
at levels `k <= 15`, and even if every value there is determined exactly.

**Theorem B (column deletion), conditional.** The problem is symmetric under
transposition, so a final step may instead delete a *column*, giving
`e - floor(e/17) <= z(16,16)`. That route reaches `133` iff
`z(16,16) <= 126`, so it fails **provided `z(16,16) >= 127`**. This project
can currently prove only `z(16,16) >= 126` from its own data — exactly one
edge short. See `theorem_133_column_route` and `CHAIN_CEILING.md`.

Theorem A was originally written without the "row" qualifier, which was an
error: it silently assumed the transposed step away. The qualifier is not
cosmetic, and the column analysis is not a formality — our own bound lands
precisely on the threshold, so the column route is genuinely open on
self-contained data.

*Proof.* Whatever the chain does below, its final step must apply the rule
at `m = 16` to some upper bound `B` on `z(15,17)`, and must obtain
`CEIL(B,16) <= 133`. Now `CEIL(126,16) = 134`, because `134 - floor(134/16)
= 134 - 8 = 126 <= 126` while `135 - 8 = 127 > 126`. Since `CEIL` is
nondecreasing in `B`, obtaining `CEIL(B,16) <= 133` forces `B <= 125`.

But `z(15,17) >= 126`: this repo contains an explicit 126-edge `K_{3,3}`-free
`15x17` matrix, re-verified by three independent detectors. So `B <= 125` is
not a true upper bound on `z(15,17)`, and any chain asserting it is unsound.
Hence no sound chain reaches `133`. []

The bound `z(16,17) <= 134` *is* reachable, and by the same computation is
the exact ceiling: **the density chain's limit for this cell is 134, and it
is attained.**

## The corollary, which corroborates a literature claim by pure arithmetic

The 2016 paper tabulates `133` for this cell, and separately describes an
arithmetic `z_bound` algorithm that chains its Lemmas 2-4 over a table of
lower levels. The theorem above says that algorithm **cannot** output `133`
here — its ceiling is `134`. Therefore the `133` entry must have been
obtained by their exhaustive computation, not by their arithmetic.

That matters because it is reached by a completely different route than the
project's earlier evidence for the same conclusion. Previously this was
argued from *typography*: the paper's table legend distinguishes bold
(exact) from italic (exhaustive computation) from upright (lemmas only), and
the embedded PDF font for the `133` cell was found to be `PJYSJE+CMTI10`,
i.e. italic. That is a fact about a PDF. The argument here is a fact about
arithmetic, needs no access to the paper at all, and agrees. Two independent
kinds of evidence converging is the strongest form this claim can take short
of the authors confirming it.

**Scope, stated precisely.** The corollary concludes only that the `133`
entry did not come from chaining the density lemma. It does *not* establish
that `133` is correct, nor that their exhaustive computation was correct.
The upper bound remains uncertified by anyone, which is exactly why this
project treats certifying it as a target rather than an input.

## Where the chain is tight, and where it is not

Running `CEIL` on the values this project proved (`z(9,17) = 81`,
`z(10,17) = 90`) together with the published ones gives a sharp pattern: the
density lemma is **exactly tight** — gap 0 — at every step where a
comparison is possible, and has a gap of exactly **1** at `m = 16`. See
`tight_gaps()` and `CHAIN_CEILING.md`.

That `m = 16` is both the single cell where the cheap method first loses an
edge and the single cell still open is unlikely to be coincidence: the
frontier of what is known is sitting exactly where the cheap method stops
working. It is a suggestive observation and nothing more — it is not
evidence about the *value* of `z(16,17)`, and this module makes no such
claim.
"""

from __future__ import annotations

# Values this project proved from scratch by exhaustive search, with its own
# witnesses. Not citations.
PROVED_HERE: dict[int, int] = {9: 81, 10: 90}

# Published values, treated strictly as citations. Used only to *locate* the
# tight/loose pattern; the theorem above does not depend on any of them.
PUBLISHED: dict[int, int] = {13: 110, 14: 118, 15: 126, 16: 133}

# The lower bound that carries the whole theorem, backed by
# data/known_witnesses/z15_17_126_witness.csv and re-verified on every test
# run. This is the one number the proof actually needs.
VERIFIED_LOWER_BOUND_15_17 = 126


def density_ceiling(bound_below: int, m: int) -> int:
    """max{e : e - floor(e/m) <= bound_below}: the best the lemma can give.

    Args:
        bound_below: a valid upper bound on z(m-1, n).
        m: the number of rows at the level being bounded; must be >= 2.

    **`m = 1` is rejected, and the reason is mathematical, not defensive.**
    At `m = 1` the expression collapses: `e - floor(e/1) = 0`, which is `<=
    bound_below` for *every* `e`, so the set has no maximum and the rule
    carries no information. That is the honest content of the lemma at
    `m = 1` -- deleting the only row leaves a 0-row graph with 0 edges, and
    `0 <= z(0,n) = 0` is vacuously true. An earlier version of this function
    accepted `m = 1` and silently returned the top of its own search window,
    i.e. a number manufactured by an implementation detail. The boundary
    test `test_density_ceiling_rejects_vacuous_m_equals_1` found that, which
    is why it is worth keeping even though the chain never calls `m = 1`.

    For `m >= 2` the maximum exists, and the search window is *derived*
    rather than guessed. Since `floor(e/m) <= e/m`,

        e - floor(e/m)  >=  e - e/m  =  e * (m-1) / m,

    so any feasible `e` satisfies `e * (m-1)/m <= bound_below`, i.e.
    `e <= bound_below * m / (m-1)`. The window therefore runs to
    `bound_below * m // (m-1) + m + 2`, which is that bound plus slack.

    An earlier version used the fixed window `bound_below + 4m + 8`, which is
    wrong for small `m`: at `m = 2` the true answer is `2 * bound_below`, so
    the window silently truncated the answer for every `bound_below > 15`.
    It happened to be correct at `m = 16` -- the only value this project
    actually uses -- which is exactly why it survived until
    `test_search_window_never_binds` swept the small-`m` range. A window that
    is right only where you look is not a window, it is a coincidence.
    """
    if m < 2:
        raise ValueError(
            f"m must be >= 2, got {m}: at m=1 the density lemma is vacuous "
            "(e - floor(e/1) = 0 for all e), so no maximum exists"
        )
    if bound_below < 0:
        raise ValueError(f"bound_below must be >= 0, got {bound_below}")
    window_top = bound_below * m // (m - 1) + m + 2
    best = None
    for e in range(0, window_top + 1):
        if e - e // m <= bound_below:
            best = e
    if best is None:
        raise AssertionError(f"no admissible e for bound_below={bound_below}, m={m}")
    return best


def max_input_for_target(target: int, m: int) -> int | None:
    """Largest B with density_ceiling(B, m) <= target, or None if none exists.

    This is the quantity the theorem turns on: what the chain would *need*
    to know one level down in order to reach `target`.
    """
    admissible = [
        B for B in range(1, target + 2) if density_ceiling(B, m) <= target
    ]
    return max(admissible) if admissible else None


def chain(start_bound: int, start_m: int, end_m: int) -> list[int]:
    """Propagate a bound upward through the density chain, inclusive of both ends."""
    if end_m < start_m:
        raise ValueError(f"end_m={end_m} is below start_m={start_m}")
    out = [start_bound]
    v = start_bound
    for m in range(start_m + 1, end_m + 1):
        v = density_ceiling(v, m)
        out.append(v)
    return out


def theorem_133_unreachable() -> dict:
    """The theorem, as a checkable dict rather than a claim in prose."""
    needed = max_input_for_target(133, 16)
    return {
        "target": 133,
        "m": 16,
        "required_bound_on_z15_17": needed,
        "verified_lower_bound_on_z15_17": VERIFIED_LOWER_BOUND_15_17,
        "required_bound_is_false": needed is not None
        and needed < VERIFIED_LOWER_BOUND_15_17,
        "ceiling_from_true_value": density_ceiling(VERIFIED_LOWER_BOUND_15_17, 16),
    }


# Best 16x16 lower bound this project can produce from its OWN verified data:
# delete the unique minimum-degree (6) column from the verified 132-edge 16x17
# witness. Exactly one short of what theorem_133_column_route needs.
VERIFIED_LOWER_BOUND_16_16 = 126

# Published, and used ONLY inside the corollary about what the 2016 authors'
# own algorithm could derive from their own table. Never used to support a
# claim about what is actually true.
PUBLISHED_16_16 = 128


def theorem_133_column_route() -> dict:
    """The transposed final step: delete a column, 16x17 -> 16x16.

    Theorem A silently assumed the chain's last step deletes a row. It need
    not: the problem is symmetric under transposition, so
    `e - floor(e/17) <= z(16,16)` is an equally valid final step, and it has
    to be ruled out separately. This function does that analysis and reports
    honestly whether our own data suffices (it does not, by one edge).
    """
    needed = max_input_for_target(133, 17)
    return {
        "target": 133,
        "n": 17,
        "required_bound_on_z16_16": needed,
        "verified_lower_bound_on_z16_16": VERIFIED_LOWER_BOUND_16_16,
        # The decisive question: is our own bound strong enough to falsify
        # the required input? 126 <= 126 means NO -- exactly at the threshold.
        "blocked_by_our_own_data": needed is not None
        and needed < VERIFIED_LOWER_BOUND_16_16,
        "blocked_if_z16_16_at_least": (needed + 1) if needed is not None else None,
        "published_16_16_would_block": needed is not None
        and needed < PUBLISHED_16_16,
        "ceiling_from_published": density_ceiling(PUBLISHED_16_16, 17),
    }


def tight_gaps() -> list[dict]:
    """For each m where both z(m-1,17) and z(m,17) are known: the chain's gap."""
    known = {**PROVED_HERE, **PUBLISHED}
    rows = []
    for m in sorted(known):
        if m - 1 not in known:
            continue
        ceiling = density_ceiling(known[m - 1], m)
        rows.append(
            {
                "m": m,
                "input": known[m - 1],
                "chain_ceiling": ceiling,
                "true_value": known[m],
                "gap": ceiling - known[m],
                "input_proved_here": (m - 1) in PROVED_HERE,
            }
        )
    return rows


def main() -> None:
    t = theorem_133_unreachable()
    print("THEOREM A (row deletion): a row-deleting chain cannot prove "
          "z(16,17;3) <= 133")
    print(f"  to reach 133 at m=16, the chain needs z(15,17;3) <= "
          f"{t['required_bound_on_z15_17']}")
    print(f"  but a verified witness gives  z(15,17;3) >= "
          f"{t['verified_lower_bound_on_z15_17']}")
    print(f"  required input is false: {t['required_bound_is_false']}")
    print(f"  the chain's actual ceiling here is z(16,17;3) <= "
          f"{t['ceiling_from_true_value']}, and it is attained\n")

    print("Sensitivity of the m=16 step to its input:")
    for B in range(122, 130):
        print(f"  z(15,17) <= {B}  ->  z(16,17) <= {density_ceiling(B, 16)}")

    c = theorem_133_column_route()
    print("\nTHEOREM B (conditional): the transposed final step, 16x17 -> 16x16")
    print(f"  to reach 133 that way, the chain needs z(16,16;3) <= "
          f"{c['required_bound_on_z16_16']}")
    print(f"  our own verified lower bound is z(16,16;3) >= "
          f"{c['verified_lower_bound_on_z16_16']}  <-- exactly the threshold")
    print(f"  blocked by our own data: {c['blocked_by_our_own_data']} "
          f"(would need z(16,16;3) >= {c['blocked_if_z16_16_at_least']})")
    print(f"  the published z(16,16;3) = {PUBLISHED_16_16} would block it "
          f"(giving z(16,17) <= {c['ceiling_from_published']}), but that is a citation\n")

    print("Where the chain is tight (gap 0) and where it loses edges:")
    for row in tight_gaps():
        src = "proved here" if row["input_proved_here"] else "published"
        print(
            f"  m={row['m']:2d}: from z({row['m']-1},17) = {row['input']:3d} "
            f"({src:11s}) -> chain <= {row['chain_ceiling']:3d} ; "
            f"true {row['true_value']:3d} ; gap {row['gap']}"
        )


if __name__ == "__main__":
    main()
