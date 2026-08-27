# Soundness of every pruning and canonicity rule in `orderly.c`

`orderly.c`'s header previously pointed at an `ORDERLY_LOG.md` that does not
exist in this repository — so the soundness argument for the rules the entire
upper-bound half of `EXACT_VALUES.md` rests on was **not available to a
reader**, only summarised in code comments and asserted by reference to a
missing file. A reviewer flagged that. This document is the referenced
argument, landed.

## What has to be true

The generator's `EXHAUSTED` verdict asserts a negative: *no* `m x n`
`K_{3,3}`-free graph with at least `T` edges exists. That is only meaningful
if every rule below is **conservative** — it may reject a candidate only when
some other candidate isomorphic to it, or dominating it, is still reachable.
A rule that prunes one edge too many produces a false `EXHAUSTED`, which is
the single most dangerous failure mode in this project.

Notation: rows are subsets of the `n` columns, `d_r = |N(r)|`,
`h(j,d)` = max edges of a `j x n` `K_{3,3}`-free graph with all row degrees
`<= d`, and `f(j) = z(j,n;3) = h(j,n)`.

## R0 — the characterisation the whole search maintains

**Claim.** A bipartite graph is `K_{3,3}`-free **iff** every 3-subset `T` of
the columns is contained in `N(r)` for at most 2 rows `r`.

*Proof.* A `K_{3,3}` is exactly a choice of 3 rows and 3 columns with all
nine pairs adjacent, i.e. a 3-subset `T` of columns contained in `N(r)` for
3 distinct rows. So a `K_{3,3}` exists iff some `T` has 3 or more containing
rows. []

Implemented as `C(n,3)` counters (680 for `n = 17`) capped at 2, incremented
as a row is built column by column and decremented on backtrack. The cap is
safe because the search rejects at the moment a counter would reach 3, so no
information above 2 is ever needed.

**Independently checked.** `verify/test_checker.py` confirms this
characterisation against a definition-literal brute force over all `2^9` 3x3
and `2^12` 3x4 matrices, plus random larger cases. That test exists precisely
because R0 is an equivalence the whole project leans on, and a
characterisation is not the definition.

## R1 — rows may be assumed sorted by (degree DESC, mask DESC)

**Claim.** Restricting to row-sorted graphs loses nothing.

*Proof.* Permuting rows is an isomorphism of the bipartite graph: it changes
neither the edge count nor `K_{3,3}`-freeness (a `K_{3,3}` is a set of three
rows, and sets are unordered). So every graph is isomorphic to exactly one
row-sorted representative, which the search reaches. []

**The subtlety, which is load-bearing.** The ordering must be by **degree**
first, not by raw integer mask. R4 below concludes "rows after `k` have
degree `<= d_k`" — that is a statement about degrees, and mask order alone
does **not** imply degree order (e.g. mask `10000` = 16 exceeds mask `01111`
= 15 while having smaller degree). Sorting by mask only would make R4
unsound. The code sorts by `(degree, mask)`, and the comment in `orderly.c`
flags this explicitly.

## R2 — column canonicity

**Claim.** Row `k` may be required to be the lexicographically maximal
element of its orbit under the stabiliser, in the column symmetric group, of
rows `0..k-1`.

*Proof sketch.* Any column permutation fixing rows `0..k-1` setwise maps a
valid completion to a valid completion, since column permutations preserve
`K_{3,3}`-freeness and edge counts. So within each orbit it suffices to
enumerate one representative, and the lexicographic maximum is a
well-defined choice.

**Why it is implementable as "a prefix of every cell".** The stabiliser of
rows `0..k-1` is the direct product of the symmetric groups on the cells of
the column partition those rows induce. By induction the cells are contiguous
intervals (the initial partition is the single interval `[0,n)`, and
refinement by a row that is a prefix of each cell splits each interval into
two intervals). Hence "lexicographically maximal in its orbit" says exactly:
**within every cell, row `k`'s columns form a prefix of that cell.**

For `k = 0` the partition is the single cell `[0,n)`, so row 0 is forced to
`1^{d_0} 0^{n-d_0}` — the familiar "first row fixed WLOG", here *derived*
rather than assumed.

