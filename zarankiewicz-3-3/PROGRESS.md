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

### 2026-08-25 — literature re-verification: citation chain and witness data

- What it is: independently re-verify the sources behind the published
  `132 <= Z(16,17,3,3) <= 133` bounds. A subagent did the initial research
  pass; per the acceptance criteria ("never rely on an external paper's
  own unverified assertion") and the working discipline ("no citation
  without certainty"), I re-derived the load-bearing claims myself rather
  than trusting either the subagent's report or the papers' own prose.
- What was checked, and by what:
  - Confirmed `github.com/KAVentures/z1322-exact` is a real, public repo
    (GitHub API `repos/.../` and `git/trees/main?recursive=1`), and its
    file tree matches what was reported.
  - Downloaded `z16_17_132_witness_seed201.csv`/`.json` directly from
    GitHub's raw content (not the subagent's transcription of it, which
    was visibly garbled) and ran it through **our own**
    `verify/checker.py` from scratch: confirmed exactly 132 edges,
    genuinely `K_{3,3}`-free, all three internal methods agree.
  - Cross-checked five more witnesses from the same repo
    (`z13_18_116`, `z14_17_118`, `z14_18_124`, `z15_17_126`,
    `z15_18_132`) the same way — all independently confirmed. These
    overlap with the separately-authored Hou paper's (arXiv:2608.08549)
    claimed values, so this is cross-source corroboration, not just
    re-checking one paper's own numbers.
  - Traced the 133 upper bound to Collins, Riasanovsky, Wallace,
    Radziszowski, "Zarankiewicz Numbers and Bipartite Ramsey Numbers,"
    arXiv:1604.01257 (2016). Downloaded the actual PDF myself and
    extracted Table 4 with `pdftotext`: row `m=16` reads
    `... 128* 133 140` for `n = 16,17,18`, i.e. `z(16,17;3) = 133` in
    their table, unmarked (no `*`/`†` superscript).
  - Went one step past the subagent's "looks italic" claim: used
    `pdftohtml -xml` to read the **embedded font name** on that exact
    table cell, not just a visual impression. The "133" glyph is set in
    font `PJYSJE+CMTI10` (Computer Modern Text *Italic*), while
    neighboring undecorated entries (e.g. "140") use `CMR10` (roman) and
    bold-starred entries (e.g. "128*") use `CMBX10` (bold). The paper's
    own legend: *"An italicized entry indicates that the bound or value
    was determined with exhaustive computations. Otherwise, an
    undecorated number indicates the bound was obtained by using Lemmas
    2, 3 and 4... without exhaustive enumeration."* So 133 is confirmed
    (by typesetting, not just narrative) to be the 2016 authors'
    exhaustive-computation upper bound — not bold, so per their own
    convention not claimed exact, i.e. they never found a matching
    133-edge construction.
  - Found direct textual corroboration that the original authors
    themselves flagged this exact region as suspect: *"The interested
    reader may note other weak-looking bounds in Table 4, such as for
    z(k, 17; 3) for 13 <= k <= 17"* (p.12 of the PDF) — our target,
    k=16, falls inside that self-flagged range.
- Precise claim this licenses: *the 133 upper bound for Z(16,17,3,3) is a
  10-year-old, exhaustively-computed-but-uncertified result, with no
  known matching construction, on a cell the original authors themselves
  called weak-looking.* This is what makes acceptance criterion (C) a
  real, non-trivial target — reproducing or refuting a specific,
  identifiable, decade-old computer-search claim with no available
  certificate, not just re-citing a number.
- What could break this: the whole citation chain rests on trusting that
  a LaTeX author used italics consistently with their own stated legend.
  Mitigated (not eliminated) by the bold+asterisk pattern matching the
  plain-text `*` markers consistently across the row I inspected — but I
  did not audit every cell in the table by hand, only the target cell and
  its immediate neighbors.
