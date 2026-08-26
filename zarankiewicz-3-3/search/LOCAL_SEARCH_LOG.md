# Local-search / constructive attack log: does a 133-edge K_{3,3}-free 16x17 graph exist?

This is the log for the local-search/SA/constructive workstream (as
distinct from the parallel SAT workstream in `sat_encoding.py` /
`SAT_LOG.md`). Follows the `PROGRESS.md` entry template and the working
discipline in `README.md`. Builds entirely on `search/zark_core.py`
(`IncrementalState`, `certify()`, `load_known_witness_rowmasks()`), which
was independently reviewed and re-run before this work started (its
self-test — 2000 random toggles cross-checked against a full recompute,
plus the 132-edge witness re-certified — was re-run here too and still
passes; see the `zark_core.py` self-test output reproduced below).

Driver code: `search/local_search_attack.py` (phases 1-3) and
`search/refine_near_miss.py` (follow-up refinement on the best near-misses
phase 1 found). Raw run logs: `search/_last_run_stdout.txt`,
`search/_refine_stdout.txt`. Machine-readable summary:
`search/local_search_results.json`.

```
$ .venv/bin/python search/zark_core.py
witness: edges(incremental)=132 energy(incremental)=0
2000 random toggles: incremental bookkeeping matches full recompute. OK.
checker.verify on known witness: {'shape': (16, 17), 'edges': 132, 'has_k33': False,
  'is_k33_free': True, 'methods': {'row_triples': False, 'col_triples': False, 'networkx': False}}
Self-test passed.
```

## 2026-08-25/26 — SA seeded from the known 132-edge witness (Phase 1)

- What it is / what it's trying to establish: whether the known 132-edge
  witness's local neighborhood contains a 133-edge, 0-conflict-energy
  point — i.e. whether the 133rd edge is a "small" local repair away from
  the known construction.
- Method: `IncrementalState` loaded from
  `load_known_witness_rowmasks()`, one random missing cell added (forces
  133 edges, creates >=1 conflicting row-triple), then simulated annealing
  over single-cell toggles with objective
  `cost = energy * BIG_PENALTY + |edges - 133| * EDGE_WEIGHT` (the
  "target" mode) or `cost = energy * BIG_PENALTY - edges` (the "reward"
  mode, uncapped edge growth) — both variants from the task instructions,
  alternated across restarts. Geometric cooling `T0 -> 0.02` over the run.
  150 restarts, each with an independently randomized: RNG seed, cost
  mode, `T0 in {1,2,4}`, `edge_weight in {1,3}`, `big_penalty in
  {200,1000,5000}`, and which missing cell was added first. 20,000 SA
  iterations per restart (`_full_energy` recompute cross-checked every
  4,000 iterations via `assert_incremental_matches_full` — never fired,
  i.e. no incremental-bookkeeping drift was observed across ~3,000,000
  toggle operations).
- Lemma relied on: the incremental energy model in `zark_core.py`
  (conflict energy of a row-triple = `max(0, popcount(r_i&r_j&r_k)-2)`,
  0 total energy <=> K_{3,3}-free). This is exactly the same lemma
  `verify/checker.py` uses (stated and independently confirmed there) —
  not re-derived here, but its incremental-vs-full consistency was
  re-checked (see above) rather than assumed.
- What was checked to try to break it: every run's final state was
  re-verified against a full (non-incremental) energy recompute
  (`assert_incremental_matches_full`) — zero disagreements across the
  whole run. Any run that reported energy 0 at 133 edges was slated for
  immediate `certify()` against the real checker (per task instructions)
  — see outcome below: this never triggered, because energy 0 at 133
  edges was never observed.
