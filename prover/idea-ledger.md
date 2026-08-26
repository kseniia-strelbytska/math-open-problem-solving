# Idea ledger — Z(16,17,3,3)

One entry per distinct approach tried against the target problem: does a
133-edge K_{3,3}-free bipartite graph exist on parts of size 16 and 17
(equivalently, is `Z(16,17,3,3) = 132` or `133`)? Current published bounds:
`132 <= Z(16,17,3,3) <= 133`, with the 133 side traced to a 2016 paper's
exhaustive-computation result with no known matching construction (see
`zarankiewicz-3-3/PROGRESS.md` for the full citation-chain verification).

Read this before starting any new approach — check whether it's a
rediscovery of something already logged `ABANDONED`, and whether anything
logged `PROMISING-UNEXPLORED` should be revived instead of starting fresh.

### [L1] Literature re-verification and witness adoption
- Status: DEAD-END-CONFIRMED (not abandoned — completed successfully, just
  no further action available on this specific idea)
- First appeared: iteration 1 (project start)
- Independently traced and re-verified both ends of the published gap:
  fetched the actual 132-edge witness matrix from its source (GitHub repo
  `KAVentures/z1322-exact`) and confirmed with our own checker; traced the
  133 upper bound to Collins et al. (arXiv:1604.01257, 2016) and confirmed
  via PDF font extraction that it's an exhaustive-computation bound with
  no matching construction, never claimed exact by its own authors.
- Outcome: both ends grounded. No further literature-tracing action
  available on this specific sub-task; feeds directly into all other
  entries below.

### [L2] Independent verification checker (verify/checker.py)
- Status: ACTIVE (infrastructure, not an attack on the problem itself)
- First appeared: iteration 1
- Two independent edge-counters, three structurally different K_{3,3}
  detectors, all required to agree. Tested against hand-verified cases,
  500 random trials against a 4th code-independent ground truth, and all
  6 known literature witnesses. This is the trust anchor every other
  entry below depends on for certifying a result.
- Named weakness (see zarankiewicz-3-3/PROGRESS.md): two of the three
  internal K_{3,3} methods share the same underlying row-triple lemma —
  mitigated by the 4th, code-independent test-only ground truth, not
  eliminated.

### [L3] Simulated annealing, uniform-random moves (local_search_attack.py)
- Status: DEAD-END-CONFIRMED, but see [L5] which revisits with a different
  move strategy
- First appeared: iteration ~3
- Seeded SA from the known 132-edge witness (150 restarts) and from
  scratch (80 restarts), uniform-random single-cell-toggle moves. 0/230
  reached 133 edges at zero conflict energy. The 7 best near-misses
  (133 edges, conflict energy 2) were exhaustively distance-1-swap-checked
  (18,487 pairs each) plus 100k further SA iterations each — all 7 are
  strict local optima under both.
- Reason abandoned: not that it failed once — it failed exhaustively at
  its own local neighborhood, and a full budget of restarts never escaped
  the energy-2 floor. Its own log names the real weakness precisely: the
  move set never biased toward cells in active conflicts. That gap is
  what [L5] fills — this entry is not "wrong," just superseded as the
  best use of further compute under this move strategy.
- Does the reason still hold? Yes for *this specific move strategy*. See
  [L5] for whether a smarter move strategy changes the picture.

### [L4] Structural/algebraic construction: quadratic residues mod 17
- Status: DEAD-END-CONFIRMED, with an identified structural reason (not
  just "didn't find it")
- First appeared: iteration ~3 (same workstream as L3, Phase 3)
- Circulant bipartite graphs on 16x17 via a connection set D subset of
  Z/17. Quadratic-residue D (|D|=8): clean 128 edges, energy 0 — but 128
  is below the known 132, not competitive. Every single-residue extension
  to |D|=9 (9 variants tried): 144 edges but energy 168-224, uniformly
  catastrophic.