- Did **not** independently fetch the Zenodo DOI (`10.5281/zenodo.21768210`)
  the subagent cited for the Hou paper's supplement — considered
  unnecessary, since re-deriving and re-checking the underlying witness
  matrices directly from GitHub with our own checker (done above) is
  strictly stronger evidence than validating a SHA-256 manifest would be.
  Flagged here rather than silently skipped, per the working discipline.
- Calibration note: arXiv:2608.08154 (the paper citing the 133 bound) has
  a wrong author name in its own reference list and self-discloses
  "OpenAI GPT 5.6 Sol High was used for assistance" — it's a non-peer-
  reviewed, small-author 2026 preprint. Treated as a pointer to real data
  (which checked out), not as an authority in itself.
- Outcome: both ends of the gap are now independently grounded — 132 is a
  real, checked, explicit witness; 133 is a real, traced, but genuinely
  never-certified bound. Promising; proceed to attacking the gap directly.
- Confidence: overall 92% that this is an accurate characterization of
  the current state of published knowledge on `Z(16,17,3,3)`. Weakest
  step: 80% — the font-name-based italic detection, cross-checked against
  neighboring cells but not audited across the full table.
- Next rotation: refine — attack the gap directly per plan steps 3/4: a
  constructive search for a 133rd edge (seeded from, but not copied from,
  the verified 132-edge witness), in parallel with a SAT encoding aimed
  at an UNSAT proof.

### 2026-08-25/26 — constructive/local-search attack: no 133-edge witness found

Full detail in `search/LOCAL_SEARCH_LOG.md`; summarized here.

- What it is: an independent (non-SAT) attack on "does a 133-edge
  K_{3,3}-free 16x17 graph exist?", via simulated annealing (seeded from
  the known 132-edge witness, and separately from scratch) plus a
  structurally-motivated algebraic construction attempt (circulant graphs
  from quadratic residues mod 17).
- Lemma relied on: the same row-triple-intersection K_{3,3} characterization
  `verify/checker.py` uses, reimplemented here as an *incremental* energy
  function (`search/zark_core.py`) for speed. Its incremental-vs-full
  consistency was checked continuously (every 4,000 SA iterations, and
  after every exhaustive-swap/reheat pass) across ~4M+ operations with
  zero disagreements — I independently re-ran its self-test myself before
  handing this off to a subagent, and the subagent re-ran it again
  independently before starting; both passed.
- What was checked to try to break the negative result, specifically: not
  just "SA didn't find one" — the 7 best near-misses found (each at 133
  edges, conflict energy 2 — genuinely K_{3,3}-containing, never
  `certify()`-ed as anything positive) were each subjected to an
  *exhaustive* (not sampled) single-swap search of their entire
  distance-1 neighborhood (18,487 pairs each) plus 100,000 further SA
  iterations across 5 reheat cycles. All 7 are strict local optima under
  both. This is meaningfully stronger than "a search didn't happen to
  find it."
- Outcome: 0/230 fresh SA restarts (150 seeded + 80 from-scratch) and 0/7
  refined near-misses reached 133 edges at zero conflict energy. The
  structural quadratic-residue-mod-17 construction is clean but caps out
  at 128 edges (below the known 132), and single-residue extensions of it
  fail catastrophically (energy 168-224) for an identifiable structural
  reason (vertex-transitivity replicates any violation across all 16
  rotations at once) — a real explanation, not just a failed tuning
  attempt. A back-of-envelope Kővári–Sós–Turán-style counting bound
  (`16*C(9,3)=1344 <= 2*C(17,3)=1360`) confirms this simple relaxation
  alone doesn't even rule out 144 edges, consistent with the literature's
  133 bound needing a finer case-based argument.
- Best certified candidate: 132 edges / energy 0 (the known witness,
  re-certified as a byproduct — not a new result).
- Confidence (this workstream's evidence only, before combining with the
  parallel SAT workstream): **~20%** that 133 is achievable. Named
  weakest point of the methodology: the SA move set was uniform random
  single-cell toggles throughout, never biased toward cells in currently
  violated triples despite the tooling for that existing
  (`conflict_triples()`), and multi-cell compound moves were only used as
  a one-off diagnostic on the 7 near-misses, not as a primary search
  driver — a genuinely different search design (conflict-biased or
  large-neighborhood search) is the most likely place a stronger attempt
  could still move this number in either direction.
