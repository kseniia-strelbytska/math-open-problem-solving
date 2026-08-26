# SAT attack log

Companion log to `PROGRESS.md`, scoped to the SAT-encoding attack on
`Z(16,17,3,3)` (`search/sat_encoding.py`, `search/test_sat_encoding.py`,
`search/sat_attack.py`). Follows the same working-discipline template as
`PROGRESS.md`: what was tried, what was checked to try to break it,
outcome, calibrated confidence. The orchestrating session integrates the
bottom line here into `PROGRESS.md`/`README.md` -- this file is not
touched by that integration step.

Environment: `.venv` (Python 3.14), `python-sat` with `Cadical153`,
`Glucose3`, `Minisat22` solvers available. 8 logical CPUs.

---

## Step 1 -- Validating the symmetry-breaking gadget (the missing piece)

`search/sat_encoding.py`'s module docstring is explicit that its own
soundness argument for the "double lex" symmetry-breaking clauses
(`symmetry_breaking_clauses` / `lex_ge_clauses`) has a gap in the informal
part of the argument, and that the actual load-bearing justification is
meant to be an exhaustive empirical check that adding both row- and
column-ordering clauses never flips SAT to UNSAT relative to the
unconstrained instance. That check did not exist yet (crashed before it
was written) -- writing and running it was step 1, before trusting the
encoding on anything real.

Wrote `search/test_sat_encoding.py` with two independent checks:

### 1a. `test_lex_ge_gadget` -- the gadget in total isolation

For bit-lengths 2, 3, 4: built a CNF containing *only* the
`lex_ge_clauses(a_lits, b_lits, ...)` output, no other constraints, over
free literals `a_lits`/`b_lits`. For **every** possible bit assignment of
`a` and `b` (full enumeration: `2^n * 2^n` pairs -- 16, 64, 256 pairs for
n=2,3,4, all fully enumerated, not sampled), fixed those literals via SAT
assumptions and checked the gadget's satisfiability against
`_lex_ge_python(a_bits, b_bits)`, a from-scratch plain-Python scan for the
first differing bit (index 0 = MSB), sharing zero code with
`lex_ge_clauses`.

- Lemma under test, stated precisely: the gadget (an "equal-so-far"
  auxiliary chain, Tseitin-transformed) is satisfiable for a given fixed
  `(a_bits, b_bits)` iff `a_bits >=_lex b_bits`.
- Result: **all 16 + 64 + 256 = 336 pairs agree**, across all three bit
  lengths, with zero disagreements. Solver used: Cadical153.
- What would have broken it: any single one of the 336 pairs disagreeing
  (either a spurious UNSAT on a legitimately-`>=`-lex pair, i.e. the
  "silent-UNSAT" failure mode the module docstring explicitly names as
  the risk of getting the completeness direction of the Tseitin
  transform wrong; or a spurious SAT on a pair that should be `<_lex`,
  i.e. a soundness bug). Neither occurred.

### 1b. `test_symmetry_breaking_preserves_sat_status_{tiny,larger}` -- the full pipeline

For 6 small `(m, n)` shapes -- `(3,3), (3,4), (3,5), (4,4)` (tiny: `m*n <=
16`) and `(4,5), (5,5)` (larger) -- solved `build_instance(m, n, K, ...)`
both with `symmetry_breaking=True` and `symmetry_breaking=False`, across
several `K` values per shape spanning sparse / near-boundary / full-board
(`m*n`), and confirmed SAT/UNSAT agreement.

For the 4 tiny shapes, agreement was checked against an actual
**brute-force ground truth**: full enumeration of all `2^(m*n)` possible
0/1 matrices (`_brute_force_max_k33_free`, a from-scratch K_{3,3} check
sharing no code with `sat_encoding.py` or `verify/checker.py`), using the
fact that the set of achievable K33-free edge counts is downward-closed
(removing an edge from a K33-free graph cannot create a K33), so "does a
K-edge K33-free matrix exist" reduces to "K <= brute-force max". This
means the tiny-case tests incidentally also re-validate the K33-freeness
clauses themselves at these sizes, not just symmetry breaking.

For the 2 larger shapes (`m*n` up to 25, too slow to fully enumerate),
only WITH-vs-WITHOUT solver agreement was checked (no independent ground
truth), across K in `{0, 1, 0.4*mn, 0.6*mn, mn-1, mn}`.

Every SAT verdict produced (in every case, both configurations) was
additionally decoded via `model_to_matrix` and re-verified with the real,
independent `verify/checker.py` (`checker.verify(matrix,
expected_edges=K)`) -- never trusted directly from the SAT model.

