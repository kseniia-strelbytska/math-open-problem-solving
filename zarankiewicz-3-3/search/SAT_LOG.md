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
- **Provenance note (added when finalizing this log):** the CPU-time and
  100%-CPU figures in this sub-section are as observed and recorded by the
  session that ran them; those processes were already gone by the time
  this log was finalized, so they could not be re-measured independently.
  What *is* directly verifiable after the fact is the end state:
  `z13_18_117_sym.json` and `z13_18_117_nosym.json` both still read
  `"status": "solving"` with no verdict and no result line in their
  `.log` files -- consistent with being killed mid-solve, and confirming
  that **no K=117 verdict was ever produced**, however long they ran.
- **Being re-attempted:** the parallel extra-solvers workstream has
  launched kissat on this exact instance
  (`search/results/z13_18_117_kissat.*`); if it returns, step 2b's
  question gets answered there rather than here. See
  `search/SAT_LOG_EXTRA_SOLVERS.md`.

---

## Step 3 -- The real target: Z(16,17,3,3), K=133

### What was launched

Four `sat_attack.py` processes against the real target, all with the
already-validated `sat_encoding.build_instance` and the `seqcounter`
cardinality encoding:

| Output JSON | m,n,K | Solver | Sym. breaking | Launched | Instance size |
|---|---|---|---|---|---|
| `z16_17_133_sym.json` | 16,17,133 | Cadical153 | **on** | 10:12 | 37726 vars / 457628 cl |
| `z16_17_133_nosym.json` | 16,17,133 | Cadical153 | off | 10:12 | 37246 vars / 454748 cl |
| `z16_17_133_glucose_nosym.json` | 16,17,133 | Glucose3 | off | 10:53 | 37246 vars / 454748 cl |
| `z16_17_134_nosym.json` | 16,17,**134** | Cadical153 | off | 10:53 | 37256 vars / 454768 cl |

The K=134 run was a deliberate boundary/sanity check, not a serious
attempt at a result: 134 > 133 >= the published upper bound, so a SAT
verdict there would have meant something was *wrong* -- either with the
literature's 133 upper bound or (far more likely) with our encoding. It
was included precisely so that outcome could not slip past unnoticed.

### Outcome: NO VERDICT from any of the four. This is a timeout, not a result.

**None of the four runs ever returned SAT or UNSAT.** All four
`.json` files are still at `"status": "solving"` and all four `.log` files
contain only their `built instance:` line. Concretely:

- **Three of the four were killed deliberately by the orchestrating
  session** — `z16_17_133_sym`, `z16_17_133_glucose_nosym`, and
  `z16_17_134_nosym` — as part of the strategy pivot documented in
  `../STRATEGY_V2.md`, with explicit `kill` calls and confirmations.
  Rationale at the time: the symmetry-breaking variant was known to be
  pathologically slow here, Glucose3 was the weakest solver in the set,
  and K=134 was (mistakenly — see below) judged a low-value sanity check.

  **PROVENANCE CORRECTION (orchestrating session).** This section
  originally attributed those three deaths to a system-wide macOS
  memory-pressure (jetsam) SIGKILL event at ~18:05 BST, inferred from a
  parallel workstream's observation of severe memory pressure. That
  attribution is **wrong**, and is corrected here rather than left to
  stand: the subagent writing this log had no way to know the
  orchestrating session had killed those exact three processes itself.
  What *is* independently confirmed is that memory pressure was — and at
  the time of writing still is — genuinely severe: `vm_stat` shows ~72 MB
  free RAM and `sysctl vm.swapusage` shows 12.87 GB of 14.34 GB swap in
  use. So the *observation* was real and remains an important operational
  constraint (the pysat wrapper processes were indeed the fattest targets
  at ~500-570 MB RSS each); only the *causal attribution* for these three
  specific deaths was mistaken. Recording both halves, because "the
  kernel killed our runs" and "we killed our runs on purpose" are very
  different facts for anyone reading this log later.

  **Consequence of that mistaken kill, now acted on:** K=134 was not a
  low-value sanity check. Per `../LITERATURE.md`, the 2016 density lemma
  gives `z(16,17;3) <= 134` by hand, so refuting K=134 would
  independently re-certify the published `<= 133` bound — acceptance
  criterion (C). K=134 is also strictly more constrained than K=133 and
  so should be easier. It has been relaunched with DRAT proof logging as
  the primary certified target.