- Next rotation: recombine with the SAT workstream's result (in
  progress, see below) — a search-side "no" plus a proof-side answer
  together are much stronger than either alone.

### 2026-08-25/26 — SAT attack, step 1: symmetry-breaking gadget validated

Full detail in `search/SAT_LOG.md`; summarized here. Steps 2 (known-value
validation) and 3 (the real target) are still running as of this entry —
see the next log entry for their outcome.

- What it is: before trusting a SAT-based UNSAT/witness search on the
  real target, validate the encoding itself — especially the
  symmetry-breaking ("double lex" row/column lexicographic ordering)
  clauses, whose own soundness argument (in `search/sat_encoding.py`'s
  module docstring) explicitly flagged a gap in its informal reasoning
  and named exhaustive empirical validation as the actual load-bearing
  justification.
- What was checked: (1a) the lex-order gadget in total isolation, fully
  enumerated (not sampled) against an independent from-scratch Python
  implementation across 336 bit-pairs (bit-lengths 2/3/4) — zero
  disagreements. (1b) the full pipeline on 6 small shapes, WITH vs.
  WITHOUT symmetry breaking, including 4 tiny shapes checked against a
  true brute-force ground truth (full `2^(mn)` enumeration) — zero
  disagreements, and every SAT witness produced was independently
  re-verified with `verify/checker.py`, never trusted from the solver
  model directly.
- I independently re-ran this validation suite myself
  (`pytest search/test_sat_encoding.py -v`) rather than trusting the
  report: 3/3 passed.
- Outcome: promising, symmetry breaking is trusted going forward.
- Confidence: overall 90%; weakest step 80% — validation is only at
  `m,n <= 5`, not yet at the structural regime (13x18, 16x17) it will
  actually be relied on for; step 2 (running) directly addresses this.
- Next rotation: refine — proceed to step 2 (known-value validation at
  Z(13,18,3,3)=116) before trusting the pipeline on the real target,
  exactly as planned.

### 2026-08-26 — SAT step 2 succeeds (with a real performance finding); step 3 (real target) still running across 6 solver configurations

Full detail in `search/SAT_LOG.md` and `search/SAT_LOG_EXTRA_SOLVERS.md`.
A long session pause happened mid-run; picking up the thread here.

- **Step 2a succeeded**: Cadical153, WITHOUT symmetry breaking, found a
  genuine SAT witness at `m=13,n=18,K=116` in 213.4s. I independently
  re-verified the matrix myself (not just trusting the script's own
  `checker_verified` field): 13x18, 116 edges, K_{3,3}-free. This
  confirms the K_{3,3}-freeness clauses are correct and effective at
  13x18 scale, matching the known exact value.
- **Real, honest finding, not a bug**: the WITH-symmetry-breaking variant
  of the same K=116 instance (and several retries: default seqcounter
  encoding, totalizer cardinality encoding, Glucose3) never finished —
  all abandoned mid-"solving" after a crashed prior process. Despite
  symmetry breaking being *logically* validated as sound (step 1), it
  appears to badly hurt *solver performance* at this scale — plausibly
  interacting badly with CDCL heuristics (VSIDS/restarts), a known
  phenomenon in the SAT literature. Logged in the idea ledger
  (`prover/idea-ledger.md`, [L7]) so this isn't silently re-tried
  expecting a different outcome.
- **Step 2b (independent UNSAT-at-117 re-proof of Z(13,18,3,3)=116)**:
  abandoned once (process lost during the session pause), revived via a
  kissat retry — still running.
