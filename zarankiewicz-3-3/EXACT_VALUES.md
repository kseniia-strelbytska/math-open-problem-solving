# Four exact Zarankiewicz values in the `n = 17` column, from scratch

## What this PR establishes

| cell | value | lower bound | upper bound | both self-contained? |
|---|---|---|---|---|
| `z(8,17;3)`  | **74** | 74-edge witness, checker-verified | `--decide 75` EXHAUSTED | **yes** |
| `z(9,17;3)`  | **81** | 81-edge witness, checker-verified | `--decide 82` EXHAUSTED | **yes** |
| `z(10,17;3)` | **90** | 90-edge witness, checker-verified | `--decide 91` EXHAUSTED | **yes** |
| `z(11,17;3)` | **96** | 96-edge witness, checker-verified | `--decide 97` EXHAUSTED | **yes** |

"Self-contained" means: **no published value appears anywhere in the
derivation.** The witnesses are in `data/our_witnesses/` and are re-verified
on every test run by `verify/checker.py`, whose three independent `K_{3,3}`
detectors must agree or the run raises. The upper bounds come from the
generator in `search/orderly/orderly.c`, which is landed in this PR so the
refutations are reproducible rather than asserted.

**Why this PR exists.** A reviewer rejected an earlier PR in this series
partly because it referred to `z(9,17;3) = 81` and `z(10,17;3) = 90` as
"proved by this project" while no supporting artifact was reachable from the
branch — they had been proved on an abandoned mega-branch that this
restarted, smaller-PR series never carried over. That objection was correct.
This PR lands the artifacts. The values were re-run fresh here rather than
copied forward.

## Relation to the literature

Stated plainly, because three of these four are **not new**. Provenance
labels are the ones this repo uses elsewhere, and they are mandatory in any
table here that mixes derived and external values:

- **[VERIFIED HERE]** — derived by code and data in this PR.
- **[CITED, NOT LANDED]** — precise source given, but **not** recorded in
  this repo's own `LITERATURE.md`, so a reader of this repository cannot
  check it without fetching the paper.
- **[NOT CHECKED]** — we have not read the source for this cell.

| cell | our result | published status | label |
|---|---|---|---|
| `z(8,17;3) = 74`  | **[VERIFIED HERE]** | **we have not read this cell.** A literature query is outstanding. | **[NOT CHECKED]** |
| `z(9,17;3) = 81`  | **[VERIFIED HERE]** | Collins–Riasanovsky–Wallace–Radziszowski, arXiv:1604.01257 (J. Algorithms and Computation 47(1) (2016) 63–78), **Table 4**, row `m=9` col `n=17`, **boldface** = "an exact value" per their legend; also **boldface** in Tan arXiv:2203.02283 **Table 3** | **[CITED, NOT LANDED]** |
| `z(10,17;3) = 90` | **[VERIFIED HERE]** | same table, row `m=10`, **boldface + superscript `*`** ("a superscript `*` indicates that there exists a unique `(m,n,z(m,n;s))_s`-graph"); also **boldface** in Tan Table 3 | **[CITED, NOT LANDED]** |
| `z(11,17;3) = 96` | **[VERIFIED HERE]** | same table, row `m=11`, **boldface**; also **boldface** in Tan Table 3 | **[CITED, NOT LANDED]** |

**On the `[CITED, NOT LANDED]` label, and why it is used here rather than
plain `[CITED]`.** These three citations are precise — paper, table, row,
column, and the legend convention that gives the marking its meaning — and
they came from a glyph-level reading of the embedded PDF fonts. But none of
them is recorded in this repo's `LITERATURE.md`, which currently covers the
`k >= 13` cells and the `(16,17)` cell only. Until they are, a reader who
trusts nothing but this repository cannot check them. Landing them in
`LITERATURE.md` is a separate, small change and is deliberately not bundled
into this PR.

**Nothing in this PR's own claims depends on any of them.** The four exact
values are established entirely by the witnesses in `data/our_witnesses/`
and the refutations in the run log. The literature column exists solely to
be honest about novelty, and it is:

- `z(9,17;3)`, `z(10,17;3)`, `z(11,17;3)` are **third independent
  derivations** of twice-published values. Useful — they are the lower half
  of any exactness claim, sourced from matrices we checked rather than from
  citations — but **not new**, and not presented as such.
- `z(8,17;3) = 74` is **not claimed as new either.** We have not read that
  cell. Note that `74` breaks the `9k` pattern holding at `k = 9` (81) and
  `k = 10` (90), since `9 * 8 = 72`. If a published table gives `72` there,
  that is a **disagreement to chase**, not a discovery — and the right first
  suspicion would be our own generator, not the table.

## Method

### The upper bounds

`orderly.c` is an orderly-generation / canonical-augmentation search. It
builds the matrix row by row with rows constrained lex-non-increasing, keeps
`C(17,3) = 680` column-triple multiplicity counters capped at 2, and prunes
on prefix, suffix, and triple-budget bounds. `--decide T` answers "does an
`m x 17` `K_{3,3}`-free graph with at least `T` edges exist?" and returns

