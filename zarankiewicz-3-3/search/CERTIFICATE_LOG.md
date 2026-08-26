# Proof-certificate toolchain and proof-logged solver runs

Started 2026-08-26. Closes ledger entry **[L12]**: until now, *no* solver run
in this project had proof logging enabled, so an UNSAT result would have been
an unverifiable solver claim rather than a certificate — worthless against
acceptance criterion (B)/(C), and the CPU time would have had to be re-spent.

Everything below is what was actually run, with the commands, in order.
Where a measurement is an extrapolation rather than an observation, it says so.

---

## 1. Checkers installed

### 1.1 `drat-trim` (DRAT checker)

```
git clone --depth 1 https://github.com/marijnheule/drat-trim.git
cd drat-trim
gcc -O2 drat-trim.c -o drat-trim
gcc -O2 lrat-check.c -o lrat-check      # also built; bundled in the same repo
```

- Location: `zarankiewicz-3-3/tools/drat-trim/drat-trim`
- Upstream commit: `2e3b2dc0ecf938addbd779d42877b6ed69d9a985` (2024-11-25)
- Compiler: Apple clang 15.0.0, target `arm64-apple-darwin23.6.0`
- Built clean, no warnings surfaced at `-O2`.

Sanity check on the author's own bundled examples (before touching our CNFs):

```
./drat-trim examples/example-4-vars.cnf examples/example-4-vars.drat   -> s VERIFIED
./drat-trim examples/uuf-100-1.cnf     examples/uuf-100-1.drat         -> s VERIFIED
./lrat-check examples/example-4-vars.cnf examples/example-4-vars.lrat  -> c VERIFIED
```

### 1.2 `cake_lpr` (LRAT/LPR checker, formally verified in HOL4)

This one built fine, so we have it — no need to fall back to `drat-trim`
alone. It matters because `cake_lpr` is itself verified in HOL4, which is
what actually closes the "who checks the checker" loop: `drat-trim` is a
few thousand lines of untrusted C.

```
git clone --depth 1 https://github.com/tanyongkiam/cake_lpr.git
cd cake_lpr
make cake_lpr_arm8        # the repo ships an explicit ARMv8/Mac target
# = gcc basis_ffi.c cake_lpr_arm8.S -o cake_lpr -std=c99
```

- Location: `zarankiewicz-3-3/tools/cake_lpr/cake_lpr`
- Upstream commit: `a36874a8b750b43fe4b385b8ddbf5b033e46a3fa` (2026-07-22)
- Self-test: `./cake_lpr example.cnf example.lpr` -> `s VERIFIED UNSAT`

**Integrity note, recorded because it is a real (if minor) gap.**
`shasum -a 256 -c cake_lpr.sha256` reports:

```
Makefile:          OK
cake_lpr.S:        OK
cake_lpr_arm8.S:   OK
basis_ffi.c:       FAILED
```

The two `.S` files — the CakeML-compiler output, i.e. the artifact the HOL4
proof is *about* — match their recorded hashes exactly. The mismatch is on
`basis_ffi.c`, the small hand-written C foreign-function shim that provides
file I/O and is explicitly outside the verified core. The checked-in
`cake_lpr.sha256` is simply stale with respect to the checked-in
`basis_ffi.c` at this commit (the working tree is a clean checkout —
`git status` shows no modifications). So: the verified part verifies; the
I/O glue is unverified and its recorded hash is stale upstream. Not a
blocker, but it is part of the trust surface and should be stated in any
write-up rather than glossed as "we used a formally verified checker".

### 1.3 The pipeline

kissat emits DRAT; `cake_lpr` consumes LRAT. So the chain is:

```
kissat -q --force <cnf> <proof.drat>                 # solve, emit binary DRAT
tools/drat-trim/drat-trim <cnf> <proof.drat> \
    -L <proof.lrat>                                  # check DRAT, emit LRAT
tools/cake_lpr/cake_lpr <cnf> <proof.lrat>           # HOL4-verified re-check
```

`drat-trim` is *untrusted* in this chain — it is a proof *transformer*, and
its output is independently re-checked by `cake_lpr` against the same
original CNF. A bug in `drat-trim` that accepted a bad DRAT proof would have
to also produce an LRAT file that `cake_lpr` accepts, which is a far higher
bar (LRAT carries explicit resolution hints that `cake_lpr` re-derives).

**Compressed variant** (needed here, see §5): kissat writes a gzipped proof
if the path ends in `.gz` (it pipes through `sh -c 'gzip -c > path'`), and
`drat-trim` reads a proof from stdin when given no proof argument:

