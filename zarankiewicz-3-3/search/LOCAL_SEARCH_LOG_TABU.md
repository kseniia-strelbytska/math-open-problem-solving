# Conflict-biased / tabu / large-neighborhood-search attack log

This is a companion, independent workstream to `search/LOCAL_SEARCH_LOG.md`
(the uniform-random-single-toggle SA workstream, 230 restarts, found an
energy-2 floor at 133 edges — see that log for full detail). That
workstream's own log named its weakest point explicitly: *"the move set was
uniform random single-cell toggles throughout, never biased toward cells in
currently violated triples ... a conflict-biased or simulated-annealing-
with-tabu variant, or a proper large-neighborhood search ... was not
attempted due to time."* This workstream fills exactly that gap. Follows
the `PROGRESS.md` entry template and the working discipline in `README.md`.
Builds entirely on `search/zark_core.py` (`IncrementalState`, `certify()`,
`load_known_witness_rowmasks()`) — no new K_{3,3}-detection logic was
written; only move-selection / meta-heuristic bookkeeping on top of it.

Driver code: `search/tabu_search_attack.py`. Raw run log:
`search/_tabu_run_stdout.txt`. Machine-readable summary:
`search/tabu_search_results.json`.

## Design

1. **Conflict-biased move selection.** `IncrementalState.conflict_triples()`
   is called periodically (every 8 iterations — see "known limitation of
   this design" below) to get the list of currently-violating row-triples;
   the rows involved (with repeats, so a row in more violations is sampled
   more often) form a bias pool. Each single-cell proposal draws its row
   from that pool with probability `bias_prob` (randomized per restart over
   `{0.7, 0.8, 0.9}`), else a uniform-random row — the column is always
   uniform-random. This is a genuinely different proposal distribution from
   the prior workstream's pure `rng.randrange(m), rng.randrange(n)`.
2. **Tabu list.** `tabu_until: dict[(i,j) -> iteration]`. A move is
   forbidden if any of its cells are still tabu, UNLESS accepting it would
   set a new best-ever energy record for the run (aspiration criterion),
   in which case it's allowed regardless. Tenure randomized per restart
   over `{6, 12, 20}` iterations.
3. **Compound / large-neighborhood moves.** Every `compound_every`
   iterations (randomized per restart over `{150, 250, 400}`), or whenever
   `since_improve >= patience` (randomized over `{200, 300, 500}`), a
   compound move is proposed: pick an actively-conflicting row-triple (or a
   conflict-biased/random triple if none is currently violated), identify
   its shared "overloaded" columns (the ones causing
   `popcount(r_i & r_j & r_k) > 2`), toggle **off** 1-2 of them in one row
   of the triple (a targeted repair), and toggle **on** 1-2 random
   compensating cells elsewhere — 2 to 4 cells total, applied and
   accepted/rejected as a single atomic step via the same energy-based
   criterion (never a post-hoc diagnostic; it's a live branch of the main
   loop on every restart).
4. **Same objective/annealing core as the prior workstream's Phase 1**
   (`cost = energy*big_penalty + |edges-target|*edge_weight`, geometric
   cooling `T0 -> 0.02`), and the **same seeding**: the known 132-edge
   witness (`load_known_witness_rowmasks()`) plus one randomly-added
   missing edge (forces 133 edges, >=1 conflict). This isolates
   move-selection strategy as the only varying factor between the two
   workstreams, per the task's explicit fairness requirement.

## A bug caught before the real run (worth logging honestly)

While profiling a small run (`cProfile`, 2 restarts x 5000 iters) before
committing to the full 150-restart run, `propose_compound_move` was being
called 9,060 times out of 10,000 total iterations — i.e. compound moves
were firing on almost every iteration, not "periodically." Root cause: the
stagnation counter `since_improve` was only reset to 0 on improvement, so
once it first exceeded `patience` it stayed `>= patience` forever (nothing
decremented it on non-improving iterations), making every subsequent
iteration trigger a patience-driven compound move. Fixed by also resetting
`since_improve` after a patience-triggered compound move is *attempted*
(accepted or not), so the search gets a fresh `patience`-iteration window of
single moves before the next stagnation-triggered compound fires. This cut
per-restart wall time by ~3.5x (12.5s -> 3.5s on the profiling case) and
brought compound-move frequency back in line with the intended "periodic,
plus when genuinely stuck" design. Caught by profiling *before* the real
run, not discovered after the fact — flagging this per the working
discipline's "try to break it before extending it."

## Run parameters and self-checks

- 150 independent restarts x 20,000 iterations each (a "step" is either one
  single-cell move or one compound move, same iteration-budget accounting
  as the prior workstream's Phase 1) — same restart count and same
  iteration count as the prior workstream's Phase 1, for a fair,
  scale-matched comparison.
- `assert_incremental_matches_full()` checked every 4,000 iterations within
  each restart, plus once more after each restart completes: **zero
  disagreements** across the full run (~3,000,000 single-move toggle calls
  + 16,399 compound-move proposals, each applying 2-4 further `toggle()`
  calls plus reverts on rejection) — no incremental-bookkeeping drift was
  introduced by the new compound-move code path.
- `certify()` (the real, independent `verify/checker.py`) is called
  automatically on any run that reports energy 0 at 133 edges (none did —
  see results) and on the single best overall candidate found (which turned
  out to be a 132-edge, energy-0 recovery of the known witness's basin —
  see below), exactly per the certification discipline.
- Total wall time: **359.4s** (~6.0 minutes) for the full 150x20000 run.

## Results

- **0/150 restarts reached energy 0 at 133 edges.** No `certify()`-worthy
  positive candidate was produced, so no positive result is being reported.
- **The floor is exactly the same: minimum energy at 133 edges = 2**,
  reached by 5/150 restarts (3.3%). The prior workstream's Phase 1 (also
  150 restarts, uniform-random single-toggle, same seeding) reached the
  *identical* floor of energy=2, in 7/150 restarts (4.7%). Two structurally
  different move-selection strategies — one with no conflict awareness at
  all, one with explicit conflict-biasing, tabu, and compound
  large-neighborhood moves — converge to the exact same minimum
  conflict-energy value from the same starting basin. Neither ever went
  below 2.
- **Distributional comparison (both n=150, same seeding, same iteration
  budget):**

  | metric | prior (uniform random) | this workstream (conflict-biased/tabu/compound) |
  |---|---|---|
  | min energy at 133 edges (the floor) | 2 | 2 |
  | mean energy at 133 edges | 15.71 | 16.21 |
  | median energy at 133 edges | 19.0 | 19.0 |
  | runs hitting the floor (energy=2) | 7/150 (4.7%) | 5/150 (3.3%) |
  | runs recovering 132 edges / energy 0 | 3/150 (2.0%) | **14/150 (9.3%)** |
  | mean `best_edges_at_zero_energy` | 121.24 | **125.43** |
  | median `best_edges_at_zero_energy` | 120.0 | **125.0** |
  | wall time (150x20000) | 186.2s | 359.4s |

  A two-sided Fisher's exact test on the 132/0-recovery counts (14/150 vs
  3/150) gives **p ≈ 0.0104** — a statistically significant improvement in
  the search's ability to repair back to the known-good basin after the
  forced 133rd-edge perturbation, not noise.