- Reason abandoned: vertex-transitivity (16-fold rotational symmetry)
  means any single bad triple recurs at all 16 rotations simultaneously —
  symmetric ansatze structurally can't land precisely at a tight
  threshold, they either sit comfortably below it or blow through it.
  This is a real structural argument, not just a failed parameter search.
- Untried variant, flagged as PROMISING-UNEXPLORED below: an *asymmetric*
  near-circulant perturbation (small non-uniform tweak to 1-2 rows,
  breaking the vertex-transitivity that caused the catastrophic jumps).

### [L4b] Asymmetric near-circulant perturbation of the QR construction
- Status: PROMISING-UNEXPLORED
- First appeared: iteration ~3 (flagged, never attempted)
- Idea: take the clean 128-edge QR construction from [L4] and perturb a
  small, non-uniform subset of cells (not a whole new residue class
  applied uniformly to every row) — this breaks the vertex-transitivity
  that made [L4]'s extensions fail catastrophically, so a small targeted
  change might climb from 128 toward 132-133 gracefully instead of
  jumping to energy 168+.
- Why never pursued: ran out of allocated time budget in the workstream
  that found [L4]'s clean base case.
- What it needs: someone to actually implement and run it. Likely a
  short task (start from the 128-edge QR matrix already known, do local
  search restricted to a small number of asymmetric perturbations).

### [L5] Conflict-biased tabu / large-neighborhood search
- Status: DEAD-END-CONFIRMED, but see note on what it *does* establish
- First appeared: iteration ~6
- Directly targets [L3]'s named weakness: move selection biased toward
  `conflict_triples()`, a tabu list with aspiration criterion, and a live
  2-4-cell compound-move component (not just a one-off diagnostic).
  150 restarts, same seeding as [L3]'s Phase 1, for a fair scale-matched
  comparison.
- Outcome: same energy-2 floor as [L3] (5/150 hit it here vs 7/150
  there — statistically indistinguishable). This design WAS measurably,
  significantly better at repairing back to the 132-edge/energy-0 basin
  (14/150 = 9.3% vs [L3]'s 3/150 = 2.0%, Fisher's exact p~0.01) — so the
  move-strategy upgrade demonstrably improved search quality on a
  measurable axis, yet still hit the identical ceiling on the actual
  target metric.
- Why this matters more than a second "no": because a *genuinely better*
  search design converged to the exact same floor, that's real evidence
  the energy-2 floor is a structural feature of the search space near
  this basin, not an artifact of [L3]'s specific (weaker) move set. Still
  only explored the same starting basin as [L3], though — see [L6].
- Reason still open: a from-scratch version of this same improved move
  strategy (analogous to [L3]'s weaker from-scratch Phase 2, but with
  the tabu/conflict-biased moves) has not been tried. Logged as
  PROMISING-UNEXPLORED below.

### [L6] From-scratch tabu/conflict-biased search (not yet attempted)
- Status: PROMISING-UNEXPLORED
- First appeared: iteration ~6 (identified as a gap, not attempted)
- [L3]'s from-scratch Phase 2 (uniform-random moves, no seed) was much
  weaker than its seeded Phase 1 (best 122 edges vs 132). [L5]'s improved
  move strategy was only ever run seeded from the known witness. Whether
  a from-scratch start with [L5]'s better moves can find a genuinely
  different basin (rather than just repairing back to the same one) is
  untested.
- What it needs: rerun [L5]'s tabu_search_attack.py machinery with
  from-scratch (random/greedy) starting points instead of the known
  witness seed, same iteration/restart budget as [L3]'s Phase 2 for a
  fair comparison.

### [L7] SAT encoding, exact-K + K_{3,3}-freeness clauses + "double lex" symmetry breaking
- Status: ACTIVE
- First appeared: iteration ~4
- Full exact-cardinality + K_{3,3}-clause SAT encoding (`sat_encoding.py`).
  Symmetry-breaking soundness independently validated: 336/336 exhaustive
  lex-gadget checks + brute-force-verified small cases, zero
  disagreements (re-run independently by the orchestrating session,
  confirmed).