- `FOUND` plus an explicit witness (`WITNESS_ROWS`), or
- `EXHAUSTED`, meaning the entire search space was traversed with no
  solution.

`EXHAUSTED` at `T` gives `z(m,17;3) <= T - 1`, using monotonicity: deleting
an edge from a `K_{3,3}`-free graph cannot create a `K_{3,3}`, so achievable
edge counts are downward-closed and refuting "at least `T`" refutes
everything above it too.

### The lower bounds

Each witness is the generator's own `FOUND` output, re-parsed and handed to
`verify/checker.py` — which shares no code with the generator and was
developed and merged before it (PR #4, the trust anchor). A witness the
generator produced but the checker rejected would fail the test suite.

### Reproducing

```
cd zarankiewicz-3-3/search/orderly
cc -O2 -o orderly orderly.c
./orderly -n 17 -m 8  --decide 75          # EXHAUSTED  -> z(8,17)  <= 74
./orderly -n 17 -m 9  --decide 82          # EXHAUSTED  -> z(9,17)  <= 81
./orderly -n 17 -m 10 --decide 91 --assume 9:81   # EXHAUSTED -> z(10,17) <= 90
./orderly -n 17 -m 11 --decide 97 --assume 9:81   # EXHAUSTED -> z(11,17) <= 96
./orderly -n 17 -m 11 --decide 96          # FOUND      -> z(11,17) >= 96
cd ../..
pytest verify/test_our_witnesses.py        # re-verifies all four witnesses
```

## Attempts to break this before believing it

- **Is the generator's `EXHAUSTED` trustworthy?** The failure mode that
  matters is an over-constrained search that misses solutions and reports a
  false `EXHAUSTED`. Three guards:

  1. `brute.c`, landed alongside it, is a deliberately independent and
     deliberately simple searcher written to cross-check small cells.
     `make cross-check` sweeps n=4..7, m=3..6, targets 6..24 and compares
     verdicts. **Result: 144 cells compared, 144 agreed (107 FOUND, 37
     EXHAUSTED).**

     **This target was broken and is now fixed -- read this before trusting
     it.** The earlier version invoked `./brute -n $n -m $m --decide $t`, but
     `brute.c` parses argv *positionally*, so every cell silently ran as
     `n=0, m=<n>, T=0`. It also grepped brute's output for `status=`, a
     substring brute never prints. Either bug alone made the target print
     "agree on every small cell" **unconditionally**, whatever the two
     programs computed -- and that empty result was cited in this PR as
     load-bearing evidence. A reviewer found both.

     Guards added so it cannot silently pass again: it counts cells and fails
     on zero; it fails on a *missing* verdict rather than skipping the cell;
     and it fails unless **both** FOUND and EXHAUSTED occur in the sweep, so a
     degenerate range that only ever yields one verdict is rejected.

     The validator was then itself validated: comparing `orderly` at target 18
     against `brute` at target 16 on `(n=5,m=4)` -- which straddles a genuine
     verdict boundary -- correctly reports EXHAUSTED vs FOUND. So the check
     provably distinguishes verdicts rather than being blind.
  2. Every `EXHAUSTED` in the table above is bracketed by a `FOUND` one edge
     below. A search too constrained to find anything would fail to produce
     the witness, and the witness is independently checked. This is the
     specific reason the table has both columns rather than just the
     refutations.
  3. `--nocanon` disables the column-canonicity pruning rule for validation.

- **Is `--assume` smuggling in an input? No -- and not for the reason an
  earlier version of this document gave.** That version argued at length that
  `--assume 9:81` "can only tighten pruning, never cause a false FOUND", and
  that the dependency was internal and acyclic. A reviewer traced the code and
  found the argument analyses a mechanism that **never runs**:

    * `hassume[]` is read in exactly one place, `hub()` (`orderly.c:211`).
    * But `suffix_bound()` (`:223`) and the prefix check in `gen()` (`:381`)
      both select `hval()` -- the *exact* recursive sub-search -- whenever
      `h_exact && j <= hcap_level`. `h_exact` defaults to 1 and `hcap_level`
      defaults to `MAXM` = 24.
    * Every `j` in these runs is `<= 11 <= 24`, and neither `--hmode ub` nor
      `--hcap` is passed anywhere. So `hub()` is never called, `hassume[]` is
      never read, and **`--assume` has no effect on any run in this PR.**

  This is *better* for soundness than the argument it replaces: the bounds
  actually used are exact, so they need no assumption to be valid. The flag is
  **vestigial here** and is retained in the reproduction commands only so they
  match the command lines that were actually run. It could be dropped with no
  change to any result.

  The general lesson is the one this document keeps relearning: an argument
  about why a mechanism is safe is worthless if the mechanism is not the one
  in the path. The check is to read the code, not the flag.

- **Degenerate cases.** `--decide 0` and empty targets: an early version of
  a *shell loop* here passed an empty `--decide` argument (zsh does not
  word-split unquoted parameters, unlike bash) and the generator returned an
  all-zero 8-row "witness" with 0 edges. That would have passed a naive
  "is it `K_{3,3}`-free?" check — it is trivially free. It was caught because
  the checker is always called with `expected_edges`, which no longer matched.
  Recorded because it is a good argument for always asserting the edge count
  and never only the freeness.

- **Reproducibility.** Two node counts in this PR were reproduced exactly:
  `-m 8 --decide 75` returned **50,175** from the Makefile-built binary here,
  and `-m 9 --decide 82` returned **2,412,355**, matching a count archived in
  an earlier session from a different build.

  An earlier version of this paragraph also cited "32,034,663 nodes" as a
  re-run of "one k=11 search" while the run-log table gives **32,073,855** for
  `-m 11 --decide 97`. A reviewer flagged the mismatch. Both figures are
  correct but they are **different searches**: 32,073,855 is `--decide 97`
  (this PR), and 32,034,663 is `--decide 99` from an earlier session, which is
  not landed here. Juxtaposing them read as one number contradicting itself,
  in the very paragraph arguing that node counts are the trustworthy
  invariant. The unlanded figure is removed rather than explained, since it
  cannot be checked from this PR.

  Wall-clock is deliberately not tabulated: the same k=11 search took 7,760 s
  in one session and 3,255 s in another for an identical node count, so
  seconds carry no information here.

## The step I am least confident in

Not the lower bounds — those are explicit matrices, checked by three
detectors that must agree.

The exposure is entirely in the **`EXHAUSTED` verdicts**, which assert a
negative about a large search space and rest on the correctness of one C
program's pruning. The mitigations above (independent second searcher on
small cells, a `FOUND` bracketing every `EXHAUSTED`, exact node-count
reproduction, `--nocanon` validation) are real but none is a proof of the
generator.