- Result: **all cases agree**, no disagreement between `symmetry_breaking
  = True` and `False` (nor, where available, with brute-force ground
  truth) in any of the tested `(m, n, K)` combinations. All decoded SAT
  witnesses passed `checker.verify` with the expected edge count and
  `is_k33_free=True`.
- Full suite run time: ~1.2s (`pytest search/test_sat_encoding.py -v`),
  3/3 passed. Also run standalone (`python search/test_sat_encoding.py`)
  with identical result.

**Outcome of step 1: promising, symmetry breaking is trusted going
forward.** No counterexample found despite deliberately probing boundary
cases (K at/near the brute-force max, and the full board) where a
symmetry-breaking bug would be most likely to bite (dense, highly
constrained instances are exactly where an over-strong or unsound
ordering constraint would first eliminate a real witness).

**Honest limitation, named explicitly:** this is empirical validation on
small cases (`m, n <= 5`), not a machine-checked proof that the gadget is
sound at `m=16, n=17` or `m=13, n=18`. The module docstring's own
"cleaner argument" for why double-lex symmetry breaking should be sound
in general is still informal (it motivates *why* we'd expect this to
hold, it does not itself certify it). What we have is: (a) the informal
argument, (b) zero counterexamples across 336 isolated-gadget checks and
dozens of full-pipeline small-case checks including boundary/dense cases.
This is the same standard applied elsewhere in this project (e.g.
`verify/checker.py`'s reliance on a 4th independent ground truth in
tests) -- strong support, not a formal certificate. Step 2 (a known-value
cross-check at a size closer to the real target) is the next, stronger
piece of evidence.

Confidence: symmetry-breaking soundness overall **90%**; weakest
sub-step: **80%**, the fact that validation is only at `m,n <= 5` and
does not scale-test the specific structural regime (13x18, 16x17) where
it will actually be relied on for an UNSAT certificate -- step 2 directly
addresses this gap.

---

## Step 2 -- Pipeline validation against a known exact value: Z(13,18,3,3) = 116

Wrote `search/sat_attack.py`, a thin runner around `sat_encoding.build_instance`
that logs instance stats before solving (so a kill mid-solve is
distinguishable from never starting), solves, and -- if SAT -- immediately
re-verifies the decoded witness with `verify/checker.py` before reporting
`checker_verified`. Self-tested on a trivial `3x3, K=8` instance first
(SAT, checker-verified, sub-second) before trusting it on anything real.

### 2a. Confirm SAT at K=116 for 13x18

- **Independent structural check (not the SAT solver at all), done first:**
  took the actual literature-derived `z13_18_116_witness.csv` and
  iteratively row-sorted then column-sorted it. It **converged after a
  single iteration** to a matrix that is simultaneously row-lex-sorted
  AND column-lex-sorted (a genuine fixed point of both sorts at once --
  not something guaranteed by the informal "sort rows then columns"
  argument in `sat_encoding.py`'s docstring, which explicitly flags that
  column-sorting could in general disturb row order). Re-checked with
  `checker.verify`: still exactly 116 edges, still K_{3,3}-free. This is
  a concrete, checkable existence proof that a double-lex-sorted 116-edge
  witness genuinely exists at this real instance size -- i.e. the
  symmetry-breaking clauses cannot be eliminating every witness here,
  independent of whether a solver can find one quickly. Strong additional
  evidence for soundness at scale, beyond the m,n<=5 tests in step 1.
- **`symmetry_breaking=False`, Cadical153:** SAT in **213.4s**
  (28018 vars unset -- actually 27610 vars, 288128 clauses without the
  symmetry clauses). Decoded witness independently checker-verified:
  116 edges, `is_k33_free=True`. **Step 2a's core requirement (a K=116
  witness, independently checker-verified) is satisfied.**
- **`symmetry_breaking=True`, same instance:** did **not** finish inside
  any of three separate attempts, each run to a hard stop after 10-22+
  CPU-minutes with no result:
  - Cadical153, `seqcounter` cardinality encoding (the default): killed
    after **~34 minutes** wall clock (two separate launches, ~22 min then
    ~9 min more) with no verdict.
  - Glucose3, `seqcounter`: killed after **~9 min** with no verdict
    (run in parallel with the Cadical retry above, same wall-clock
    window).
  - Cadical153, `totalizer` cardinality encoding (tried specifically to
    check whether the slowdown was a seqcounter-specific interaction
    with the double-lex chains): killed after **~8 min** with no verdict.
  - Total: 3 different (solver, cardinality-encoding) combinations, all
    with `symmetry_breaking=True`, none completed within reasonable
    budgets, versus the plain (no symmetry breaking) instance solving in
    3.5 minutes. This rules out "it's just the seqcounter encoding" as
    the explanation -- the slowdown tracks `symmetry_breaking=True`
    specifically, not a particular cardinality encoding or solver.

