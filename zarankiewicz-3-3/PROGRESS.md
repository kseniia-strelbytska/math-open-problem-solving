# Progress log

Dated, honest log of what was tried, what worked, what didn't, and why.
Negative results and abandoned approaches are kept here, not deleted —
they're part of the evidence trail for the reviewer and for anyone picking
this up later. Follow the working discipline in `README.md` — in
particular, check this log before starting a new approach so a dead end
isn't silently repeated.

### Entry template for any attempted approach

```
### <date> — <approach name>

- What it is / what it's trying to establish.
- Lemmas or results invoked, with exact hypotheses, and confirmation each
  hypothesis actually holds here (or an explicit "unverified assumption"
  flag if it doesn't hold or can't be checked).
- What was checked to try to break it (small cases, boundary cases,
  counterexample search) before trusting it further.
- Outcome: refined / recombined-with-<X> / abandoned / promising, pending.
- Confidence: overall __%, weakest step (name it) __%. If these diverge,
  say why.
- Next rotation: refine this / recombine with <earlier attempt> / try a
  genuinely different strategy (name the area).
```

## 2026-08-25

- Selected `Z(16,17,3,3)` as the primary target after a broader survey of
  open math problems (see repo history / PR description for the survey).
  Known bounds at selection time: `132 <= Z(16,17,3,3) <= 133`
  (arXiv:2608.08154, Aug 2026; upper bound explicitly flagged by its own
  authors as not independently verified).
- Wrote acceptance criteria and plan (`README.md`) before writing any
  search or verification code.
- Local environment check: Python 3.14 available, `z3` installed via
  Homebrew, no SAT solver binaries (kissat/cadical/minisat/glucose) or
  Python packages (numpy, python-sat, networkx) installed yet — these are
  next steps, not assumptions.

### 2026-08-25 — independent verification checker (`verify/checker.py`)

- What it is: the trust anchor for every later claim. Answers "does this
  m x n 0/1 matrix have exactly N edges and no `K_{3,3}`?" via two
  independent edge-counters and three structurally different `K_{3,3}`
  detectors (row-triple intersection, the dual column-triple intersection
  on the transpose, and a `networkx`-graph-based check), all of which must
  agree or the checker raises loudly rather than picking a winner.
- Lemma actually being used, stated precisely: *for a fixed set of 3 rows,
  a `K_{3,3}` exists on those rows iff the number of columns equal to 1 in
  all three rows is >= 3* (any 3 of those columns complete the K_{3,3}).
  This is immediate from the definition of `K_{3,3}` as a complete
  bipartite subgraph, and it is exhaustive (checking all `C(m,3)` row
  triples finds every possible `K_{3,3}`, since every `K_{3,3}` has *some*
  3-row subset). No unverified assumption here — confirmed by hand for the
  test cases below, not just by construction.
- What was checked to try to break it: hand-verified positive/negative
  cases (`K_{3,3}` itself; `K_{3,3}` minus one edge; `K_{4,4}` minus a
  perfect matching, reasoned through by hand in the test file's comments;
  a `K_{3,3}` planted inside a larger all-zero matrix so surrounding
  structure can't hide or fake a detection); malformed-input cases
  (non-binary entries, missing `n_cols` for bitmask input) correctly
  rejected; 500 random trials at 16x17 and 8x9 across varying densities,
  each cross-checked against a **4th, fully independent** pure-Python
  ground-truth implementation that shares no code with the checker (used
  only in tests, never in the checker itself); confirmed the disagreement
  machinery itself isn't vacuous by monkeypatching one method to lie and
  checking `CheckerDisagreement` actually fires.
- I (orchestrating session) independently re-ran the full test suite
  myself (`pytest verify/test_checker.py -v`) rather than trusting the
  subagent's report — 13/13 passed.
- Honest limitation, named explicitly: Method 1 (row-triples) and Method 3
  (networkx) both enumerate row-triples and implement the *same*
  underlying lemma above, just via different data structures — so they
  are weaker as an independent pair against each other than either is
  against Method 2's genuinely dual (column-triple, transposed)
  traversal. If the lemma itself were wrong, all three internal methods
  would share that flaw, since they all rest on the same characterization
  of `K_{3,3}` existence. What actually protects against that is the 4th,
  conceptually-identical-but-code-independent pure-Python ground truth
  used only in the test suite — which is why that ground truth exists
  and is exercised on 500 random trials rather than treated as optional.
  Not yet cross-checked against an actual literature-cited witness matrix
  (the `check_against_known_exact_value` hook is a wired-but-unimplemented
  placeholder) — pending the literature-verification workstream.
- Outcome: promising, adopted as the project's verification tool.
- Confidence: overall 90%. Weakest step: the shared-lemma risk named
  above — call it 85% (mitigated, not eliminated, by the independent
  ground truth in tests; would rise once a real literature witness is
  cross-checked).
- Next rotation: recombine — once the literature-verification workstream
  returns a real witness matrix, use it to fill in
  `check_against_known_exact_value` and close the remaining gap named
  above, before trusting this checker on the real 16x17 target.
