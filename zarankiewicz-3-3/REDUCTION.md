# The reduction: `Z(16,17,3,3)` in terms of extremal 15x17 graphs

This is the mathematical core of the intended proof. Everything here is
elementary and hand-checkable; the only computational obligations are the
two enumerations named at the end.

> ## Status corrections (added after measurement)
>
> Two claims made when this document was first written have since been
> tested and must be qualified. Both are recorded here rather than edited
> away, because the reduction is still correct — what changed is what it
> costs and what it rests on.
>
> **(1) The reduction is conditional, and we cannot discharge the
> condition.** Everything below takes `z(15,17) = 126` as an input. The
> intent was to re-derive that ourselves via the bottom-up ladder. That has
> now been *measured infeasible*: the density-lemma chain needs
> `z(9,17) <= 78` to reach `126`, and the true value — which this project
> **proved** from scratch — is `z(9,17) = 81`. Our own self-contained chain
> therefore yields only `z(15,17) <= 135`. The whole remaining obstruction
> localises to levels `k = 11, 12, 13`, each needing a genuine exhaustive
> refutation costing an estimated `1e9`, `2e10`, `4e11` nodes respectively.
> So the reduction below stands as mathematics, but its input is a
> **citation we cannot currently replace**. See
> `search/orderly/ORDERLY_LOG.md` §5.
>
> **(2) The "narrow ladder" framing does not reduce the work.** The claim
> that climbing `Ext(13,110) -> Ext(14,118) -> Ext(15,126)` is cheaper
> because each rung needs only degree-8 extension rows was **wrong**. It is
> the *same search tree*: a generator that orders rows by descending degree
> has its last row equal to the very row the density lemma deletes, so the
> tight-prefix constraints arise with no ladder framing at all. The ladder
> looks narrow because `|Ext(k,e)|` — the size of the *answer* at each rung
> — is small, but the cost is passing through the intermediate levels, which
> were measured still branching ~40x per row (`8.1e7` surviving
> configurations at level 6 alone). Confusing the size of an answer with the
> cost of computing it was the error. See `ORDERLY_LOG.md` §6.3.
>
> **Consequence for §"computational obligations" below:** those obligations
> are correct but are cluster-scale, not laptop-scale — optimistically ~40
> core-hours if the width peaks at level 8, realistically `1e12`-`1e14`
> nodes.

All arithmetic below was verified by direct computation, and the
degree-sequence counts come out as partition numbers, which serves as an
independent check on the enumeration (see the last section).

## Notation

- `z(m,n)` := `z(m,n;3)` = max edges of a `K_{3,3}`-free bipartite graph
  with parts of size `m` (rows) and `n` (columns).
- `Ext(m,n,e)` := the set of `e`-edge `K_{3,3}`-free `m x n` graphs, up to
  isomorphism.
- Target: `z(16,17)`, known to satisfy `132 <= z(16,17) <= 133`, with the
  lower bound witnessed by an explicitly verified matrix in this repo and
  the upper bound resting on an uncertified 2016 computation.

## Ingredients

**(I1) Monotonicity.** If a `K_{3,3}`-free graph with `e` edges exists then
so does one with `e-1` edges: delete any edge; deleting edges cannot create
a `K_{3,3}`. So achievable edge counts are downward closed, and refuting
"exactly `e`" refutes "at least `e`".

**(I2) Density lemma** (Collins–Riasanovsky–Wallace–Radziszowski 2016,
Lemma 3; re-derived here). In an `m x n` graph with `e` edges the minimum
row degree is at most `floor(e/m)`, since the minimum is at most the
average and is an integer. Deleting a row of degree `d` leaves an
`(m-1) x n` graph, still `K_{3,3}`-free, with `e - d` edges. Hence

```
e - d  <=  z(m-1, n)      where d = the degree of the deleted row.
```

**(I3) Two-sided degree pinch.** Combining: for any `K_{3,3}`-free
`m x n` graph with `e` edges, every row degree `d` satisfies
`d >= e - z(m-1,n)`, and the minimum row degree additionally satisfies
`d_min <= floor(e/m)`.

**(I4) Counting budget.** `K_{3,3}`-freeness says exactly that every
3-subset of columns lies in the neighbourhood of at most 2 rows. Counting
(row, column-triple) incidences two ways:
`sum_r C(d_r,3) <= 2*C(n,3)`, i.e. `<= 1360` for `n = 17`. (Transposing
gives `sum_c C(e_c,3) <= 2*C(16,3) = 1120`.) Note this budget turns out
**not to bind** in either case below — recorded for completeness, not
because it does work.

