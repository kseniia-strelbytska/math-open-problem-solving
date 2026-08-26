"""
Runs actual SAT attack attempts using the validated encoding in
sat_encoding.py: first against a cell with an independently-verified known
exact answer (Z(13,18,3,3) = 116, see PROGRESS.md), as a pipeline sanity
check, then against the real target (Z(16,17,3,3), K in {132,133,134}).

This script deliberately does NOT decide anything by itself -- any SAT
witness it finds is re-verified with verify/checker.py before being
reported (see checker_verified in the output), and any UNSAT result is
reported as exactly that: "the solver returned UNSAT for this exact CNF",
with no additional interpretation layered on. See SAT_LOG.md for the
actual runs, their timings, and what was concluded from them.

Usage:
    .venv/bin/python search/sat_attack.py <m> <n> <K> --out <path.json> \
        [--solver cadical153|glucose3|minisat22] [--no-symmetry-breaking]

Writes (and repeatedly overwrites, at each phase transition) a JSON result
file at --out, so that if this process is killed by an external wall-clock
timeout (e.g. `timeout 1500 ...`), the file on disk still shows how far it
got (e.g. "status": "solving" with instance stats already recorded, vs.
never having started) -- a kill during solve() is distinguishable from a
kill before the instance was even built.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent
for p in (_HERE, _REPO_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import sat_encoding as se  # noqa: E402
from verify import checker  # noqa: E402
from pysat.card import EncType  # noqa: E402


def _card_enc(name: str):
    return getattr(EncType, name)


def _solver_cls(name: str):
    from pysat.solvers import Glucose3, Cadical153, Minisat22
    return {
        "cadical153": Cadical153,
        "glucose3": Glucose3,
        "minisat22": Minisat22,
    }[name]


def _write(out_path: Path, result: dict) -> None:
    out_path.write_text(json.dumps(result, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("m", type=int)
    ap.add_argument("n", type=int)
    ap.add_argument("K", type=int)
    ap.add_argument("--solver", default="cadical153",
                     choices=["cadical153", "glucose3", "minisat22"])
    ap.add_argument("--no-symmetry-breaking", action="store_true")
    ap.add_argument("--card-encoding", default="seqcounter")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    sym = not args.no_symmetry_breaking
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "m": args.m,
        "n": args.n,
        "K": args.K,
        "solver": args.solver,
        "symmetry_breaking": sym,
        "card_encoding": args.card_encoding,
        "status": "building",
    }
    _write(out_path, result)

    t0 = time.time()
    cnf, x, vpool = se.build_instance(
        args.m, args.n, args.K, symmetry_breaking=sym,
        card_encoding=_card_enc(args.card_encoding),
    )
    build_time = time.time() - t0

    result.update({
        "status": "solving",
        "build_time_s": round(build_time, 2),
        "num_vars": cnf.nv,
        "num_clauses": len(cnf.clauses),
    })
    _write(out_path, result)
    print(f"[sat_attack] built instance: m={args.m} n={args.n} K={args.K} "
          f"sym={sym} solver={args.solver} nvars={cnf.nv} "
          f"nclauses={len(cnf.clauses)} build_time={build_time:.2f}s",
          flush=True)

    cls = _solver_cls(args.solver)
    t1 = time.time()
    with cls(bootstrap_with=cnf.clauses) as solver:
        sat = solver.solve()
        model = solver.get_model() if sat else None
    solve_time = time.time() - t1

    result["status"] = "done"
    result["sat"] = sat
    result["solve_time_s"] = round(solve_time, 2)
    result["total_time_s"] = round(time.time() - t0, 2)
    print(f"[sat_attack] solve finished: sat={sat} solve_time={solve_time:.2f}s",
          flush=True)

    if sat:
        matrix = se.model_to_matrix(model, x, args.m, args.n)
        result["matrix"] = matrix
        check = checker.verify(matrix, expected_edges=args.K)
        result["checker"] = {
            "shape": check["shape"],
            "edges": check["edges"],
            "is_k33_free": check["is_k33_free"],
            "methods": check["methods"],
        }
        result["checker_verified"] = bool(
            check["is_k33_free"] and check["edges"] == args.K
        )
        print(f"[sat_attack] checker_verified={result['checker_verified']} "
              f"(edges={check['edges']}, is_k33_free={check['is_k33_free']})",
              flush=True)

    _write(out_path, result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