- **Interpretation, stated carefully:** the new move strategy is
  measurably, significantly better at one thing — recovering the starting
  point's own known-good structure after a perturbation (repair-to-132/0
  rate more than quadrupled, and the whole `best_edges_at_zero_energy`
  distribution shifted up by ~4 edges on average). This is real evidence
  the conflict-biased/tabu/compound design does search differently and
  better in a *general* sense, not merely different noise. But it is **not**
  better at the one thing that would matter most here: neither the mean/
  median energy achieved specifically at 133 edges, nor the floor itself,
  improved. If anything the floor was reached by slightly *fewer* runs here
  (5 vs 7) — well within noise at this sample size, not read as a
  regression, just as "no improvement." Taken together, this is evidence
  that leans toward **the energy-2 floor being a real structural feature of
  this particular basin (the known witness plus a locally-repaired
  neighborhood), not an artifact of the specific "uniform random toggle"
  move-selection design that the prior workstream flagged as its weakest
  point** — because a genuinely different, more sophisticated search design
  that provably searches better in an adjacent sense (repair capability)
  still could not cross it.
- **Cost honestly noted:** this design is not free — per equivalent
  iteration budget it took 359.4s vs. 186.2s (~1.93x slower), due to the
  `conflict_triples()` refresh (an O(C(16,3))=560-triple scan) called every
  8 iterations for the bias pool. It did not find the same floor *faster*;
  it found the same floor in comparable restart-count and iteration-count
  terms, but higher wall-clock cost.
- **Best certified candidate:** 132 edges, conflict energy 0 (the known
  witness's basin, recovered by the search and re-certified via `certify()`
  as a byproduct — not a new result): `{'shape': (16, 17), 'edges': 132,
  'has_k33': False, 'is_k33_free': True, 'methods': {'row_triples': False,
  'col_triples': False, 'networkx': False}}`. The single best 133-edge
  near-miss found (never certified as anything positive — it genuinely
  contains K_{3,3} subgraphs, energy=2, same floor as the prior workstream,
  not reported as any kind of near-positive result per the "not acceptable
  under any circumstance" clause in `README.md`) was seed 400027 (params:
  `t0=1.0, edge_weight=1.0, big_penalty=5000.0, tabu_tenure=20, bias_prob=0.8,
  compound_every=400, patience=300`).
