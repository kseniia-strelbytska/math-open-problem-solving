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
