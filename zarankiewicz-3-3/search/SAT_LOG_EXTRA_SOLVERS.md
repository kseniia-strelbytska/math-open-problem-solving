# Extra SAT solver backends: kissat and z3

Separate, independent workstream from `search/SAT_LOG.md`. Written by a
subagent asked to try solver backends not yet attempted, while a parallel
workstream ran 4 background Cadical153/Glucose3 processes (via
`search/sat_attack.py`) against the same target. Per instructions, this
workstream did **not** touch those processes or their output files
(`search/results/z16_17_133_sym.json`, `z16_17_133_nosym.json`,
`z16_17_133_glucose_nosym.json`, `z16_17_134_nosym.json`), and does not
edit `SAT_LOG.md`, `PROGRESS.md`, or `README.md` — this file is meant to
be integrated by the orchestrating session afterward.

## Setup

- Installed `kissat` 4.0.4 via `brew install kissat` (Homebrew bottle,
  arm64_sonoma). Confirmed working: `kissat --version` -> `4.0.4`.
- `z3` 4.15.4 was already installed at `/opt/homebrew/bin/z3` (per task
  brief). Confirmed it accepts DIMACS CNF directly via `z3 -dimacs
  <file>`, printing the same `s SATISFIABLE`/`s UNSATISFIABLE` + `v ...`
  lines as a standard SAT-competition solver — no awkwardness here, it
  worked cleanly on the first try.

## Wiring: `search/external_sat_runner.py`

Neither kissat nor `z3 -dimacs` is wrapped by python-sat, so both are
standalone DIMACS-CNF binaries invoked as subprocesses. Wrote a new
script, `search/external_sat_runner.py`, as a sibling to `sat_attack.py`
(not a modification of it, to avoid any risk of interfering with the
parallel workstream's use of that file):

1. Builds the CNF with the **same, already-validated**
   `sat_encoding.py::build_instance(...)` used by `sat_attack.py` — no
   new encoding code, only a new solving/parsing path.
2. Writes it to DIMACS via `pysat.formula.CNF.to_file(...)`.
3. Invokes the external binary as a subprocess:
   - kissat: `kissat -q <cnf>` (exit code 10 = SAT, 20 = UNSAT — this is
     the standard SAT-competition convention; confirmed by hand-run
     smoke tests, see below, before relying on it).
   - z3: `z3 -dimacs <cnf>` (always exits 0; verdict is read from the
     `s SATISFIABLE`/`s UNSATISFIABLE` text line, not the exit code).
4. Parses the `v ...` literal lines into a model, decodes it via the
   existing `sat_encoding.py::model_to_matrix(...)`.
5. **Independently re-verifies any claimed SAT witness with
   `verify/checker.py`** before setting `checker_verified` — exactly the
   same discipline as `sat_attack.py`: the solver's own "SATISFIABLE"
   claim is never trusted on its own. `checker_verified` in the output
   JSON is the actual load-bearing claim, not `sat: true` by itself.
6. As a belt-and-suspenders cross-check specific to parsing raw
   subprocess text output (a new failure surface `sat_attack.py` doesn't
   have, since it reads structured objects from python-sat): the parsed
   `s ...` verdict is cross-checked against kissat's exit code, and any
   mismatch, or a `sat` verdict with no `v` lines at all, is treated as
   `"unknown"` rather than trusted — logged loudly as an anomaly, not
   silently resolved either way.
7. Output JSON schema deliberately mirrors `sat_attack.py`'s fields
   (`m, n, K, solver, symmetry_breaking, status, sat, matrix, checker,
   checker_verified, solve_time_s, ...`), plus a few extra fields specific
   to running an external binary (`backend`, `cmd`, `cnf_path`,
   `exit_code`, `solver_status`), so results are directly comparable
   across both runners.

### Smoke tests before trusting it on the real target

Per the working discipline ("try to break it before extending it"), ran
both backends on tiny hand-checkable cases first:

- `m=3, n=3, K=9` (forces a complete `K_{3,3}` on the only possible 3x3
  block — must be UNSAT): both kissat and z3 correctly returned
  `unsat`, matching the analytically-obvious answer.
- `m=4, n=4, K=8` (trivially SAT — e.g. two full rows, two empty rows, no
  3-row subset is ever all-1 together, so no `K_{3,3}` possible with only
  2 fully-populated rows): both backends returned SAT; both witnesses were
  independently confirmed by `verify/checker.py`
  (`checker_verified: true`, 8 edges, `is_k33_free: true`). kissat's
  witness and z3's witness were different matrices (as expected — no
  claim of canonical form), and both checked out independently.

Only after these passed were the real-target runs launched.

## Real runs

Instance for `m=16, n=17, K=133`, no symmetry breaking: 37,246 variables,
454,748 clauses — build time ~1.4s, matches the size reported by the
parallel Cadical153/Glucose3 runs on the identical encoding (consistency
cross-check: same encoder, same instance size, independent confirmation
the CNF construction itself isn't backend-dependent).

Instance for `m=13, n=18, K=117`, no symmetry breaking: 27,612 variables,
288,132 clauses — build time ~0.9s.

Launched at 2026-08-26 17:43 BST (machine already running 4 background
solver processes from the parallel workstream at that point, ~50% CPU
used out of 8 cores — confirmed via `ps aux` before launching, so this
adds 3 more single-threaded solver processes on the spare capacity, not
oversubscribing beyond ~7/8 cores):

| Run | Command | Output | Status |
|---|---|---|---|
| kissat, 16x17, K=133, no-sym | `external_sat_runner.py 16 17 133 --solver kissat --no-symmetry-breaking` | `search/results/z16_17_133_kissat.json` (+ `.cnf`, `.log`) | launched, PID 68041 (solver subprocess PID varies per restart) |
| z3, 16x17, K=133, no-sym | `external_sat_runner.py 16 17 133 --solver z3 --no-symmetry-breaking` | `search/results/z16_17_133_z3.json` (+ `.cnf`, `.log`) | launched, PID 68047 |
| kissat, 13x18, K=117, no-sym | `external_sat_runner.py 13 18 117 --solver kissat --no-symmetry-breaking` | `search/results/z13_18_117_kissat.json` (+ `.cnf`, `.log`) | launched, PID 68067 |

No internal solver time limit was set (`--time-limit` omitted) — per the
task brief, these are allowed to run long; status will be updated below
as they progress or are left running past the end of this workstream's
active work.

(Status updates continue below as runs progress.)