Confidence: **~0.97** on each exact value as a whole. Separately, **~0.97**
on the weakest step, the `EXHAUSTED` verdicts — the two are close because
the lower-bound halves are near-certain and the whole claim is
gated by the refutations, so the overall number essentially *is* the
refutation number. The honest way to raise it is a machine-checkable
certificate for the refutations, not more restatements of confidence; this
project has such a pipeline working end-to-end for a smaller cell
(`z(7,7;3) <= 33`, verified by `drat-trim` and by the HOL4-verified
`cake_lpr`), but the proofs for these cells were measured far past the local
checking ceiling and are not attempted here.

## Run log — the node counts, which are the reproducible invariant

Produced by the binary built from `search/orderly/Makefile` in this PR.

| run | verdict | nodes | what it establishes |
|---|---|---|---|
| `-m 8  --decide 74` | FOUND | — | `z(8,17;3) >= 74` (witness) |
| `-m 8  --decide 75` | **EXHAUSTED** | 50,175 | `z(8,17;3) <= 74` |
| `-m 8  --decide 76` | EXHAUSTED | 10,402 | corroborating (monotonicity makes it redundant) |
| `-m 8  --decide 77` | EXHAUSTED | 1,706 | corroborating |
| `-m 9  --decide 81` | FOUND | — | `z(9,17;3) >= 81` (witness) |
| `-m 9  --decide 82` | **EXHAUSTED** | 2,412,355 | `z(9,17;3) <= 81` |
| `-m 10 --decide 90` | FOUND | — | `z(10,17;3) >= 90` (witness) |
| `-m 10 --decide 91` | **EXHAUSTED** | 2,411,772 | `z(10,17;3) <= 90` |
| `-m 11 --decide 96` | FOUND | 4,708,286 | `z(11,17;3) >= 96` (witness) |
| `-m 11 --decide 97` | **EXHAUSTED** | 32,073,855 | `z(11,17;3) <= 96` |

Note the shape of the `-m 8` rows: the refutations get *cheaper* as the
target rises (50,175 → 10,402 → 1,706 nodes), which is what should happen —
a higher edge target prunes harder. A search whose cost went the other way
would be a red flag worth investigating before trusting any `EXHAUSTED`
from it.

`-m 9 --decide 82` reproduced **2,412,355 nodes exactly**, matching a count
archived in an earlier session by a different build. `-m 8 --decide 75`
reproduced **50,175 nodes exactly** from the Makefile-built binary in this
PR. Wall-clock is deliberately not tabulated: an identical re-run of one
`k = 11` search took 7,760 s against 3,255 s for the same node count under
different load, so seconds carry no information here.

### Independence cross-check

`make cross-check` sweeps `n = 4..7`, `m = 3..6`, targets `6..20` and
compares `orderly`'s verdict against `brute`'s on every cell. Both are built
from separate sources with no shared helpers, precisely so that agreement
means something. Current status: **agree on every cell tried, in both
directions.**