```
kissat -q --force <cnf> <proof.drat.gz>
gzip -dc <proof.drat.gz> | tools/drat-trim/drat-trim <cnf> -i
```

Both halves of that were smoke-tested, not assumed — see §3.

### 1.4 kissat interface, confirmed by direct use

- `kissat [options] <dimacs> [<proof>]` — the proof file is a bare
  **positional** argument, verified against `kissat --help` (kissat 4.0.4).
- `--force` / `-f` is needed to write a proof to an existing path.
- Exit codes observed: **10 = SAT, 20 = UNSAT**, matching the competition
  convention.
- Binary DRAT is used for real file paths (`--no-binary` would force ASCII).

---

## 2. Code changes

Deliberately minimal; the validated encoder and runner were extended, not
replaced.

- `search/external_sat_runner.py`
  - new `--proof PATH` (kissat only; errors out for z3, which emits no DRAT).
  - new `--card-mode {equals,atleast}` (see §4).
  - On UNSAT with `--proof`, the JSON records `proof_written`,
    `proof_bytes`, `proof_verified: null`, and a `proof_note` stating in
    words that this is an **unverified candidate** certificate. The runner
    deliberately does **not** verify the proof itself: verification is a
    separate program run separately, so the thing that produced the proof is
    never the thing that blesses it.
  - On SAT with `--proof`, `proof_verified` is set to `false` with a note
    that a satisfiable instance has no refutation and the file has no
    certificate value.
- `search/sat_encoding.py` — added `card_mode="atleast"` alongside the
  existing (default, unchanged) `card_mode="equals"`, with the monotonicity
  lemma written out and proved in the docstring.
- `search/proof_disk_guard.sh` — new resource guard (§5).
- `.gitignore` — proof artifacts (`*.drat`, `*.lrat`) and `tools/` excluded;
  they are generated and can reach many GB.

---

## 3. Smoke tests

Per the project's working discipline, the checkers were exercised on cases
whose answers are known *before* being pointed at the real target — and
then deliberately fed bad input, because a checker you have never seen say
"no" is not yet a checker you can trust.

### 3.1 Positive: does the pipeline confirm a real refutation?

| case | expect | kissat | proof | drat-trim | cake_lpr |
|---|---|---|---|---|---|
| `m=3,n=3,K=9` exactly-K | UNSAT (the only 3x3 all-ones block *is* a K_{3,3}) | UNSAT, exit 20 | 2 bytes | `s VERIFIED` | n/a (degenerate) |
| `m=3,n=3,K=9` at-least-K | UNSAT | UNSAT, exit 20 | 2 bytes | `s VERIFIED` | n/a |
| `m=6,n=6,K=27` exactly-K | UNSAT (`z(6,6;3)=26`) | UNSAT, exit 20, 0.55 s | 828,713 B | `s VERIFIED` (753/1372 clauses in core, 17195/28865 lemmas, 455005 resolution steps) | `s VERIFIED UNSAT` |
| `m=6,n=6,K=27` at-least-K | UNSAT | UNSAT, exit 20, 0.25 s | 489,461 B | `s VERIFIED` (767/904 clauses, 12840/17413 lemmas, 344342 steps) | `s VERIFIED UNSAT` |
| `m=4,n=4,K=8` exactly-K | SAT | SAT, exit 10 | (no refutation) | n/a | n/a |
| `m=4,n=4,K=8` at-least-K | SAT | SAT, exit 10 | (no refutation) | n/a | n/a |
| **`m=7,n=7,K=34` at-least-K** | UNSAT (`z(7,7;3)=33`) | UNSAT, exit 20, 180 s | **133,702,540 B** | `s VERIFIED` (470 s, 652 MB RSS) | `s VERIFIED UNSAT` (53 s, 4.07 GB RSS) |

**Note on the `m=3,n=3,K=9` case.** It works, but it is a *bad* smoke test on
its own: `drat-trim` reports `UNSAT via unit propagation on the input
instance` and the "proof" is 2 bytes. It exercises essentially none of the
DRAT machinery. That is why `m=6,n=6,K=27` was added — a genuinely
non-trivial refutation (17k core lemmas, 455k resolution steps) that
actually drives backward checking, RAT handling, and the LRAT conversion.
The 3x3 case is retained only as a "the plumbing is connected" check.

