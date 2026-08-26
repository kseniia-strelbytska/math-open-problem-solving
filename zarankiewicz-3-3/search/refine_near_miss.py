"""
Follow-up refinement pass on the near-misses found by local_search_attack.py
phase 1: several seeded SA runs bottomed out at conflict energy 2 (never 0)
while sitting at exactly 133 edges. This script:

  1. Reproduces those specific seeds deterministically (same rng sequence)
     to recover the actual 133-edge / energy-2 matrix, not just the scalar
     energy that was logged.
  2. Runs an EXHAUSTIVE single-swap check on each: try every (turn off one
     currently-set cell, turn on one currently-unset cell) pair -- this
     preserves edges==133 exactly and is a strictly stronger, non-random
     check than more stochastic SA steps ("is this specific near-miss
     literally one swap away from a solution?"). At 133 edges x 139
     non-edges this is ~18.5k pair evaluations per state, fully tractable.
  3. Runs a longer, multi-cycle ("reheat") anneal from each near-miss as a
     second, independent refinement attempt.

Any energy==0 result at 133 edges found here is immediately certified via
zark_core.certify() before being trusted -- see LOCAL_SEARCH_LOG.md.
"""
from __future__ import annotations

import math
import pathlib
import random
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from search.zark_core import (  # noqa: E402
    IncrementalState,
    N_COLS,
    TARGET_EDGES,
    assert_incremental_matches_full,
    certify,
    load_known_witness_rowmasks,
)
from search.local_search_attack import anneal, cost  # noqa: E402


def reproduce_seed_state(seed: int, n_iters: int) -> tuple[IncrementalState, dict]:
    """Exactly reproduce a phase1_seeded run for one seed (same rng
    sequence as phase1_seeded in local_search_attack.py) and return the
    final IncrementalState plus the anneal() summary."""
    base_rows = load_known_witness_rowmasks()
    modes = ["target", "reward"]
    t0_choices = [1.0, 2.0, 4.0]
    edge_weight_choices = [1.0, 3.0]
    big_penalty_choices = [200.0, 1000.0, 5000.0]

    # NOTE: mirrors phase1_seeded's per-k derivation. k is recovered from
    # seed = 100_000 + k.
    k = seed - 100_000
    rng = random.Random(seed)
    mode = modes[k % len(modes)]
    t0 = rng.choice(t0_choices)
    edge_weight = rng.choice(edge_weight_choices)
    big_penalty = rng.choice(big_penalty_choices)

    st = IncrementalState(base_rows)
    zero_cells = [(i, j) for i in range(st.m) for j in range(st.n) if not st.is_set(i, j)]
    i0, j0 = rng.choice(zero_cells)
    st.toggle(i0, j0)

    summary = anneal(
        st, rng, n_iters=n_iters, t0=t0, t_min=0.02, mode=mode,
        target=TARGET_EDGES, big_penalty=big_penalty, edge_weight=edge_weight,
    )
    return st, summary


def exhaustive_single_swap(rows: list[int], n_cols: int = N_COLS) -> dict:
    """Given a 133-edge state's rows, try EVERY (turn-off-one-edge,
    turn-on-one-non-edge) pair exhaustively. Returns the best energy found
    and, if 0 is found, the winning rows. Uses IncrementalState.toggle
    twice per candidate pair (off, on), reverting if not an improvement."""
    st = IncrementalState(rows, n_cols=n_cols)
    assert st.edges == TARGET_EDGES
    base_energy = st.energy

    set_cells = [(i, j) for i in range(st.m) for j in range(st.n) if st.is_set(i, j)]
    unset_cells = [(i, j) for i in range(st.m) for j in range(st.n) if not st.is_set(i, j)]

    best_energy = base_energy
    best_rows = list(st.rows)
    checked = 0
    for (i1, j1) in set_cells:
        st.toggle(i1, j1)  # turn off
        for (i2, j2) in unset_cells:
            st.toggle(i2, j2)  # turn on
            checked += 1
            if st.energy < best_energy:
                best_energy = st.energy
                best_rows = list(st.rows)
            st.toggle(i2, j2)  # revert turn-on
        st.toggle(i1, j1)  # revert turn-off

    assert_incremental_matches_full(st)
    assert st.energy == base_energy and st.edges == TARGET_EDGES, "swap search failed to restore state"
    return dict(base_energy=base_energy, best_energy=best_energy, best_rows=best_rows, pairs_checked=checked)