- Outcome (quantitative): 0/150 restarts reached energy 0 at 133 edges.
  Histogram of `best_energy_at_target` (minimum conflict energy ever seen
  while sitting at exactly 133 edges, over all 150 runs):
  ```
  energy=2:  7 runs   <- best value ever found, never lower
  energy=4:  4 runs
  energy=5:  6 runs
  energy=6:  6 runs
  energy=7:  6 runs
  energy=8:  4 runs
  energy=9:  3 runs
  energy=10: 14 runs
  ... (long tail up to energy=25)
  ```
  Also notable and worth logging honestly: only 3/150 restarts ever
  *recovered* the starting point's own quality (132 edges, energy 0) after
  the forced 133rd-edge perturbation — the other 147 wandered into worse
  132-edge-or-fewer plateaus (histogram of `best_edges_at_zero_energy`
  peaks at 118-121). This says as much about this particular SA
  schedule's "repair" ability as about the target itself (see weakest
  point, below) — it does not even reliably re-find a point it started
  one toggle away from, which caps how much weight the "never reached
  133/0" result alone should carry.
- Best single result: seed 100132 (`mode=target, T0=1.0, edge_weight=3.0,
  big_penalty=1000.0`, first added cell `(7,2)`) reached energy 2 at 133
  edges as its best, and separately reached back to 132 edges / energy 0
  (**certified** via `certify()`: `{'edges': 132, 'is_k33_free': True}` —
  matches the known witness's certification, not a new result, just
  confirms the pipeline).
- Confidence: refined further below (see Refinement pass and Final
  assessment).

## 2026-08-25/26 — SA from scratch, independent of the known witness (Phase 2)

- What it is / what it's trying to establish: whether the known witness's
  basin is itself the limiting factor — i.e. whether an independently
  discovered region of the search space might reach 133 even if the known
  witness's neighborhood can't.
- Method: two families of from-scratch starts, 40 restarts each, 30,000
  SA iterations per restart, same annealing core as Phase 1:
  - **2a (pure random):** 133 cells chosen uniformly at random as the
    initial edge set (guaranteed 133 edges, typically very high initial
    energy), then annealed.
  - **2b (greedy K_{3,3}-free construction):** cells visited in random
    order, each added permanently only if it keeps energy at 0 (a
    maximal-greedy K_{3,3}-free graph), then annealed from wherever that
    greedy process stalled (observed greedy stall points: 114-131 edges
    depending on random order, well below 132 as a starting point — see
    `search/local_search_results.json`, `phase2_summary`).