**SAT/UNSAT discrimination.** Both SAT cases returned exit 10, the runner
decoded the model, and `verify/checker.py` independently confirmed the
witness (`checker_verified=True`, edges=8, `is_k33_free=True`). No refutation
proof was expected or produced. So the pipeline does distinguish the two
outcomes, and a SAT result is still anchored on the independent checker
rather than the solver's self-report.

**Compressed-proof path.** `kissat -q --force <cnf> gz.drat.gz` on the 6x6
case produced a 431,741-byte gzip file (exit 20, `s UNSATISFIABLE`), and
`gzip -dc gz.drat.gz | drat-trim <cnf> -i` reported `s VERIFIED`. So the
compressed round-trip is validated, not assumed.

### 3.2 Negative: does the pipeline *reject* bad input?

All against the 6x6 at-least-K instance, whose valid proof verifies.

`drat-trim`, fed a broken DRAT:

| corruption | result |
|---|---|
| DRAT truncated to 50% of its bytes | `c ERROR: no conflict` / **`s NOT VERIFIED`** |
| DRAT replaced by an empty file | `c ERROR: no conflict` / **`s NOT VERIFIED`** |
| ~41 bytes XOR-flipped in the middle of the binary DRAT | `c ERROR: no conflict` / **`s NOT VERIFIED`** |

`cake_lpr`, fed a broken LRAT:

| corruption | result |
|---|---|
| valid LRAT (control) | **`s VERIFIED UNSAT`** |
| LRAT truncated to 50% of its lines | `c empty clause not derived at end of proof` |
| LRAT replaced by an empty file | `c empty clause not derived at end of proof` |
| one literal's sign flipped in a mid-proof lemma | `c Checking failed at line: 9746. Reason: clause not empty or singleton after reduction` |
| valid LRAT checked against a *different* CNF (the 4x4 K=8 instance) | `c Checking failed at line: 1. ...` |

So both checkers refuse bad proofs, including the subtle case (a single
flipped literal deep inside an otherwise well-formed proof) and the
wrong-formula case — the two failure modes that would matter most.

### 3.3 **TRAP: neither checker signals failure via its exit code**

Measured directly, with no pipeline in the way:

```
drat-trim <cnf> <valid.drat>   -> "s VERIFIED"      exit 0
drat-trim <cnf> <trunc.drat>   -> "s NOT VERIFIED"  exit 0
drat-trim <cnf> <empty.drat>   -> "s NOT VERIFIED"  exit 0
drat-trim <cnf> <flip.drat>    -> "s NOT VERIFIED"  exit 0
cake_lpr  <cnf> <valid.lrat>   -> "s VERIFIED UNSAT"  exit 0
cake_lpr  <cnf> <trunc.lrat>   -> "c empty clause not derived..."  exit 0
cake_lpr  <cnf> <tamper.lrat>  -> "c Checking failed at line..."   exit 0
```

**Both tools return exit status 0 whether they accept or reject.** Any
automation that keys off `$?` would silently accept a corrupted proof as a
certificate. Verification MUST be decided by requiring the exact string
`s VERIFIED` (drat-trim) or `s VERIFIED UNSAT` (cake_lpr) on stdout, and
treating its absence — including any tool crash, OOM, or timeout — as
failure. This is recorded prominently because it is exactly the sort of
detail that turns a "verified" claim into a false one.

---

## 4. Encoding change: at-least-K, and the monotonicity lemma

### 4.1 The monotonicity lemma (load-bearing for reading *any* UNSAT as a bound)

Our CNF asks for a *specific* edge count. Reading UNSAT as an upper bound
needs this lemma, so it is stated and proved rather than assumed:

> **Lemma.** If an `m x n` `K_{3,3}`-free bipartite graph with `e` edges
> exists, then for every `0 <= e' <= e` an `m x n` `K_{3,3}`-free graph with
> exactly `e'` edges exists.
>
> **Proof.** Delete any one edge. The edge count drops by exactly 1.
> Deleting an edge cannot create a `K_{3,3}`: a `K_{3,3}` in the smaller
> graph is a set of 3+3 vertices with all 9 cross edges present, and every
> edge present after the deletion was already present before it, so that
> same `K_{3,3}` would have been present in the original graph —
> contradicting its `K_{3,3}`-freeness. Iterate `e - e'` times. ∎

**Corollary (the step that licenses the bound).**

- *exactly-K* UNSAT `==>` no `K_{3,3}`-free graph with `>= K` edges exists.
  (If one with `e >= K` existed, the lemma would yield one with exactly `K`,
  which would satisfy the CNF.) Hence `z(m,n;3) <= K-1`.
