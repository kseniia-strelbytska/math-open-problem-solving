"""
Runs the same validated SAT encoding (search/sat_encoding.py) through
external, standalone DIMACS-CNF SAT solver *binaries* that are not wrapped
by python-sat: kissat (CDCL, installed via `brew install kissat`) and z3
(SMT solver with a strong built-in SAT engine, invoked as `z3 -dimacs`).

This is a SEPARATE, independent runner from search/sat_attack.py (which
drives python-sat-bundled solvers -- Cadical153/Glucose3/Minisat22 -- via
their Python bindings). The two runners share the *encoding*
(sat_encoding.build_instance / model_to_matrix) but not the solving path,
which is the point: a different backend is a different independent
cross-check on any SAT/UNSAT claim.

Discipline, same as sat_attack.py:
  - Any SAT witness is decoded from the solver's own DIMACS model output
    (kissat's `v` lines / z3 -dimacs's `v` lines), then independently
    re-verified with verify/checker.py before being trusted at all. The
    solver's own self-report of "SATISFIABLE" is never taken as sufficient
    on its own -- checker_verified in the output JSON is the actual claim.
  - Any UNSAT result is reported exactly as that ("the solver returned
    UNSAT for this exact CNF"), no further interpretation layered on here.
  - Output JSON schema deliberately mirrors sat_attack.py's, plus a few
    extra fields (backend, cmd, cnf_path, exit_code) specific to running
    an external binary via subprocess, so results are directly comparable.

Usage:
    .venv/bin/python search/external_sat_runner.py <m> <n> <K> \
        --solver kissat|z3 --out <path.json> \
        [--no-symmetry-breaking] [--card-encoding seqcounter] \
        [--time-limit SECONDS] [--cnf-path path.cnf]
"""

from __future__ import annotations

import argparse
import json
import subprocess
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


KISSAT_BIN = "kissat"
Z3_BIN = "/opt/homebrew/bin/z3"


def _card_enc(name: str):
    return getattr(EncType, name)


def _write(out_path: Path, result: dict) -> None:
    out_path.write_text(json.dumps(result, indent=2))


def _build_cmd(solver: str, cnf_path: Path, time_limit: int | None,
               memory_limit_mb: int | None = None,
               proof_path: Path | None = None) -> list[str]:
    if solver == "kissat":
        # kissat's CLI is `kissat [options] <dimacs> [<proof>]` -- the proof
        # file is a bare POSITIONAL argument, not a flag (verified against
        # `kissat --help`, kissat 4.0.4). With a real file path kissat writes
        # a BINARY DRAT proof by default; `--force` is needed to overwrite an
        # existing path. The proof positional must come AFTER the dimacs
        # positional, so options are appended before it.
        cmd = [KISSAT_BIN, "-q"]
        if time_limit:
            cmd.append(f"--time={time_limit}")
        if proof_path is not None:
            cmd.append("--force")
        cmd.append(str(cnf_path))
        if proof_path is not None:
            cmd.append(str(proof_path))
        return cmd
    elif solver == "z3":
        cmd = [Z3_BIN, "-dimacs"]
        if time_limit:
            cmd.append(f"-T:{time_limit}")
        if memory_limit_mb:
            cmd.append(f"-memory:{memory_limit_mb}")
        cmd.append(str(cnf_path))
        return cmd
    else:
        raise ValueError(f"unknown external solver {solver!r}")