- Outcome: 0/80 restarts reached energy 0 at 133 edges. Worse than Phase
  1 in absolute terms: best `best_edges_at_zero_energy` across all 80
  from-scratch runs was **122** (vs. Phase 1's 132), i.e. from-scratch SA
  in this iteration budget never got anywhere near the known witness's own
  quality, let alone past it. This is consistent with the known witness
  itself almost certainly being the product of a much larger search budget
  (its filename, `..._seed201.csv`, and the KAVentures source repo's
  structure both suggest a large batch of independent seeded runs, of
  which this was the best) than the 40-80 restarts affordable here.
- Honest interpretation: Phase 2's negative result is **weak evidence**
  specifically about "starting from scratch with this iteration budget is
  not competitive with the known witness's basin" — it is not informative
  about whether some *other*, unexplored region of the search space might
  reach 133; 40-80 restarts x 30k iterations is a small sample of a space
  of size `C(272, 133)`.
- Outcome: abandoned in favor of concentrating remaining budget on
  refining Phase 1's near-misses (see below) — rotating from "explore
  broadly" to "exploit the best lead found so far," per the working
  discipline's rotation rule.

## 2026-08-26 — Structurally-motivated construction: quadratic residues over GF(17) (Phase 3)

- What it is / what it's trying to establish: whether a clean algebraic
  incidence structure (not found by search) could plausibly sit near
  132-133 edges while being K_{3,3}-free *by construction*.
- Construction tried: circulant bipartite graphs on 16 rows x 17 columns,
  edge `(i,j)` iff `(j - i) mod 17` lies in a fixed connection set `D`.
  With `D` = the 8 quadratic residues mod 17 (17 is prime and `17 ≡ 1 mod
  4`, so this is the connection set of the order-17 Paley-type circulant),
  and variants (`D` = non-residues, `D` = residues plus 0).
- What was checked (computationally, via `IncrementalState`, cross-checked
  by exact energy, not assumed): `QR_mod17_16rows` (|D|=8): **128 edges,
  energy 0** — genuinely K_{3,3}-free by direct computation, not by
  citing a design-theory theorem (no such theorem was invoked — this is
  an empirical finding about this specific circulant at this specific
  size, not a claimed general result about Paley graphs). `non_QR_mod17`
  (the complementary residue class): same, 128 edges / energy 0.
  `QR_plus_zero` (|D|=9, i.e. also connecting `i` to itself's residue
  class): 144 edges but **energy 168** (badly K_{3,3}-violating). Every
  single-residue extension of the base QR set tried (9 different `|D|=9`
  variants, each adding one non-residue to the QR set): 144 edges,
  energy in **168-224** in all 9 cases (see `search/_last_run_stdout.txt`
  for the exact list) — i.e. uniformly catastrophic, not a graceful
  near-miss.
- Interrogating this as a helper lemma (per working discipline "is this
  actually easier than the original problem"): the clean 128-edge result
  is **below** the known 132-edge witness, so on its own it's not
  competitive. The interesting question was whether it could be perturbed
  *toward* 132-133 — the "add one residue" experiment above answers that:
  no, not gracefully. The reason is structural and generalizes beyond
  this one example: in any circulant/vertex-transitive construction, if
  adding one edge-type creates *any* K_{3,3} conflict, that exact
  violation pattern recurs at every one of the 16 rotations simultaneously
  (that's what vertex-transitivity means), so a single bad triple doesn't
  cost a small, controllable energy penalty — it costs a multiple of ~16
  immediately. This is the opposite of what's needed to land exactly at
  the 132-to-133 boundary, where by definition (if 133 is achievable at
  all) a construction must tolerate being *just barely* K_{3,3}-free with
  no slack. Symmetric algebraic ansatze are structurally biased toward
  landing either comfortably below the threshold (like the clean 128-edge
  case) or catastrophically over it, not precisely on it. This reasoning
  is offered as an explanation for why this line didn't pan out, not as a
  theorem — it was not proven that *no* algebraic construction could work,
  only that this natural, first-tried family fails for an identifiable,
  generalizable reason.
- Also checked (not run as code, but as a "ground the riskiest step"
  sanity calculation, since it bears on how much to trust the search's
  negative results): the classical Kővári–Sós–Turán-style triple-counting
  bound for this shape is `sum_i C(k_i, 3) <= 2 * C(17, 3) = 1360` (each
  column-triple usable by at most 2 rows, else K_{3,3}). With 16 equal
  rows of degree 9: `16 * C(9,3) = 16 * 84 = 1344 <= 1360` — i.e. this
  aggregate counting bound alone does **not** rule out 144 edges, let
  alone 133. This confirms (as the literature review in `PROGRESS.md`
  already flagged) that the real 133 upper bound must come from a finer,
  case-based argument (the CRWR 2016 paper's Lemmas 2-4), not from this
  simple relaxation — and correspondingly, that this simple counting
  bound is not a useful tool for deciding whether 133 is achievable here.
  This calculation is easy to independently re-check by hand
  (`math.comb(9,3)*16 = 1344`, `math.comb(17,3)*2 = 1360`).
- Untried, flagged honestly rather than silently skipped: an
  "asymmetric near-circulant" ansatz (take the clean 128-edge QR
  construction and perturb a *small, non-uniform* subset of cells, e.g.
  only 1-2 rows' worth, rather than adding a whole new residue class
  uniformly to every row) was not attempted — it would break the
  vertex-transitivity that caused the catastrophic jumps above, and is a
  reasonable next structural idea if this workstream continues, but ran
  out of allocated time budget here.
- Outcome: abandoned as a direct path to 133 (128 edges is not
  competitive, and the natural way to push it higher fails
  catastrophically for a structural reason, not a tuning problem);
  promising only as an explanation for *why* symmetric algebraic
  constructions are a poor fit for this specific near-threshold question.
- Confidence: 85% in the specific empirical findings (all directly
  computed and re-derivable by rerunning `phase3_structural()`); 60% in
  the generalization ("symmetric ansatze structurally can't land near a
  tight threshold") as an *explanation*, since only one connection-set
  family (quadratic residues mod 17, its complement, and single-residue
  extensions) was actually tried, not a survey of all circulant/algebraic
  options.

## 2026-08-26 — Refinement of Phase 1's best near-misses

- What it is: Phase 1 found a floor of conflict energy 2 at 133 edges (7
  of 150 restarts hit exactly this, never lower — see histogram above).
  Rather than accept a single scalar as the final word, the 7 exact
  133-edge / energy-2 matrices were reproduced deterministically (same
  RNG seeds, `search/refine_near_miss.py::reproduce_seed_state`) and
  subjected to two independent, stronger checks:
  1. **Exhaustive single-swap search**: every one of the
     `133 x 139 = 18,487` (turn off one currently-set cell, turn on one
     currently-unset cell) pairs was tried on each of the 7 near-miss
     matrices — this exactly preserves 133 edges and is a *complete*,
     non-random check of the entire distance-1 swap neighborhood (as
     opposed to SA's random sampling of it).
  2. **Reheat annealing**: 5 independent cooling cycles (temperature
     reset to `T0=1.5` at the start of each cycle) x 20,000 iterations
     each (100,000 total per near-miss) from the same starting state, as
     a genuinely different escape strategy from a single monotonic
     schedule.
- Outcome (see `search/_refine_stdout.txt` for full output): **all 7**
  near-misses are strict local optima under exhaustive single-swap search
  — `best_energy_after_1_swap == base_energy == 2` in every single case,
  with zero exceptions across `7 * 18,487 = 129,409` swap evaluations.
  Reheat annealing (an additional `7 * 100,000 = 700,000` SA iterations)
  also never improved on energy 2 for any of the 7 near-misses.
  `assert_incremental_matches_full` was checked after every exhaustive
  swap pass and after every reheat cycle — no drift detected.
- This is meaningfully stronger evidence than the raw Phase 1 numbers
  alone: it's not just that SA *didn't happen* to find a 0-energy
  133-edge point near these near-misses — it's that the entire
  distance-1 neighborhood of each of 7 independently-found near-misses
  was exhaustively checked and contains no improvement at all, and 100k
  further SA iterations per near-miss from a wide range of temperatures
  couldn't escape energy 2 either.
- What this does **not** establish: these are 7 specific points in a
  space of `C(272,133)` possible 133-edge graphs; exhaustive distance-1
  optimality at 7 points is not exhaustive optimality of the whole space,
  and distance-2-or-more swaps (multiple simultaneous cell changes) were
  not exhaustively checked (that neighborhood is far too large to check
  exhaustively: `C(133,2) * C(139,2) ≈ 8.6 * 10^7` pairs of pairs, times
  7 near-misses — feasible in principle with more time, not attempted
  here).
- Outcome: promising as *negative* evidence (a genuine local-optimum
  wall at energy 2, not just an SA-didn't-try-hard-enough artifact), not
  as a proof.
- Confidence: overall 88% that these 7 specific matrices are true local
  optima under both move sets tested (high confidence — this is an
  exhaustive, deterministic check for the swap part, and a large,
  independently-cross-checked SA budget for the reheat part). Weakest
  step: 40% that this generalizes to "133 is unreachable from *any*
  starting point" — this refinement pass only ever explored basins
  reachable from the one known 132-edge witness plus small perturbations;
  it says nothing about basins unreachable from that witness (Phase 2's
  much weaker from-scratch results are suggestive that other basins are
  hard to find in this budget, but that is itself a budget limitation,
  not evidence those basins don't exist or wouldn't do better).

## Final assessment

- **Best candidate found, checker-verified:** 132 edges, conflict energy
  0 — this is the pre-existing known witness
  (`data/known_witnesses/z16_17_132_witness_seed201.csv`), re-certified
  here via `certify()` (`{'edges': 132, 'is_k33_free': True, 'methods':
  {'row_triples': False, 'col_triples': False, 'networkx': False}}`) as a
  byproduct of Phase 1's annealing recovering it. **No 133-edge,
  0-conflict-energy K_{3,3}-free graph was found or is being claimed.**
  The closest approach to 133 was conflict energy **2** at exactly 133
  edges (7 independent SA runs converged to this exact floor and no
  lower; all 7 were then shown to be strict local optima under exhaustive
  single-swap search plus 100k further SA iterations each — see above).
  Per the "not acceptable under any circumstance" clause in `README.md`,
  this energy-2 near-miss is explicitly **not** reported as any kind of
  positive or near-positive result — it is a graph that genuinely
  contains K_{3,3} subgraphs (2 units of excess triple-intersection), not
  a certified witness of anything, and no `certify()` call was made
  against it as a K_{3,3}-free claim (only against confirmed energy-0
  states, per the task's certification discipline).
- **Total search volume:** Phase 1 + Phase 2 = 230 independent SA restarts
  (150 seeded + 80 from-scratch), ~3.5M-5M toggle operations, 329.8s wall
  time; refinement pass = 7 exhaustive-swap searches (129,409 pair
  evaluations total) + 7 x 100,000 reheat-SA iterations, 40.0s wall time.
  Total: ~370s of actual search compute across ~265 independent
  annealing trajectories. `assert_incremental_matches_full` was checked
  periodically throughout (every 4,000 SA iterations, plus after every
  exhaustive-swap pass and reheat cycle) with zero disagreements observed
  — the incremental bookkeeping this entire workstream depends on held up
  under sustained, varied use, consistent with (and adding further
  evidence to) the orchestrating session's earlier independent review.
- **Calibrated confidence that a 133-edge K_{3,3}-free 16x17 graph
  exists**, based *only* on what this local-search workstream observed
  (explicitly not incorporating the parallel SAT workstream's results,
  which this session did not see): **~20%**. Reasoning: 0/230 fresh SA
  restarts and 0/7 refined near-misses (each exhaustively checked in its
  immediate neighborhood) found one; the energy-2 floor was hit
  repeatedly and independently (7 times) rather than as a one-off, which
  is mild evidence it's a real structural floor rather than noise; the
  structural/algebraic route also failed for an identifiable
  (non-tuning) reason. This is deliberately not pushed lower than ~20%
  because: (a) local search failing to find a needle is always weak
  evidence of the needle's absence, especially given Phase 2 showed this
  budget cannot even reliably rediscover a *known-to-exist* 132-edge
  solution from scratch, so its failure to find a hypothetical 133-edge
  solution carries correspondingly limited weight; (b) the published 133
  upper bound is real but, per the literature-verification entry in
  `PROGRESS.md`, was itself flagged by its original 2016 authors as one
  of several "weak-looking" bounds in this exact region, i.e. even the
  people who proved `Z(16,17,3,3) <= 133` seem to have suspected the true
  value might be lower without stating so outright — which cuts toward
  132 being the true value, but is second-hand reasoning about other
  authors' unstated suspicions, not a result of this workstream's own
  computation, so it is not weighted heavily here.
- **Named weakest point of this search methodology:** the move set used
  in all SA runs (Phases 1, 2, and the reheat refinement) was **uniform
  random single-cell toggles**, with no bias toward cells that
  participate in currently-violated triples and no multi-cell "compound"
  moves (e.g. simultaneous 2-cell swaps as a primary move type, rather
  than only as a post-hoc exhaustive check on 7 specific near-misses).
  Concretely: `IncrementalState.conflict_triples()` exists precisely to
  identify which rows are involved in current violations, but the SA
  loop never used it to bias move selection — every move is a uniform
  draw over all 272 cells regardless of whether the toggled row is
  anywhere near a conflict. On a 16x17 board, most conflicts likely
  involve only a handful of the 16 rows at a time, so a large fraction of
  proposed moves in any given state are "irrelevant" to resolving the
  current conflict and only serve to explore/perturb elsewhere. A
  conflict-biased or simulated-annealing-with-tabu variant, or a
  proper large-neighborhood search (exhaustive or near-exhaustive 2-swap
  moves as the *primary* driver rather than a one-off diagnostic on 7
  points) was not attempted due to time, and is the most likely place
  where a genuinely different search design could still find something
  this run missed — or could instead sharpen the negative result by
  showing the energy-2 floor survives that stronger search too. This is
  weighted more heavily than restart/iteration count in the confidence
  score above precisely because it is a design gap (a whole move type
  never tried at scale), not just "not enough of what was already tried."