- *at-least-K* UNSAT `==>` `z(m,n;3) <= K-1` directly.

Without this lemma, "exactly-134 is UNSAT" would formally rule out only the
single value 134 and say nothing about 135+. The lemma is what makes it an
upper bound. It is elementary, but it is a real link in the chain.

### 4.2 Why at-least-K was added

`CardEnc.equals` is `atleast AND atmost` glued together; only the `atleast`
half encodes the claim we care about. Dropping the `atmost` half roughly
halves the auxiliary variables:

| instance | mode | vars | clauses |
|---|---|---|---|
| 16x17 K=134 | equals | 37,256 | 454,768 |
| 16x17 K=134 | **atleast** | **18,764** | **417,780** |
| 13x18 K=117 | equals | 27,612 | 288,132 |
| 13x18 K=117 | **atleast** | **13,923** | **260,754** |
| 6x6 K=27 | equals | 522 | 1,372 |
| 6x6 K=27 | **atleast** | **279** | **904** |

On the 6x6 case the effect was measurable end-to-end: solve time 0.55 s ->
0.25 s, proof 828,713 B -> 489,461 B. One small case is not proof of a
speedup at scale, but it is the right direction and the encoding is
strictly smaller.

**Caveat handled:** an at-least-K model may have *more* than K edges, so
`external_sat_runner.py` asserts `edges >= K` (not `== K`) when
`--card-mode atleast`, and records which test it applied in
`checker_edge_test`.

### 4.3 Cross-validation before trusting it on the real target

The lemma says the two encodings must agree on SAT/UNSAT for every
`(m,n,K)`. That was tested rather than assumed: all `K` from 1 to `m*n` for
`(m,n)` in `{(3,3),(3,4),(4,4),(4,5),(5,5),(5,6),(6,6)}`, both encodings
solved with Cadical153, verdicts compared, and every SAT witness pushed
through `verify/checker.py`:

```
cases=148  agree_sat=115  agree_unsat=33  disagreements=0
```

Zero disagreements, and no bad witnesses. (Script kept out of the repo — it
is a one-shot check; the numbers above are the record.)

---

## 5. Resource ceiling — this is the binding constraint, not CPU

### 5.1 Disk

Free space measured **before** launching: **18.12 GB** (`df -k /Users`);
the volume is at 99% capacity (871 GiB of 926 GiB used). That is the whole
budget available for proof files.

Measured proof growth rate, uncompressed, three concurrent runs
(16x17 K=133, 16x17 K=134, 13x18 K=117, exactly-K encoding), over ~50 s:

```
z13_18_117: 105.9 MB    z16_17_133: 90.2 MB    z16_17_134: 75.5 MB
=> ~1.8 MB/s per solver, ~5.4 MB/s combined
=> the 18 GB of free disk would have been gone in ~56 minutes
```

That is a machine-wedging trajectory, so those three runs were stopped and
relaunched compressed. Measured compression on a real binary DRAT proof
(the 829 KB 6x6 proof):

```
gzip  -> 431,741 B  (1.92x)
bzip2 -> 455,779 B  (1.82x)
xz -1 -> 412,980 B  (2.01x)
```

Binary DRAT compresses only about 2x — worth taking (gzip is nearly free
and kissat supports it natively) but nowhere near a fix.

Growth rate of the current, compressed runs. Sampled over the first 90 s:

```
17:22:49 -> 17:24:19   z13_18_117: 25.9 MB -> 75.8 MB   = 0.55 MB/s
                       z16_17_134: 21.6 MB -> 69.2 MB   = 0.53 MB/s
                       combined                          ~1.08 MB/s
```

and then over a longer 5-minute window (from `guard.log`), which is the more
representative figure — the rate drops once kissat starts its learnt-clause
reduction cycles:

```
17:25:08 -> 17:30:09   z16_17_134:  84.3 MB -> 186.3 MB  = 0.34 MB/s
                       z13_18_117:  90.6 MB -> 201.2 MB  = 0.37 MB/s
                       combined                           ~0.71 MB/s
```

At ~0.71 MB/s combined, ~17.4 GB of free disk is roughly **6.8 hours** of
solving before the global floor trips; the per-run budgets (7 GB / 5 GB)
would bind first, at roughly 5.7 h and 3.8 h respectively. Growth is being
logged continuously to `search/results/proofs/guard.log`, so the actual
curve — not just these two windows — is on record.

### 5.2 Memory