def reheat_anneal(state: IncrementalState, rng: random.Random, n_cycles: int, iters_per_cycle: int,
                   t0: float, t_min: float, mode: str, big_penalty: float, edge_weight: float) -> dict:
    """Multiple independent cooling cycles from the SAME running state
    (temperature is reset to t0 at the start of each cycle), as a
    diversification tactic distinct from a single monotonic schedule."""
    best_energy_at_target = state.energy if state.edges == TARGET_EDGES else math.inf
    best_rows_at_target = list(state.rows) if state.edges == TARGET_EDGES else None
    best_edges_at_zero_energy = state.edges if state.energy == 0 else -1

    for c in range(n_cycles):
        summary = anneal(
            state, rng, n_iters=iters_per_cycle, t0=t0, t_min=t_min, mode=mode,
            target=TARGET_EDGES, big_penalty=big_penalty, edge_weight=edge_weight,
        )
        if summary["best_energy_at_target"] < best_energy_at_target:
            best_energy_at_target = summary["best_energy_at_target"]
            best_rows_at_target = summary["best_rows_at_target"]
        if summary["best_edges_at_zero_energy"] > best_edges_at_zero_energy:
            best_edges_at_zero_energy = summary["best_edges_at_zero_energy"]

    return dict(
        best_energy_at_target=best_energy_at_target,
        best_rows_at_target=best_rows_at_target,
        best_edges_at_zero_energy=best_edges_at_zero_energy,
    )


def main():
    near_miss_seeds = [100004, 100085, 100094, 100097, 100098, 100100, 100132]
    n_iters_reproduce = 20000  # must match the original phase1 run's --phase1-iters

    print(f"Reproducing {len(near_miss_seeds)} energy=2-at-133 near-miss states...")
    overall_best_swap = None
    overall_best_reheat = None

    for seed in near_miss_seeds:
        t_start = time.time()
        st, summary = reproduce_seed_state(seed, n_iters_reproduce)
        reproduced_energy = summary["best_energy_at_target"]
        reproduced_rows = summary["best_rows_at_target"]
        print(f"seed={seed}: reproduced best_energy_at_target={reproduced_energy} "
              f"(expected 2) in {time.time()-t_start:.1f}s")
        if reproduced_rows is None or reproduced_energy != 2:
            print(f"  WARNING: reproduction mismatch (got {reproduced_energy}, expected 2) -- skipping this seed")
            continue

        # 1. Exhaustive single-swap check on the exact near-miss matrix.
        t0 = time.time()
        swap_result = exhaustive_single_swap(reproduced_rows)
        print(f"  exhaustive swap: base_energy={swap_result['base_energy']} "
              f"best_energy_after_1_swap={swap_result['best_energy']} "
              f"({swap_result['pairs_checked']} pairs) in {time.time()-t0:.1f}s")
        if overall_best_swap is None or swap_result["best_energy"] < overall_best_swap["best_energy"]:
            overall_best_swap = swap_result | {"seed": seed}

        # 2. Reheat-anneal refinement (5 cycles x 20000 iters) from the
        #    same near-miss state.
        rng = random.Random(seed * 7 + 1)
        st2 = IncrementalState(reproduced_rows)
        t0 = time.time()
        reheat_result = reheat_anneal(
            st2, rng, n_cycles=5, iters_per_cycle=20000,
            t0=1.5, t_min=0.01, mode="target", big_penalty=2000.0, edge_weight=2.0,
        )
        print(f"  reheat anneal (5x20000): best_energy_at_target={reheat_result['best_energy_at_target']} "
              f"best_edges_at_zero_energy={reheat_result['best_edges_at_zero_energy']} "
              f"in {time.time()-t0:.1f}s")
        if overall_best_reheat is None or reheat_result["best_energy_at_target"] < overall_best_reheat["best_energy_at_target"]:
            overall_best_reheat = reheat_result | {"seed": seed}

    print("\n=== Summary ===")
    if overall_best_swap:
        print(f"Best exhaustive-swap result: seed={overall_best_swap['seed']} "
              f"base_energy={overall_best_swap['base_energy']} -> best_energy={overall_best_swap['best_energy']}")
        if overall_best_swap["best_energy"] == 0:
            res = certify(overall_best_swap["best_rows"], expected_edges=TARGET_EDGES)
            print("  *** CERTIFYING energy=0 swap result ***:", res)
        elif overall_best_swap["best_energy"] < overall_best_swap["base_energy"]:
            print("  (improved but did not reach 0; not certifiable as K33-free)")
    if overall_best_reheat:
        print(f"Best reheat-anneal result: seed={overall_best_reheat['seed']} "
              f"best_energy_at_target={overall_best_reheat['best_energy_at_target']}")
        if overall_best_reheat["best_energy_at_target"] == 0 and overall_best_reheat["best_rows_at_target"]:
            res = certify(overall_best_reheat["best_rows_at_target"], expected_edges=TARGET_EDGES)
            print("  *** CERTIFYING energy=0 reheat result ***:", res)


if __name__ == "__main__":
    main()
