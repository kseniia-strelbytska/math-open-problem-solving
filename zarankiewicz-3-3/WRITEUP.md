# Z(16,17,3,3) — master write-up and index

**Single entry point for this project.** Every document, program, and
experimental run is indexed here. Read this first.

Convention, binding on all future work: **every new program gets an entry in
§3 and every new run gets a row in §4, at the time it happens.** A result that
is not written down here does not count.

---

## 1. The problem, and the honest status

`z(m,n) := z(m,n;3)` is the maximum number of edges a bipartite graph with
parts of size `m` and `n` can have while containing no `K_{3,3}` subgraph.

**Target: `z(16,17)`.** Published bounds `132 <= z(16,17) <= 133`. The lower
bound is witnessed by an explicit matrix; the upper bound rests on an
uncertified 2016 exhaustive computation. The open question is whether a
133-edge `K_{3,3}`-free `16 x 17` graph exists.

### What this project has actually established

| result | status |
|---|---|
| `z(7,7) <= 33`, machine-verified end to end (HOL4-verified checker) | **PROVED, certified** |
| `z(9,17) = 81` and `z(10,17) = 90`, computed from scratch | **PROVED**, witnesses independently certified |
| `z(11,17) <= 98`, by exhaustive refutation of `11x17 @ 99` | **PROVED**, and by **two independent routes** (a direct 32.0M-node refutation, and a separate reduction route via 10x17 extensions: 24 parents, 0 extensions) |
| **`z(16,17) <= 138`, entirely self-contained** — no published value anywhere in the derivation | **PROVED** (density chain from our own `z(11,17) <= 98`) |
| `z(k,k)` for `k = 3..9` reproduced from scratch | **PROVED**, agrees with published values |
| 32 small cells agree with a deliberately independent second searcher | **verified, both directions** |
| A complete elementary reduction of `z(16,17)` to two finite enumerations | **derived** (§ `REDUCTION.md`), but *conditional* — see below |
| `z(16,17) <= 134` by hand | **derived**, conditional on the published `z(15,17) <= 126` |
| Self-contained re-derivation of `z(15,17) = 126` | **NOT achieved.** Best self-contained bound is `<= 130`. (An earlier claim of "infeasible by ~10 orders of magnitude" was based on a projection later contradicted by measurement and is **withdrawn** — see §Measured feasibility.) |
| `z(16,17) <= 133` (criterion C) | **NOT achieved** |
| `z(16,17) = 132` (full resolution) | **NOT achieved** |

**Bottom line: the open problem is not resolved.** Full resolution (settling
133 vs 132) remains out of reach on this hardware. But the picture is less
closed than an earlier version of this document claimed: the self-contained
upper bound has moved `144 -> 138`, and one further refutation at `k=12`
— now measured at roughly 6-16 hours rather than the week previously
projected — would reach **`z(16,17) <= 134` with no citation anywhere in the
derivation**, matching the hand-derived bound while depending on nothing but
our own proved values.

The value of the work is (a) a rigorous reduction, (b) a validated and
genuinely certifying toolchain, (c) three from-scratch exact-or-bound values
(`z(9,17)=81`, `z(10,17)=90`, `z(11,17)<=98`), (d) a self-contained
`z(16,17) <= 138`, and (e) a *quantified*, and now twice-corrected, account
of exactly where the wall is and why.

### The three findings that most changed the plan

1. **SAT/CDCL is hopeless here** (§`search/SAT_LOG.md`). Not a hunch — an
   8x8 instance at `K=43`, only 967 variables, failed to resolve in 300 s.
   The target has 272 cells. ~5 CPU-hours across six solver configurations
   produced zero verdicts. The instance carries `16! * 17! ~ 1.2e26`
   symmetry that CDCL cannot exploit, and the symmetry-breaking clauses
   intended to fight it made a *known-satisfiable* instance unsolvable that
   otherwise solved in 213 s.
