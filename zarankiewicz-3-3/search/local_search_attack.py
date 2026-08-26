"""
Local-search / simulated-annealing attack on Z(16,17,3,3): does a 133-edge
K_{3,3}-free 16x17 bipartite graph exist?

Builds entirely on search/zark_core.py (IncrementalState, certify(),
load_known_witness_rowmasks()) -- see that module's docstring for the
incremental conflict-energy model. This file is SEARCH-SIDE ONLY: it never
decides a result is real. Every "energy==0" observation at edges==133 is
immediately re-checked with zark_core.certify(), which calls the real,
independently-developed verify/checker.py. See LOCAL_SEARCH_LOG.md for the
full run log, parameters, and honest results (including negative ones).

Three attack phases (see README.md task / LOCAL_SEARCH_LOG.md):
  1. SA seeded from the known 132-edge witness (add a 133rd edge, anneal).
  2. SA from scratch (random and greedy starting points), independent of
     the known witness's basin of attraction.
  3. A structurally-motivated construction attempt (quadratic-residue /
     circulant ansatz over GF(17)), evaluated the same way.

Run with:  .venv/bin/python search/local_search_attack.py [--quick]
"""
from __future__ import annotations

import argparse
import dataclasses
import itertools
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
    matrix_to_rowmasks,
)

_HERE = pathlib.Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent


# ---------------------------------------------------------------------------
# Result bookkeeping
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class RunResult:
    label: str
    seed: int
    params: dict
    best_edges_at_zero_energy: int
    best_energy_at_target: int  # min energy ever observed while edges==TARGET_EDGES
    iters_run: int
    wall_time: float
    hit_target_zero: bool  # True iff energy==0 was observed at edges==TARGET_EDGES
    best_rows_at_zero_energy: list[int] = dataclasses.field(default_factory=list)
    best_rows_at_target: list[int] | None = None

    def to_json(self) -> dict:
        d = dataclasses.asdict(self)
        # rows lists can be long; keep them (only 16 ints), fine to log.
        return d


# ---------------------------------------------------------------------------
# Simulated annealing core
# ---------------------------------------------------------------------------

def cost(energy: int, edges: int, mode: str, target: int, big_penalty: float, edge_weight: float) -> float:
    if mode == "target":
        return energy * big_penalty + abs(edges - target) * edge_weight
    elif mode == "reward":
        return energy * big_penalty - edges
    else:
        raise ValueError(mode)


def anneal(
    state: IncrementalState,
    rng: random.Random,
    n_iters: int,
    t0: float,
    t_min: float,
    mode: str,
    target: int,
    big_penalty: float,
    edge_weight: float,
    assert_every: int = 4000,
) -> dict:
    """
    Run SA for n_iters single-cell-toggle moves against `state` in place.
    Returns a dict summarizing the best things seen during the run:
      best_edges_at_zero_energy, best_rows_at_zero_energy (deep copy),
      best_energy_at_target, best_rows_at_target.
    """
    m, n = state.m, state.n
    cur_cost = cost(state.energy, state.edges, mode, target, big_penalty, edge_weight)

    best_edges_at_zero_energy = state.edges if state.energy == 0 else -1
    best_rows_at_zero_energy = list(state.rows) if state.energy == 0 else None
    best_energy_at_target = state.energy if state.edges == target else math.inf
    best_rows_at_target = list(state.rows) if state.edges == target else None

    for t in range(n_iters):
        # geometric cooling
        frac = t / max(1, n_iters - 1)
        T = t0 * ((t_min / t0) ** frac)

        i = rng.randrange(m)
        j = rng.randrange(n)
        delta_energy = state.toggle(i, j)  # mutates in place, returns energy delta
        new_cost = cost(state.energy, state.edges, mode, target, big_penalty, edge_weight)
        d = new_cost - cur_cost

        accept = d <= 0 or rng.random() < math.exp(-d / max(T, 1e-9))
        if accept:
            cur_cost = new_cost
        else:
            # revert
            state.toggle(i, j)
            # cur_cost unchanged (state restored)

        if state.energy == 0 and state.edges > best_edges_at_zero_energy:
            best_edges_at_zero_energy = state.edges
            best_rows_at_zero_energy = list(state.rows)

        if state.edges == target and state.energy < best_energy_at_target:
            best_energy_at_target = state.energy
            best_rows_at_target = list(state.rows)

        if assert_every and (t + 1) % assert_every == 0:
            assert_incremental_matches_full(state)

    return dict(
        best_edges_at_zero_energy=best_edges_at_zero_energy,
        best_rows_at_zero_energy=best_rows_at_zero_energy,
        best_energy_at_target=best_energy_at_target,
        best_rows_at_target=best_rows_at_target,
    )


# ---------------------------------------------------------------------------
# Phase 1: seeded from the known 132-edge witness
# ---------------------------------------------------------------------------