**Interpretation, stated carefully:** this is a *performance* finding,
not a soundness finding. Step 1 (isolated gadget check + full small-case
agreement check, all passing) and the double-lex-sort convergence check
above are both still valid evidence that the symmetry-breaking clauses do
not change the SAT/UNSAT status of an instance. What this shows instead
is that, at the 13x18 scale, adding the double-lex ordering clauses on
top of a tight "exactly K" cardinality constraint appears to make CDCL
search *dramatically harder* in practice for both solvers tried --
plausibly because the ordering chains interact badly with the cardinality
encoding's own propagation structure and/or the solvers' variable-ordering
heuristics, a known failure mode for symmetry-breaking constraints in the
SAT/CP literature (added constraints can prune the search *space* while
still making the *search* slower, if they don't align with how the solver
explores). This was not anticipated going in and is a genuine, honestly-
reported dead end for "always turn symmetry breaking on."

**Consequence for strategy (rotation, per working discipline):** proceed
with `symmetry_breaking=False` as the primary configuration for both the
K=117 UNSAT attempt below and the real target in step 3. This is still a
fully sound choice for an UNSAT *proof* specifically: an UNSAT verdict
from the plain (K33-freeness + exactly-K cardinality, no symmetry
clauses) CNF is already a complete, self-contained proof of
non-existence on its own terms -- it does not depend on the
symmetry-breaking soundness argument at all, since that argument is only
needed when symmetry clauses are actually added to the instance being
solved. Symmetry breaking was only ever meant to be a *speed*
optimization (by pruning symmetric duplicates from the search space); it
is not required for either a SAT witness or an UNSAT proof to be valid.
Given it measurably hurt speed here rather than helping, dropping it for
the harder downstream attempts is the right call, not a compromise on
rigor.

### 2b. Attempt UNSAT at K=117 for 13x18

Given the finding above, ran two attempts **in parallel**, both Cadical153:
`symmetry_breaking=False` (primary, since it's the configuration that
actually worked in 2a) and `symmetry_breaking=True` (kept as a secondary
attempt in case UNSAT-proving behaves differently from SAT-finding).

- **Result: TIMEOUT, both configurations.** Killed after **~30 minutes**
  wall clock (~28 CPU-minutes each, both pegged at ~100% CPU the whole
  time, i.e. actively searching, not stuck/hung) with no SAT/UNSAT
  verdict from either. This is a few minutes over the ~20-25 minute
  budget given for this step; extended slightly to get one more clean
  data point before stopping, per "report honestly rather than abandon
  silently."
- Neither run produced a partial verdict of any kind -- Cadical153 (like
  most modern CDCL solvers) does not expose incremental progress short of
  a final SAT/UNSAT answer via the plain `solve()` API used here, so
  "still running" is the only information available mid-search.
- **Honest read of this result:** proving UNSAT at K=117 for a 13x18
  instance (27610-28018 vars, ~288-291k clauses, most of them 9-literal
  K33-freeness clauses) is harder than the ~3.5-minute SAT search at
  K=116 -- expected in general (UNSAT proofs require exhausting/pruning
  the whole relevant search space, not just finding one witness), but the
  degree of difficulty here (>28 CPU-minutes with no result, on a cell
  small enough that its exact value is independently known and confirmed)
  is itself important calibration data for what to expect at the real
  16x17 target in step 3, which is a strictly larger and harder instance
  along every relevant axis (more rows/columns, more K33 clauses --
  `C(16,3)*C(17,3) = 560*680 = 380800` vs `C(13,3)*C(18,3) = 286*816 =
  233376` here).
- This does **not** retroactively undermine step 2a: the K=116 SAT
  witness (no symmetry breaking) is still a fully valid, independently
  checker-verified confirmation that the known exact value is achievable,
  which is what step 2a asked for. Step 2b was an *additional*, harder
  ask (an independent re-proof of optimality) and its timeout is reported
  as exactly that -- a timeout, not a failure of the pipeline's
  correctness, and not evidence one way or the other about whether 117
  edges are achievable at 13x18 (we simply don't know, from this run).

---

## Step 3 -- The real target: Z(16,17,3,3), K=133

(filled in below as runs complete)

---

## Bottom line

(filled in at the end)