2. **The density-lemma ladder does not close from below — and the reason is
   a one-edge divisor cliff, not a general leak.** (§5 and §11.4a of the
   orderly log.) The chain step is
   `f(j) <= max{e : e - floor(e/j) <= f(j-1)}`. Starting from our proved
   `f(9) = 81`, the `k=10` value is 90, `floor(90/10) = 9`, and the whole
   chain then runs on divisor 9: `81, 90, 99, ..., 144`. Starting from
   `f(9) = 80` it would run on divisor **8** throughout and land at 136.

   So `f(9) = 81` sits **exactly one edge on the expensive side of a cliff
   worth eight edges at the target.** And that door is *mathematically*
   shut, not merely expensive: `f(9) = 81` is proved exactly — UNSAT at 82
   and 83, plus an explicit certified 9-regular 81-edge witness. No amount
   of compute improves it. This is the clearest place in the project where
   the obstruction is mathematical rather than computational.

   Consequence: all remaining progress must be bought edge-by-edge at
   `k = 11, 12`, where the chain propagates 1:1 (`+8` per level, so one
   edge saved at `k=11` is one edge saved at `k=16`). Buying one such edge
   is what took the self-contained bound from 144 to **138**.
3. **My "narrow ladder" reformulation was wrong** (§6.3 of the orderly log).
   I proposed climbing `Ext(13,110) -> Ext(14,118) -> Ext(15,126)` on the
   grounds each rung needs only degree-8 extension rows. It is *the same
   search tree*, not a smaller one: the generator already orders rows by
   descending degree, so its last row is exactly the row the density lemma
   deletes, and the tight-prefix constraints fall out with no ladder framing.
   The ladder feels narrow because `|Ext(k,e)|` — the *answer* size — is
   small; the cost is the intermediate levels, still branching ~40x per row.
   **Confusing the size of an answer with the cost of computing it was my
   error, and it is recorded here rather than quietly dropped.**

---

## 2. Document index

| document | what it contains |
|---|---|
| `WRITEUP.md` | **this file** — index, program inventory, run log |
| `README.md` | problem statement, acceptance criteria (A)-(E), working discipline |
| `PROGRESS.md` | dated chronological narrative of the whole project |
| `REDUCTION.md` | the mathematical core: reduction to two extremal enumerations |
| `STRATEGY_V2.md` | the strategy re-evaluation and pivot away from monolithic SAT |
| `LITERATURE.md` | the 2016 method (Lemmas 2-4), what's been tried in the field, what's ruled out |
| `SETUP.md` | environment and exact package versions |
| `data/known_witnesses/SOURCES.md` | provenance of the six literature witness matrices |
| `search/SAT_LOG.md` | the SAT workstream, including its closure with no verdict |
| `search/SAT_LOG_EXTRA_SOLVERS.md` | kissat / z3 backends |
| `search/CERTIFICATE_LOG.md` | the DRAT/LRAT certificate pipeline and the `z(7,7)` result |
| `search/LOCAL_SEARCH_LOG.md` | simulated annealing, uniform-random moves |
| `search/LOCAL_SEARCH_LOG_TABU.md` | conflict-biased tabu search |
| `search/orderly/ORDERLY_LOG.md` | orderly generation, the exact values, the feasibility measurements |
| `../prover/idea-ledger.md` | every approach tried, with status and reason ([L1]-[L18]) |
| `../prover/reviewer.md` | the independent-reviewer persona used for consultation |

---

## 3. Program inventory

### 3.1 Verification — the trust anchor

**`verify/checker.py`** — the only component allowed to certify a result.
Answers "does this `m x n` 0/1 matrix have exactly `N` edges and no
`K_{3,3}`?". Deliberately over-built: edge count by two independent methods
(numpy sum, plain-Python double loop) and `K_{3,3}` detection by three
structurally different ones — row-triple intersection, the dual column-triple
intersection on the transpose, and a `networkx` adjacency-based check. All
must agree; disagreement raises `CheckerDisagreement` rather than picking a
winner. Underlying lemma: for a fixed 3-row set, a `K_{3,3}` exists iff at
least 3 columns are 1 in all three rows.
*Known weakness, named not hidden:* all three detectors rest on that same
characterisation, so they are independent in implementation but NOT in
mathematics — their agreement is evidence about the code, not the lemma.