def phase1_seeded(n_restarts: int, n_iters: int, quick: bool = False) -> list[RunResult]:
    base_rows = load_known_witness_rowmasks()
    results = []
    modes = ["target", "reward"]
    t0_choices = [1.0, 2.0, 4.0]
    edge_weight_choices = [1.0, 3.0]
    big_penalty_choices = [200.0, 1000.0, 5000.0]

    for k in range(n_restarts):
        seed = 100_000 + k
        rng = random.Random(seed)
        mode = modes[k % len(modes)]
        t0 = rng.choice(t0_choices)
        edge_weight = rng.choice(edge_weight_choices)
        big_penalty = rng.choice(big_penalty_choices)

        st = IncrementalState(base_rows)
        # Add one random edge first (a missing cell), deliberately creating
        # at least one conflict, per task instructions.
        zero_cells = [(i, j) for i in range(st.m) for j in range(st.n) if not st.is_set(i, j)]
        i0, j0 = rng.choice(zero_cells)
        st.toggle(i0, j0)
        assert st.edges == 133

        t_start = time.time()
        summary = anneal(
            st, rng, n_iters=n_iters, t0=t0, t_min=0.02, mode=mode,
            target=TARGET_EDGES, big_penalty=big_penalty, edge_weight=edge_weight,
        )
        wall = time.time() - t_start
        assert_incremental_matches_full(st)

        rr = RunResult(
            label="phase1_seeded",
            seed=seed,
            params=dict(mode=mode, t0=t0, edge_weight=edge_weight, big_penalty=big_penalty,
                        first_added_cell=[i0, j0]),
            best_edges_at_zero_energy=summary["best_edges_at_zero_energy"],
            best_energy_at_target=(
                summary["best_energy_at_target"] if math.isfinite(summary["best_energy_at_target"]) else -1
            ),
            iters_run=n_iters,
            wall_time=wall,
            hit_target_zero=(summary["best_edges_at_zero_energy"] >= TARGET_EDGES),
            best_rows_at_zero_energy=summary["best_rows_at_zero_energy"] or [],
            best_rows_at_target=summary["best_rows_at_target"],
        )
        results.append(rr)
        if quick and k >= 2:
            break
    return results


# ---------------------------------------------------------------------------
# Phase 2: from-scratch (random + greedy starting points)
# ---------------------------------------------------------------------------

def random_start_rows(rng: random.Random, m: int, n: int, n_edges: int) -> list[int]:
    cells = [(i, j) for i in range(m) for j in range(n)]
    chosen = rng.sample(cells, n_edges)
    rows = [0] * m
    for i, j in chosen:
        rows[i] |= (1 << j)
    return rows


def greedy_start_rows(rng: random.Random, m: int, n: int) -> list[int]:
    """Greedily add edges one at a time, in random order, only if the
    addition keeps conflict energy at 0. Stops when no zero-cell addition
    keeps energy at 0 (i.e. reaches a maximal K_{3,3}-free graph greedily).
    Not guaranteed anywhere near optimal -- just a different, algorithm-
    diverse starting basin for the SA to refine from."""
    st = IncrementalState([0] * m, n_cols=n)
    cells = [(i, j) for i in range(m) for j in range(n)]
    rng.shuffle(cells)
    for i, j in cells:
        delta = st.toggle(i, j)
        if st.energy != 0:
            st.toggle(i, j)  # revert
    return st.rows