The machine was under severe memory pressure at launch: `sysctl
vm.swapusage` reported **12.87 GB of 14.34 GB swap in use** (24 GB RAM
total). No solver-side cap is available:

- kissat 4.0.4 has no `--memory` option (checked `--help`).
- macOS Darwin 23.6 does **not** support `ulimit -v` or `ulimit -d`. Both
  refuse outright (`cannot modify limit: Invalid argument`), and a
  deliberately-tested 3 GB allocation succeeded under an attempted 500 MB
  `ulimit -v` cap. So there is no way to make the solver self-limit.

Consequence: concurrency was cut from 3 proof-logged runs to 2, and memory
is policed externally by the guard below.

### 5.3 The guard: `search/proof_disk_guard.sh`

Polls every 60 s, appends to `search/results/proofs/guard.log`, and:

- enforces a per-run **proof-size budget** (7 GB for K=134, 5 GB for
  13x18 K=117, 2.5 GB for the deferred K=133);
- enforces a per-run **RSS budget** (4 GB, 4 GB, 3 GB) — the substitute for
  the unavailable `ulimit`;
- enforces a global **3 GB free-disk floor**, shedding runs in *reverse*
  priority order (stretch goals die first) until the floor is clear;
- on stopping a run, **deletes its partial proof**, because a truncated
  DRAT proof certifies nothing and only consumes space;
- exits once no proof-logged run is alive.

The guard makes no claim about any proof. It only bounds resource use.

### 5.4 The uncomfortable consequence: producible ≠ checkable here

Measured LRAT blow-up from `drat-trim -L`:

```
6x6  exactly-K:  DRAT     828,713 B -> LRAT     3,028,605 B  (3.65x)
6x6  at-least-K: DRAT     489,461 B -> LRAT     2,241,568 B  (4.58x)
7x7  at-least-K: DRAT 133,702,540 B -> LRAT   450,008,449 B  (3.37x)
```

Checker resource use, measured with `/usr/bin/time -l`:

| proof | drat-trim wall | drat-trim RSS | cake_lpr wall | cake_lpr RSS |
|---|---|---|---|---|
| 6x6, 489 KB DRAT / 2.24 MB LRAT | 0.43 s | 56 MB | 0.26 s | 106 MB |
| **7x7, 133.7 MB DRAT / 450 MB LRAT** | **470 s** | **652 MB** | **53 s** | **4.07 GB** |

The 7x7 figures are the ones to use — the 6x6 ones are dominated by fixed
overhead. Derived rates:

```
drat-trim:  3.51 s per MB of DRAT;  peak RSS ~4.9x the DRAT size
cake_lpr :  0.12 s per MB of LRAT;  peak RSS ~9.0x the LRAT size (~30x DRAT)
```

Two things stand out, both bad:

1. **Backward DRAT checking is slower than solving.** kissat produced this
   refutation in 180 s; `drat-trim` took 470 s to check it — 2.6x the solve
   time. Verification is not a cheap afterthought.
2. **`cake_lpr`'s memory is the binding wall**, at ~9x the LRAT size. With
   ~20 GB of usable RAM (24 GB physical, and 12.87 GB of swap already in
   use), `cake_lpr` caps out at an LRAT of about **2.2 GB**, i.e. a DRAT of
   about **660 MB raw / 340 MB gzipped**. At the measured 0.34 MB/s
   compressed growth rate that is roughly **17 minutes of solving**.

**Stated plainly: on this machine the full certified chain
(DRAT -> drat-trim -> LRAT -> cake_lpr) is only feasible for a refutation
kissat finds in roughly its first ~17 minutes**, i.e. a gzipped proof of
order 340 MB. That is now a *measured* ceiling, not a guess.

**Both currently running proof-logged jobs have already passed it.** As of
17:52 UTC their proofs were 483 MB and 520 MB gzipped (~930 MB and ~1.0 GB
raw), which would convert to ~3.1 GB and ~3.4 GB of LRAT and demand ~28-30
GB of RAM in `cake_lpr` — beyond this machine. So if either resolves UNSAT
from here on:

- `drat-trim` alone may still manage it for a while (its RSS is only ~4.9x
  the DRAT size, so ~4 GB of RAM per GB of raw proof), giving a
  `s VERIFIED` from an untrusted-but-widely-used C checker;
- the HOL4-verified `cake_lpr` confirmation would have to be run on a
  machine with more RAM.

