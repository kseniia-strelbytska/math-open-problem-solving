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

(filled in below as runs complete)

---

## Step 3 -- The real target: Z(16,17,3,3), K=133

(filled in below as runs complete)

---

## Bottom line

(filled in at the end)
