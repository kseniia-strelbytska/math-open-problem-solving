# Lower bounds on `z(k,17;3)` from row deletion

## Summary

Applying row-deletion monotonicity to the witness matrices re-verified in
this repo yields, with no search at all:

| `k` | lower bound from row deletion | upper bound proved in this project | true value, where known | shortfall of the lower bound |
|---|---|---|---|---|
| 9  | 78  | `<= 81` (exhaustive) | **81** | **3** |
| 10 | 86  | `<= 90` (exhaustive) | **90** | **4** |
| 11 | **94**  | `<= 97` (exhaustive) | **96** (published, twice) | **2** |
| 12 | 102 | `<= 105` (density chain) | **103** (published once, never re-proved) | **1** |
| 13 | 110 | `<= 113` (density chain) | 110 (published) | 0 |
| 14 | 118 | `<= 121` (density chain) | 118 (published) | 0 |
| 15 | 126 | `<= 129` (density chain) | 126 (published) | 0 |

The last column is the point of the table, and it is bad news, not good:
**wherever the true value is known, this method undershoots it** — by 3 and
4 at `k = 9, 10` (values proved here), and by 2 and 1 at `k = 11, 12`
(values published; see the section below). It happens to be tight at
`k = 13, 14, 15`, which is exactly where the witnesses were optimised.

The apparent agreement of the lower bounds with `8k+6` at `k = 11, 12` is
therefore **not evidence that the true values are `94` and `102`** — and
indeed they are not; they are `96` and `103`.

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

### Settled by the literature while this was being written: it is 96

A literature check completed after the analysis above was written, and it
resolves the bracket from outside:

> **`z(11,17;3) = 96` is a published exact value.** Collins–Riasanovsky–
> Wallace–Radziszowski, *Zarankiewicz Numbers and Bipartite Ramsey Numbers*,
> arXiv:1604.01257 (J. Algorithms and Computation 47(1) (2016) 63–78),
> **Table 4**, row `m=11`, column `n=17`, set in **boldface**, which their
> legend defines as "a boldfaced entry is an exact value". Independently,
> Jeremy Tan, *An attack on Zarankiewicz's problem through SAT solving*,
> arXiv:2203.02283, **Table 3**, row 11 column 17, also **bold**, which his
> legend defines as "a bold value is exact, proven by the methods in this
> paper".

Two independent computational proofs, in two papers, six years apart. Both
markings were read at the glyph level from the embedded PDF fonts, not from
a rendering — the same method that earlier established the `133` cell of the
same table is italic (`PJYSJE+CMTI10`), and reproducing that known result
was used to confirm the column alignment.

**This is recorded rather than used to edit the reasoning above.** The
bracket `[94, 97]` and the argument about the `8k+6` regime change were
derived from this project's own computations and remain exactly as valid as
they were; the published value simply lands inside the bracket, at `96`.
Keeping both is the point — the prediction was that `94` is the least likely
value in the bracket, and that prediction was right.

**Consequences, all bad for the shortcut and good for the honesty of the
record:**

1. **`z(16,17;3) <= 134` via `k = 11` is dead.** It required
   `z(11,17;3) = 94`. If `96` is correct, a 96-edge graph exists, so
   `--decide 95` and `--decide 96` can only return SAT. The `--decide 95`
   run was killed for this reason, with the reasoning written into its
   output file rather than left as a silent corpse.
2. **Our own bounds are weaker than the literature at this cell**, in both
   directions: our `>= 94` against a published `96`, and our `<= 97` against
   a published `96`. Stating that plainly matters more than the bounds
   themselves.
3. **The self-contained target becomes `z(11,17;3) = 96` exactly**, which is
   now reachable: `--decide 97` returning EXHAUSTED gives `<= 96`, and
   `--decide 96` returning SAT hands us our own 96-edge matrix, giving
   `>= 96` from a witness we checked rather than from a citation. That is a
   re-derivation of a twice-published value, not a new result — and it is
   labelled as such.

**A caveat on the caveat.** If `--decide 96` returns EXHAUSTED, that would
*contradict* the published value, and the correct response is to suspect our
generator before suspecting two independent papers. That check is worth
having precisely because it is a check.

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
   - The three jobs launched on this basis (`--decide 95/96/97`) would
     therefore resolve `z(11,17;3)` exactly, since the bracket has only four
     values in it.

   **Update after the literature check (see the section above).**
   `z(11,17;3) = 96` is published, twice. So `--decide 95` can only return
   SAT and was killed as subsumed; the surviving pair `--decide 96` (expect
   SAT, handing us our own 96-edge witness) and `--decide 97` (expect
   EXHAUSTED, giving `<= 96`) still pin the value exactly, now as a
   **self-contained re-derivation of a published result** rather than a new
   one. The `134` row of the table below is unreachable.

   Chain values for each outcome, computed from
   `f(j) <= max{e : e - floor(e/j) <= f(j-1)}` (divisor 8 throughout this
   range, so the propagation is 1:1 from `k = 11` to `k = 16`):

   | if `z(11,17;3) =` | then chain gives `z(16,17;3) <=` | status |
   |---|---|---|
   | 97 | 137 | already proved self-contained |
   | **96** | **136** | **the real value** — the best this route can give |
   | 95 | 135 | unreachable (a 96-edge graph exists) |
   | 94 | 134 | unreachable |

   So the `k = 11` route's true ceiling is `z(16,17;3) <= 136`, one better
   than we have, and it cannot do better no matter how much compute is
   spent at that level. Improving past `136` requires going to `k = 12`.

## Reproducing

```
cd zarankiewicz-3-3
python verify/lower_bounds.py      # prints the table above
pytest verify/test_lower_bounds.py # 16 passed, 3 skipped (18-column witnesses)
```