The proofs remain valid and worth keeping either way — a DRAT file is
portable, and verifying it elsewhere is a purely mechanical step. But it
should be said up front rather than discovered at the end: **this machine
can produce a certificate it cannot fully check.** Reporting a result as
"independently verified" would then require either the `drat-trim`-only
check (weaker: unverified checker) or access to bigger hardware.

---

### 5.5 The scaling data points those numbers come from

To get a mid-scale measurement of the checkers, a deliberately *small*
known-UNSAT instance was run with proof logging: `m=8, n=8, K=43`
(`z(8,8;3)=42` per the literature), at-least-K, 967 variables, 4,964
clauses — roughly 1/20th the variables and 1/85th the clauses of the real
target.

**It did not resolve.** kissat hit its 300 s limit with
`solver_status: unknown`, having written a 293 MB uncompressed DRAT proof
(~0.98 MB/s) that certifies nothing and was deleted.

This is worth recording as a negative result in its own right: direct
evidence that the difficulty here is not merely the *size* of the 16x17
instance but the structure of the problem for CDCL, consistent with the
symmetry argument in `STRATEGY_V2.md`. If an 8x8 instance is not a
five-minute problem, 16x17 is very unlikely to be a five-hour one.

**`m=7, n=7, K=34` did resolve** — and it is the useful case, because it
gives the whole pipeline a real-scale end-to-end run:

```
kissat    -q --time=1200 --force <cnf> <proof.drat>   -> UNSAT, exit 20, 179.97 s
                                                         DRAT 133,702,540 B
drat-trim <cnf> <proof.drat> -L <proof.lrat>          -> s VERIFIED
                                                         469.94 s, 652 MB RSS
                                                         LRAT 450,008,449 B
cake_lpr  <cnf> <proof.lrat>                          -> s VERIFIED UNSAT
                                                         53.32 s, 4.07 GB RSS
```

Two payoffs from this beyond the timing data:

1. **The full certified chain is now validated end-to-end on a 134 MB
   proof, not just on toy cases** — ~270x larger than the 6x6 smoke test.
2. **It independently certifies `z(7,7;3) <= 33`**, which matches the
   published `z(7,7;3) = 33`. That is a real-scale check that the encoding
   (including the new at-least-K cardinality path) computes the intended
   quantity: had the encoding been subtly wrong, agreeing with a known exact
   value at this size would be a coincidence. It does not *prove* encoding
   correctness — see §7 step (2) — but it is meaningfully stronger evidence
   than the small-case sweep alone.

The DRAT proof is kept at `search/results/smoke/scale_z7_7_34.drat`; the
450 MB LRAT was deleted after checking to reclaim disk and is regenerable in
~470 s.

---

## 6. What is running now

Launched **2026-08-26 17:22 UTC**, all with `--no-symmetry-breaking` and
`--card-mode atleast`, proofs gzipped:

| priority | instance | runner PID | kissat PID | proof path |
|---|---|---|---|---|
| **(a) PRIMARY** | `m=16 n=17 K=134` | 90111 | 90130 | `search/results/proofs/z16_17_134_kissat_proof.drat.gz` |
| **(b)** | `m=13 n=18 K=117` | 90158 | 90163 | `search/results/proofs/z13_18_117_kissat_proof.drat.gz` |
| guard | — | 90182 | — | log: `search/results/proofs/guard.log` |

Result JSON / stdout log for each run sit alongside the proof with `.json`
and `.log` extensions. Each kissat has a `sh -c 'gzip -c > ...'` child doing
the compression.

**Symmetry breaking is OFF**, for both of the reasons that motivated it:
it was measured to hurt solver performance badly at this scale, and turning
it off removes the double-lex soundness argument — which was only ever
empirically validated on small cases, never formally proven (see the long
comment in `sat_encoding.py`, which is candid that the hand argument does
not close) — from the proof's dependency chain entirely. Nothing in the
current certificate path depends on it.

### Deferred / not launched

- **`m=16 n=17 K=133` with proof logging: deferred, not running.** Reasons:
  (i) the explicit instruction to keep concurrency to 2-3 solvers given the
  swap situation; (ii) K=133 is strictly *less* constrained than K=134 and
  so the least likely of the three to terminate; (iii) an unlogged kissat on
  K=133 (PID 68085) is already running as informal evidence. Its budget and
  priority are already wired into the guard, so it can be started the moment
  (a) or (b) finishes or is shed.

### Pre-existing runs, and one that died

- PID 68085 — `kissat -q search/results/z16_17_133_kissat.cnf`, unlogged,
  exactly-K. Left running as informal evidence only; it can never produce a
  certificate.