- **A design element that turned out to be inert, worth flagging
  honestly:** the aspiration criterion (allow a tabu move if it sets a new
  best-ever energy record) fired **zero times** across all 150 restarts x
  20,000 iterations (`n_aspiration_overrides` summed to 0). Aggregate move
  stats: ~2.98M single moves proposed (182,698 accepted, ~6.1%), 16,399
  compound moves proposed (520 accepted, ~3.2%), 8,146 single/compound
  moves blocked by tabu (~0.27% of all proposals). The tabu-blocking rate
  is low enough, and best-ever-energy records rare enough once past the
  initial descent, that a tabu-blocked move essentially never happened to
  coincide with a new record in this run. The tabu component was
  therefore doing real work (blocking ~8k moves), but its aspiration
  override — a standard piece of tabu-search theory included per the task
  instructions — was never actually exercised here. This does not
  invalidate the design (the aspiration criterion is a safety valve, not
  expected to fire often), but it means this run does not provide direct
  evidence either for or against its usefulness at this problem's scale.

## Comparison to the prior workstream's finding — explicit answer to "did conflict-biasing help find the same floor more efficiently?"

Not in the way originally hoped: this workstream did **not** find a lower
floor, and did not reach the same floor in fewer restarts or faster
wall-clock time. But it **did** show, with a statistically significant
result on a genuinely different metric (repair-to-known-good rate), that
the search design change had a real, measurable effect on search
efficiency — just not one that broke through the 133-edge/energy-2 wall.
That combination (real improvement in general search quality, zero
improvement in this one specific outcome, exact same floor value hit by
both designs) is itself informative: it is evidence *for* the floor being a
structural property of this region of the search space, since it survived
a genuinely stronger, differently-designed attempt to search around it, not
merely a symptom of the prior workstream's move set being naive.

## Confidence assessment (combining with the prior workstream)

- **This workstream's evidence alone:** ~18% that 133 is achievable
  (slightly below the prior workstream's own 20%, reflecting that a
  second, more sophisticated search design also failed to cross the exact
  same floor — mild additional evidence for the floor being real, offset
  only slightly since both workstreams still explore the same starting
  basin, see limitation below).
- **Combined with the prior workstream's ~20% (230 restarts, uniform
  random, plus exhaustive distance-1-swap verification on 7 near-misses)
  and the still-running SAT workstream (not seen by this session):**
  **~15-18%** that a 133-edge K_{3,3}-free 16x17 graph exists. Two
  independently-designed local-search strategies (380 restarts combined,
  ~3.7M+3M toggle-equivalent operations) now agree on an energy-2 floor at
  133 edges from the known witness's basin, and the more sophisticated of
  the two — explicitly built to address the weaker one's named
  shortcoming — still could not cross it despite being significantly
  better at general local repair. This tightens (does not overturn) the
  prior negative finding. It remains bounded above 0% because local search
  failing to find a needle is inherently weak evidence of the needle's
  absence, and because neither workstream has explored basins far from the
  known 132-edge witness with this stronger move strategy (see below) —
  the strongest possible negative evidence would be a certified SAT UNSAT
  result, which this workstream does not attempt or supersede.

## Named weakest point of this workstream's methodology

Three, in order of how much they'd change the confidence assessment if
addressed:

1. **Same single starting basin as the prior workstream's Phase 1, by
   design (for fair comparison) — never combined with Phase 2's
   from-scratch exploration.** Every one of the 150 restarts here starts
   from the known 132-edge witness plus one added edge. The task explicitly
   asked for this (to isolate move-selection strategy as the only
   variable), and it succeeded at that — but it means the conflict-biased/
   tabu/compound move strategy has never been tried starting from scratch
   or from a structurally different basin (e.g. the QR-circulant
   construction from the prior workstream's Phase 3, or a random 133-edge
   start). Given this workstream's design proved to have a real, measurable
   advantage in general search quality (the 132/0-recovery-rate result),
   it is the most natural next combination to try — recombine this
   strategy with Phase 2's "from scratch" setup — rather than a genuinely
   new approach area.
2. **The compound-move family is one specific, hand-designed repair
   heuristic (targeted column-drop-in-a-conflicting-triple plus random
   compensating additions), not a systematic large-neighborhood search.**
   It was not, e.g., an exhaustive or near-exhaustive scan of all 2-swaps
   or 3-swaps as the *primary* move (which the prior workstream's
   refinement pass did, but only as a one-off diagnostic on 7 fixed
   points, exactly the gap this workstream was supposed to close as a
   *live* search driver — and it did close it as a live driver, but the
   specific move shape chosen is still narrow, not the true full
   2-swap/3-swap neighborhood evaluated at every stuck point).
3. **The conflict-bias refresh interval (every 8 iterations) is a
   staleness/cost tradeoff that was tuned for wall-clock feasibility, not
   empirically validated as optimal** — a finer refresh (every iteration)
   would track the true conflict set more precisely but cost ~8x more in
   `conflict_triples()` calls (this was empirically ~1.93x slower than the
   prior workstream even at this interval); a coarser one would save time
   but bias moves using stale conflict information. No sweep over this
   parameter was done; it was fixed once and used for all 150 restarts.