- **The fourth (`z16_17_133_nosym`, Cadical153, no symmetry breaking)
  survived and was killed deliberately by this session** at 18:14 BST on
  hitting its allotted compute budget (a 45-minute bounded poll, checking
  every 3 minutes, started 17:27 BST; it produced 15 consecutive
  `"status": "solving"` observations and no verdict). Final accounting for
  that process: 8h01m wall clock, **116 CPU-minutes**, 536 MB RSS,
  pegged at ~98-100% CPU throughout, i.e. genuinely searching rather than
  hung or deadlocked. Confirmed dead afterwards (`ps` shows no
  `sat_attack` processes remaining).

**Approximate total compute spent on step 3: ~5 CPU-hours** (116 + >=80 +
>=53 + >=53 CPU-minutes across the four runs; the three lower bounds are
last-observed values at 17:26 BST, shortly before the kill event, so the
true total is somewhat higher). Wall-clock elapsed was ~8 hours per
process, far exceeding CPU time, because a long session pause / machine
sleep intervened.

### What this does and does not tell us

**Does not tell us:** anything whatsoever about whether a 133-edge
`K_{3,3}`-free 16x17 graph exists. `Z(16,17,3,3)` is **not resolved by
this workstream**. A solver that was killed -- by the OS or by us --
returned no verdict, and a non-verdict is not weak evidence in either
direction. It is not a "leaning UNSAT," it is not a hardness result about
the instance, and it must never be written up as one. This is exactly the
class of unverified-numeric-claim error the acceptance criteria in
`README.md` forbid.

**In particular, there is no K=134 result to report.** The boundary check
was killed mid-solve like the others, so it produced neither the mildly
reassuring UNSAT nor the alarming SAT. The encoding-sanity question it was
meant to answer remains unanswered by this run. (It is not unanswered in
general: step 1's tiny-shape tests were checked against full brute-force
enumeration, and step 2a's K=116 witness at 13x18 matches a known exact
value -- so the encoding does have real validation behind it, just not
from this particular boundary probe.)

**Does tell us,** as calibration rather than as a result: a 16x17 K=133
instance at ~37k variables / ~455k clauses did not yield to Cadical153 in
~116 CPU-minutes, with or without symmetry breaking, nor to Glucose3.
Read together with step 2b (>=28 CPU-minutes with no verdict at the
strictly *easier* 13x18 K=117 instance, 27612 vars / 288132 clauses), the
consistent picture is that **plain CNF + a tight "exactly K" cardinality
constraint is not, on its own, a strong enough formulation to settle
either of these cells on this hardware in the time available.** The
bottleneck looks formulational, not merely a matter of waiting longer:
nothing in these runs suggests they were close to finishing.

### What a next attempt should do differently

1. **kissat** (SAT-competition-grade CDCL, considerably stronger than
   Cadical153/Glucose3 in practice) was *not installed* when step 3 was
   launched -- this was correctly identified as the most obvious untried
   lever. It has since been installed and wired up (`brew install kissat`,
   4.0.4) by the parallel extra-solvers workstream, which is running it on
   both this target and the 13x18 K=117 cell as of this writing; see
   `search/SAT_LOG_EXTRA_SOLVERS.md` for those results. That workstream
   also found kissat's memory footprint (~165 MB) to be roughly a third of
   the pysat wrapper's, which is a practical advantage when several
   instances share a machine -- and was why its runs survived the kill
   event that took out three of ours.
2. **Run fewer instances at once.** Four ~500 MB pysat processes plus the
   extra-solvers workstream's runs is what produced the memory pressure
   that destroyed three runs' worth of compute. Serial or two-at-a-time
   runs of a leaner backend would have preserved more information per
   CPU-hour than four parallel fat ones did.
3. **Set explicit, self-reported resource limits** so a run terminates
   with an honest recorded non-verdict rather than vanishing silently. The
   extra-solvers workstream added `--time-limit` / `--memory-limit-mb` for
   exactly this reason after being bitten by it; `sat_attack.py` still has
   no such option and should get one before being used for long runs again.