- PID 68090 — `kissat -q search/results/z13_18_117_kissat.cnf`, unlogged.
  Kept, per instruction: it costs one core and might resolve first, giving
  early information — but the certified version of the same question is
  run (b) above, and only (b) could yield an admissible result.
- **PID 7176 (Cadical, 16x17 K=133, ~110 CPU-min sunk) is no longer
  running.** It was not targeted by anything done here (the kills issued
  were the three specific PIDs of this session's own first-attempt runs plus
  `pkill -f` on patterns matching only `*_kissat_proof` paths, which do not
  match its command line). Its `z16_17_133_nosym.json` was never updated
  past `"status": "solving"`, so it produced **no verdict** — it died before
  finishing. Most likely cause is the OS memory killer under the swap
  pressure described in §5.2, possibly aggravated by this session briefly
  running three extra solver processes; that is a plausible contribution and
  is recorded as such rather than denied. No result was lost, because it had
  no proof logging and so could not have produced a certificate anyway.

---

## 7. What a verified DRAT refutation would, and would not, establish

This is the part most likely to be overclaimed, so it is spelled out
step by step. Suppose `drat-trim` prints `s VERIFIED` and `cake_lpr` prints
`s VERIFIED UNSAT` for the `m=16, n=17, K=134` CNF.

**What that establishes — exactly one thing:**

> **(1)** The specific DIMACS file
> `search/results/proofs/z16_17_134_kissat_proof.cnf`, as a propositional
> formula, is **unsatisfiable**.

That is a statement about a file of clauses. It is a strong, independently
machine-checked statement, and it does not depend on trusting kissat at all.

**What it does *not* establish on its own.** Getting from (1) to a
statement about `Z(16,17,3,3)` needs three further steps, each of which is a
separate claim with its own justification and its own risk:

> **(2) Encoding correctness.** That the CNF is satisfiable **iff** a 16x17
> bipartite graph exists with at least 134 edges and no `K_{3,3}`.
> Combined with (1): no such graph exists.
>
> *Current justification: a hand-written argument in `sat_encoding.py`'s
> docstrings — the `k33_clauses` derivation unrolling the definition of
> `K_{3,3}` over all `C(16,3) x C(17,3)` row/column triples with explicit
> necessity and sufficiency arguments, plus reliance on pysat's
> `CardEnc.atleast` for the cardinality half — together with small-case
> validation: `test_sat_encoding.py`, the 148-case equals/atleast
> cross-validation in §4.3, and agreement with known `z` values on small
> cells. This is **not a formal proof**. It is the weakest link in the
> chain, and it is weakest precisely because it is the one step a DRAT
> checker cannot touch: the checker verifies the formula, never the
> translation. A latent bug here — a mis-indexed triple, a pysat
> cardinality edge case at this bound — would make a perfectly verified
> refutation refute the wrong question.*
>
> **(3) The monotonicity lemma** (§4.1), to turn "no graph with at least
> 134 edges" into the bound `Z(16,17,3,3) <= 133`.
>
> *Justification: proved above, elementary. Low risk.*
>
> **(4) A matching lower bound**, to turn a bound into an exact value.
> For the published `<= 133` this is our independently re-verified
> **132-edge witness**, which gives `132 <= Z(16,17,3,3) <= 133` — i.e.
> acceptance criterion **(C)**: an independently certified version of the
> published-but-never-certified upper bound. It does **not** settle the
> open question, because 133 remains possible.
>
> *Justification: the witness passes `verify/checker.py`, which checks
> `K_{3,3}`-freeness three independent ways and the edge count two, and was
> validated against hand cases, 500 random trials, and all 6 known
> literature witnesses.*

**Concretely, per instance:**

| verified UNSAT of | gives (with (2),(3)) | and with which lower bound |
|---|---|---|
| 16x17, at-least **134** | `Z(16,17,3,3) <= 133` | with our 132-witness: `132 <= Z <= 133` — criterion **(C)**, the published bound independently certified for the first time |
| 16x17, at-least **133** | `Z(16,17,3,3) <= 132` | with our 132-witness: **`Z(16,17,3,3) = 132` exactly** — criterion **(B)**, resolving the open problem |
| 13x18, at-least **117** | `z(13,18;3) <= 116` | with our verified 116-witness: **`z(13,18;3) = 116` exactly**, a self-contained certified result of our own |