**Validated empirically.** `--nocanon` disables R2 entirely (cells become
singletons, so every subset is enumerated), leaving only R1. Node counts
differ enormously but verdicts must agree. This is the direct test that R2
does not over-prune.

## R3 — prefix bound

The first `k` rows form a `k x n` `K_{3,3}`-free graph all of whose degrees
are `<= d_0` (by R1, row 0 has the largest degree). So their edge total
satisfies `E_k <= h(k, d_0)`. Sound because it is an upper bound on a
quantity the partial graph already realises.

## R4 — suffix bound

By R1, every row after `k` has degree `<= d_k`. So the remaining `j` rows
contribute at most `h(j, d_k)` edges, and the branch can be cut if
`E_k + h(j, d_k) < T`. Sound given R1's **degree**-first ordering — see the
subtlety noted there.

## R5 — triple-budget bound

Counting (row, column-triple) incidences two ways against R0 gives
`sum_r C(d_r,3) <= 2*C(n,3)`. Given the degrees already committed, the
remaining rows' degrees are constrained by a knapsack in the residual
capacity, solved exactly by the DP table `knaptab`. Sound because it is an
exact solution of a relaxation: every real completion satisfies the knapsack,
so anything the knapsack rules out was already impossible.

## R6 — density-lemma upper bound

Used **only** as an upper bound on `h`, which is what makes it sound. The
minimum row degree is at most `floor(e/j)`; deleting a minimum-degree row
leaves `j-1` rows whose degrees are still `<= d`; hence
`e - floor(e/j) <= h(j-1, d)`. Disabled by `--nodensity` for validation.

## R9 — a hoisted complement of the degree-floor / `emax` test

R9 lifts a post-row feasibility test (R7) into a degree cap applied before
the row is built. It is an optimisation, not a new constraint: it rejects
exactly the rows R7 would have rejected afterwards.

**Verified non-semantic by measurement**, which is the only convincing check
for an optimisation of this kind: on identical inputs the R9 build and the
pristine build produced **identical node counts and identical per-level
width profiles** (29,622,896 nodes, level profiles matching digit for digit),
at 2.12x the speed.

## `h(j,d)` and the `--assume` flag

`h(j,d)` is computed lazily bottom-up and memoised. Two implementations
exist:

- `hval(j,d)` — the **exact** value, by recursive sub-search.
- `hub(j,d)` — a cheap closed-form **upper bound**, which is where an
  `--assume k:v` declaration would be consulted (`orderly.c:211`).

**`--assume` is inert in every run reported in `EXACT_VALUES.md`.** Both call
sites (`suffix_bound()` at `:223`, and the prefix check in `gen()` at
`:381`) select `hval()` whenever `h_exact && j <= hcap_level`; `h_exact`
defaults to 1 and `hcap_level` to `MAXM` = 24, and every `j` involved is
`<= 15`. So `hub()` is never called and `hassume[]` is never read.

This is *better* for soundness than the alternative — the bounds actually
used are exact and need no declared assumption — but it means any argument
about `--assume`'s safety is describing a code path that does not execute.
`--hmode ub` or `--hcap` would be required to reach it.

## The two checks that do not depend on any of the above

Because all the reasoning above is mine, the results are also guarded by two
arguments that route around it entirely:

1. **An independent second searcher.** `brute.c` shares no code with
   `orderly.c` and implements none of R2–R9. `make cross-check` compares
   verdicts across `n = 4..7`, `m = 3..6`, targets `6..24`: **144 cells, 144
   agreed (107 FOUND, 37 EXHAUSTED)**. The target also fails if it compares
   zero cells, if either verdict is missing, or if only one verdict kind
   appears — guards added after an earlier version of it was found to pass
   unconditionally. And it was itself validated by confirming it *detects* a
   deliberate mismatch at a genuine verdict boundary.

2. **Every `EXHAUSTED` is bracketed by a `FOUND` one edge below**, with the
   witness re-verified by `verify/checker.py`, which shares no code with the
   generator. A search over-pruned enough to produce a false `EXHAUSTED`
   would very likely also fail to produce the witness.

Neither is a proof of the generator. The only thing that would be is a
machine-checkable certificate; this project has that pipeline working
end-to-end for `z(7,7;3) <= 33` (`drat-trim` plus the HOL4-verified
`cake_lpr`), but the proofs for the cells here were measured far past the
local checking ceiling.
