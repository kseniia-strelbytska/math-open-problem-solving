# The Zarankiewicz z(m,n;3,3) frontier

> **Start with [`WRITEUP.md`](WRITEUP.md)** — the master index: current
> status, every document, every program with what it does and what it
> produced, and the consolidated run log.

## Problem

`Z(m,n,3,3)` is the maximum number of edges a bipartite graph with parts of
size `m` and `n` can have while containing no `K_{3,3}` (no 3 vertices on
one side all adjacent to the same 3 vertices on the other side).

**Primary target: `Z(16,17,3,3)`.**

As of the literature check that motivated this problem's selection
(25 Aug 2026), the best published bounds are:

```
132 <= Z(16,17,3,3) <= 133
```

- Lower bound (132): an explicit witness graph is known (see literature
  survey, to be re-derived/re-verified independently in this repo rather
  than taken on faith — see acceptance criteria).
- Upper bound (133): established in Afrasyab, "Exact Zarankiewicz Values on
  Two Finite Frontier Slices" (arXiv:2608.08154, Aug 2026), which explicitly
  states this bound "relies on prior published work, not an independently
  verified certificate" — i.e. even the upper bound, as it stands in the
  literature, has not been independently machine-checked by anyone yet.

A follow-up paper (arXiv:2608.08549, 9 Aug 2026) closed seven adjacent
cells from a shared certificate core but does not touch `Z(16,17,3,3)`.

**Before spending compute, this repo will re-run a fresh literature check**
(see Progress log) to confirm the gap is still open, since this is an
actively-worked niche (three papers in the ~15 weeks before this problem was
selected).

## Acceptance criteria

This problem is considered **fully solved** if we produce one of:

- **(A) Exact value = 133.** An explicit 16x17 (or 17x16) 0/1 matrix with
  exactly 133 ones and no `K_{3,3}` submatrix, verified by a checker that is
  implemented and tested independently of whatever process generated the
  matrix (see "Independent verification" below).
- **(B) Exact value = 132.** A machine-checkable proof that no such
  133-edge graph exists (e.g. a SAT UNSAT result with an independently
  verified proof certificate), *combined with* an independently
  re-verified 132-edge witness (we re-derive/re-check the known
  construction ourselves rather than citing it).

If full resolution is not reached within the working budget, this problem
is considered to have received **substantial, real progress** if we deliver
at least one of:

- **(C)** An independently-verified, from-scratch certificate for the
  currently-published (but explicitly uncertified) upper bound
  `Z(16,17,3,3) <= 133` — i.e. we turn "relies on prior published work"
  into an independently reproduced result, with our own proof/search code
  and our own checker.
- **(D)** A new exact value or a strictly tightened bound for a genuinely
  different `(m,n)` slice near this frontier that is open after our fresh
  literature check, independently verified to the same standard as (A)/(B).
- **(E)** A precisely stated, rigorously justified negative result — e.g. a
  specific, clearly-described construction family provably cannot reach
  133 edges — with independent verification and a clear account of what
  was tried and ruled out (including dead ends).

**Not acceptable, under any circumstance:** unverified numeric claims,
results that rely on an external paper's own unverified assertion instead
of our own re-derivation, floating-point or heuristic "near-miss" results
without exact combinatorial certification, or a claimed result where the
checker and the generator/solver share code or an author bias that could
hide a shared bug. Every claimed result must be reproducible by someone
who trusts nothing except the checker script and its test suite.

## Plan

1. **Re-verify the literature state.** Confirm `Z(16,17,3,3)` is still open
   as of today and catalog nearby untested `(m,n)` slices as fallback
   targets, before committing significant compute to a possibly-already-closed
   gap.
2. **Build and stress-test independent verification tooling first.** A
   checker for "exactly N edges, no `K_{3,3}`" implemented via two
   independently-coded methods, validated against known positive and
   negative test cases, before it is trusted on the real target.
3. **Attack the upper-bound side.** Encode "does a 133-edge `K_{3,3}`-free
   16x17 bipartite graph exist?" as SAT with symmetry-breaking; run a solver
   to find either a witness or an UNSAT proof, independently checked.
4. **Attack the lower-bound / construction side in parallel.** Local
   search / simulated annealing / algebraic ansatze (finite-geometry
   incidence structures, difference sets) seeded independently of any
   published construction, hunting for a 133rd edge.
5. **Cross-verify and report.** Whichever side yields a candidate result,
   re-check it with the independent tooling from step 2 before writing it
   up; update this PR with the concrete claim, the evidence, and the
   reasoning trail (including abandoned approaches).
6. **Fall back deliberately if needed.** If the primary target isn't
   resolved within budget, deliver one of the substantial-progress
   criteria (C)-(E) rather than leaving an inconclusive PR.

## Working discipline

This applies to every step of the work, not just the final write-up. It
governs how approaches are attempted, logged, and reported — by the
orchestrating session and by any subagent delegated a piece of this work.

- **Try to break it before extending it.** Before building on any claim,
  actively search for small counterexamples and check degenerate/boundary
  cases first, rather than assuming a promising-looking argument holds.
- **State lemma hypotheses precisely and confirm them here.** Never invoke
  a result (a SAT solver's correctness, a symmetry/automorphism argument,
  a combinatorial identity, a paper's claimed construction) without stating
  exactly what it requires and checking that it actually holds in this
  instance.
- **Interrogate helper lemmas.** When a helper lemma or reformulation is
  introduced to isolate the hard part, honestly assess whether it is
  actually easier than the original problem, or just a restatement of the
  same difficulty under a new name.
- **No citation without certainty.** Never cite a theorem, paper, or named
  result unless it can be stated precisely and its existence is certain.
  If unsure, say so explicitly in the log and mark it an unverified
  assumption rather than asserting it.
- **Ground the riskiest step in something checkable.** A computation, a
  small-case exhaustive search, or the independent checker decides whether
  to proceed — not the stated confidence of whoever produced the step.
- **Keep the running log current, and read it before starting a new
  approach.** `PROGRESS.md` records every approach tried, including
  abandoned ones and why, specifically so dead ends aren't silently
  repeated and promising leads aren't lost.
- **Rotate strategy after each attempt.** After each attempt, deliberately
  choose one of: refine the current best approach, recombine ideas from
  two earlier attempts, or try a genuinely different strategy from a
  different area of math. Don't just keep pushing on one line of attack.
- **Report calibrated confidence, split by step.** Any claimed result
  needs an overall confidence score *and* a separate score for its single
  weakest step. If the two diverge significantly, explain why — that gap
  is itself information about where the risk actually lives.

## Independent verification

The checker(s) used to certify any claimed result live in
`verify/` and are developed and tested *before* they are relied upon for
the real target, against small hand-built or literature-cited cases whose
answer is already known. The search/generation code lives in `search/`.
No single script is allowed to both generate and certify a result.

## Progress log

See `PROGRESS.md` for a running, dated log of what was tried, what worked,
what didn't, and why.