**`verify/test_checker.py`** — 18 tests. Includes the lemma guard that the
above weakness requires: `_brute_force_definition_literal` enumerates
row-triples CROSSED with column-triples and tests all 9 cells, i.e. the
definition with no intersection reformulation, so it *can* detect a wrong
characterisation. The equivalence is checked exhaustively over all `2^9`
3x3 and all `2^12` 3x4 matrices, plus randomised shapes to 16x17. Also
hand-verified small cases (reasoning in comments), malformed-input
rejection, and 500 random trials.
**Result: 18/18 pass**, re-run independently by the coordinator rather than
taken on report. (An earlier revision claimed a "definition-based" 4th
ground truth that was in fact the same characterisation in different code;
the reviewer caught this and it was replaced with a real one.)

**`verify/test_known_witnesses.py`** — checks all six literature witness
matrices. **Result: all six verified** (13x18=116, 14x17=118, 14x18=124,
15x17=126, 15x18=132, and the target cell's 16x17=132).

### 3.2 Local search (concluded, negative)

**`search/zark_core.py`** — shared core. Maintains a 0/1 matrix as row
bitmasks with an *incrementally* updated conflict energy: per row-triple,
`max(0, popcount(r_i & r_j & r_k) - 2)`, summed. `O(m^2)` per cell toggle
rather than `O(m^3)`. Also holds `certify()`, the single bridge to the real
checker — search-side bookkeeping is never trusted as a verdict.
**Result: self-test passes** (2000 random toggles agree with a full
recompute; known witness re-certified).

**`search/local_search_attack.py`** — simulated annealing in three phases:
(1) 150 restarts seeded from the known 132-edge witness, (2) 80 from-scratch
restarts, (3) structural circulant constructions from quadratic residues
mod 17. **Result: 0/230 reached 133 edges at zero conflict energy.** Best
was the 132-edge seed itself; forced to 133 the floor was conflict energy 2.
Phase 3 gave a clean 128-edge construction, below the known 132, and every
single-residue extension jumped to energy 168-224 — explained structurally:
vertex-transitivity replicates any violation across all 16 rotations at once,
so symmetric ansatze cannot land on a tight threshold.

**`search/refine_near_miss.py`** — takes the 7 best near-misses and applies
an *exhaustive* single-swap search (18,487 pairs each) plus 100k further
annealing iterations across reheat cycles. **Result: all 7 are strict local
optima under both** — 129,409 swap evaluations, zero improvements.

**`search/tabu_search_attack.py`** — conflict-biased move selection (using
`conflict_triples()`), a tabu list with aspiration criterion, and live 2-4
cell compound moves. Built specifically to fix the previous workstream's
named weakness (uniform-random moves). **Result: identical energy-2 floor**
(5/150 vs 7/150). It *was* significantly better at repairing back to the
132-edge basin (9.3% vs 2.0%, Fisher's exact p ~ 0.01) — a measurably better
searcher hitting the same ceiling, which is the useful part: it suggests the
floor is structural rather than an artifact of a weak move set.

### 3.3 SAT (concluded, no verdict on the target)

**`search/sat_encoding.py`** — CNF encoder. Variables `x[i][j]` per cell;
one 9-literal clause per (row-triple x column-triple) forbidding all nine
being true, which is exactly the definition of `K_{3,3}` unrolled and is both
necessary and sufficient; a cardinality constraint in either `equals` or
`atleast` mode; and optional "double lex" row/column symmetry breaking via a
Tseitin-encoded lex-comparison gadget. Also documents the **monotonicity
lemma** (achievable edge counts are downward closed, since deleting an edge
cannot create a `K_{3,3}`), without which an "exactly-K UNSAT" result would
not formally imply an upper bound. The `atleast` mode halved auxiliary
variables (37,256 -> 18,764 at K=134).

**`search/test_sat_encoding.py`** — validation of the riskiest component.
Exhaustively checks the lex gadget against an independent plain-Python
lex-compare over **all 336 bit-pairs** for widths 2,3,4; then checks
symmetry-breaking on/off SAT/UNSAT agreement on 6 small shapes, 4 of them
against full brute-force ground truth. **Result: 3/3 pass, zero
disagreements**, re-run independently by the coordinator. Also a 148-case
`equals` vs `atleast` cross-validation with zero disagreements.

**`search/sat_attack.py`** — pysat-based runner (Cadical153, Glucose3,
Minisat22), independently re-verifying any SAT witness through the checker.
**Result: found a genuine 116-edge witness at 13x18 in 213 s** (no symmetry
breaking), independently re-verified. **No verdict on the real target.**
Missing feature worth noting: no `--time-limit`/`--memory-limit`.

**`search/external_sat_runner.py`** — DIMACS export plus external-binary
subprocess runner for kissat and z3, with DRAT proof output, parsing the
`s SATISFIABLE`/`s UNSATISFIABLE` line and cross-checking it against the
exit code (mismatch is reported as `unknown`, never silently resolved).

**`search/proof_disk_guard.sh`** — enforces per-run proof-size and RSS
budgets and a 3 GB free-disk floor, shedding runs in reverse priority.
Necessary because macOS supports neither `ulimit -v` nor `-d` and kissat has
no memory flag. Written after uncompressed proofs burned 5.4 MB/s — 18 GB in
56 minutes, on a machine-wedging trajectory.

### 3.4 Orderly generation (the main effort; C, for speed)

**`search/orderly/orderly.c`** — the main exhaustive isomorph-reduced
generator. Builds row by row over 17-bit row masks with rows in descending
degree order; maintains the 680 column-triple multiplicity counters, each
capped at 2; prunes by prefix bound (`E_k <= f(k)`), suffix bound
(remaining rows can contribute at most `(m-k) * d_k`), and remaining triple
budget. Has a `--countlevel L` mode that cuts the search at level `L` so the
surviving-configuration count at that level is *exact*, which is how the
feasibility numbers below were measured rather than guessed.

**`search/orderly/brute.c`** — a deliberately independent second searcher,
written to cross-check `orderly.c` rather than share its assumptions.

**`search/orderly/validate.py`**, **`search/orderly/test_reduction.py`** —
validation harnesses, including asserting the degree-sequence counts come out
as the partition numbers `p(6)=11` and `p(5)=7` predicted in `REDUCTION.md`.

**Results:**
- `z(9,17) = 81` and `z(10,17) = 90` **proved from scratch**, witnesses
  certified by `verify/checker.py`. The `f(9)` witness is 9-regular.
- `z(k,k)` for `k = 3..9` reproduced, including all four published anchors.
- 32 small cells agree with `brute.c` in both directions.
- The load-bearing negative: `f(9) = 81`, not the `78` the ladder needs.

---

## 4. Consolidated run log

Every experiment, with its outcome. Times are single-core on an 8-core Apple
M-series unless noted.

| # | program / run | parameters | outcome |
|---|---|---|---|
| R1 | `verify/test_checker.py` | 18 tests incl. exhaustive lemma check over all 3x3/3x4 matrices | **18/18 pass** |
| R2 | `verify/test_known_witnesses.py` | 6 literature matrices | **all 6 verified** |
| R3 | `local_search_attack.py` ph.1 | 150 restarts x 20k iters, seeded | 0/150 at 133; floor energy 2 |
| R4 | `local_search_attack.py` ph.2 | 80 restarts x 30k iters, from scratch | 0/80; best 122 edges |
| R5 | `local_search_attack.py` ph.3 | QR mod 17 circulants, 12 variants | 128 edges clean; extensions energy 168-224 |
| R6 | `refine_near_miss.py` | 7 near-misses, 129,409 swaps + 700k iters | all 7 strict local optima |
| R7 | `tabu_search_attack.py` | 150 restarts, conflict-biased + tabu | 0/150; same energy-2 floor; better basin repair (p~0.01) |
| R8 | `test_sat_encoding.py` | 336 lex pairs + 6 shapes | **3/3 pass, 0 disagreements** |
| R9 | `sat_attack.py` | 13x18, K=116, no sym-break, Cadical153 | **SAT in 213 s**, witness certified |
| R10 | `sat_attack.py` | 13x18, K=116, **with** sym-break, 3 solver/encoding combos | **no verdict**, 10-22+ CPU-min each — performance finding |
| R11 | `sat_attack.py` | 16x17, K=133, Cadical153, no sym-break | **no verdict**, 116 CPU-min at 98-100% CPU |
| R12 | `sat_attack.py` | 16x17 K=133 (sym), K=134, Glucose3 | killed during the strategy pivot; no verdicts |
| R13 | `external_sat_runner.py` | 3x3 K=9; 4x4 K=8 (smoke) | UNSAT / SAT as expected, witness certified |
| R14 | certificate chain | 6x6, K=27 | **`s VERIFIED`** — certifies `z(6,6) <= 26` |
| R15 | certificate chain | **7x7, K=34**, 133.7 MB proof | **`s VERIFIED` + `s VERIFIED UNSAT`** — certifies `z(7,7) <= 33` |
| R16 | certificate chain | corrupted / truncated / byte-flipped / wrong-CNF proofs | **all correctly rejected** |
| R17 | `external_sat_runner.py` | 8x8, K=43, 967 vars | **no verdict in 300 s** — the datum that retired SAT |
| R18 | `orderly.c` | `z(k,k)`, k=3..9 | all reproduced, match published |
| R19 | `orderly.c` | 32 small cells vs `brute.c` | all agree, both directions |
| R20 | `orderly.c` | `z(9,17)`: SAT at 81, UNSAT at 82 | **`f(9) = 81` PROVED**, 2.41M nodes, 74.9 s |
| R21 | `orderly.c` | `z(10,17)` | **`f(10) = 90` PROVED**, 7.55M nodes, 302 s |
| R22 | `orderly.c --countlevel` | 15x17, dfloor 8, emax 126 | exact widths L1..L6: 6 / 67 / 1,395 / 43,447 / 1,966,099 / 81,381,805 |
| R25 | `orderly` | 11x17, `--decide 99` | **EXHAUSTED, 32,034,663 nodes, 3,255.8 s -> `f(11) <= 98`** |
| R26 | `orderly` | 10x17, `--enum 90 --extend 9` | **EXHAUSTED, 24 parents, 0 extensions -> `f(11) <= 98` by a SECOND independent route** |
| R27 | `orderly2` | 11x17, `--decide 99`, re-run of R25 | reproduced exactly -- 32,034,663 nodes |
| R28 | `orderly2` | 9x17, `--decide 83` / `--decide 82` | regression vs log: 347,899 / 2,412,355 nodes, both exact matches |
| R29 | `orderly3` | 9x17 (R9 optimisation) | identical node counts to R28 -- optimisation verified non-semantic |
| R30 | `orderly2` | 11x17, `--decide 98` | decides `f(11)=98` vs `<=97` -- running |
| R31 | `orderly3 --countlevel` | 12x17, `--decide 106`, L=6..9 | exact `k=12` tree widths, to replace projection with measurement -- running |
| R23 | kissat + DRAT | 16x17 **K=134**, at-least-K, no sym-break | **running** (primary certified target) |
| R24 | kissat + DRAT | 13x18 **K=117**, no sym-break | **running** (would give us `z(13,18)=116` as our own certified result) |

### Measured feasibility

> **An earlier version of this section was wrong and is withdrawn.** It
> projected a uniform 20x-per-level growth from a `k <= 9` anchor, giving
> `k=11` ≈ 8 h, `k=12` ≈ 7 days, `k=15` ≈ 160 years, and concluded the
> bottom-up route was out of reach "by roughly 10 orders of magnitude."
> The `k=11` refutation then *actually ran* in **0.9 h**, i.e. the anchor
> was 9x too high. **That 10-orders-of-magnitude margin is retracted.**
> Per-level growth in time is ~6.5x-17x, not ~21x. The lesson recorded:
> the projection was built on an anchor two levels below where it was
> being applied, and nothing flagged that as a risk until measurement
> contradicted it.

Measured refutation costs, `n = 17`, all EXHAUSTED and all using only this
project's own values:

| `k` | probe | nodes | time | nodes/s |
|---|---|---|---|---|
| 7 | whole level | 21,437 | 0.49 s | 44 k |
| 8 | whole level | 73,007 | 3.70 s | 20 k |
| 9 | `>= 83` | 347,899 | 19.3 s | 18 k |
| 9 | `>= 82` (the hard one) | 2,412,355 | 74.9 s | 32 k |
| 10 | `>= 91` | **0** | **0 s** | — (free: chain is tight here) |
| 11 | `>= 99` | **32,034,663** | **3,255.8 s** | 9.8 k |

Note "the refutation at level `k`" is not one thing — cost depends on how
far the target sits above the true value, so the honest per-level factor
is a range (3.6x-9.6x in nodes), and throughput *falls* with level
(~0.55x per level) because constraints reject deeper inside the row
enumeration.

Revised projection for one refutation at the chain's bound:

| `k` | projected nodes | projected 1-core time | old (withdrawn) |
|---|---|---|---|
| 12 | 1.2e8 - 3.1e8 | **6 h - 16 h** | ~7 days |
| 13 | 4e8 - 3.0e9 | 1.6 d - 12 d | ~5 months |
| 14 | 1.5e9 - 2.9e10 | 10 d - 6 mo | ~8 years |
| 15 | 5e9 - 2.8e11 | 2 mo - 9 yr | ~160 years |

**This changes the practical verdict at exactly one level:** `k = 12` moves
from "a week, don't bother" to "about a day, worth attempting" — and it is
being attempted (width measurement in progress). `k = 13` moves from
impossible to plausible-with-patience but outside a session. `k >= 14`
stays out of reach.

### What each further edge would buy

Because the chain step is `+8` throughout this range, the requirement
inverts exactly:

| goal | needs | status |
|---|---|---|
| `z(16,17) <= 138` | `f(11) <= 98` | **done** |
| `z(16,17) <= 137` | `f(11) <= 97` or `f(12) <= 105` | one more refutation |
| `z(16,17) <= 134` | `f(11) <= 94` or `f(12) <= 102` or `f(13) <= 110` | `k=12` route is ~6-16 h |
| `z(16,17) <= 133` | `f(11) <= 93` or `f(12) <= 101` | see below |

And the hard limit no compute fixes: **you cannot refute a value that is
actually achievable.** If the published `8k+6` progression
(`f(13)=110, f(14)=118, f(15)=126`) extrapolates down correctly, then
`f(12) = 102` exactly — in which case `f(12) <= 102` is attainable and
`z(16,17) <= 134` is reachable by a *single* `k=12` refutation, while
`z(16,17) <= 133` would require `f(12) <= 101`, which would be **false**
and therefore unreachable by this route at all. Reaching 133 would then
need the extremal-enumeration route of `REDUCTION.md`, not the chain.

Separately, the `e=134` extremal-parent enumeration measured ~40x width
growth per row, still `8.1e7` configurations at level 6 — optimistically
~40 core-hours if the width peaks at level 8, realistically `1e12`-`1e14`
nodes.

---

## 5. What would actually be needed to finish

Stated plainly, since the honest answer is "more than this machine has":

1. **The reduction is sound but conditional.** `REDUCTION.md` reduces the
   problem to enumerating `Ext(15,17,126)` and `Ext(15,17,125)`. That
   reduction assumes `z(15,17) = 126`, which we can cite but *cannot*
   self-derive (best self-contained bound: `<= 130`, improved from `<= 135`
   by the `f(11) <= 98` result).
2. **Either accept the citation and buy compute** — the `e=134` enumeration
   at `1e12`-`1e14` nodes is a cluster-scale job, not a laptop one — **or
   close the `k = 11, 12, 13` refutations**, which is where the entire
   bottom-up obstruction now provably lives.
3. **The certificate pipeline is ready and validated**, so if either
   computation is run elsewhere, the result can be certified rather than
   asserted — subject to one measured caveat: this machine can *produce* a
   certificate larger than it can *check* (cake_lpr needs ~9x the LRAT size
   in RAM, capping us near 660 MB of raw DRAT).
