# Lower bounds on `z(k,17;3)` from row deletion

## Summary

Applying row-deletion monotonicity to the witness matrices re-verified in
this repo yields, with no search at all:

| `k` | lower bound from row deletion | upper bound proved in this project | true value, where known | shortfall of the lower bound |
|---|---|---|---|---|
| 9  | 78  | `<= 81` (exhaustive) | **81** | **3** |
| 10 | 86  | `<= 90` (exhaustive) | **90** | **4** |
| 11 | **94**  | `<= 97` (exhaustive) | unknown, in `[94, 97]` | unknown |
| 12 | 102 | `<= 105` (density chain) | unknown | unknown |
| 13 | 110 | `<= 113` (density chain) | unknown | unknown |
| 14 | 118 | `<= 121` (density chain) | unknown | unknown |
| 15 | 126 | `<= 129` (density chain) | unknown | unknown |

The last column is the point of the table, and it is bad news, not good:
**wherever the true value is known, this method undershoots it by 3 or 4
edges.** The apparent agreement of the lower bounds with `8k+6` for
`k >= 11` is therefore weak evidence at best — the same formula undershoots
by 3 at `k = 9` and by 4 at `k = 10`, where we can actually check.

### The `8k+6` reading is worse than weak — it is the wrong model

Worth spelling out, because the plan briefly rested on it. The values this
project actually *proved* are `z(9,17;3) = 81` and `z(10,17;3) = 90`. Those
are not `8k+6` (which gives 78 and 86); they are `9k` — i.e. **9-regular**,
the densest thing the shape allows. The published values at the top of the
range, `110`, `118`, `126`, are `8k+6`. So the sequence changes regime
somewhere in between, and `k = 11` is inside the transition, which is
exactly where a formula fitted to either end is least trustworthy.

What we know at `k = 11` narrows it from both sides:

- 9-regular would be `99`. Ruled out: `--decide 98` at `k = 11` returned
  EXHAUSTED, so `z(11,17;3) <= 97`. The 9-regular regime therefore ends at
  `k = 10`, and it ends by at least 2 edges.
- Independently, extending the 24 extremal 9-regular `10x17` graphs by a
  degree-9 row returned `ext_success = 0` — no 99-edge `11x17` graph has a
  9-regular extremal parent. Consistent, and reached by a different code
  path.
- Row deletion gives `>= 94`.

So `z(11,17;3)` is in `[94, 97]`, and the honest reading is that the
**bottom of that bracket is the least likely value**, since `94` is where a
formula fitted to the far end of the range lands and the near end (`k = 9`,
`10`) sits 3-4 edges above what the same construction yields. This matters
because, as the last section shows, `z(16,17;3) <= 134` through `k = 11`
needs precisely `z(11,17;3) = 94` — the one value in the bracket the
evidence points away from.

Every bound in the second column is backed by an explicit matrix that
`verify/checker.py` re-checked with all three of its independent `K_{3,3}`
detectors. Nothing here is cited.

## The one lemma

**Row-deletion monotonicity.** If `G` is `K_{3,3}`-free with row set `R` and
column set `C`, and `S` is a subset of `R`, then the induced subgraph
`G[S union C]` is `K_{3,3}`-free.

*Proof.* A `K_{3,3}` in the subgraph uses three rows of `S` and three
columns of `C`, with all nine pairs adjacent. Since the subgraph is
*induced* and `S` is a subset of `R`, those nine adjacencies hold in `G`
too, so `G` contains a `K_{3,3}`. Contradiction. []

Because each row's edges are disjoint from every other row's, the edge count
of `G[S union C]` is exactly the sum of the degrees of the rows in `S`. So
the best bound a given witness yields at a given `k` is the sum of its `k`
largest row degrees.

`verify/lower_bounds.py` nevertheless brute-forces all `C(m,k)` subsets
rather than relying on that last sentence — the cost is negligible at these
sizes, and `test_brute_force_agrees_with_largest_degrees_shortcut` asserts
the two methods agree, which is the actual check on the reasoning.

## Attempts to break it before using it

