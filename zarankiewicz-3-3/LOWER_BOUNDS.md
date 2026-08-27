# Lower bounds on `z(k,17;3)` from row deletion

## Summary

Applying row-deletion monotonicity to the witness matrices re-verified in
this repo yields, with no search at all:

| `k` | lower bound from row deletion | verified in this PR? |
|---|---|---|
| 9  | 78  | **yes** |
| 10 | 86  | **yes** |
| 11 | **94** | **yes** |
| 12 | 102 | **yes** |
| 13 | 110 | **yes** |
| 14 | 118 | **yes** |
| 15 | 126 | **yes** |

Every number in the second column is produced by this PR's code from a
matrix in this PR's data directory, and re-checked by the three-detector
checker on every test run. **Nothing else in this document is on that
footing, and the rest of this section is explicit about which is which.**

> ### Provenance notice — read before using any comparison value below
>
> An earlier version of this document carried a "true value, where known"
> column comparing these bounds against `81, 90, 96, 103, 110, 118, 126`,
> and built a "shortfall" narrative on it. A reviewer correctly rejected
> that, on three counts, all of which were right:
>
> 1. **`k=12` (`103`) was uncited** — no paper, no table, no row. That
>    directly violates this project's own charter rule ("No citation without
>    certainty").
> 2. **`k=13` (`110`) was presented as a settled published value with
>    shortfall 0, contradicting `LITERATURE.md`** — already merged, and
>    which states that `z(13,17;3) = 110` *remains open*, because the
>    2016 table sets that cell in *italic* (= "determined with exhaustive
>    computations") and **not** bold (= exact). That was a factual error on
>    my part, not merely a missing citation: I conflated "appears in a table
>    as an upper bound" with "published as an exact value".
> 3. **`k=9, 10` (`81`, `90`) have no supporting artifact reachable from
>    this PR.** They were proved elsewhere in this project, on the abandoned
>    107-file branch that `README.md` itself describes as unreviewable and
>    superseded. That work was never carried into this restarted PR series,
>    and this PR does not add it. A reader who trusts only this repository
>    cannot check them.
>
> Accordingly, the comparison table is **removed**, not repaired. What
> follows uses only values whose provenance is stated precisely at the point
> of use, with the following labels used consistently:
>
> - **[VERIFIED HERE]** — derived by this PR's code from this PR's data.
> - **[CITED]** — a published value with paper, table, and cell given, and
>   with the marking convention stated. Not re-derived here.
> - **[CLAIMED ELSEWHERE, NOT LANDED]** — proved by this project on a branch
>   not yet in this PR series. **Not verifiable from this PR.** Treated as an
>   unverified assumption wherever it is used, and never as a fact.

### The one comparison this PR can make on its own footing

At `k = 11`, row deletion gives `94` **[VERIFIED HERE]**, and the published
value is `96` **[CITED**: Collins–Riasanovsky–Wallace–Radziszowski,
arXiv:1604.01257, J. Algorithms and Computation 47(1) (2016) 63–78,
**Table 4**, row `m=11`, column `n=17`, set in **boldface**, which their
legend defines as "a boldfaced entry is an exact value"; independently
**boldface** in Jeremy Tan, arXiv:2203.02283, **Table 3**, row 11 column 17,
whose legend reads "a bold value is exact, proven by the methods in this
paper"**]**.

So at the one cell where this PR has both halves on a stated footing, the
row-deletion bound **undershoots by 2**. That single data point is the whole
of the honest version of the old "shortfall" narrative, and it is enough for
the operational conclusion in the last section: these bounds must not be
read as tight.

### Two rows ARE certified exact, and deleting the column obscured that

A reviewer pointed out that the previous fix over-corrected. The comparison
column was deleted because three of its seven entries were bad — but two of
them, `k = 14` and `k = 15`, were never in question and have precise
citations *already landed in this repository*:

> `LITERATURE.md` (merged in the PR this one stacks on) states that Afrasyab,
> arXiv:2608.08154 (Aug 2026), proves `Z(14,17,3,3) = 118` and
> `Z(15,17,3,3) = 126` as **exact** values. `data/known_witnesses/SOURCES.md`
> records that `z14_17_118_witness.csv` and `z15_17_126_witness.csv` were
> copied from that same paper's repository, at a pinned commit, and
> re-verified here.

Combining that with this PR's own output:

| `k` | row-deletion bound | published exact value | conclusion |
|---|---|---|---|
| 14 | `118` **[VERIFIED HERE]** | `118` **[CITED**: Afrasyab arXiv:2608.08154**]** | **`z(14,17;3) = 118`**, lower half verified here |
| 15 | `126` **[VERIFIED HERE]** | `126` **[CITED**: Afrasyab arXiv:2608.08154**]** | **`z(15,17;3) = 126`**, lower half verified here |

So at these two cells the row-deletion bound is **tight**, and this PR
supplies the lower half of the exactness claim from a matrix checked here
rather than from a citation — which is precisely the first stated purpose of
this module. The general caution below ("never read `>= b_k` as `= b_k`")
therefore has two explicit exceptions, and they are named rather than left
under a blanket warning.

**Why this needed a reviewer to catch.** The previous round's finding was
that the comparison column mixed verified, cited, and unverifiable numbers in
identical formatting. Deleting the whole column removed the defect but also
removed two true, properly-sourced conclusions — trading an overclaim for an
underclaim. Both are errors; the second is just quieter. The fix is per-row
labelling, which is what the rest of this document already does.

### The `8k+6` reading is the wrong model — restated without the unlanded values

The original argument here leaned on `z(9,17;3) = 81` and `z(10,17;3) = 90`
being `9k` rather than `8k+6`. Those are **[CLAIMED ELSEWHERE, NOT LANDED]**,
so the argument cannot be made in this PR on that basis.

What survives without them, and it is enough: at `k = 11` the row-deletion
bound is `94 = 8*11 + 6` **[VERIFIED HERE]**, and the true value is `96`
**[CITED]**. So the `8k+6` line is **demonstrably not the true value at
`k = 11`**, and any plan that assumed it was — as one of mine did — was
unsound. That conclusion needs no unlanded input.

### The upper-bound side, and why it is not asserted in this PR

Elsewhere this project ran exhaustive refutations at `k = 11` and recorded
`z(11,17;3) <= 97`, later `<= 96`, plus an independent degree-9-extension
argument. All of that is **[CLAIMED ELSEWHERE, NOT LANDED]** -- the
generator, its logs, and its output files sit on a branch this PR series has
not yet carried over, so a reader of this PR cannot check any of it.

It is therefore **not used here**, not even as supporting colour. The
bracket `[94, 97]` that an earlier version of this document reasoned about,
and the argument that `94` was the least likely value in it, both depended
on that unlanded upper bound. They are removed rather than restated with a
caveat, because a bracket whose top is unverifiable is not a bracket.

What this PR can say about `k = 11`, and all it can say:

- `z(11,17;3) >= 94` **[VERIFIED HERE]**, from a matrix in this repository.
- `z(11,17;3) = 96` **[CITED]**, per the two sources given above.
- Therefore row deletion undershoots the published value by 2 at this cell,
  and `8k+6` is not the true value here.

**Consequence for the plan, with its dependency visible.** A route to
`z(16,17;3) <= 134` through `k = 11` requires `z(11,17;3) <= 94`. A 94-edge
graph exists **[VERIFIED HERE]**, so that route needs `z(11,17;3)` to equal
exactly `94`, and the **[CITED]** value says `96`. The route is dead **if
the citation is correct** -- which is the strongest form available in this
PR, and deliberately weaker than the unconditional claim the earlier version
made.

**And a caveat on the citation itself.** Two independent papers agreeing is
strong but not proof. If a from-scratch search here ever contradicted `96`,
the correct first response would be to suspect our own generator, not two
independent papers -- but the possibility is why the **[CITED]** label exists
rather than being silently promoted to fact.

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
  are included in the sweep and behave. `k > m` and `k = 0` raise rather than
  silently returning something — now actually covered by
  `test_out_of_range_k_raises`. (An earlier version of this document listed
  that bullet under "each now a test" when no test passed an out-of-range
  `k` at all. The behaviour was real; the coverage claim was not. A reviewer
  caught the mismatch.)
- **The transposition trap.** A bug that selected *columns* while believing
  they were rows would still produce `K_{3,3}`-free matrices with plausible
  edge counts, so the checker alone would not catch it — what it would
  change is which cell the bound applies to.
  `test_deleting_columns_is_not_what_this_module_does` pins the shape.
- **Witnesses on the wrong cell.** The directory contains 18-column
  witnesses. Mixing those in would produce bounds for `z(k,18;3)` labelled
  as `z(k,17;3)`. They are skipped explicitly, not filtered by accident.

## The step I am least confident in

Not the mathematics -- the lemma is elementary and machine-checked by
exhaustion over all `2^16` matrices on `4x4`. The risk is **interpretive**:
reading these bounds as tight.

The one comparison this PR can make on its own footing already refutes that
reading. At `k = 11` row deletion gives `94` **[VERIFIED HERE]** while the
published value is `96` **[CITED]** -- a shortfall of **2**. A witness
optimised for `m = 14` or `15` need not contain an optimal `k`-row subgraph
for smaller `k`, and here it demonstrably does not.

`test_lower_bound_is_known_to_be_loose_at_k_11` asserts that shortfall as a
live test against the cited value, so if a future witness closes it the suite
fails and forces the claim to be re-examined deliberately rather than
absorbed silently.

**Therefore: `z(k,17;3) >= b_k` must never be read as `z(k,17;3) = b_k`.**
That applies at every `k` in the table, including the ones where no
comparison value is available in this PR -- absence of a known shortfall is
not evidence of tightness.

## Why this is worth having anyway

These are lower bounds derived from published constructions, so they are not
new mathematics. Two concrete uses:

1. **They supply the lower half of any future exactness claim.** An upper
   bound of `v` proved by a from-scratch search, paired with a lower bound of
   `v` from a matrix checked here, gives `z = v` with nothing cited. That is
   the standard `README.md` sets. This PR supplies only the lower halves; the
   matching upper bounds are **[CLAIMED ELSEWHERE, NOT LANDED]** and are not
   combined with these bounds anywhere in this document.

2. **They rule out searches that cannot succeed, which is directly
   operational.** If `z(k,17;3) >= v` **[VERIFIED HERE]**, then no exhaustive
   search can refute `v` edges at that `k` -- such a run is guaranteed to
   return a witness, so its cost is wasted if the goal was a refutation.
   Concretely: `z(11,17;3) >= 94` means a `--decide 94` run at `k = 11` can
   never legitimately come back UNSAT, so `95` is the smallest target at that
   level worth attempting. `test_lower_bound_forbids_refutation_at_that_target`
   exhibits the 94-edge matrix rather than caching the number, so the claim
   stays falsifiable.

### What the density chain does with these numbers

The chain step `f(j) <= max{e : e - floor(e/j) <= f(j-1)}` is pure
arithmetic and is computed and asserted in this PR
(`test_density_chain_table_in_the_log_is_correct`), so the mapping below is
**[VERIFIED HERE]** as arithmetic. What is *not* verified here is any claim
about which row is the true one -- that depends on the value of
`z(11,17;3)`, which this PR only has **[CITED]**.

| if `z(11,17;3) =` | then the chain gives `z(16,17;3) <=` |
|---|---|
| 97 | 137 |
| 96 | 136 |
| 95 | 135 |
| 94 | 134 |

On the **[CITED]** value `96`, the `k = 11` route's ceiling is
`z(16,17;3) <= 136`, and no amount of compute at that level improves it --
improving past `136` requires going to `k = 12`. Stated as a conditional
because its input is a citation, not a result of this PR.

## Reproducing

```
cd zarankiewicz-3-3
python verify/lower_bounds.py      # prints the table above
pytest verify/test_lower_bounds.py # 16 passed, 3 skipped (18-column witnesses)
```
