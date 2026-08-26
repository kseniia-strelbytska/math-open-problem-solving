"""
Conflict-biased / tabu / large-neighborhood-search attack on Z(16,17,3,3):
does a 133-edge K_{3,3}-free 16x17 bipartite graph exist?

This is a companion workstream to search/local_search_attack.py (uniform-
random single-cell-toggle SA, 230 restarts, found an energy-2 floor at 133
edges -- see search/LOCAL_SEARCH_LOG.md). That workstream's own log named
its weakest point explicitly: the move set was uniform random single-cell
toggles throughout, never biased toward cells actually in conflict, and
multi-cell compound moves were only a one-off diagnostic on 7 fixed points,
never a primary search driver. This script fills exactly that gap:

  1. Conflict-biased move selection: IncrementalState.conflict_triples()
     is used to find rows currently involved in a K_{3,3} violation, and
     move proposals are biased (default 80%) toward cells in those rows.
  2. A simple tabu list: recently-toggled cells are forbidden from being
     re-toggled for a short tenure, UNLESS the candidate move would set a
     new best-ever energy record for the run (aspiration criterion).
  3. A genuine large-neighborhood / compound-move component: periodically,
     and whenever stuck (no improvement for `patience` iterations), a
     compound move simultaneously toggles 2-4 cells (drawn from an actively
     conflicting triple's shared columns, plus compensating random cells
     elsewhere) as ONE atomic step, accepted/rejected as a whole via the
     same energy-based criterion. This is a live part of the search loop
     across every restart, not a post-hoc diagnostic on a handful of
     points.

Reuses search/zark_core.py entirely for the incremental energy model,
certify() (the only bridge to the real, independent verify/checker.py),
and load_known_witness_rowmasks(). This file adds NO new K_{3,3}-detection
logic of its own -- only move-selection / meta-heuristic bookkeeping on top
of IncrementalState. Every "energy==0 at 133 edges" observation is
immediately certify()-ed before being believed, per the task's
certification discipline. assert_incremental_matches_full() is checked
periodically to catch drift in the new compound-move code paths.

Run with: .venv/bin/python search/tabu_search_attack.py [--quick]
See search/LOCAL_SEARCH_LOG_TABU.md for the full run log and honest results.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
import pathlib
import random
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from search.zark_core import (  # noqa: E402
    IncrementalState,
    M_ROWS,
    N_COLS,
    TARGET_EDGES,
    assert_incremental_matches_full,
    certify,
    load_known_witness_rowmasks,
)

_HERE = pathlib.Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Cost function (same "target" formulation as the prior workstream's Phase 1,
# so the only thing that differs between the two workstreams is move
# selection, not the objective being optimized).
# ---------------------------------------------------------------------------

def cost(energy: int, edges: int, target: int, big_penalty: float, edge_weight: float) -> float:
    return energy * big_penalty + abs(edges - target) * edge_weight


# ---------------------------------------------------------------------------
# Move proposal
# ---------------------------------------------------------------------------

def refresh_conflict_rows(state: IncrementalState) -> list[int]:
    """Rows implicated in currently-violating triples, WITH repeats (a row
    appearing in more violating triples is weighted more heavily when
    sampled -- naturally biases toward the most-conflicted rows, not just
    any conflicted row)."""
    triples = state.conflict_triples()
    rows = []
    for i, j, k in triples:
        rows.append(i)
        rows.append(j)
        rows.append(k)
    return rows


def propose_single_move(state: IncrementalState, rng: random.Random,
                         conflict_rows: list[int], bias_prob: float) -> tuple[int, int]:
    """Pick one cell to toggle. With probability `bias_prob` (if any conflict
    rows are known), pick a row implicated in a current conflict and a
    uniform-random column in that row. Otherwise, uniform-random cell over
    the whole board (preserves exploration)."""
    if conflict_rows and rng.random() < bias_prob:
        i = rng.choice(conflict_rows)
    else:
        i = rng.randrange(state.m)
    j = rng.randrange(state.n)
    return (i, j)


def propose_compound_move(state: IncrementalState, rng: random.Random,
                           conflict_rows: list[int]) -> list[tuple[int, int]]:
    """Propose a compound (large-neighborhood) move: 2-4 simultaneous cell
    toggles. Strategy: pick an actively-conflicting row-triple (or, if none
    exists right now, a random triple), find its shared/over-loaded columns
    (the columns causing popcount(r_i & r_j & r_k) > 2), and toggle OFF 1-2
    of those shared columns in a row of the triple (a direct, targeted
    conflict-repair move) while toggling ON 1-2 compensating cells elsewhere
    at random (to avoid the move being pure edge-loss, giving the search a
    chance to find a repaired-and-still-133-edges state). Applied and
    evaluated as a single atomic step by the caller."""
    triples = state.conflict_triples()
    if triples:
        i, j, k = rng.choice(triples)
    else:
        # No active conflict right now -- fall back to 3 rows biased toward
        # recently-conflicted rows if we have any memory of them, else pure
        # random, so compound moves remain useful for escaping non-conflict
        # local optima too (e.g. stuck below the edge target).
        pool = conflict_rows if conflict_rows else list(range(state.m))
        chosen = set()
        while len(chosen) < 3:
            chosen.add(rng.choice(pool) if conflict_rows else rng.randrange(state.m))
        i, j, k = tuple(chosen)

    common = state.rows[i] & state.rows[j] & state.rows[k]
    common_cols = [c for c in range(state.n) if (common >> c) & 1]

    moves: list[tuple[int, int]] = []
    if common_cols:
        n_off = rng.randint(1, min(2, len(common_cols)))
        off_cols = rng.sample(common_cols, n_off)
        for c in off_cols:
            r = rng.choice((i, j, k))
            if (r, c) not in moves:
                moves.append((r, c))

    # Add 1-2 compensating "turn on" cells elsewhere, so the compound move
    # isn't pure edge-loss -- gives the search a shot at landing back on
    # exactly 133 edges with fewer conflicts, in one atomic step.
    n_on = rng.randint(1, 2)
    on_added = 0
    attempts = 0
    while on_added < n_on and len(moves) < 4 and attempts < 30:
        attempts += 1
        ri = rng.randrange(state.m)
        rj = rng.randrange(state.n)
        if not state.is_set(ri, rj) and (ri, rj) not in moves:
            moves.append((ri, rj))
            on_added += 1

    if not moves:
        # Extremely unlikely fallback: no shared columns and no room found
        # for "on" moves -- just toggle a random cell in the triple.
        r = rng.choice((i, j, k))
        c = rng.randrange(state.n)
        moves = [(r, c)]

    return moves[:4] if len(moves) > 4 else moves


# ---------------------------------------------------------------------------
# Tabu + conflict-biased + compound-move search core
# ---------------------------------------------------------------------------

def tabu_conflict_search(
    state: IncrementalState,
    rng: random.Random,
    n_iters: int,
    t0: float,
    t_min: float,
    target: int,
    big_penalty: float,
    edge_weight: float,
    tabu_tenure: int = 12,
    compound_every: int = 250,
    patience: int = 300,
    conflict_bias_prob: float = 0.8,
    conflict_refresh_interval: int = 8,
    assert_every: int = 4000,
) -> dict:
    """
    Run the conflict-biased / tabu / compound-move search for n_iters
    "steps" (a step is one single-cell move OR one compound move -- compound
    moves count as a single step for iteration-budget purposes, same as the
    prior workstream's single-toggle steps, so restart/iteration counts are
    comparable in scale).
    """
    m, n = state.m, state.n
    cur_cost = cost(state.energy, state.edges, target, big_penalty, edge_weight)

    best_edges_at_zero_energy = state.edges if state.energy == 0 else -1
    best_rows_at_zero_energy = list(state.rows) if state.energy == 0 else None
    best_energy_at_target = state.energy if state.edges == target else math.inf
    best_rows_at_target = list(state.rows) if state.edges == target else None
    best_energy_ever = state.energy  # for the aspiration criterion (any edge count)

    tabu_until: dict[tuple[int, int], int] = {}
    conflict_rows: list[int] = refresh_conflict_rows(state)
    since_improve = 0
    n_compound_proposed = 0
    n_compound_accepted = 0
    n_single_proposed = 0
    n_single_accepted = 0
    n_tabu_blocked = 0
    n_aspiration_overrides = 0

    for t in range(n_iters):
        frac = t / max(1, n_iters - 1)
        T = t0 * ((t_min / t0) ** frac)

        if t % conflict_refresh_interval == 0:
            conflict_rows = refresh_conflict_rows(state)

        do_compound = (compound_every and t > 0 and t % compound_every == 0) or (
            patience and since_improve >= patience
        )

        if do_compound:
            moves = propose_compound_move(state, rng, conflict_rows)
            n_compound_proposed += 1
        else:
            moves = [propose_single_move(state, rng, conflict_rows, conflict_bias_prob)]
            n_single_proposed += 1

        for (i, j) in moves:
            state.toggle(i, j)
        new_cost = cost(state.energy, state.edges, target, big_penalty, edge_weight)
        d = new_cost - cur_cost

        is_tabu = any(tabu_until.get(mv, -1) > t for mv in moves)
        aspiration = state.energy < best_energy_ever
        accept_thermal = d <= 0 or rng.random() < math.exp(-d / max(T, 1e-9))

        if is_tabu and not aspiration:
            accept = False
        else:
            if is_tabu and aspiration:
                n_aspiration_overrides += 1
            accept = accept_thermal

        if accept:
            cur_cost = new_cost
            for mv in moves:
                tabu_until[mv] = t + tabu_tenure
            if do_compound:
                n_compound_accepted += 1
            else:
                n_single_accepted += 1
        else:
            for (i, j) in reversed(moves):
                state.toggle(i, j)
            if is_tabu:
                n_tabu_blocked += 1

        improved = False
        if state.energy == 0 and state.edges > best_edges_at_zero_energy:
            best_edges_at_zero_energy = state.edges
            best_rows_at_zero_energy = list(state.rows)
            improved = True
        if state.edges == target and state.energy < best_energy_at_target:
            best_energy_at_target = state.energy
            best_rows_at_target = list(state.rows)
            improved = True
        if state.energy < best_energy_ever:
            best_energy_ever = state.energy
            improved = True

        # Reset the stagnation counter on improvement, OR after a
        # patience-triggered compound move has actually been attempted
        # (whether or not it was accepted) -- otherwise, once patience is
        # exceeded once, `since_improve >= patience` stays true forever
        # (nothing here decrements it) and every subsequent iteration would
        # fire a compound move instead of a periodic one. This way a
        # patience-triggered compound move fires, then the search gets a
        # fresh `patience`-iteration window of single moves before the next
        # stagnation-triggered compound move.
        if improved or do_compound:
            since_improve = 0
        else:
            since_improve += 1

        if assert_every and (t + 1) % assert_every == 0:
            assert_incremental_matches_full(state)

    return dict(
        best_edges_at_zero_energy=best_edges_at_zero_energy,
        best_rows_at_zero_energy=best_rows_at_zero_energy,
        best_energy_at_target=best_energy_at_target,
        best_rows_at_target=best_rows_at_target,
        n_compound_proposed=n_compound_proposed,
        n_compound_accepted=n_compound_accepted,
        n_single_proposed=n_single_proposed,
        n_single_accepted=n_single_accepted,
        n_tabu_blocked=n_tabu_blocked,
        n_aspiration_overrides=n_aspiration_overrides,
    )


# ---------------------------------------------------------------------------
# Result bookkeeping (mirrors local_search_attack.py's RunResult shape so
# the two workstreams' JSON summaries are easy to compare side by side).
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class RunResult:
    label: str
    seed: int
    params: dict
    best_edges_at_zero_energy: int
    best_energy_at_target: int
    iters_run: int
    wall_time: float
    hit_target_zero: bool
    stats: dict
    best_rows_at_zero_energy: list[int] = dataclasses.field(default_factory=list)
    best_rows_at_target: list[int] | None = None


def run_restarts(n_restarts: int, n_iters: int, quick: bool = False) -> list[RunResult]:
    """Seeded from the known 132-edge witness plus one added edge (133
    edges, >=1 conflict) -- same setup as the prior workstream's Phase 1,
    so the comparison isolates move-selection strategy as the only
    variable."""
    base_rows = load_known_witness_rowmasks()
    results = []
    t0_choices = [1.0, 2.0, 4.0]
    edge_weight_choices = [1.0, 3.0]
    big_penalty_choices = [200.0, 1000.0, 5000.0]
    tabu_tenure_choices = [6, 12, 20]
    bias_prob_choices = [0.7, 0.8, 0.9]
    compound_every_choices = [150, 250, 400]
    patience_choices = [200, 300, 500]

    for k in range(n_restarts):
        seed = 400_000 + k
        rng = random.Random(seed)
        t0 = rng.choice(t0_choices)
        edge_weight = rng.choice(edge_weight_choices)
        big_penalty = rng.choice(big_penalty_choices)
        tabu_tenure = rng.choice(tabu_tenure_choices)
        bias_prob = rng.choice(bias_prob_choices)
        compound_every = rng.choice(compound_every_choices)
        patience = rng.choice(patience_choices)

        st = IncrementalState(base_rows)
        zero_cells = [(i, j) for i in range(st.m) for j in range(st.n) if not st.is_set(i, j)]
        i0, j0 = rng.choice(zero_cells)
        st.toggle(i0, j0)
        assert st.edges == 133

        t_start = time.time()
        summary = tabu_conflict_search(
            st, rng, n_iters=n_iters, t0=t0, t_min=0.02, target=TARGET_EDGES,
            big_penalty=big_penalty, edge_weight=edge_weight,
            tabu_tenure=tabu_tenure, compound_every=compound_every,
            patience=patience, conflict_bias_prob=bias_prob,
        )
        wall = time.time() - t_start
        assert_incremental_matches_full(st)

        rr = RunResult(
            label="tabu_conflict_biased",
            seed=seed,
            params=dict(t0=t0, edge_weight=edge_weight, big_penalty=big_penalty,
                        tabu_tenure=tabu_tenure, bias_prob=bias_prob,
                        compound_every=compound_every, patience=patience,
                        first_added_cell=[i0, j0]),
            best_edges_at_zero_energy=summary["best_edges_at_zero_energy"],
            best_energy_at_target=(
                summary["best_energy_at_target"] if math.isfinite(summary["best_energy_at_target"]) else -1
            ),
            iters_run=n_iters,
            wall_time=wall,
            hit_target_zero=(summary["best_edges_at_zero_energy"] >= TARGET_EDGES),
            stats={k2: v2 for k2, v2 in summary.items() if k2.startswith("n_")},
            best_rows_at_zero_energy=summary["best_rows_at_zero_energy"] or [],
            best_rows_at_target=summary["best_rows_at_target"],
        )
        results.append(rr)
        if quick and k >= 2:
            break
    return results


def summarize_and_certify(all_results: list[RunResult]) -> dict:
    report = {"hits_at_133_zero_energy": []}
    hits = [r for r in all_results if r.hit_target_zero]
    for r in hits:
        rows = r.best_rows_at_zero_energy
        res = certify(rows, n_cols=N_COLS, expected_edges=TARGET_EDGES)
        report["hits_at_133_zero_energy"].append({
            "label": r.label, "seed": r.seed, "params": r.params, "checker_result": res,
        })

    def best_key(r: RunResult):
        return (r.best_edges_at_zero_energy,
                -r.best_energy_at_target if r.best_energy_at_target >= 0 else -math.inf)

    if all_results:
        best = max(all_results, key=best_key)
        report["best_overall_run"] = dict(
            label=best.label, seed=best.seed, params=best.params,
            best_edges_at_zero_energy=best.best_edges_at_zero_energy,
            best_energy_at_target=best.best_energy_at_target,
        )
        if best.best_rows_at_zero_energy:
            rows = best.best_rows_at_zero_energy
            n_edges = sum(bin(r).count("1") for r in rows)
            res = certify(rows, n_cols=N_COLS, expected_edges=n_edges)
            report["best_overall_certified"] = res

        # Also certify the best 133-edge near-miss (min energy at target),
        # for direct floor-comparison with the prior workstream, even
        # though a nonzero-energy graph is never reported as a positive
        # result (it genuinely contains K_{3,3}s).
        best_near_miss = min(
            (r for r in all_results if r.best_rows_at_target is not None),
            key=lambda r: r.best_energy_at_target,
            default=None,
        )
        if best_near_miss is not None:
            report["best_near_miss_at_133"] = dict(
                seed=best_near_miss.seed,
                params=best_near_miss.params,
                energy=best_near_miss.best_energy_at_target,
            )
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--restarts", type=int, default=150)
    ap.add_argument("--iters", type=int, default=20000)
    args = ap.parse_args()

    if args.quick:
        args.restarts = 3
        args.iters = 500

    t_all = time.time()
    print(f"=== Conflict-biased / tabu / compound-move search "
          f"({args.restarts} restarts x {args.iters} iters) ===")
    results = run_restarts(args.restarts, args.iters, quick=args.quick)
    print(f"done in {time.time()-t_all:.1f}s")

    hits = [r for r in results if r.hit_target_zero]
    print(f"hits at 133/energy0: {len(hits)} / {len(results)}")

    energies = sorted(r.best_energy_at_target for r in results if r.best_energy_at_target >= 0)
    print(f"best_energy_at_target histogram (sorted): {energies[:20]}{'...' if len(energies) > 20 else ''}")
    if energies:
        print(f"min energy at 133 edges across all restarts: {energies[0]}")

    print("\n=== Certification pass ===")
    report = summarize_and_certify(results)
    print(json.dumps({k: v for k, v in report.items() if k != "best_overall_certified"}, indent=2, default=str)[:4000])
    if "best_overall_certified" in report:
        print("best_overall_certified:", report["best_overall_certified"])

    out_path = _HERE / "tabu_search_results.json"
    with open(out_path, "w") as f:
        json.dump({
            "results_summary": [
                dataclasses.asdict(r) | {"best_rows_at_zero_energy": "omitted", "best_rows_at_target": "omitted"}
                for r in results
            ],
            "certification_report": report,
            "total_wall_time": time.time() - t_all,
        }, f, indent=2, default=str)
    print(f"\nWrote summary to {out_path}")
    print(f"Total wall time: {time.time()-t_all:.1f}s")


if __name__ == "__main__":
    main()