def _parse_dimacs_output(solver: str, stdout: str, returncode: int) -> tuple[str, list[int] | None]:
    """
    Returns (status, model) where status is one of "sat"/"unsat"/"unknown",
    and model is a list of signed ints (DIMACS literal convention) if
    status == "sat", else None.

    Parses the standard SAT-solver DIMACS output convention shared by both
    kissat and `z3 -dimacs`:
      - a line starting with "s SATISFIABLE" / "s UNSATISFIABLE" / "s UNKNOWN"
      - zero or more lines starting with "v " listing signed literals,
        terminated by a literal "0" (possibly on the same line as the s
        satisfiable in some solvers, but not observed here -- handled
        generally by scanning all "v " lines regardless of line breaks).

    kissat exit codes (SAT solver competition convention, confirmed by a
    hand-run smoke test before relying on it here): 10 = SAT, 20 = UNSAT,
    anything else (0 on a time-limited "s UNKNOWN", or a nonzero parse/
    other error) is NOT trusted as sat/unsat -- we key off the "s " line
    text, not the exit code, and only use the exit code as a secondary
    sanity cross-check (mismatch is flagged as an anomaly).
    """
    status = "unknown"
    model: list[int] = []
    saw_v = False
    for line in stdout.splitlines():
        line = line.strip()
        # z3 -dimacs, on hitting -T:/-memory:, prints a bare "timeout" or
        # "unknown" line and exits 0 -- NOT an "s UNKNOWN" line. Recognize
        # these explicitly so the JSON distinguishes "solver gave up within
        # its budget" from "we could not parse the output at all"; both are
        # non-verdicts, but they mean different things when read later.
        if line in ("timeout", "unknown", "memout"):
            status = f"resource_limit:{line}"
            continue
        if line.startswith("s "):
            tag = line[2:].strip()
            if tag == "SATISFIABLE":
                status = "sat"
            elif tag == "UNSATISFIABLE":
                status = "unsat"
            else:
                status = "unknown"
        elif line.startswith("v "):
            saw_v = True
            for tok in line[2:].split():
                lit = int(tok)
                if lit == 0:
                    continue
                model.append(lit)

    # Secondary cross-check against exit code, where the convention is known.
    exit_code_status = None
    if solver == "kissat":
        if returncode == 10:
            exit_code_status = "sat"
        elif returncode == 20:
            exit_code_status = "unsat"
    anomaly = exit_code_status is not None and exit_code_status != status
    if anomaly:
        print(f"[external_sat_runner] ANOMALY: parsed status={status!r} but "
              f"exit code {returncode} implies {exit_code_status!r} -- "
              "treating as unknown, not trusting either.", flush=True)
        status = "unknown"

    if status == "sat" and not saw_v:
        print("[external_sat_runner] ANOMALY: status=sat but no 'v' model "
              "lines were found -- treating as unknown.", flush=True)
        status = "unknown"

    return status, (model if status == "sat" else None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("m", type=int)
    ap.add_argument("n", type=int)
    ap.add_argument("K", type=int)
    ap.add_argument("--solver", required=True, choices=["kissat", "z3"])
    ap.add_argument("--no-symmetry-breaking", action="store_true")
    ap.add_argument("--card-encoding", default="seqcounter")
    ap.add_argument("--card-mode", default="equals", choices=["equals", "atleast"],
                     help="'equals' = exactly-K edges (original validated "
                          "path). 'atleast' = at-least-K edges: a smaller "
                          "one-sided cardinality constraint that asks the "
                          "SAME question by the monotonicity lemma proved in "
                          "sat_encoding.build_instance's docstring. NOTE: "
                          "under 'atleast' a SAT model may have MORE than K "
                          "edges, so the witness check below asserts "
                          "edges >= K rather than edges == K.")
    ap.add_argument("--out", required=True)
    ap.add_argument("--proof", default=None,
                     help="Path for the solver's DRAT refutation proof "
                          "(kissat only). If UNSAT, kissat writes a binary "
                          "DRAT proof here, which can then be independently "
                          "checked with tools/drat-trim (and, after "
                          "conversion to LRAT via `drat-trim -L`, with the "
                          "HOL4-verified tools/cake_lpr). WARNING: DRAT "
                          "proofs for hard instances grow without bound -- "
                          "monitor free disk space. On a SAT result the "
                          "proof file is meaningless (no refutation exists) "
                          "and is reported as such. If the path ends in "
                          "'.gz' kissat pipes the proof through gzip "
                          "(measured 1.92x smaller on a real binary DRAT "
                          "proof); such a proof is checked by streaming, "
                          "`gzip -dc proof.drat.gz | drat-trim <cnf> -i`, "
                          "which was smoke-tested to report VERIFIED.")
    ap.add_argument("--cnf-path", default=None,
                     help="Where to write the intermediate DIMACS CNF file "
                          "(default: alongside --out, same stem, .cnf ext).")
    ap.add_argument("--time-limit", type=int, default=None,
                     help="Solver-internal wall-clock limit in seconds "
                          "(kissat --time=, z3 -T:). Omit for unlimited.")
    ap.add_argument("--memory-limit-mb", type=int, default=None,
                     help="Solver-internal memory cap in MB (z3 -memory: "
                          "only). Setting this lets the solver give up "
                          "gracefully and self-report instead of being "
                          "silently SIGKILLed by the OS under memory "
                          "pressure -- see SAT_LOG_EXTRA_SOLVERS.md.")
    args = ap.parse_args()

    sym = not args.no_symmetry_breaking
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cnf_path = Path(args.cnf_path) if args.cnf_path else out_path.with_suffix(".cnf")

    proof_path = Path(args.proof) if args.proof else None
    if proof_path is not None:
        if args.solver != "kissat":
            ap.error("--proof is only supported for --solver kissat "
                     "(z3 -dimacs emits no DRAT proof)")
        proof_path.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "m": args.m,
        "n": args.n,
        "K": args.K,
        "solver": args.solver,
        "backend": "external-dimacs-subprocess",
        "symmetry_breaking": sym,
        "card_encoding": args.card_encoding,
        "card_mode": args.card_mode,
        "time_limit_s": args.time_limit,
        "memory_limit_mb": args.memory_limit_mb,
        "proof_path": str(proof_path) if proof_path else None,
        "status": "building",
    }
    _write(out_path, result)

    t0 = time.time()
    cnf, x, vpool = se.build_instance(
        args.m, args.n, args.K, symmetry_breaking=sym,
        card_encoding=_card_enc(args.card_encoding),
        card_mode=args.card_mode,
    )
    build_time = time.time() - t0

    result.update({
        "status": "writing_cnf",
        "build_time_s": round(build_time, 2),
        "num_vars": cnf.nv,
        "num_clauses": len(cnf.clauses),
    })
    _write(out_path, result)
    print(f"[external_sat_runner] built instance: m={args.m} n={args.n} K={args.K} "
          f"sym={sym} solver={args.solver} nvars={cnf.nv} "
          f"nclauses={len(cnf.clauses)} build_time={build_time:.2f}s",
          flush=True)

    t_cnf = time.time()
    cnf.to_file(str(cnf_path))
    cnf_write_time = time.time() - t_cnf
    result["cnf_path"] = str(cnf_path)
    result["cnf_write_time_s"] = round(cnf_write_time, 2)
    result["status"] = "solving"
    _write(out_path, result)
    print(f"[external_sat_runner] wrote CNF to {cnf_path} in {cnf_write_time:.2f}s",
          flush=True)

    cmd = _build_cmd(args.solver, cnf_path, args.time_limit, args.memory_limit_mb,
                     proof_path)
    result["cmd"] = cmd
    _write(out_path, result)
    print(f"[external_sat_runner] running: {' '.join(cmd)}", flush=True)

    t1 = time.time()
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=(args.time_limit + 120) if args.time_limit else None,
        )
        timed_out = False
        stdout, stderr, returncode = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as e:
        timed_out = True
        stdout = e.stdout or ""
        stderr = e.stderr or ""
        returncode = None
    solve_time = time.time() - t1

    result["solve_time_s"] = round(solve_time, 2)
    result["total_time_s"] = round(time.time() - t0, 2)
    result["exit_code"] = returncode
    result["subprocess_timed_out"] = timed_out
    result["stderr_tail"] = stderr[-2000:] if stderr else ""

    if timed_out:
        result["status"] = "timeout"
        result["sat"] = None
        _write(out_path, result)
        print(f"[external_sat_runner] TIMED OUT after {solve_time:.2f}s "
              f"(hard subprocess timeout, beyond solver's own --time limit)",
              flush=True)
        return 0

    if returncode is not None and returncode < 0:
        # Negative returncode == killed by signal N. On macOS under memory
        # pressure this is how the OS's memory killer (jetsam) terminates a
        # process: SIGKILL (-9), with no output and no solver-side warning.
        # Record it explicitly -- a solver that was killed proved NOTHING,
        # and must never be conflated with a solver that returned UNSAT.
        result["killed_by_signal"] = -returncode
        print(f"[external_sat_runner] KILLED BY SIGNAL {-returncode} -- the "
              "solver was terminated externally (on macOS, most likely the "
              "OS memory killer). This is NOT a SAT/UNSAT result and proves "
              "nothing about the instance.", flush=True)

    status, model = _parse_dimacs_output(args.solver, stdout, returncode)
    result["solver_status"] = status
    result["status"] = "done"
    print(f"[external_sat_runner] solve finished: solver_status={status} "
          f"exit_code={returncode} solve_time={solve_time:.2f}s", flush=True)

    if status == "sat":
        result["sat"] = True
        matrix = se.model_to_matrix(model, x, args.m, args.n)
        result["matrix"] = matrix
        # Under card_mode="atleast" a model legitimately has >= K edges, so
        # pinning expected_edges=K would make the checker reject a perfectly
        # good witness. Ask the checker for the unconstrained verdict and
        # apply the mode-appropriate edge-count test ourselves.
        if args.card_mode == "atleast":
            check = checker.verify(matrix)
            edges_ok = check["edges"] >= args.K
        else:
            check = checker.verify(matrix, expected_edges=args.K)
            edges_ok = check["edges"] == args.K
        result["checker"] = {
            "shape": check["shape"],
            "edges": check["edges"],
            "is_k33_free": check["is_k33_free"],
            "methods": check["methods"],
        }
        result["checker_edge_test"] = (
            f"edges >= {args.K}" if args.card_mode == "atleast"
            else f"edges == {args.K}"
        )
        result["checker_verified"] = bool(check["is_k33_free"] and edges_ok)
        print(f"[external_sat_runner] checker_verified={result['checker_verified']} "
              f"(edges={check['edges']}, is_k33_free={check['is_k33_free']})",
              flush=True)
        if proof_path is not None:
            # A SAT result has no refutation, so whatever kissat left in the
            # proof file is a partial derivation log, NOT a certificate of
            # anything. Say so explicitly rather than leaving a file that
            # looks like a proof lying around unlabelled.
            result["proof_written"] = proof_path.exists()
            result["proof_bytes"] = (proof_path.stat().st_size
                                     if proof_path.exists() else 0)
            result["proof_verified"] = False
            result["proof_note"] = (
                "Instance is SATISFIABLE -- there is no refutation to "
                "certify. This file is a partial DRAT derivation log with no "
                "certificate value. The trust anchor for a SAT result is "
                "verify/checker.py on the decoded witness (checker_verified)."
            )
    elif status == "unsat":
        result["sat"] = False
        if proof_path is not None:
            # Report the proof artifact but make NO claim about it here. The
            # solver's own "UNSATISFIABLE" is not evidence; the proof file is
            # only a *candidate* certificate until an independent checker
            # (tools/drat-trim, and tools/cake_lpr on the LRAT conversion)
            # says VERIFIED. Verification is deliberately a separate step run
            # by a separate program -- see search/CERTIFICATE_LOG.md.
            exists = proof_path.exists()
            result["proof_written"] = exists
            result["proof_bytes"] = proof_path.stat().st_size if exists else 0
            result["proof_verified"] = None
            result["proof_note"] = (
                "UNVERIFIED candidate DRAT refutation. Run "
                "tools/drat-trim <cnf> <proof> (and cake_lpr on the -L LRAT "
                "output) before treating this as a certificate."
            )
            print(f"[external_sat_runner] UNSAT; candidate DRAT proof at "
                  f"{proof_path} ({result['proof_bytes']} bytes). NOT yet "
                  "verified -- run drat-trim/cake_lpr on it.", flush=True)
    else:
        result["sat"] = None
        print("[external_sat_runner] solver returned no definitive "
              "SAT/UNSAT verdict (unknown/anomaly) -- see solver_status, "
              "stderr_tail, and exit_code above.", flush=True)

    _write(out_path, result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