Note what K=134 does **not** do: it does not resolve the open question. It
certifies the bound that was already published on someone else's
uncertified authority. That is genuine, reportable progress (criterion (C))
and it is the load-bearing case for the hand-derived chain — but it must not
be written up as having closed the gap.

**On the hand-derived `<= 134`.** The one-line derivation via the density
argument (min row degree `<= floor(e/m)`; delete that row; `e - floor(e/16)
<= z(15,17;3) = 126`; `e=135` gives `127 > 126`, contradiction) is
arithmetically correct, but it **consumes a published, uncertified value**,
`z(15,17;3) = 126`. So `Z(16,17,3,3) <= 134` by that route inherits exactly
the dependency on unverified literature that this project refuses to build
on. A verified UNSAT at K=134 is therefore *not* redundant with it: the SAT
route reaches `<= 133` while citing nothing external beyond our own
encoding and checkers. Worth keeping straight, because it is the difference
between "we re-derived a published bound" and "we cited one".

**Trust surface of a verified result, stated in full.** Even at its best,
step (1) rests on: the DIMACS file itself (auditable, and it is the same
file both the solver and both checkers read); `drat-trim`'s C
implementation (untrusted, but only as a transformer, since its LRAT output
is re-checked); `cake_lpr`'s HOL4 correctness proof *plus* its unverified
`basis_ffi.c` I/O shim (§1.2) *plus* the CakeML compiler's own verification;
and the compiler/OS underneath. What it does **not** rest on is kissat,
which is the point of the exercise.

---

## 8. Calibrated confidence

Split, because the two halves have very different risk.

**Will a run terminate?** — **Low: ~10-15%** for at least one of (a)/(b)
resolving within the resource budget. Against it: six earlier solver
configurations ran 80-107 CPU-min each on the K=133 instance and resolved
nothing; the symmetry (`16! * 17! ~ 1.2e26` equivalent copies) that made
those fail is untouched here; the disk/memory ceiling in §5 caps each run at
a few hours. And a sobering new data point measured here (§5.5): an **8x8**
instance — 967 variables, 4,964 clauses, three orders of magnitude smaller
than the target — **failed to resolve in 300 s** of kissat with the
at-least-K encoding. If 8x8 is not a 5-minute problem for CDCL, 16x17 is
very unlikely to be a 5-hour one. For it: K=134 is strictly more constrained
than K=133 and has never been run to completion; the at-least-K encoding
halves the auxiliary variables; 13x18 K=117 is a materially smaller instance
and is the likeliest near-term win.

**If one terminates UNSAT, is the certificate sound?** — **High: ~92%.**
The chain is validated in both directions: it accepts a real refutation at
two scales (a 489 KB toy proof and a 134 MB proof, the latter also
reproducing the known `z(7,7;3)=33`), and it rejects truncated,
byte-flipped, literal-tampered, and wrong-formula proofs. The final checker
is formally verified in HOL4. The residual ~8% is almost entirely step (2),
**encoding correctness** — justified by a careful hand argument plus
small-case and now mid-scale validation, but not by a formal proof, and
structurally invisible to any proof checker: the checker verifies the
formula, never the translation. Secondary residuals: `cake_lpr`'s unverified
I/O shim (§1.2), and the operational risk of mistaking a checker crash for
success — mitigated by the exit-code finding in §3.3, which whatever runs
the final check *must* respect.

**And can it be checked here?** — **Low, and this is now the sharpest
constraint of the three.** The ceiling is measured, not guessed: `cake_lpr`
needs ~9x the LRAT size in RAM, capping this machine at a ~660 MB raw
(~340 MB gzipped) DRAT proof, i.e. about 17 minutes of solving (§5.4). Both
running jobs are already past that. So conditional on one of them
terminating UNSAT, I would put only ~10-15% on the proof still being small
enough for the full HOL4-verified check locally; `drat-trim`-only checking
stays feasible somewhat longer, and the proof file remains portable to
bigger hardware. **The realistic plan if a run lands is: keep the DRAT,
check it with `drat-trim` here if RAM allows, and run `cake_lpr` elsewhere.**

The gap between the two headline numbers is the useful signal: the
*certificate infrastructure* is now sound and tested, and it is no longer
the bottleneck. The bottleneck is, as it was before, whether CDCL can
resolve an instance with `1.2e26`-fold symmetry at all — which is exactly
why `STRATEGY_V2.md` moved the primary effort to orderly generation. This
work makes the SAT lane *capable* of producing an admissible result if it
ever lands; it does not make it likely to land.