- Key finding: symmetry breaking, while logically sound, appears to badly
  hurt SOLVER PERFORMANCE at 13x18+ scale — the symmetry-breaking variant
  of the K=116 validation instance never finished, while the
  no-symmetry-breaking variant found a real, checker-verified 116-edge
  witness in ~213s. This is a performance finding, not a correctness bug
  — logged so it isn't silently re-tried expecting a speedup.
- Status of the real target (m=16,n=17,K=133): as of this ledger entry,
  running on FOUR solver backends in parallel (Cadical153 with and
  without symmetry breaking, Glucose3 without, and — see [L8] — Kissat
  and Z3 without) for well over an hour of real CPU time each, none
  resolved yet (all `status: "solving"`). This is itself informative:
  multiple different solver algorithms are all struggling on this exact
  instance, which is at minimum consistent with (not proof of) the
  instance being genuinely hard, not just under-resourced.
- Reason NOT abandoned: this is the only approach on the list capable of
  producing a genuine proof (UNSAT = proof Z=132; SAT = proof Z=133) as
  opposed to evidence. Still running.

### [L8] Additional SAT solver backends: kissat, z3
- Status: ACTIVE (both still running)
- First appeared: iteration ~7
- Kissat (modern, often much faster than bundled solvers) and Z3 (SMT
  solver, genuinely different core algorithm) both wired in via DIMACS
  export + subprocess, both attempting m=16,n=17,K=133, no symmetry
  breaking (per [L7]'s finding). Also retrying the abandoned [L9]
  UNSAT-at-117 validation with kissat.
- Not yet resolved as of this ledger entry.

### [L9] UNSAT-at-117 validation for Z(13,18,3,3) (independent re-proof of optimality)
- Status: ABANDONED once (Cadical153, ran out of time budget mid-session
  pause, process lost) — REVIVED under [L8] (kissat retry, in progress)
- First appeared: iteration ~4
- Goal: prove no 117-edge K_{3,3}-free 13x18 graph exists, which would be
  an independent machine-checked confirmation that Z(13,18,3,3)=116
  exactly, strengthening confidence in the whole SAT pipeline before
  leaning on its (much harder) verdict for the real 16x17 target.
- First attempt (Cadical153, both with and without symmetry breaking)
  was abandoned without a result when its process was lost during a long
  session pause — not a negative result, just incomplete. Kissat retry
  in progress under [L8].

### [L10] ILP / other combinatorial-optimization formulations (not yet attempted)
- Status: PROMISING-UNEXPLORED
- First appeared: this ledger entry (flagged during review prep, not
  previously logged)
- Not yet tried: formulating the same problem as an integer linear
  program (binary variables, exact-133-edges constraint, one
  linear inequality per row-triple-x-column-triple forbidding the K_{3,3}
  pattern — same combinatorial structure as the SAT encoding but solved
  via branch-and-bound/cutting-planes rather than CDCL) using an
  available ILP solver, if one can be installed. Worth trying as a
  genuinely different algorithmic paradigm from SAT, since ILP solvers
  exploit LP-relaxation bounds that might prune the search very
  differently than CDCL's clause learning does on this specific instance.

### [L11] Sharper counting/extremal bounds beyond simple KST (not yet attempted)
- Status: PROMISING-UNEXPLORED
- First appeared: this ledger entry
- The simple Kővári–Sós–Turán-style triple-counting bound
  (`sum_i C(k_i,3) <= 2*C(n,3)`) does not rule out 133 (checked by hand
  in [L4]'s workstream: doesn't even rule out 144). The 2016 paper's own
  method (Lemmas 2-4, "backwards path extensions") is more refined and is
  what actually produced the 133 bound — but we have not yet read or
  attempted to reproduce/extend that specific finer argument ourselves.
  This is a literature/technique gap, not a computational one, and is a
  candidate for a genuinely different (human-mathematics-style, not
  brute-force) angle on the upper-bound side.

### [L12] DRAT/LRAT proof certificate generation + independent verification
- Status: ACTIVE, URGENT
- First appeared: iteration ~8 (raised by the prover-reviewer's first call,
  2026-08-26 — was NOT previously logged despite being the single highest-
  value gap in the project)
- The problem: none of the solver processes running as of that review had
  proof logging enabled. So if any of them had resolved UNSAT, the result
  would have been worthless as a *certificate* — only informal internal
  evidence — and the 100+ combined CPU-hours would have to be re-spent.
  This directly blocks acceptance criterion (B) and the explicitly-raised
  "conference-admittable proof" bar.
- Independently verified (not taken on the reviewer's word): `kissat --help`
  confirms proof output is a plain positional argument
  (`kissat [options] <dimacs> [<proof>]`, binary DRAT for real files) —
  an unused CLI flag, not a research problem. Also confirmed `drat-trim`,
  `cake_lpr`, `lrat-check` are all absent from this machine.
- What it needs: (a) relaunch a no-symmetry-breaking 16x17/K=133 kissat run
  WITH a proof file; (b) install `drat-trim`, and `cake_lpr` if buildable
  (preferred — it is itself formally verified in HOL4, which closes the
  "who checks the checker" loop far more tightly); (c) smoke-test both
  checkers on a tiny hand-constructed UNSAT case (e.g. m=3,n=3,K=9) before
  trusting either on the real proof.
- Note: the certifying run should NOT use symmetry breaking — it hurts
  performance here anyway, and dropping it removes the (only empirically
  validated, never formally proven) double-lex soundness argument from the
  proof's dependency chain entirely. Two birds.

### [L13] Bottom-up isomorph-free exhaustive generation (orderly generation)
- Status: ACTIVE — now the primary computational strategy
- First appeared: iteration ~8 (strategy re-evaluation, see
  `zarankiewicz-3-3/STRATEGY_V2.md` for the full argument)
- Why: the monolithic SAT approach fights ~`16!*17! = 1.2e26` row/column
  permutation symmetry with clauses, which CDCL cannot exploit and which
  was measured to make the solver *slower*. Orderly generation instead
  eliminates that symmetry *by construction* via canonical forms.
- Method: build row-by-row over 17-bit row masks, rows kept lex
  non-increasing (sound: sorting rows preserves both edge count and
  K_{3,3}-freeness), first row fixed as `1^d 0^(17-d)` WLOG by column
  permutation, incremental 680-counter triple-multiplicity state each
  capped at 2, and pruning by prefix bound (`E_k <= f(k)`), suffix bound
  (`E_k + (16-k)*d_k >= target`), and remaining triple budget.
- Key structural advantage: compute `f(k) := z(k,17;3)` bottom-up for
  k=1..16 ourselves, so the final result cites NO external upper bound —
  it re-derives the sub-cell values (z(13,17)=110, z(14,17)=118,
  z(15,17)=126) that the case-reduction argument would otherwise have to
  assume on the 2016 paper's uncertified authority.
- Validation before trust: must reproduce known published exact values
  (small cells z(6,6)=26, z(7,7)=33, z(8,8)=42, z(9,9)=49, then the
  directly relevant 13/14/15 x 17 cells). Reproducing those is much
  stronger evidence than anything the SAT pipeline has produced.
- Supporting result already verified this session: the counting bounds
  (`sum_r C(d_r,3) <= 2*C(17,3) = 1360`, `sum_c C(e_c,3) <= 2*C(16,3) =
  1120`) plus deletion-derived degree floors cut the hypothetical 133-edge
  graph's possible row degree sequences to just **438** (and column
  sequences to 3167) — an explicit, human-checkable, parallelisable case
  reduction. Counting alone does NOT rule out 133 (balanced sequences give
  1036 and 889, both within budget), so search is genuinely required.
