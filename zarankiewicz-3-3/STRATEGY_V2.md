# Strategy v2 — re-evaluation and pivot (2026-08-26)

Written after a model change prompted a hard review of the approach so far.
Verdict: the infrastructure built so far is good and worth keeping; the
**main computational strategy was the wrong tool**, and is being replaced.

## What was right, and is kept

- `verify/checker.py` — the independent checker, multiple methods forced to
  agree, validated against hand cases + 500 random trials + all 6 known
  literature witnesses. This stays as the trust anchor.
- The literature grounding: 132 is a real, independently re-verified
  witness; 133 is a real, traced, *never-certified* 2016 bound. Correct and
  load-bearing.
- The honesty discipline (`PROGRESS.md`, the idea ledger, calibrated
  confidence with named weakest steps). Kept and extended.

## What was wrong

**A monolithic SAT call was the wrong tool for this instance.** Six solver
configurations ran for 80–107 CPU-minutes each and resolved nothing. That
is not bad luck; it is predictable from the instance's structure:

1. **Symmetry.** The instance is invariant under all row and column
   permutations: `16! · 17! ≈ 1.2e26` symmetric copies of every solution
   (or of every refutation subtree). CDCL has no mechanism to exploit this.
   The "double lex" symmetry-breaking clauses added to fight it were
   *logically* sound (validated) but made the solver **slower** — observed
   directly: with symmetry breaking the known-satisfiable `K=116` instance
   never finished, without it the same instance solved in 213 s.
2. **A propagation-poor encoding.** A single global "exactly 133 of 272
   variables" cardinality constraint, sequential-counter encoded, adds
   ~37k auxiliary variables and propagates weakly. Nothing tells the solver
   the *per-row* structure that actually drives the combinatorics.
3. **No use of known sub-structure.** The encoding throws away everything
   already known about smaller sub-rectangles.

Local search (two independent designs, 380 restarts total) was worth doing
and produced consistent negative evidence, but it is structurally incapable
of *proving* anything, and both attempts have now converged on the same
floor. Further local search has low marginal value.

## The reformulation that unlocks the right method

A 16x17 0/1 matrix is `K_{3,3}`-free **iff** every 3-subset `T` of the 17
columns is contained in the neighbourhood of **at most 2** rows:

```
m(T) := #{ rows r : T subset of N(r) }  <=  2     for all T, |T| = 3
```

Counting `(row, column-triple)` incidences two ways gives the row-side
budget `sum_r C(d_r,3) <= 2*C(17,3) = 1360`, and transposing gives the
column-side budget `sum_c C(e_c,3) <= 2*C(16,3) = 1120`.

**Verified computationally (this session):** these counting bounds alone do
*not* rule out 133 — the balanced row sequence gives 1036 <= 1360 and the
balanced column sequence 889 <= 1120. So counting is genuinely
insufficient and real search is required. (Also checked and found
*vacuous*: an attempt to bound the max row degree below 17 via the counting
budget — `C(17,3) + 15*C(7,3) = 1205 <= 1360` — yields nothing. Recorded
because it was tried and failed, not quietly dropped.)

## What the reformulation *does* buy: a 438-case reduction

Using deletion of a minimum-degree row/column against sub-cell values:

| derived constraint | from |
|---|---|
| every row degree `>= 7` | `133 - z(15,17;3) = 133 - 126` |
| every column degree `>= 5` | `133 - z(16,16;3) = 133 - 128` |
| last two rows supply `>= 15` | `133 - z(14,17;3) = 133 - 118` |
| last three rows supply `>= 23` | `133 - z(13,17;3) = 133 - 110` |

Combined with the two counting budgets, the number of *possible row degree
sequences* for a hypothetical 133-edge graph collapses to **438** (and 3167
column sequences) — verified by direct enumeration this session.

That is the whole point: the problem is not one monolithic search, it is a
few hundred explicit, independently-checkable, parallelisable cases.

**Caveat, and the fix.** Those four constraints currently lean on
*published* sub-cell upper bounds (`z(15,17)<=126` etc.) which are exactly
the kind of uncertified claim this project refuses to build on. So the plan
below does not import them — it **re-derives them**.

## Strategy v2: bottom-up self-contained exhaustive generation

Compute `f(k) := z(k,17;3)` ourselves for `k = 1, 2, ..., 16` by
isomorph-free exhaustive generation, each level using only the levels below
it. Then `f(16)` *is* the answer (132 or 133), and the proof cites nothing
external.

Generation, row by row, rows as 17-bit masks:

1. **Row canonicity:** rows kept in lexicographically non-increasing order.
   Sound and trivial — sorting rows changes neither edge count nor
   `K_{3,3}`-freeness.
2. **First row fixed:** WLOG `1^{d_1} 0^{17-d_1}` by column permutation.
3. **Incremental triple multiplicity:** 680 counters, each capped at 2,
   updated on each row placement.
4. **Prefix pruning:** after `k` rows, `E_k <= f(k)` using *our own*
   previously computed `f(k)`.
5. **Suffix pruning:** rows are non-increasing, so the remaining `16-k`
   rows add at most `(16-k)*d_k`; prune if `E_k + (16-k)*d_k < target`.
6. **Triple-budget pruning:** remaining triple capacity must still
   accommodate the remaining rows' `C(d,3)` demand.

**Validation before trust (non-negotiable):** run the generator on cells
whose exact values are independently published and check it reproduces them
— small cells first (`z(6,6)=26`, `z(7,7)=33`, `z(8,8)=42`, `z(9,9)=49`),
then the directly relevant `z(13,17)=110`, `z(14,17)=118`, `z(15,17)=126`.
Reproducing those is far stronger evidence than anything the SAT pipeline
produced, *and* it converts the four table lookups above from cited
assumptions into our own results.

## Why this is the right shape for a publishable proof

If the answer is `132`, the proof is: an explicit case reduction
(human-checkable mathematics — the counting bounds and deletion arguments
above, cutting to 438 cases) plus an exhaustive isomorph-free search whose
correctness is evidenced by reproducing every known value below it, ideally
confirmed by a second independent implementation. That is precisely the
accepted structure of computer-assisted results in this literature.

A bare solver "UNSAT" would not meet that bar; a certified UNSAT (DRAT/LRAT)
would be *acceptable* but we have no certificate toolchain wired in, and
the monolithic instance is not solving anyway.

## Disposition of running compute

Killed as futile: Cadical *with* symmetry breaking (known pathological
here), the `K=134` sanity check (low value), Glucose3 (weakest of the
solvers tried), Z3 (weak SAT engine for this shape).

Kept as cheap lottery tickets on already-warm processes: Kissat on
`K=133`, Cadical-no-symmetry on `K=133`, and Kissat on the `13x18, K=117`
instance — the last is genuinely valuable, since UNSAT there is an
independent confirmation that `z(13,18;3)=116` exactly.