## Input values

`z(15,17) = 126` and `z(16,16) = 128`.

These are published values. **They are inputs to the reduction, not
outputs**, and per this project's discipline the intended proof re-derives
`z(15,17) <= 126` itself via the same bottom-up machinery rather than
citing it. The `+8` ladder `z(13,17)=110`, `z(14,17)=118`, `z(15,17)=126`
is tight at every step under (I2), which is what makes the bottom-up
re-derivation itself a narrow computation (see `LITERATURE.md`, and
`prover/idea-ledger.md` [L18]).

## Case e = 134 (certifies the published upper bound)

By (I3) with `z(15,17) = 126`: every row degree is `>= 134 - 126 = 8`, and
the minimum is `<= floor(134/16) = 8`. Therefore

> **the minimum row degree is exactly 8.**

Since all 16 rows have degree `>= 8`, any single row's degree is at most
`134 - 15*8 = 14`. So all degrees lie in `[8,14]`, sum to 134, and the
minimum is attained.

Writing each degree as `8 + x_r` with `x_r >= 0` and `sum x_r = 6`, the
admissible degree sequences correspond exactly to the partitions of 6.
There are `p(6) = 11` of them, all satisfying (I4) comfortably.

Moreover, deleting a minimum-degree row leaves exactly `134 - 8 = 126`
edges on `15 x 17` — **exactly extremal**. Hence:

> **Every 134-edge `K_{3,3}`-free `16 x 17` graph arises as a member of
> `Ext(15,17,126)` plus a single row of degree exactly 8.**

Refuting this gives `z(16,17) <= 133`, i.e. an independent certification of
the published bound (acceptance criterion (C) — never certified by anyone).

## Case e = 133 (the open question)

By (I3): every row degree is `>= 133 - 126 = 7`, and the minimum is
`<= floor(133/16) = 8`. So the minimum row degree is **7 or 8**, splitting
into two sub-cases:

| sub-case | deleting the min row leaves | parent set needed | extension row |
|---|---|---|---|
| `d_min = 7` | `133 - 7 = 126` on `15 x 17` | `Ext(15,17,126)` — *exactly extremal* | degree 7 |
| `d_min = 8` | `133 - 8 = 125` on `15 x 17` | `Ext(15,17,125)` | degree 8 |

The `d_min = 8` branch has all degrees in `[8,13]` summing to 133, i.e.
excess 5, giving `p(5) = 7` degree sequences. The `d_min = 7` branch admits
431 degree sequences (degrees in `[7,17]`), but that count is a coarse
filter and largely irrelevant: what actually constrains the branch is that
its parent must be *extremal*.

**Note the reuse:** the `d_min = 7` branch needs the same `Ext(15,17,126)`
as the `e = 134` case. So one enumeration serves the whole of `e = 134` and
the dominant branch of `e = 133`.

## The complete set of computational obligations

The entire problem reduces to two enumerations plus cheap extension tests:

1. **Compute `Ext(15,17,126)`** (up to isomorphism).
   - Test all degree-8 row extensions. None `=>` `z(16,17) <= 133`.
     *(criterion (C): certifies the published bound)*
   - Test all degree-7 row extensions. None `=>` the `d_min = 7` branch of
     `e = 133` is dead.
2. **Compute `Ext(15,17,125)`.**
   - Test all degree-8 row extensions. None `=>` the `d_min = 8` branch of
     `e = 133` is dead.

If all of the above come back empty, then `z(16,17) = 132` **exactly**,
combined with our already-verified 132-edge witness. That is full
resolution of the open problem.

Extension tests are cheap: `C(17,8) = 24310` and `C(17,7) = 19448`
candidate rows per parent, each rejected or accepted in one pass over the
triple-multiplicity counters.

## The one thing that can go wrong

Because the ladder is tight, **dropping a single graph from
`Ext(15,17,126)` or `Ext(15,17,125)` could remove precisely the parent that
extends**, turning a real witness into a false "no". This is the dominant
correctness risk in the whole plan, and it is why the enumeration must use
a *sound over-approximation* (retaining possibly-isomorphic duplicates)
rather than any clever canonical form whose completeness we cannot prove.
Redundant work is acceptable; a false negative is not.

## Self-check on the enumeration

The degree-sequence counts are `p(6) = 11` for `e = 134` and `p(5) = 7` for
the `d_min = 8` branch of `e = 133`. That these fall out as exact partition
numbers — as they must, since fixing the minimum degree at `m*d_min` and
distributing the excess is precisely a partition — is an independent check
that the enumeration code is not over- or under-counting.