def phase2_scratch(n_restarts_random: int, n_restarts_greedy: int, n_iters: int, quick: bool = False) -> list[RunResult]:
    results = []
    modes = ["target", "reward"]

    # 2a: pure random 133-edge start
    for k in range(n_restarts_random):
        seed = 200_000 + k
        rng = random.Random(seed)
        rows = random_start_rows(rng, M_ROWS, N_COLS, TARGET_EDGES)
        st = IncrementalState(rows)
        mode = modes[k % len(modes)]
        t0 = rng.choice([2.0, 4.0, 8.0])

        t_start = time.time()
        summary = anneal(
            st, rng, n_iters=n_iters, t0=t0, t_min=0.02, mode=mode,
            target=TARGET_EDGES, big_penalty=1000.0, edge_weight=1.0,
        )
        wall = time.time() - t_start
        assert_incremental_matches_full(st)

        results.append(RunResult(
            label="phase2_random_start",
            seed=seed,
            params=dict(mode=mode, t0=t0, start_edges=TARGET_EDGES),
            best_edges_at_zero_energy=summary["best_edges_at_zero_energy"],
            best_energy_at_target=(
                summary["best_energy_at_target"] if math.isfinite(summary["best_energy_at_target"]) else -1
            ),
            iters_run=n_iters,
            wall_time=wall,
            hit_target_zero=(summary["best_edges_at_zero_energy"] >= TARGET_EDGES),
            best_rows_at_zero_energy=summary["best_rows_at_zero_energy"] or [],
            best_rows_at_target=summary["best_rows_at_target"],
        ))
        if quick and k >= 1:
            break

    # 2b: greedy K33-free construction, then SA refine
    for k in range(n_restarts_greedy):
        seed = 300_000 + k
        rng = random.Random(seed)
        rows = greedy_start_rows(rng, M_ROWS, N_COLS)
        st = IncrementalState(rows)
        greedy_edges = st.edges
        mode = modes[k % len(modes)]
        t0 = rng.choice([1.0, 2.0, 4.0])

        t_start = time.time()
        summary = anneal(
            st, rng, n_iters=n_iters, t0=t0, t_min=0.02, mode=mode,
            target=TARGET_EDGES, big_penalty=1000.0, edge_weight=1.0,
        )
        wall = time.time() - t_start
        assert_incremental_matches_full(st)

        results.append(RunResult(
            label="phase2_greedy_start",
            seed=seed,
            params=dict(mode=mode, t0=t0, greedy_start_edges=greedy_edges),
            best_edges_at_zero_energy=summary["best_edges_at_zero_energy"],
            best_energy_at_target=(
                summary["best_energy_at_target"] if math.isfinite(summary["best_energy_at_target"]) else -1
            ),
            iters_run=n_iters,
            wall_time=wall,
            hit_target_zero=(summary["best_edges_at_zero_energy"] >= TARGET_EDGES),
            best_rows_at_zero_energy=summary["best_rows_at_zero_energy"] or [],
            best_rows_at_target=summary["best_rows_at_target"],
        ))
        if quick and k >= 1:
            break

    return results


# ---------------------------------------------------------------------------
# Phase 3: structurally-motivated construction (quadratic residues / GF(17))
# ---------------------------------------------------------------------------

def quadratic_residues(p: int) -> set[int]:
    return {(x * x) % p for x in range(1, p)}


def build_circulant_rows(m: int, n: int, connection_set: set[int], row_offset: int = 0) -> list[int]:
    """rows i in [0,m), cols j in [0,n): edge iff (j - i) mod n in connection_set.
    (m need not equal n; row index i is just used mod n for the difference.)"""
    rows = []
    for i in range(m):
        mask = 0
        for j in range(n):
            if (j - (i + row_offset)) % n in connection_set:
                mask |= 1 << j
        rows.append(mask)
    return rows


def phase3_structural() -> list[dict]:
    """Try a handful of algebraic/circulant ansatze over GF(17) (17 is
    prime, matches the column count). Report edges + energy for each,
    honestly, whether or not any beat/match 132-133."""
    out = []
    p = 17
    qr = quadratic_residues(p)  # |QR(17)| = 8
    non_qr = set(range(1, p)) - qr

    candidates = {
        "QR_mod17_16rows": (qr, M_ROWS),
        "QR_plus_zero_mod17_16rows": (qr | {0}, M_ROWS),
        "non_QR_mod17_16rows": (non_qr, M_ROWS),
        "QR_mod17_17rows_truncated16": (qr, M_ROWS),  # same as first, kept for clarity of naming
    }

    for name, (conn_set, m) in candidates.items():
        rows = build_circulant_rows(m, N_COLS, conn_set)
        st = IncrementalState(rows)
        out.append(dict(
            name=name,
            connection_set=sorted(conn_set),
            conn_set_size=len(conn_set),
            edges=st.edges,
            energy=st.energy,
        ))

    # Also try connection sets built by taking QR and adding one extra
    # difference (to push degree from 8 toward 9, i.e. edges from 128
    # toward 144), to see how quickly circulant symmetry creates conflicts.
    for extra in sorted(non_qr):
        conn_set = qr | {extra}
        rows = build_circulant_rows(M_ROWS, N_COLS, conn_set)
        st = IncrementalState(rows)
        out.append(dict(
            name=f"QR_mod17_plus_{extra}",
            connection_set=sorted(conn_set),
            conn_set_size=len(conn_set),
            edges=st.edges,
            energy=st.energy,
        ))

    return out


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------