- **Step 3, the real target (m=16,n=17,K=133)**: currently running in
  parallel across SIX solver configurations: Cadical153 (with and
  without symmetry breaking), Glucose3 (without), a K=134 boundary sanity
  check (Cadical153, without), and — added to use idle CPU capacity
  productively — Kissat and Z3 (both without symmetry breaking, both
  newly wired in via a DIMACS-subprocess runner,
  `search/external_sat_runner.py`, smoke-tested on hand-checkable tiny
  cases before being trusted on the real target). As of this entry: none
  have resolved.

  **Correction (flagged by the prover-reviewer, 2026-08-26)**: an earlier
  version of this entry claimed all six configurations had accumulated
  "75-100+ minutes of CPU time each" and leaned on that for a
  "four different solver algorithms all struggling" hardness argument.
  That was an overclaim on my part. Verified breakdown: Cadical153 (both
  configs) ~105 CPU-min and Glucose3 ~78 CPU-min — but Kissat and Z3 had
  only ~11-13 CPU-min, having been launched much later. Eleven CPU-minutes
  is not informative either way for a modern CDCL solver on an instance
  this size, so the hardness argument rests only on the Cadical/Glucose
  figures, and is correspondingly weaker than stated. Additionally, all
  seven solver processes were then sharing 8 logical cores at ~55-70% of
  a core each, so wall-clock was not a clean proxy for solver effort.
  Future log entries should record each solver's *launch time* alongside
  its CPU time so staleness is visible at a glance.
- Confidence: SAT encoding correctness itself remains ~90% (unchanged
  from step 1 — nothing here contradicts it; step 2a's real, checker-
  verified witness is further positive evidence the K_{3,3} clauses are
  right). No confidence yet assignable to the real target's SAT/UNSAT
  status — still open, still running.

### 2026-08-26 — Second local-search attempt: conflict-biased tabu search finds the same floor

Full detail in `search/LOCAL_SEARCH_LOG_TABU.md`; idea ledger entry [L5].

- Directly targeted the first local-search workstream's own named
  weakness (uniform-random moves, never biased toward active conflicts).
  Built conflict-biased move selection + tabu list + live compound moves,
  150 restarts, same seeding as before for a fair comparison.
- Outcome: identical energy-2 floor (5/150 vs the earlier 7/150 — not a
  meaningful difference). But this design was *measurably, significantly*
  better at repairing back to the 132-edge/0-energy basin (9.3% vs 2.0%,
  Fisher's exact p~0.01) — real evidence of a better search design that
  nonetheless hit the identical ceiling on the actual target.
- Why this matters more than "another no": a genuinely improved search
  design converging on the same floor is stronger evidence the floor is
  a real structural feature near this basin, not an artifact of the
  earlier, weaker move set. Still only explored the same starting basin,
  though — a from-scratch version of this improved strategy is untested
  (idea ledger [L6], flagged PROMISING-UNEXPLORED).
- Confidence 133 is achievable, combining both local-search workstreams:
  ~15-18% (down slightly from the first workstream's own 20%).

### 2026-08-26 — CI reviewer-gate bug found and fixed (external), prover/reviewer.md persona adopted

- Discovered while investigating why 5 consecutive automated PR reviews
  all failed CI despite several actually containing "Verdict: ACCEPTED"
  in their posted text: the workflow's "Enforce verdict" step and
  `.github/reviewer.md`'s instructions had mismatched file paths for the
  verdict file at the time those runs executed, causing CI to fail closed
  even on genuinely-accepted reviews. This was fixed on `main` (PR #2,
  outside this branch) while this work was in progress; merged the fix
  into this branch. The 3 reviews that did complete were read in full —
  substantive, correct feedback (citation-verification concerns, a stale
  test-count claim in this log now corrected, confirmation no prompt
  injection was found in this branch's content) — see PR #3 comments for
  the full text.
- Also merged: `prover/reviewer.md`, a distinct reviewer persona (from
  `.github/reviewer.md`, which gates PR merges) meant to be called
  iteratively during the work itself — a skeptical, independent audit +
  strategic-redirection tool, with `prover/idea-ledger.md` as shared
  memory against re-deriving abandoned dead ends. Created the ledger
  (backfilled with every approach above) and will call this reviewer
  periodically going forward, per its own protocol.