- **Is the lemma really true, or does deleting a row let a `K_{3,3}`
  appear?** It cannot: deletion only removes adjacencies. But since the
  entire document rests on this, it is checked by exhaustion rather than by
  argument — `test_monotonicity_holds_on_exhaustive_small_cases` enumerates
  all `2^16` matrices on `4x4`, keeps the `K_{3,3}`-free ones, and confirms
  every 3-row subgraph is `K_{3,3}`-free, with the checker (not this module)
  deciding. A random 12x17 version does the same where `K_{3,3}`s are
  plentiful.
- **Boundary cases.** `k = m` (delete nothing) and `k = 1` (a single row)
  are included in the sweep and behave. `k > m` raises rather than silently
  returning something.
- **The transposition trap.** A bug that selected *columns* while believing
  they were rows would still produce `K_{3,3}`-free matrices with plausible
  edge counts, so the checker alone would not catch it — what it would
  change is which cell the bound applies to.
  `test_deleting_columns_is_not_what_this_module_does` pins the shape.
- **Witnesses on the wrong cell.** The directory contains 18-column
  witnesses. Mixing those in would produce bounds for `z(k,18;3)` labelled
  as `z(k,17;3)`. They are skipped explicitly, not filtered by accident.

## The step I am least confident in

Not the mathematics — the lemma is elementary and now machine-checked by
exhaustion. The risk is **interpretive**: reading these bounds as tight.

The table above contains its own refutation of that reading. At `k = 10`
the witnesses give `86`, but this project *proved* `z(10,17;3) = 90` by
exhaustive search. So a witness optimised for `m = 14` or `15` need not
contain an optimal 10-row subgraph, and the shortfall here is **4 edges**.
At `k = 9` the gap is `81 - 78 = 3`.

`test_witness_bound_is_known_to_be_loose_at_k_10` asserts the `k = 10` gap
as a live test, so if a future witness closes it, the suite fails and forces
that to be examined deliberately instead of absorbed silently.

**Therefore: `z(11,17;3) >= 94` must not be read as `z(11,17;3) = 94`.**
The proved bracket is `94 <= z(11,17;3) <= 97`, and given a 3-4 edge
shortfall at `k = 9,10`, the true value being `95`, `96` or `97` is entirely
consistent with the data.

## Why this is worth having anyway

These are lower bounds derived from published constructions, so they are not
new mathematics. Two concrete uses:

1. **They supply the lower half of every exactness claim.** An upper bound
   of `v` proved by our own search, paired with a lower bound of `v` from a
   matrix we checked ourselves, gives `z = v` with nothing cited. That is
   the standard this project set for itself in `README.md`.

2. **They bound in advance what the upper-bound search can achieve, which
   changes what is worth running.** If `z(k,17;3) >= v`, then no exhaustive
   search can refute `v` edges at that `k` — such a run is guaranteed to
   return a witness, and its cost is wasted if the goal was a refutation.
   Concretely, at the time of writing this reshaped the plan:

   - `z(11,17;3) >= 94` means **`--decide 94` at `k = 11` cannot come back
     UNSAT** — a 94-edge graph demonstrably exists. So the smallest target
     with any chance of refutation is `95`.
   - `z(16,17;3) <= 134` via the density chain requires `z(11,17;3) <= 94`,
     i.e. exactly `z(11,17;3) = 94`. Combined with the bracket above, the
     `k = 11` route reaches `134` **if and only if** the lower bound is
     tight — and the `k = 9, 10` shortfalls are direct evidence that
     tightness is not to be assumed.
   - The three currently running jobs (`--decide 95/96/97`) therefore
     resolve `z(11,17;3)` exactly, since the bracket has only four values
     in it.

   Chain values for each outcome, computed from
   `f(j) <= max{e : e - floor(e/j) <= f(j-1)}` (divisor 8 throughout this
   range, so the propagation is 1:1 from `k = 11` to `k = 16`):

   | if `z(11,17;3) =` | then chain gives `z(16,17;3) <=` |
   |---|---|
   | 97 | 137 *(already proved)* |
   | 96 | 136 |
   | 95 | 135 |
   | 94 | **134** — matches the hand bound, with nothing cited |

## Reproducing

```
cd zarankiewicz-3-3
python verify/lower_bounds.py      # prints the table above
pytest verify/test_lower_bounds.py # 16 passed, 3 skipped (18-column witnesses)
```