def summarize_and_certify(all_results: list[RunResult]) -> dict:
    """Look across all RunResults for the best candidate(s); certify any
    energy==0-at-133 hit immediately (per task instructions); also certify
    the single best near-miss found (for exact edge/energy reporting)."""
    report = {"hits_at_133_zero_energy": [], "best_overall": None}

    hits = [r for r in all_results if r.hit_target_zero]
    for r in hits:
        rows = r.best_rows_at_zero_energy
        res = certify(rows, n_cols=N_COLS, expected_edges=TARGET_EDGES)
        report["hits_at_133_zero_energy"].append({
            "label": r.label, "seed": r.seed, "params": r.params, "checker_result": res,
        })

    # Best overall candidate: prefer highest edges at energy==0; tie-break
    # by lowest best_energy_at_target.
    def best_key(r: RunResult):
        return (r.best_edges_at_zero_energy, -r.best_energy_at_target if r.best_energy_at_target >= 0 else -math.inf)

    if all_results:
        best = max(all_results, key=best_key)
        report["best_overall_run"] = dict(
            label=best.label, seed=best.seed, params=best.params,
            best_edges_at_zero_energy=best.best_edges_at_zero_energy,
            best_energy_at_target=best.best_energy_at_target,
        )
        # Certify whichever concrete candidate is most informative: if we
        # have rows at 133 edges (even with energy>0 they're not
        # certifiable as K33-free, but let's certify the best zero-energy
        # candidate found anywhere, since that's a real K33-free claim).
        if best.best_rows_at_zero_energy:
            rows = best.best_rows_at_zero_energy
            n_edges = sum(bin(r).count("1") for r in rows)
            res = certify(rows, n_cols=N_COLS, expected_edges=n_edges)
            report["best_overall_certified"] = res
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="tiny smoke-test run")
    ap.add_argument("--phase1-restarts", type=int, default=150)
    ap.add_argument("--phase1-iters", type=int, default=20000)
    ap.add_argument("--phase2-random-restarts", type=int, default=40)
    ap.add_argument("--phase2-greedy-restarts", type=int, default=40)
    ap.add_argument("--phase2-iters", type=int, default=30000)
    args = ap.parse_args()

    if args.quick:
        args.phase1_restarts = 3
        args.phase1_iters = 500
        args.phase2_random_restarts = 2
        args.phase2_greedy_restarts = 2
        args.phase2_iters = 500

    t_all = time.time()
    print("=== Phase 3: structural (quadratic-residue / circulant over GF(17)) ===")
    p3 = phase3_structural()
    for row in p3:
        print(f"  {row['name']:30s} |D|={row['conn_set_size']:2d}  edges={row['edges']:4d}  energy={row['energy']:6d}")

    print(f"\n=== Phase 1: SA seeded from known 132-edge witness "
          f"({args.phase1_restarts} restarts x {args.phase1_iters} iters) ===")
    t0 = time.time()
    p1 = phase1_seeded(args.phase1_restarts, args.phase1_iters, quick=args.quick)
    print(f"  done in {time.time()-t0:.1f}s")
    hits1 = [r for r in p1 if r.hit_target_zero]
    print(f"  hits at 133/energy0: {len(hits1)} / {len(p1)}")
    best1 = max(p1, key=lambda r: (r.best_edges_at_zero_energy,))
    print(f"  best run: edges_at_zero_energy={best1.best_edges_at_zero_energy} "
          f"best_energy_at_133={best1.best_energy_at_target} params={best1.params}")

    print(f"\n=== Phase 2: SA from scratch "
          f"({args.phase2_random_restarts} random + {args.phase2_greedy_restarts} greedy starts "
          f"x {args.phase2_iters} iters) ===")
    t0 = time.time()
    p2 = phase2_scratch(args.phase2_random_restarts, args.phase2_greedy_restarts, args.phase2_iters, quick=args.quick)
    print(f"  done in {time.time()-t0:.1f}s")
    hits2 = [r for r in p2 if r.hit_target_zero]
    print(f"  hits at 133/energy0: {len(hits2)} / {len(p2)}")
    best2 = max(p2, key=lambda r: (r.best_edges_at_zero_energy,))
    print(f"  best run: edges_at_zero_energy={best2.best_edges_at_zero_energy} "
          f"best_energy_at_133={best2.best_energy_at_target} params={best2.params}")

    all_results = p1 + p2
    print("\n=== Certification pass ===")
    report = summarize_and_certify(all_results)
    print(json.dumps({k: v for k, v in report.items() if k != "best_overall_certified"}, indent=2, default=str)[:4000])
    if "best_overall_certified" in report:
        print("best_overall_certified:", report["best_overall_certified"])

    # Persist machine-readable summary for the log / follow-up.
    out_path = _HERE / "local_search_results.json"
    with open(out_path, "w") as f:
        json.dump({
            "phase3_structural": p3,
            "phase1_summary": [dataclasses.asdict(r) | {"best_rows_at_zero_energy": "omitted", "best_rows_at_target": "omitted"} for r in p1],
            "phase2_summary": [dataclasses.asdict(r) | {"best_rows_at_zero_energy": "omitted", "best_rows_at_target": "omitted"} for r in p2],
            "certification_report": {k: v for k, v in report.items()},
            "total_wall_time": time.time() - t_all,
        }, f, indent=2, default=str)
    print(f"\nWrote summary to {out_path}")
    print(f"Total wall time: {time.time()-t_all:.1f}s")


if __name__ == "__main__":
    main()