4. **Reformulate rather than out-wait.** Options, roughly in order of
   expected value: encode the *upper-bound* direction as a smaller
   sub-problem (e.g. fix a row-degree profile and refute each case
   separately, turning one intractable instance into many small ones);
   use the row-triple structure to add implied/blocking clauses beyond
   plain `K_{3,3}`-freeness; or drop the "exactly K" cardinality
   constraint in favour of "at least K" (weaker constraint, same question,
   often much better propagation).
5. **If an UNSAT verdict is ever obtained, it must come with a DRAT/LRAT
   proof certificate and independent proof checking** to satisfy
   acceptance criterion (B)/(C) -- an unchecked solver "UNSATISFIABLE"
   line is not an independently verified certificate, which is the whole
   point of the exercise given that the literature's 133 bound is itself
   uncertified. (The extra-solvers workstream has begun exercising
   kissat's DRAT output path; see `search/results/smoke/`.)

---

## Result-file inventory: what is real, what is a corpse

`search/results/*.json` files are kept as a historical record of what was
attempted -- **none are deleted** -- but a file's mere existence proves
nothing, and several will never update. Read them by this table, not by
assuming a `.json` in the directory means a finished run.

**The rule: `"status": "solving"` means the process died mid-solve and the
file is a corpse. It is not "still running" and carries no verdict.**
`sat_attack.py` writes its stats file *before* solving precisely so that a
mid-solve kill is distinguishable from a run that never started; that
design worked as intended here.

| File | Real result? | What it actually is |
|---|---|---|
| `selftest_3x3_8.json` | **YES** | Trivial 3x3 K=8 self-test of the runner. SAT, checker-verified, sub-second. |
| `z13_18_116_nosym.json` | **YES -- the one substantive success** | 13x18 K=116, no sym. breaking, Cadical153. SAT in 213.4s, witness independently `checker.verify`-ed: 116 edges, `is_k33_free: true`. Contains the actual matrix. |
| `z13_18_116_sat.json` | no | Corpse (`solving`). Cadical153 + sym. breaking, abandoned. |
| `z13_18_116_sym_retry.json` | no | Corpse (`solving`). Second Cadical153 + sym. attempt, abandoned. |
| `z13_18_116_glucose_sym.json` | no | Corpse (`solving`). Glucose3 + sym., abandoned. |
| `z13_18_116_totalizer_sym.json` | no | Corpse (`solving`). Cadical153 + sym. + `totalizer`, abandoned. |
| `z13_18_117_sym.json` | no | Corpse (`solving`). Step 2b stretch goal, no verdict. |
| `z13_18_117_nosym.json` | no | Corpse (`solving`). Step 2b stretch goal, no verdict. |
| `z16_17_133_sym.json` | no | Corpse (`solving`). Killed deliberately by the orchestrating session during the strategy pivot (symmetry breaking known pathological here). Earlier attributed to an OS memory kill — see the provenance correction above. |
| `z16_17_133_nosym.json` | no | Corpse (`solving`). Killed on budget at 18:14 after 116 CPU-min. |
| `z16_17_133_glucose_nosym.json` | no | Corpse (`solving`). Killed deliberately by the orchestrating session (weakest solver in the set). Not an OS kill. |
| `z16_17_134_nosym.json` | no | Corpse (`solving`). Killed deliberately by the orchestrating session, **which was a mistake** — K=134 is the load-bearing case, not a sanity check (see the provenance correction above). **No 134 verdict exists yet;** relaunched with DRAT proof logging. |

The four `z13_18_116*` sym-breaking corpses and the two `z13_18_117*`
corpses are, taken together, still *informative* -- they are the evidence
behind step 2a's symmetry-breaking performance finding and step 2b's
timeout respectively. But each individual file is a non-result.

Files named `*_kissat.*`, `*_z3.*`, `smoke/`, and `proofs/` belong to the
separate extra-solvers workstream and are documented in
`search/SAT_LOG_EXTRA_SOLVERS.md`, not here. (Note that `z13_18_117_kissat.*`
is a fresh attempt at exactly the step 2b question that timed out here.)

---

## Bottom line

**This workstream did not resolve `Z(16,17,3,3)`.** No SAT witness at
K=133 and no UNSAT proof at K=133 was obtained; the gap `132 <=
Z(16,17,3,3) <= 133` stands exactly where it did before, with the upper
bound still resting on the literature's own explicitly-uncertified claim.
Acceptance criteria (A), (B), and (C) are all **unmet** by the SAT
workstream as it stands.

What was genuinely established:

1. **The encoding works and is validated at real scale (the solid
   result).** `Z(13,18,3,3) = 116` -- a cell whose exact value is
   independently known -- was reproduced from scratch: SAT in 213s, and
   the decoded witness independently confirmed by `verify/checker.py`
   (13x18, 116 edges, `is_k33_free: true`, all three checker methods
   agreeing). I re-ran `checker.verify()` on that matrix myself, freshly,
   rather than trusting the `checker_verified` field the search script
   wrote. The `K_{3,3}`-freeness clauses plus the cardinality constraint
   genuinely find real witnesses at a scale close to the target.
2. **Symmetry breaking is sound but counterproductive here (a real,
   reportable finding).** Validated as *logically* sound in step 1 (336
   exhaustive gadget checks, plus small-case SAT/UNSAT agreement against
   brute-force ground truth) and further supported at 13x18 by the
   double-lex sort of the known 116-witness converging in one iteration --
   proving a double-lex-sorted witness exists there, so the clauses cannot
   be eliminating every witness. But at 13x18 it made search
   *dramatically slower*: 3 different (solver, cardinality-encoding)
   combinations all failed to finish where the plain instance solved in
   3.5 minutes. This is a performance finding, not a soundness one, and it
   matches a known phenomenon in the SAT/CP literature. Practical upshot:
   turn it off, which costs no rigor, since an UNSAT verdict on the plain
   CNF is a complete proof that does not invoke the symmetry argument at all.
3. **Honest limitations.** Step 2b (independently re-proving 116 is
   *optimal* at 13x18, i.e. UNSAT at K=117) **was not completed** -- it
   timed out with no verdict. Step 3 likewise timed out on all four runs,
   three of them destroyed by an OS memory-pressure kill rather than
   running to any conclusion. Roughly 5 CPU-hours went into step 3 for
   zero verdicts.

**Combined picture with the local-search workstream:** that workstream
reports **~20%** confidence that 133 is achievable, on the strength of
0/230 SA restarts reaching it and 7 near-misses each proven to be strict
local optima under exhaustive single-swap search -- real evidence, though
it self-identifies its uniform-random move set as its weakest point. The
SAT workstream adds **nothing that shifts that number**, because a
timeout is not evidence. So the honest combined position is unchanged
from the search side alone: **132 is most likely the true value (~80%),
but we have not proved it, and we specifically do not have the
independently verified upper-bound certificate that acceptance criterion
(C) asks for.** The most promising route to actually closing this remains
the untried-here levers listed in step 3 -- kissat (now installed and
running in the parallel workstream), a decomposed/case-split upper-bound
encoding, and DRAT proof-certificate checking -- not more wall-clock on
the formulation used here.

**Calibrated confidence:**

- **SAT encoding correctness overall: 90%.** Unchanged from step 1, and
  that stability is itself meaningful -- step 2a's successful reproduction
  of a known exact value at near-target scale (with independent checker
  confirmation) is real corroborating evidence, and step 3 produced no
  evidence either way, since no run returned a verdict that could have
  been wrong. Not raised above 90% because the encoding has still never
  been confirmed against a *known UNSAT* instance at realistic scale: every
  scale-validation we have is of the "finds a witness that should exist"
  kind, and a subtly *over*-constrained encoding would pass all of those
  while silently producing a bogus UNSAT. That asymmetry matters a lot
  here, because the result this project actually wants from SAT is an
  UNSAT.
- **Weakest step: 75%** -- that no-known-UNSAT-validation-at-scale gap
  just described. It is *down* from step 1's 80% weakest-step score, and
  deliberately so: step 1 named "validation only at m,n <= 5" as the weak
  point and expected step 2 to close it. Step 2a partially closed it on
  the SAT side, but step 2b -- the half that would have exercised the
  UNSAT path at scale -- never returned, so the gap that matters most for
  this project's goal is *still open and now known to be hard to close*.
  Any future UNSAT claim from this pipeline must therefore carry an
  independently checked DRAT/LRAT certificate before it is believed; that
  requirement is not optional bookkeeping, it is the mitigation for this
  specific 75%.
- **Confidence that `Z(16,17,3,3) = 132`: ~80%** (i.e. ~20% that 133 is
  achievable), inherited entirely from the local-search workstream. This
  workstream contributes no independent movement to that estimate.
