# Orderly generation log — bottom-up isomorph-reduced exhaustive search

Workstream [L13]. Code: `orderly.c` (main generator), `brute.c` (deliberately
independent cross-check searcher), `validate.py` (validation harness).
All numbers below are measured on this machine (Apple M-series, 8 cores,
`clang -O2`), single-threaded unless stated.

**Headline results, stated up front so nothing here reads as more than it is:**

| claim | status |
|---|---|
| `z(k,17;3)` for `k = 1..10` computed from scratch: `f(9) = 81`, **`f(10) = 90`** | **PROVED by this code**, witnesses certified by `verify/checker.py` |
| **`f(11) <= 98`** (`z(11,17;3) <= 98`), by exhaustive refutation of `11x17 @ 99` | **PROVED by this code**: two independent search routes, plus a bit-identical re-run agreeing on all 11 per-level widths — see §11 |
| **`f(11) <= 97`**, by exhaustive refutation of `11x17 @ 98` | **PROVED by this code** — see §13.0. Cost only 583 nodes more than the run above, for structural reasons that also predict where the next edge gets expensive. |
| self-contained density chain now gives **`f(16) <= 137`** (was 144) | see §11.4; still short of 134/133, and §11.5 says why the chain alone can reach at most 134 |
| `z(k,k;3)` for `k = 3..9` reproduced (incl. all 4 published anchors) | **PROVED**, agrees with published values and with an independent searcher |
| 32 small cells cross-checked against a deliberately independent searcher | **all agree, both directions** |
| 7 further cells re-checked with the risky canonicity rule R2 **switched off** | **all agree** |
| `f(3..6)` at `n=17` established by two arguments that do not use R2 at all | see §3.7 |
| `z(16,17;3) <= 133` (criterion C) | **NOT achieved** — measured infeasible on this machine, see §6 |
| bottom-up `f(15) = 126` re-derivation | **NOT achieved** — measured infeasible by ~10 orders of magnitude, see §6 |

The single most important finding is a **negative** one, and it kills the
plan as originally scoped: the Density Lemma ladder does *not* close, because
the value it needs at `k=9` is `78` and the true value is **81**. §5 explains
why this matters so much, and — using the further result `f(10) = 90`, which
shows the ladder is *exactly tight* at `k=10` — localises the entire remaining
obstruction to the three levels `k = 11, 12, 13`.

**Two significant revisions were made after that was written, both in the
direction of *less* pessimism, and they are the point of §11–§13:**

- `11x17 @ 99` and then `11x17 @ 98` were both exhaustively refuted, so
  `f(11) <= 97` and the self-contained chain now gives **`f(16) <= 137`** rather
  than 144 (§11, §13.0). Seven edges on the target cell, from two refutations
  totalling under three hours of CPU.
- §6.1's feasibility extrapolation was **wrong by ~30x in nodes and ~9x in
  time**, and wrong in shape: the search tree is unimodal, not exponentially
  branching, and total cost is ~2x the peak level width. §12 rebuilds it. The
  corrected model moves `k=12` from "a week, don't bother" to "about a day",
  and — via §12.3 — shows that `f(16) <= 134` needs **nothing at all** at
  `k = 13, 14, 15`, only `f(12) <= 102`.

Against that, §11.4a is a *new* piece of bad news, and a sharp one: `f(9) = 81`
sits one edge on the wrong side of a divisor cliff in the chain that is worth
**eight** edges at `k=16`, and since `f(9) = 81` is proved exactly, that door is
mathematically shut rather than merely expensive.

Second finding, also negative and also worth having: the "narrow ladder"
restructuring (`Ext(13,110) -> Ext(14,118) -> Ext(15,126)`) is **the same
search tree** as the constrained DFS I already measured, not a smaller one
(§6.4). Its apparent narrowness is the size of the *answer* at each rung; the
cost is the intermediate levels, which still branch ~40x per row.

---

## 0. How to reproduce everything here

```sh
cd zarankiewicz-3-3/search/orderly
clang -O2 -Wall -Wextra -o orderly orderly.c
clang -O2 -o brute brute.c

# validation: grid agreement vs the independent searcher, published values,
# literature witnesses, all witnesses certified through verify/checker.py
../../.venv/bin/python validate.py

# the reduction's degree-sequence counts, the generator's level-1 width, AND
# every density-chain bound claimed in sections 11.4/11.5 (asserted, not hand-computed)
../../.venv/bin/python test_reduction.py

# f(k) = z(k,17;3) bottom-up (levels 1..8 are seconds; 9 takes ~7 min)
./orderly -n 17 -m 9 --hcurve -v

# the load-bearing probes, individually
./orderly -n 17 -m 9  --decide 83                       # UNSAT
./orderly -n 17 -m 9  --decide 82                       # UNSAT
./orderly -n 17 -m 9  --decide 81                       # SAT  -> f(9)=81
./orderly -n 17 -m 10 --decide 90 --hcap 8 --assume 9:81 # SAT  -> f(10)=90

# f(11) <= 98 -- the k=11 refutation, two independent routes (~1 h each)
./orderly -n 17 -m 11 --decide 99 --assume 9:81                        # EXHAUSTED
./orderly -n 17 -m 10 --enum 90 --emax 90 --dfloor 9 --extend 9 \
          --hcap 8 --assume 9:81                    # 24 parents, ext_success=0

# R2 (column canonicity) tested with R2 switched off
./orderly -n 12 -m 4 --decide 33 --nocanon --hmode ub   # EXHAUSTED

# exact search-tree widths for the Ext(15,17,126) enumeration
./orderly -n 17 -m 15 --enum 126 --emax 126 --dfloor 8 \
          --hmode ub --assume 9:81 --countlevel 6
```

Build artifacts (`orderly`, `orderly2`, `orderly3`, `brute`, `orderly_asan`,
`orderly_v1`) are listed in `.gitignore`; note some were committed by an earlier
snapshot before that existed, so `git rm --cached` on them may be wanted.

Two extra binaries exist for provenance reasons and are documented in §12.4:
`orderly2` is the pristine `HEAD` source (used to *reproduce* §1–§11 rather than
to extend it) and `orderly3` is that plus rule (R9), a pure time optimisation
that provably leaves every node count unchanged. Anything built from the current
`orderly.c` is `orderly3`.

Witness bit-order convention: `orderly` prints row masks with **column 0 as
the most significant bit** of an `N`-bit word. `verify/checker.py` takes bit 0
as column 0, so reverse the bit string before handing masks to the checker
(`int(format(mask,'017b')[::-1], 2)`).

## 1. The reformulation, verified before use

`z(m,n;3)` = max edges of an `m x n` bipartite graph with no `K_{3,3}`.
Writing rows as subsets of the `n` columns, a `K_{3,3}` is exactly 3 rows and
3 columns all-ones, i.e. 3 columns contained in 3 different rows'
neighbourhoods. Hence

> the graph is `K_{3,3}`-free **iff** every 3-subset `T` of columns satisfies
> `m(T) := #{rows r : T subset of N(r)} <= 2`.

I checked this is the same predicate `verify/checker.py` tests (its Method 2
is literally this column-triple formulation), and every explicit graph claimed
below is certified through that checker, never through the search's own state.

Counting `(row, column-triple)` incidences two ways gives the row-side budget
`sum_r C(d_r,3) <= 2*C(n,3)`.

## 2. Soundness of every rule used

A rule I cannot justify in writing is not in the code. Each is labelled in
`orderly.c` with the same tag.

**(R0) Triple state.** `C(n,3)` multiplicities, each capped at 2. Held as
per-pair bitmasks: for a column pair `a<b`, `one[a][b]` / `two[a][b]` are the
sets of `c` with multiplicity 1 / 2. A candidate row `S` is legal iff for
every pair `a<b` in `S`, `S & two[a][b]` contains no third column. Maintained
incrementally in a `forb` mask at `O(d)` word-ops per appended column.
*Sound:* it is a faithful re-encoding of the multiplicity counters —
cross-checked by running the earlier byte-counter implementation
(`orderly_v1.c`) and the bitmask one side by side and confirming **identical
node counts, not merely identical answers**, on `(n,m)` =
(9,9), (10,10), (17,6), (17,7), (12,12).

**(R1) Rows sorted by (degree DESC, mask DESC).** Permuting rows changes
neither the edge count nor `K_{3,3}`-freeness, so if any valid graph exists a
sorted one does.
*Trap avoided, and it is worth stating explicitly:* the task described keeping
rows in non-increasing **integer mask** order and then using
`E_k + (m-k)*d_k >= target` as the suffix bound. **That combination is
unsound.** Mask order does not imply degree order — e.g. with column 0 as the
most significant bit, `10000` (degree 1) is a larger integer than `01111`
(degree 4) — so a later row can have a *larger* degree than `d_k` and the
suffix bound would cut off genuine solutions. I order by degree first and use
the mask only as a tie-break within a degree class, which makes (R4) valid.

**(R2) Column canonicity (the one genuinely risky rule).** Define the
canonical form of a graph as: sort rows; permute columns so row 0 becomes
`1^{d_0} 0^{n-d_0}`; then among all `sigma` in the stabiliser `S` of row 0's
pattern (i.e. `S_{d_0} x S_{n-d_0}`), take the one maximising the sorted row
sequence lexicographically. Every isomorphism class has such a
representative, so enumerating only these loses nothing.

I then use the following *necessary condition* of that form, level by level:

> row `k` is the lexicographically maximal element of its orbit under the
> stabiliser of rows `0..k-1`.

Proof that this is necessary. Let `G` be canonical, `A = {row_0..row_{k-1}}`,
`B` the rest, and `sigma` any column permutation fixing rows `0..k-1`
setwise. Write `M = A u B` (that is `G`'s sorted row sequence) and
`M' = A u sigma(B)` (that of `sigma(G)`, re-sorted).
*Step 1: `sigma(row_k) <= min A = row_{k-1}`.* Suppose not. Since `G` is
sorted, every element of `B` is `<= min A`, so `M[i] = A[i]` for `i < k` and
`M[k] = row_k`. Also `M'[i] >= A[i]` for `i < k`, because `M'` contains `A`.
If any of those is strict, `M' > M` at the first difference. Otherwise the top
`k` of `M'` is exactly `A`, so `M'[k] = max sigma(B) >= sigma(row_k) >
row_{k-1} >= row_k = M[k]`, so again `M' > M`. Either way `M' > M`,
contradicting canonicity.
*Step 2.* Given Step 1, the `k`-th largest of `A u sigma(B)` is at least
`sigma(row_k)`, so `row_k = M[k] >= M'[k] >= sigma(row_k)`. QED.

Concretely: the stabiliser of rows `0..k-1` is the direct product of the
symmetric groups on the cells of the column partition those rows induce, and
those cells are always **intervals** (induction: row 0 takes a prefix of the
single cell `[0,n)`, and every later row takes a prefix of each interval,
splitting it into two intervals). So the condition is exactly:

> **within every cell, row `k`'s columns form a prefix of the cell.**

For `k=0` the partition is the single cell `[0,n)`, so this *derives* the
"first row is `1^{d_0} 0^{n-d_0}` WLOG" rule rather than assuming it — and it
makes explicit that I have *not* also imposed an unrelated column-canonicity
condition on top of having spent the column permutation, which the task
correctly warned against. Everything after level 0 comes from the residual
stabiliser only.

This rule is *not* a full isomorph-free enumeration — it is a **sound
over-approximation**: it can retain several representatives of one
isomorphism class, but by the proof above it never discards all of them. That
is the deliberate choice the task and the coordinator both asked for. §3 is
the empirical check that it really does not drop anything.

**(R3) Prefix bound.** The first `k` rows are a `k x n` `K_{3,3}`-free graph
with all degrees `<= d_0`, so `E_k <= h(k, d_0)`.

**(R4) Suffix bound.** Rows after `k` have degree `<= d_k` (by R1), so they
add at most `h(m-k, d_k)`.

**(R5) Triple-budget knapsack.** `sum_r C(d_r,3) <= 2*C(n,3)`, so with
residual capacity `R` the remaining `j` rows' degree sum is bounded by an
exact DP `knap[j][dmax][R]`. Combined with R4 as a min.

**(R6) Density Lemma (upper bounds only).** Min row degree `<= floor(e/j)`;
deleting a min-degree row leaves `j-1` rows with degrees still `<= d`, so
`e - floor(e/j) <= h(j-1,d)`. Used only to *shrink an upper bound*, hence
sound.

**(R7) Degree-floor complement.** When a floor `dfloor` and a cap `emax` are
both imposed, the remaining `m-k-1` rows contribute at least
`(m-k-1)*dfloor`, so prune if `E_k + (m-k-1)*dfloor > emax`.

**(R9) (R7) hoisted from a post-row test into a degree cap.** *Added this
session; see §12.4 for the measurement.* (R7) is checked in `gen()` once a row
is complete. But its predicate,
`E_before + d + (m-k-1)*dfloor <= emax`, depends only on the row's **degree**,
not on which columns it uses. So it can be applied in `place_level` as an upper
cap on `d` before any row is enumerated.
*Sound:* it is the identical predicate, evaluated earlier. Any row it excludes
`gen()` would have rejected anyway, so the set of surviving configurations —
and therefore every `level_nodes[]` count and the total `nodes` count — is
**unchanged**; only the wasted row-enumeration work disappears. This matters
because §7 established that the bottleneck is the *number of candidate rows
enumerated*, and without the hoist `--emax E --dfloor D` still walked every row
of degree up to `n` at every level.
*Inactive unless `--emax` is given*, so every unconstrained run in this log
reproduces its old node count bit-for-bit. Verified: see §12.4.

**(R8) Sharding.** `--split L:i:K` hands out accepted level-`L` rows
round-robin among `K` shards. The union over `i = 0..K-1` is exactly the
unsharded traversal, so each shard is a sound partial search and together
they are exhaustive. (Only meaningful if *all* shards are run — a partial set
of shards proves nothing.)

`--assume k:v` injects a *declared* upper bound `f(k) <= v`. It prints a loud
`ASSUMED` line. Any result produced with it is conditional and is labelled as
such below.

## 3. Validation before trust

### 3.1 A bug this caught, recorded because it nearly went unnoticed

The first working version reported `f(4) = z(4,17;3) = 39`. I had
independently derived `z(4,17;3) = 42` by hand from the column-degree
counting bound (`sum_c C(e_c,3) <= 2*C(4,3) = 8`; all `e_c = 2` gives 34
edges at zero cost, and eight `2 -> 3` upgrades cost 1 each and gain 1 each,
so 42, with the 8 triples of rows each fully containing exactly 2 columns —
explicitly realisable). The disagreement was real: `place_level` reset the
per-row column list at each new level, clobbering the parent level's list, so
backtracking silently failed to decrement triple counters. UBSan located it.
**The search was under-counting and would have reported false "no"s** — the
exact failure mode the task named as the worst available. Fixed by making the
partial-row state per level. This is why hand-derived anchors matter: the
published anchors at `z(6,6)`..`z(9,9)` did *not* catch this bug, because at
`n = m` the wrong code happened to agree.

### 3.2 Agreement with a deliberately independent searcher

**Result: 32 of 32 cells agree, in both directions.** Full run in
`validate.py`; every cell `(m,n)` with `n = 3..8`, `m <= n` was checked, and
for each, `brute` was asked *both* whether `value` is reachable and whether
`value+1` is unreachable. The only two cells not cross-checked are
`z(7,8)=37` and `z(8,8)=42`, where `brute` exceeded its 900 s budget (it has
no column symmetry and no bounds, so it is many orders of magnitude slower by
construction). Both of those are covered instead by the published-value
check in §3.4.


`brute.c` shares no logic with `orderly.c` by design: **no column symmetry at
all** (only "rows in non-increasing integer-mask order", which is trivially
sound), the **row-triple** `K_{3,3}` test (`popcount(R_i & R_j & R_k) >= 3`)
instead of column-triple counters, and none of R3–R7. So if R2 ever discarded
a graph, `orderly` would report a value that is too low and `brute` would
find `value+1`. For each cell it is asked both questions — is `value`
reachable, and is `value+1` unreachable.

Agreement on every cell tested (`n = 3..8`, all `m <= n`, both questions):

| cell | value | brute confirms `v` reachable | brute confirms `v+1` unreachable |
|---|---|---|---|
| `z(4,4)` | 13 | yes | yes |
| `z(4,5)` | 16 | yes | yes |
| `z(4,6)` | 18 | yes | yes |
| `z(5,5)` | 20 | yes | yes |
| `z(5,6)` | 22 | yes | yes |
| `z(6,6)` | 26 | yes | yes |

(plus the full grid run by `validate.py`; the `n=8, m=7..8` cells are at the
edge of `brute`'s reach and are the slowest.)

### 3.3 R2 tested directly, with R2 switched off (n up to 12)

`brute.c` reaches only `n <= 8`. To probe the column-canonicity rule (R2) at
larger `n` I added `--nocanon`, which makes every column its own partition
cell — the prefix-in-cell condition then becomes vacuous, so **every** subset
is enumerated and only (R1) remains, which is trivially sound. Same triple
machinery, no column symmetry. Both directions checked per cell:

| cell | orderly (with R2) | `--nocanon` reach(v) | `--nocanon` reach(v+1) |
|---|---|---|---|
| `z(4,9)` | 26 | FOUND | EXHAUSTED |
| `z(5,9)` | 30 | FOUND | EXHAUSTED |
| `z(4,10)` | 28 | FOUND | EXHAUSTED |
| `z(5,10)` | 33 | FOUND | EXHAUSTED |
| `z(4,11)` | 30 | FOUND | EXHAUSTED |
| `z(5,11)` | 36 | FOUND | EXHAUSTED |
| `z(4,12)` | 32 | FOUND | EXHAUSTED |

7/7 agree. Note `--nocanon` is *itself* infeasible at `n=17` — even `3x17`
did not finish, since it must consider all `2^17` row masks with no symmetry
reduction. That is worth recording for two reasons: it shows R2 is not a
minor optimisation but the thing that makes `n=17` reachable at all, and it
explains why R2 can only be validated at smaller `n` and then relied on.

### 3.4 Published exact values reproduced

| cell | published | orderly | verdict |
|---|---|---|---|
| `z(6,6;3)` | 26 | **26** | match |
| `z(7,7;3)` | 33 | **33** | match |
| `z(8,8;3)` | 42 | **42** | match |
| `z(9,9;3)` | 49 | **49** | match |

Also reproduced, as internal consistency anchors: `z(3,3)=8`, `z(4,4)=13`,
`z(5,5)=20`, `z(10,10)=60`.

### 3.5 Hand-derived anchors reproduced

Independently of any search, the column-degree counting bound gives exact
values for small `k` at `n=17`, and the generator matches all of them:
`f(3)=36`, `f(4)=42`, `f(5)=52`, `f(6)=58`. (`f(3)`: each column lies in at
most 3 rows and at most 2 columns lie in all 3, so `e <= 2*17+2 = 36`.)

### 3.6 The reduction's degree-sequence counts (`test_reduction.py`)

`REDUCTION.md` observes that pinning the minimum row degree and distributing
the excess is an integer partition, so the admissible degree-sequence counts
must be partition numbers. Re-derived independently and asserted:

| object | sequences | expected |
|---|---|---|
| `e=134` on 16x17, `d_min=8`, degrees in `[8,14]` | 11 | `p(6) = 11` |
| `e=133` on 16x17, `d_min=8`, degrees in `[8,13]` | 7 | `p(5) = 7` |
| parent `Ext(15,17,126)`, degrees `>= 8` | 11 | `p(6) = 11` |
| parent `Ext(15,17,125)`, degrees `>= 8` | 7 | `p(5) = 7` |

All four match. **And a sharper cross-check falls out of it:** the distinct
largest parts over those 11 partitions are `{9,10,11,12,13,14}` — six values —
and level 1 of the generator's `Ext(15,17,126)` search enumerates exactly the
admissible choices of the (maximum) first row degree. Its **measured** width
is **6**. So the generator neither over- nor under-counts at the top of the
tree, verified against a closed-form combinatorial quantity rather than
against itself. `test_reduction.py` asserts this.

### 3.7 Counting bound vs computed value at n=17 — corroboration and R2 exposure

An upper bound on `f(k)` that uses **no search at all**: maximise
`sum_c e_c` over the 17 column degrees subject to
`sum_c C(e_c,3) <= 2*C(k,3)` and `e_c <= k` (exact DP, independent of the
generator).

| `k` | counting bound | computed `f(k)` | gap |
|---|---|---|---|
| 3 | 36 | 36 | **0** |
| 4 | 42 | 42 | **0** |
| 5 | 52 | 52 | **0** |
| 6 | 58 | 58 | **0** |
| 7 | 68 | 66 | 2 |
| 8 | 75 | 74 | 1 |
| 9 | 84 | 81 | 3 |
| 10 | 92 | 90 | 2 |

Two things follow, and the first is the more useful:

**`f(3)` through `f(6)` at `n=17` do not depend on R2 at all.** Their upper
bounds come from this counting DP and their lower bounds from explicit
witnesses certified by `verify/checker.py`. So four of the `n=17` values are
established by two arguments that share no code with the canonicity rule.

**The R2 exposure is small and quantified.** For `k = 7..10` the search
improves on the search-free bound by only 1–3 edges. In particular `f(9) = 81`
sits 3 below the counting bound, and of those 3 steps two are covered by (R6)
from `f(8)` (which gives `f(9) <= 83`), leaving exactly **one** R2-dependent
refutation — see §6.3.

### 3.8 The `--extend` path unit-tested positively

The failure mode that matters for `REDUCTION.md` is `--extend` *missing* an
extension (a false "no"). So it needs a positive test on a rung where an
extension is known to exist. Smallest tight rung available: `z(5,6) = 22`,
`z(6,6) = 26`; at `e = 26` the minimum degree is `<= floor(26/6) = 4` and the
parent has `>= 22 = z(5,6)` edges, so the step is tight.

```
./orderly -n 6 -m 5 --enum 22 --emax 22 --dfloor 4 --extend 4
  -> solutions=3  ext_success=2   WITNESS_ROWS 6 62 61 51 43 23 15
```

Three parents in `Ext(5,6,22)` with degrees `>= 4`; two of them extend by a
degree-4 row. **And the resulting 26-edge witness is identical to the one the
direct 6-level search produced independently** (§3.2 / §3.4), which is a real
end-to-end check: the reduction route and the direct route land on the same
graph.

### 3.9 Every witness certified through `verify/checker.py`

No claimed graph in this log is certified by the search's own bookkeeping.
`validate.py` re-checks each one via `checker.verify`, which forces three
structurally different `K_{3,3}` tests to agree. Note the bit-order
convention: `orderly` prints masks with column 0 as the **most significant**
bit, while `checker.normalize_matrix` takes bit 0 as column 0, so masks are
bit-reversed before checking. The 6 literature witnesses in
`data/known_witnesses/` were also re-checked and all pass.

## 4. `f(k) = z(k,17;3)` established by this code

Computed bottom-up, each level using only levels below it, no external value
cited:

| `k` | `f(k) = z(k,17;3)` | how | search nodes | time |
|---|---|---|---|---|
| 1 | 17 | trivial | 0 | — |
| 2 | 34 | trivial (`K_{3,3}` needs 3 rows) | 0 | — |
| 3 | 36 | search + hand counting bound | 296 | <0.01 s |
| 4 | 42 | search + hand counting bound | 943 | 0.001 s |
| 5 | 52 | search + hand counting bound | 121 | 0.003 s |
| 6 | 58 | search + hand counting bound | 5 646 | 0.026 s |
| 7 | 66 | search | 21 437 | 0.49 s |
| 8 | 74 | search | 73 007 | 3.70 s |
| **9** | **81** | search (3 probes) | 10 271 716 | **421 s** |
| **10** | **90** | witness + Density Lemma from `f(9)` | 7 550 699 | **302 s** |
| **11** | **`<= 97`** (exact value open, see §13) | exhaustive refutations of `>= 99` (two routes) and `>= 98` | 32 034 663 + 29 622 896 + 32 035 246 | **3 256 s + 2 437 s + 7 802 s** |

`f(10) = 90` deserves comment because it is established *without any
exhaustive refutation at level 10*: the upper bound `f(10) <= 90` is free from
(R6) applied to my own `f(9) = 81`, and the matching lower bound is an
explicit 10-regular 90-edge graph found by the search and certified by
`verify/checker.py`. Both halves are mine; nothing published is cited.

The `f(9) = 81` computation in detail (this is the load-bearing one):

| probe | verdict | nodes | time |
|---|---|---|---|
| `9x17 >= 83` | UNSAT | 347 899 | 19.3 s |
| `9x17 >= 82` | UNSAT | 2 412 355 | 74.9 s |
| `9x17 >= 81` | **SAT** | 7 511 462 | 326.6 s |

The `f(9)=81` witness is **9-regular** (all nine rows of degree 9), 81 edges,
certified `K_{3,3}`-free by `verify/checker.py`. The `f(10)=90` witness is
likewise **9-regular**. Certified witnesses were also produced and checked at
`10x17` with 88 and 89 edges (degree sequences `9^8 8^2` and `9^9 8`).

## 5. Why this kills the ladder — the central negative finding

The coordinator's Density Lemma refinement is correct and I verified the
arithmetic. It also gives a *bottom-up ladder*
`f(j) <= max{e : e - floor(e/j) <= f(j-1)}`, which looked as though it would
let one cheap exhaustive computation at small `k` carry all the way up. I
worked out what that requires, and it is startlingly specific:

> the chain reaches `f(15) <= 126` **iff** `f(9) <= 78`.

Because then `78 -> 86 -> 94 -> 102 -> 110 -> 118 -> 126`, an exact
arithmetic progression `8k + 6` matching the published `f(13)=110`,
`f(14)=118`, `f(15)=126` on the nose, and then `f(16) <= 134` by hand. The
entire published upper bound would have followed from one 9-row computation.

**It fails. The measured value is `f(9) = 81`, not 78** (SAT at 81, UNSAT at
82 and 83, witness certified). The chain from 81 gives instead:

| | from `f(9)=78` (needed) | from `f(9)=81` (actual) | published |
|---|---|---|---|
| `f(10)` | `<= 86` | `<= 90` | — |
| `f(11)` | `<= 94` | `<= 99` | — |
| `f(12)` | `<= 102` | `<= 108` | — |
| `f(13)` | `<= 110` | `<= 117` | 110 |
| `f(14)` | `<= 118` | `<= 126` | 118 |
| `f(15)` | `<= 126` | `<= 135` | 126 |
| `f(16)` | `<= 134` | `<= 144` | 133 |

So the ladder overshoots by 11 at `k=16`.

> **Partly superseded.** The `f(9)=81` column above is the chain run with *no*
> refutation above `k=10`. `11x17 @ 99` has since been refuted (§11), so the
> live chain now reads `98, 106, 114, 122, 130, 138` and the overshoot at `k=16`
> is **4** against the hand-derived 134, not 11. §11.4 has the current table and
> §11.5 the inversion (what each further edge costs).

**And the chain is provably tight at the bottom, which localises the loss.**
I then *proved* `f(10) = 90`, exactly the chain's prediction — the upper bound
`<= 90` free from (R6) on my `f(9)=81`, the lower bound an explicit certified
10-regular graph. So the chain loses nothing at `k=10`. Since the published
`f(13) = 110` is 7 below the chain's 117, **all of the loss is concentrated in
`k = 11, 12, 13`.** Those three levels are exactly where genuine exhaustive
refutation is unavoidable, and by §6.1 they cost roughly 1e9, 2e10 and 4e11
nodes per refuted value. That is the precise, quantified location of the
obstruction: not "the search is too big" in general, but *three specific
levels* whose combined cost is ~5e11 nodes minimum, i.e. weeks of core time,
before the 15x17 enumeration even begins.

I also checked the obvious strengthenings, and they buy nothing:
- **multi-row deletion** (`e - floor(t*e/j) <= f(j-t)`): with `t=6, j=15`
  gives `f(15) <= 135`, identical to the one-step chain; with `t=7` from
  `f(8)=74` it gives 138, worse.
- **column-side counting** `sum_c C(e_c,3) <= 2*C(16,3) = 1120`: at `e=134`
  the balanced column sequence gives 910, not binding. Row side at `e=134`
  gives 1064 vs 1360, not binding.
- LP/ILP relaxations: confirmed too weak independently by the coordinator's
  survey (best published LP bound 141 for this cell).

**Consequence.** There is no cheap route up. `f(10) = 90` came free (the chain
is tight there), but each of `f(11)..f(15)` needs its own genuine exhaustive
refutation, and the published values are strictly stronger than anything the
counting arguments give — which retrospectively explains why the 2016 paper
needed serious computation and why it stopped where it did.

## 6. Measured feasibility — the numbers

### 6.1 Growth of the bottom-up ladder

Cost of the hardest refutation at each level (`n=17`):

| level | hardest UNSAT probe | nodes | time | ratio vs previous |
|---|---|---|---|---|
| 7 | — (whole level) | 21 437 | 0.49 s | — |
| 8 | — (whole level) | 73 007 | 3.70 s | 7.6x |
| 9 | `>= 82` | 2 412 355 | 74.9 s | 20x |

Throughput is 10k–900k nodes/s depending on how tight the constraints are
(tighter constraints mean more work rejected deep in the row-candidate
enumeration, hence *fewer* accepted nodes per second).

> **This section's extrapolation was wrong, and badly so. It is superseded by
> §12, which rebuilds it around the measured `k=11` datum.** For the record, the
> original text assumed a conservative 20x per level and predicted
> `~1e9 nodes / ~8 h` for one refutation at `k=11`. The refutation was then
> actually run: **3.2e7 nodes, 3256 s** — about **30x cheaper in nodes** and
> **9x cheaper in wall time** than predicted. The 20x-per-level model is not
> merely imprecise, it is the wrong shape: the tree does not keep branching,
> it peaks and then collapses (§12.1). The stale table is reproduced here
> struck through so the error is visible rather than quietly edited away:
>
> | `k` | ~~est. nodes (WRONG)~~ | ~~est. time (WRONG)~~ | actual |
> |---|---|---|---|
> | 10 | — | free, chain is tight (§5) | free |
> | 11 | ~~1e9~~ | ~~~8 h~~ | **3.2e7 nodes, 0.90 h** |
> | 12 | ~~2e10~~ | ~~~7 days~~ | see §12.2 |
> | 13 | ~~4e11~~ | ~~~5 months~~ | see §12.2 |
> | 14 | ~~8e12~~ | ~~~8 years~~ | see §12.2 |
> | 15 | ~~1.5e14~~ | ~~~160 years~~ | see §12.2 |
>
> The *conclusion* of this section — that a bottom-up re-derivation of
> `f(15) = 126` is out of reach here — survives the correction, but by a much
> smaller margin than "10 orders of magnitude", and the reasoning is different.
> See §12.3 for the corrected version.

### 6.2 The extremal-parent enumeration (the crux, per the coordinator)

The `e=134` case reduces to: enumerate 15x17 `K_{3,3}`-free graphs with
exactly 126 edges and all row degrees `>= 8`, then test a degree-8 extension
row. (Both facts derived: min degree `<= floor(134/16) = 8`; deleting a
min-degree row leaves `>= 126 = f(15)`, so the deleted degree is exactly 8
and every remaining degree is `>= 8`.)

I measured the **exact** width of this search tree level by level, using
`--countlevel L` which cuts the search at level `L` so that `level_nodes[L]`
is the exact number of surviving `L`-row configurations. Run with the degree
floor 8, `emax = target = 126`, and the published `f(13)`, `f(14)` supplied as
declared assumptions (i.e. with *stronger* pruning than a self-contained run
could use):

| `L` | exact surviving `L`-row configurations | ratio |
|---|---|---|
| 1 | 6 | — |
| 2 | 67 | 11.2x |
| 3 | 1 395 | 20.8x |
| 4 | 43 447 | 31.1x |
| 5 | 1 966 099 | 45.3x |
| 6 | 81 381 805 | 41.4x |

(`L=1` being exactly 6 is a useful independent check on the code: with 15 rows
of degree `>= 8` summing to 126 the max degree is `<= 126 - 14*8 = 14`, and
`d_0 >= 9` since `15*8 = 120 != 126`, so `d_0` in `{9..14}` — six values.)

Level 6 took 90 s at ~0.9M nodes/s. I started the exact `L=7` measurement but
**killed it deliberately** rather than let it run: the machine is shared with
another workstream's solvers and every process was getting only ~50% of a
core, so `L=7` (~3.3e9 nodes) would have taken ~2 h of contended time that was
better spent on the soundness checks in §6.3 and §6.6. So the `L >= 7` row
below is **extrapolation, not measurement** — flagged explicitly because the
`L <= 6` rows are exact and these are not.

Extrapolating at the observed ~40x:

| `L` | est. width | est. single-core time |
|---|---|---|
| 7 | 3.3e9 | ~1 h |
| 8 | 1.3e11 | ~40 h |
| 9 | 5.3e12 | ~68 days |
| 10 | 2.1e14 | ~7 years |

The tree *must* eventually collapse, because the edge count is pinned to
`E_k` in `[8k, 8k+6]` at every level and the slack `f(k) - (8k+6)` runs
`3, 2, ?, ?, 0, 0, 0` for `k = 9,10,...,15` — at `k >= 13` the prefix must be
*exactly* extremal. So the width peaks somewhere around `k = 10..12` and then
falls off a cliff. But the peak is the cost, and even the optimistic reading
(peak at `L=8`) is ~40 core-hours; peak at `L=10` is ~7 core-years.

**Verdict: the extremal-parent enumeration for `e=134` is not feasible on this
machine.** Optimistically 40 core-hours if the width peaks at level 8;
realistically 10^12–10^14 nodes, i.e. months to years of core time. Sharding
across the 3 cores available changes this by 3x, which does not matter at
this scale. The `e=133` case is strictly larger (parents with 125 *or* 126
edges, and a weaker degree floor of 7), consistent with the observation that
the 2016 paper could refute 134 but not settle 133.

### 6.3 An R2-free check of the one load-bearing refutation

Worth isolating how much actually rests on the risky rule. For `f(9) = 81`:
- the **lower** bound (81 is achievable) is an explicit graph certified by
  `verify/checker.py` — R2 cannot affect it at all;
- the `>= 83` refutation is **redundant**: (R6) on my `f(8) = 74` already gives
  `f(9) <= 83` by arithmetic;
- so the entire R2 exposure of `f(9) = 81` is **one** exhaustive refutation:
  `9x17 >= 82`.

For comparison, the pure counting bound gives only `f(9) <= 84`, so the search
closed a gap of 3 (84 -> 81), of which 1 step is the R2-dependent one.

To attack that single exposure directly, note the refutation can be narrowed
soundly using my own `f(8) = 74`: in an 82-edge 9x17 graph every row degree is
`>= 82 - f(8) = 8` (delete any row; the remaining 8 rows carry at most 74). So
`--dfloor 8` is sound here, which shrinks the search enough to attempt it with
`--nocanon`, i.e. **with R2 switched off entirely**. Result in §9.

### 6.4 The "narrow ladder" reformulation is the same search, not a smaller one

The coordinator proposed restructuring as a rung-by-rung climb
`Ext(13,110) -> Ext(14,118) -> Ext(15,126) -> test e=134`, where `Ext(k,e)` is
the set of `e`-edge `k x 17` graphs up to isomorphism, on the grounds that
each rung needs only degree-8 extension rows. I verified the tightness
arithmetic independently (all three steps are tight, and I found the general
rule: the parent is forced extremal and the deleted degree is exactly
`e - z(k-1,17)` whenever the density lower bound meets `z(k-1,17)`).

**But the reformulation does not reduce the work, because it is the same tree.**
My generator orders rows by *descending degree*, so the last row is always a
minimum-degree row — which is precisely the row the density lemma deletes.
Concretely, in the 15x17 run with `dfloor = 8` and `target = emax = 126`:

- the last row's degree is forced to 8 (if the minimum were 9 the total would
  be `>= 135 > 126`), so `E_14 = 118` — the 14-row prefix *is* forced
  extremal, by (R4)+(R7), with no ladder framing needed;
- the same argument then forces `E_13 = 110`, `E_12 = 102`, and in general
  `E_k = 8k + 6` once `k` passes the last row of degree `> 8`.

So "enumerate `Ext(13,110)` and extend twice" and "run the 15-level DFS with
`dfloor=8, emax=126`" traverse the same configurations. The measured widths in
§6.2 therefore already *are* the ladder's cost.

The reason the ladder feels narrow but is not: `|Ext(k,e)|` — the *answer*
size at each rung — may well be small, but reaching it requires passing
through the intermediate levels, and those are the cost. My measurements show
the intermediate width still growing ~40x per row at level 6 (8.1e7
configurations). The tree must eventually collapse (the slack
`f(k) - (8k+6)` runs `3, 4, ?, ?, 0, 0, 0` for `k = 9..15`, so from `k>=13`
the prefix must be exactly extremal) but the peak sits at `k ~ 10..12`, which
is exactly where §5 says the unavoidable refutations also live.

**A reachable tight rung, as an end-to-end test of the machinery.** Using my
own `f(9) = 81`, the rung `10x17, e=89` is tight (`89 - floor(89/10) = 81`),
and so is `e=90` (`90 - 9 = 81`). These are self-contained instances of
exactly the ladder structure, with no published value involved. Both turn out
to be **satisfiable** — I found and certified 89- and 90-edge 10x17 graphs —
so they populate the rung rather than refute it, which is itself the correct
outcome given `f(10) = 90`. The first refutable rung above them, `e = 91`,
needs no search at all: (R6) on `f(9)=81` gives `f(10) <= 90` outright. So the
ladder's first genuinely *expensive* rung is at `k = 11`, matching §5.

### 6.5 Retargeting onto `REDUCTION.md`: what I can and cannot deliver

`REDUCTION.md` reduces everything to `Ext(15,17,126)` and `Ext(15,17,125)`.
I verified its arithmetic and its degree-sequence counts (§3.6 — all four
match the partition numbers, and the generator's level-1 width matches). The
reduction is correct. Two things block executing it here, both measured
rather than guessed.

**(a) The reduction is conditional on a number we cannot derive.** Every step
needs `z(15,17) <= 126`. My own chain, from my own proved `f(9)=81` and
`f(10)=90`, gives only `f(15) <= 135`. Closing that requires exhaustive
refutations at `k = 11, 12, 13` (§5), ~5e11 nodes minimum. Until then the
reduction can only be run with `z(15,17) <= 126` as a *declared assumption*,
which reintroduces exactly the uncertified 2016 dependency the project
refuses. (`REDUCTION.md` says this itself; I am confirming the gap is real and
sizing it.)

**(b) Enumerating `Ext(15,17,126)` is the wide search, not a narrow one.**
The proposed climb `Ext(13,110) -> Ext(14,118) -> Ext(15,126)` is cheap *given
its base*: each rung is `|Ext| * C(17,8) = |Ext| * 24310` one-pass tests, and
I agree those should not be over-engineered. But obtaining the base
`Ext(13,110)` self-containedly is a 13-level search over exactly the
configurations I measured, because (as §6.4 shows) my degree-ordered DFS with
`dfloor=8, emax=126` already forces `E_k` into `[8k, 8k+6]` at every level.

**The climb cannot be started from my values, and the slack numbers say why.**
Writing `slack(k) = f(k) - (8k+6)` — how far the required prefix edge count
sits below the maximum possible — the prefix is forced extremal only when
`slack(k) = 0`:

| `k` | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
|---|---|---|---|---|---|---|---|---|
| `8k+6` (required `E_k`) | 70 | 78 | 86 | 94 | 102 | 110 | 118 | 126 |
| `f(k)` | 74 | **81** | **90** | ? | ? | 110* | 118* | 126* |
| `slack(k)` | 4 | **3** | **4** | ? | ? | 0* | 0* | 0* |

(*published; bold = proved here.) The slack **grows** from 3 at `k=9` to 4 at
`k=10`. So in exactly the range where I have my own values, the prefix
constraint is getting *weaker*, and there is no extremality to exploit — the
9- and 10-row prefixes of a hypothetical 134-edge graph are nowhere near
extremal. The collapse to `slack = 0` therefore all happens in `k = 11, 12,
13`, which is both where the unavoidable refutations live and where the tree
peaks. This is the same obstruction seen from two directions.

**Measured cost of the peak.** Exact widths (§6.2) reach 8.1e7 at `L=6` with
ratios `11, 21, 31, 45, 41`. Even assuming the ratio decays steadily from ~40
toward ~10 as the constraints bite, the peak at `k = 11..12` lands around
**1e13 to 1e15 nodes**. At the measured 0.9M nodes/s that is `1e7`–`1e9`
core-seconds, i.e. **months to decades on one core**, and 3 cores does not
change the conclusion. I would rather report this honestly than run something
that silently never finishes.

**What I would do with more compute, in priority order:** (1) the `k=11`
refutation, since it is the cheapest thing that is genuinely needed and
localises the obstruction further; (2) the exact `L=7` width, to replace the
extrapolation with a measurement; (3) only then the `Ext` enumerations.

### 6.6 A fully self-contained tight rung, run two independent ways

The one thing I *can* do at reachable scale is execute `REDUCTION.md`'s
technique end-to-end on a rung built entirely from my own results, and check
it against a direct search. This validates the reduction logic itself (not
just the generator).

**The rung.** From my proved `f(10) = 90`: for an 11x17 graph with `e = 99`,
the minimum row degree is `<= floor(99/11) = 9`, and deleting it leaves
`>= 99 - 9 = 90 = f(10)` edges on 10x17. Since `f(10) = 90` is also the
maximum, the step is **tight**: the parent is exactly extremal (90 edges), the
deleted degree is exactly 9, and every parent degree is `>= 9`. With 10 rows
and 90 edges that forces **all degrees to be exactly 9** — a single degree
sequence, the narrowest possible rung. So:

> every 99-edge 11x17 graph = a **9-regular** 10x17 `K_{3,3}`-free graph
> plus one row of degree exactly 9.

Note the neighbouring value needs no search at all: at `e = 100` the parent
would need `>= 91 > 90` edges, so `f(11) <= 99` follows from `f(10) = 90` by
arithmetic alone.

**Two routes, run separately:**
1. *Reduction route:* `--enum 90 --emax 90 --dfloor 9 --extend 9` — enumerate
   the 9-regular parents and try every degree-9 extension row. The extension
   test deliberately enumerates **all** `C(17,9)` subsets with no canonicity
   restriction, which is the sound over-approximation.
2. *Direct route:* `--decide 99 -m 11` — an ordinary 11-level search with no
   degree floor, no edge cap, and no reduction reasoning.

The two share the canonicity rules but nothing else: different search depth,
different constraints, different code path for the final row. Agreement is a
real check on the reduction; disagreement would mean the reduction reasoning
or the `--extend` path is wrong, and would be reported as a blocking bug.
Results in §10.

### 6.7 Memory — not the binding constraint

Given the machine's memory pressure I designed for streaming from the start
and instrumented `ru_maxrss` on every run. **Peak RSS never exceeded 4.0 MiB**
across every run in this log, including the 81-million-node level-6 sweep.
Only the current search path is in RAM (a few KB); the `h` knapsack DP table
is 2.4 MB; enumerated graphs are streamed to disk via `--dump`, and the
`--extend` mode tests each parent inline so the parent set is never
materialised at all. No `ulimit` guard proved necessary. **Time, not memory,
is what makes this infeasible** — worth stating clearly, since the
coordinator reasonably expected the opposite.

## 7. Things tried that did not work

- **Bitmask triple state to speed up the hot loop.** Replaced the
  `O(d^2)`-per-column byte-counter updates with `O(d)` word-ops per column
  (per-pair `one`/`two` masks plus an incremental `forb` mask). Verified
  correct by identical node counts against the old implementation. **Gave
  essentially no speedup** (87.9 s -> 87.9 s on `9x17 >= 82`). The bottleneck
  is the *number of candidate rows enumerated*, not the cost of testing one.
  Kept anyway since it is cleaner and no slower.
- **Exact `h(j,d)` bounds vs cheap closed-form bounds.** Computing `h(j,d)`
  exactly for every `d` (rather than the closed-form `hub`) produced
  **identical node counts** on `9x17 >= 82` while adding 13 s of sub-search
  overhead. The expensive exact sub-table buys nothing here; `--hmode ub` is
  the better default for large runs.
- **Transposing to fewer columns.** Since `z(k,17;3) = z(17,k;3)`, computing
  `f(9)` as a 17-row x 9-column problem gives only 512 row masks instead of
  131 072. Measured: the `n=9` ladder reaches `z(14,9)=70` in 75 s but grows
  ~25x per level, so `z(17,9) = f(9)` would cost ~1e6 s — **worse** than the
  ~430 s the 17-column orientation actually took. Deeper-and-narrower loses
  to shallower-and-wider here. Recorded so nobody retries it.
- **Degree-floor/`emax` complement prune (R7).** Added expecting it to force
  the degree sequence and collapse the parent enumeration. Measured effect on
  the 15x17 run: 400 001 nodes in 20.1 s vs 24.8 s before — a ~20% time win,
  no change in tree shape. Kept; not the lever I hoped for.
- **Density-ladder shortcut as the whole strategy.** §5. Failed on the value
  of `f(9)`.

## 8. What is and is not conditional on published values

This matters enough to state separately, because the whole point of the
bottom-up plan is self-containment.

**Nothing claimed as PROVED here uses a published value.** `f(1..10)`,
including `f(9) = 81` and `f(10) = 90`, are derived from this code plus (R6)
applied to my own lower levels. The `--assume 9:81` flag that appears in the
`f(10)` command lines supplies *my own proved* `f(9) = 81`, not a citation.

**Published values were used in exactly one place: the §6.2 feasibility
measurement**, where I supplied `f(13) <= 110` and `f(14) <= 118` as declared
assumptions in order to measure the tree under the *strongest possible*
pruning — i.e. to give the enumeration its best case. Every such run prints a
loud `ASSUMED ... [DECLARED ASSUMPTION, not proved here]` line. No result is
claimed from those runs beyond node counts and timings.

**The base of the coordinator's ladder is not available to us.** Reaching
`Ext(13,110)` requires `f(13) <= 110`, and my own chain gives only
`f(13) <= 117`. Worse, the survey notes `z(13,17)=110` is itself a *2016
exhaustive-computation upper bound that has never been confirmed exact* — so
basing a self-contained proof on it would reintroduce precisely the
uncertified dependency this project refuses. Closing that gap means the
`k = 11, 12, 13` refutations of §5, at ~5e11 nodes minimum.

## 9. Results of the three validation runs

Three runs were launched near the end of the previous session. All three have
now been resolved; two concluded and one was killed. Superseded statuses are
struck through rather than deleted, so the record shows what was believed when.

| run | what it decides | status |
|---|---|---|
| `rung11_ext.out` — `--enum 90 --emax 90 --dfloor 9 --extend 9` on 10x17 | reduction route to `f(11) <= 98` or `= 99` (§6.6) | **CONCLUDED: EXHAUSTED, 24 parents, 0 extensions** → `f(11) <= 98`. §11.1 |
| `chain_m11_T99.out` — `--decide 99` on 11x17 | direct route to the same question | **CONCLUDED: EXHAUSTED, 32 034 663 nodes** → `f(11) <= 98`. §11.1, re-run and reproduced in §11.2 |
| `nocanon_9x17_82.out` — `--decide 82 --dfloor 8 --nocanon` | R2-free confirmation of the one load-bearing refutation (§6.3) | **KILLED, no result** — combinatorially infeasible, see §11.6. Nothing is inferred from it. |

The machine was shared with another workstream's solvers throughout (four
`kissat` processes on 8 cores), so these are hours-scale runs; the measured
single-process throughput was nonetheless close to uncontended (§11.2).

## 10. Not done / open (as of the previous session — see §13 for current)

- ~~`f(11)` and `f(12)`: SAT probes at the chain's predictions~~ **RESOLVED for
  `k=11`: `11x17 @ 99` is UNSAT, so the chain is *not* tight at `k=11` and
  `f(11) <= 98`.** See §11. `k=12` is addressed in §11.7/§12.
- The `Ext(9,81)` + degree-8 extension run (the reachable tight rung) was
  still running at write-up time; it should find an extension, matching the
  direct `10x17 >= 89` SAT result, as an end-to-end check of `--extend`.
- An unexploited pruning rule I derived but did not implement, recorded
  because it is the most promising next lever: from
  `sum_{r contains {a,b}} (d_r - 2) <= 2(n-2)`, **any column pair lies in at
  most 5 rows** once every degree is `>= 8` (since `6t <= 30`). This is
  logically implied by the triple constraint but is invisible to the raw
  counters until the triples actually saturate, so as a *look-ahead* on
  partial configurations it is genuinely new pruning power. Whether it moves
  the 40x branching ratio enough to matter is untested — and given §6.2 it
  would need to buy ~8 orders of magnitude, which it will not.
- No claim whatsoever is made here about `z(16,17;3)`. The 133 question is
  untouched by this workstream.

## 11. `f(11) <= 98` — the new result, and its verification

The previous session ended by reporting `11x17 @ 99` exhausted, and then died
before recording it. Because the claim arrived in a dying process's final
message it was treated here as **unverified until re-checked**, and this
section is that re-check. **Verdict: CONFIRMED**, by three separate pieces of
evidence.

### 11.1 The claim and what it rests on

> **`z(11,17;3) <= 98`.** There is no `11 x 17` `K_{3,3}`-free bipartite graph
> with 99 or more edges.

Note the `>=` in the statement: `--decide T` accepts a completed configuration
iff `E >= T` (`orderly.c`, `place_level`, `if (X->E < X->target) return 0`), so
one EXHAUSTED run at `T = 99` refutes 99 **and every larger value at once** —
it is not a single-value probe. Combined with `f(11) >= f(10) = 90` this pins
`f(11)` into `[90, 98]`.

The previous bound was `f(11) <= 99`, which follows from `f(10) = 90` by
arithmetic alone (at `e = 100` the density lemma forces a parent with
`>= 91 > 90` edges). So this run buys exactly one edge at `k=11` — and, because
the density chain is 1:1 from here up, exactly six edges at `k=16` (§11.4).

### 11.2 Route 1 (direct), verified by re-running it

`runs/`-level record, `chain_m11_T99.out`:

```
level nodes: 0:1 1:9 2:153 3:1836 4:33915 5:1020778 6:14347690 7:16095541
             8:534574 9:142 10:24
ASSUMED f(9) <= 81   [DECLARED ASSUMPTION, not proved here]
PARAMS n=17 m=11 triple_cap=1360
RESULT mode=decide m=11 n=17 target=99 dcap=17 dfloor=0 emax=-1 forced0=-1
       split=0:0:1 status=EXHAUSTED nodes=32034663 solutions=0 ext_success=0
       secs=3255.769 rss_mib=3.7
```

Every parameter checks out, and each of the four ways this could have been a
bogus result was checked explicitly:

1. **Was it the right cell and target?** `m=11 n=17 target=99`. Yes.
2. **Was the search actually complete?** `status=EXHAUSTED`. `orderly.c` sets
   `sat = 0` (printed as EXHAUSTED) only on normal return; a node-limit or any
   other early exit sets `aborted` and prints ABORTED. `emax=-1`,
   `dfloor=0`, `forced0=-1`, `split=0:0:1` — **no** degree floor, **no** edge
   cap, **no** forced row-0 degree, **no** sharding. So nothing narrowed the
   search space beyond the sound rules R0–R6.
3. **Was a published number smuggled in via `--assume`?** The only assumption
   is `f(9) <= 81`, which is *this workstream's own proved value* (§4: SAT at
   81, EXHAUSTED at 82 and 83, witness certified through `verify/checker.py`).
   No published value appears. Mechanically, `hassume[]` is read in exactly one
   place — `hub(j, d)` with `d == N` — where it can only *lower* an upper bound
   on what the remaining rows contribute, so it is sound given the assumption,
   and the assumption is ours. `f(10) <= 90` was not even supplied; `hub`
   re-derives it from `hassume[9]=81` via the density lemma.
4. **Was the binary the one the current source builds?** `orderly` on disk was
   rebuilt at 19:38, *after* the 19:04 run start, which on its own leaves room
   for the running code to differ from the committed source. Checked two ways:
   - rebuilding `orderly.c` (unmodified relative to `HEAD`) to `orderly2`
     yields the **same Mach-O UUID** `80757067-E687-3736-8B44-99DCF263B119`
     as the `orderly` on disk (the 414 differing bytes are all past offset
     51224, i.e. code-signature/symbol-table padding, not code);
   - `orderly2` **reproduces the logged node counts exactly** on the two
     archived `k=9` refutations: `--decide 83` → `347899` nodes (log: 347 899),
     `--decide 82` → `2412355` nodes (log: 2 412 355). Node counts are a far
     more sensitive fingerprint than verdicts.

   And then, as corroboration rather than as the proof, **the whole `k=11` run
   was repeated with the freshly built `orderly2` and reproduced the archived
   run's node count and all eleven of its per-level widths exactly** — see the
   table in §11.3.

Timings, for the throughput model in §12: 32 034 663 nodes in 3255.8 s =
**9 840 nodes/s**. The `k=9` re-runs gave 19.7 s and 77.3 s against the logged
19.3 s and 74.9 s, i.e. this machine is running within ~3 % of the earlier
figures despite four `kissat` processes sharing the 8 cores. So the low
`k=11` node rate is *not* contention — it is the constraints biting, exactly as
§7 predicted (the cost is per *candidate row considered*, not per accepted
node, and tight targets reject deep in the candidate enumeration).

### 11.3 Route 2 (the reduction), which is genuinely independent

The reduction route of §6.6 also concluded, and it is the strongest part of the
verification because it is a *different search*, not a repeat.

Its logic, using only our own `f(10) = 90`: in a 99-edge `11x17` graph the
minimum row degree is `<= floor(99/11) = 9`; deleting a minimum-degree row of
degree `d` leaves `99 - d <= f(10) = 90`, so `d >= 9`, hence `d = 9` exactly and
the parent has exactly `90 = f(10)` edges — extremal. Ten rows, 90 edges, all
degrees `>= 9` forces **9-regular**. So:

> a 99-edge `11x17` graph exists **iff** some 9-regular `10x17` `K_{3,3}`-free
> graph admits an extra row of degree exactly 9.

```
./orderly -n 17 -m 10 --enum 90 --emax 90 --dfloor 9 --extend 9 --hcap 8 --assume 9:81
  level nodes: 0:1 1:1 2:9 3:242 4:13265 5:667671 6:12638706 7:15769672
               8:533163 9:142 10:24
  RESULT mode=enum m=10 n=17 target=90 ... dfloor=9 emax=90 status=EXHAUSTED
         nodes=29622896 solutions=24 ext_success=0 secs=2437.368 rss_mib=3.7
```

`solutions=24`, `ext_success=0`: **24** 9-regular `10x17` graphs were
enumerated and **not one** of them admits a degree-9 extension row. Since the
`--extend` path enumerates *all* `C(17,9) = 24310` candidate rows with no
canonicity restriction whatsoever (`ext_dfs`, deliberately), and since
`--extend` has a positive unit test on a known-extendable tight rung (§3.8),
`ext_success=0` is a real refutation. Hence `f(11) <= 98`, independently.

**And the two routes agree on more than the verdict.** Compare the tails of the
two level profiles:

| level | direct (`-m 11 --decide 99`) | reduction (`-m 10 --enum 90 --dfloor 9`) |
|---|---|---|
| 8 | 534 574 | 533 163 |
| 9 | **142** | **142** |
| 10 | **24** | **24** |

The 24 objects at the bottom are the *same 24 graphs*: in the direct search a
level-10 node is a 10-row prefix that survived toward `E >= 99`, which by the
argument above must be 9-regular with 90 edges; in the reduction search they are
the 24 enumerated parents. Two differently-constrained searches — one with
`dfloor=9, emax=90` over 10 levels, one with no floor and no cap over 11 levels
— arrive at the identical count at levels 9 and 10. That is a much sharper
agreement than "both said no", and it is exactly the check §6.6 was designed to
produce.

Third piece of evidence — the bit-identical repeat of route 1, run with a
freshly built binary — **concluded and reproduced the archived run exactly**:

| | `chain_m11_T99.out` (previous session, `orderly`) | `verify_m11_T99.out` (this session, `orderly2`) |
|---|---|---|
| verdict | EXHAUSTED | **EXHAUSTED** |
| total nodes | 32 034 663 | **32 034 663** |
| level nodes 0..10 | `1 9 153 1836 33915 1020778 14347690 16095541 534574 142 24` | **identical, all eleven** |
| wall time | 3 255.8 s | 7 760.2 s |
| peak RSS | 3.7 MiB | 3.7 MiB |

Not just the same answer and the same total — **the same width at every one of
the eleven levels.** That is the strongest form this check can take: it rules
out both a different search tree and a compensating pair of errors.

The 2.4x time difference with an identical instruction count is worth recording
because it was predicted before the run finished and is the explanation for a
scare: this repeat passed the original's 54-minute CPU budget and kept going,
which looked briefly like evidence of divergence. It was not. Seven heavy
processes (three `orderly`, four `kissat`) now share 8 cores with swap near-full,
so CPU seconds inflate with memory-stall cycles while the work does not. **Node
counts, not seconds, are the invariant to check across runs** — the seconds in
this log are not comparable between sessions, and §12.2's throughput figures
should be read with that caveat.

> **A process note, recorded because it briefly escaped into a commit message.**
> An earlier draft of §11.2 asserted this repeat had "reproduced bit-for-bit"
> while it was still running, and commit `2ec6642`'s message repeats that claim.
> The claim has *since* become true — the table above is the evidence — but it
> was **written before the evidence existed**, which is exactly the failure this
> log exists to prevent. Two safeguards were added in response: §13.1b now
> records every in-flight run with what may and may not be inferred from it, and
> the sentence in §11.2 was rewritten to say the repeat is corroboration rather
> than proof. `f(11) <= 98` never depended on it: routes 1 and 2 are two
> concluded independent exhaustive searches, and route 1's binary was
> independently shown to reproduce the archived `k=9` node counts to the digit.

### 11.4 What `f(11) <= 98` buys: the revised self-contained chain

The density chain is `f(j) <= max{e : e - floor(e/j) <= f(j-1)}` (rule R6,
upper bounds only, hence sound). Re-running it from `f(11) <= 98` — every input
proved by this code, nothing published anywhere in the derivation:

| `k` | chain from `f(9)=81` (previous) | from `f(11)<=98` (§11) | from `f(11)<=97` (**now**, §13.0) | hand-derived (§5) | published |
|---|---|---|---|---|---|
| 10 | `<= 90` | `= 90` (proved) | `= 90` (proved) | — | — |
| 11 | `<= 99` | `<= 98` (proved) | **`<= 97` (proved)** | — | — |
| 12 | `<= 108` | `<= 106` | **`<= 105`** | — | — |
| 13 | `<= 117` | `<= 114` | **`<= 113`** | — | 110 |
| 14 | `<= 126` | `<= 122` | **`<= 121`** | — | 118 |
| 15 | `<= 135` | `<= 130` | **`<= 129`** | — | 126 |
| 16 | `<= 144` | `<= 138` | **`<= 137`** | 134 | 133 |

So the self-contained bound on the target cell improves from
**`z(16,17;3) <= 144` to `z(16,17;3) <= 137`** — seven edges, from two
refutations totalling under three hours of CPU. It is still 3 short of the
hand-derived 134 and 4 short of the published 133, but unlike those it is ours
end to end: every input is a value this code proved, and no published number
appears anywhere in the derivation.

The 1:1 propagation is worth stating because it makes the accounting trivial:
on this chain `floor(e/j) = 8` for every relevant `(e,j)`, so the chain step is
just `f(j) <= f(j-1) + 8`, and **one edge saved at `k=11` is one edge saved at
`k=16`.**

All of the arithmetic in this section and the next is now asserted by
`test_reduction.py` rather than done by hand — every entry of both tables, the
inverse table in §11.5, and the 1:1 sensitivity. It is the kind of thing that is
easy to get wrong by one and that the entire headline claim rests on.

### 11.4a A divisor cliff, and why the `k=9` chain was so much worse than it looked

Writing that assertion turned up something the previous sessions missed, and it
retro-explains §5. **The 1:1 propagation is not a general property of the
chain.** Asserting it globally fails, and the failure is instructive:

| chain started at | `f(16)` bound | one further edge there is worth |
|---|---|---|
| `f(9) = 81` | 144 | **8 edges at `k=16`** |
| `f(11) <= 98` | 138 | 1 edge |
| `f(12) <= 102` | 134 | 1 edge |

The reason is a cliff in `floor(e/j)`. From `f(9) = 81` the chain's `k=10` value
is 90 and `floor(90/10) = 9`, so the step is `+9` and the whole chain runs on
divisor 9: `81, 90, 99, 108, 117, 126, 135, 144`. From `f(9) = 80` it would run
`80, 88, 96, 104, 112, 120, 128, 136` — divisor **8** the whole way, and `f(16)`
lands at 136, not 143. Continuing: `f(9) = 79` gives 135 and `f(9) = 78` gives
134, both 1:1.

So `f(9) = 81` sits *exactly one edge* on the expensive side of a cliff that is
worth eight edges at the target. That is the sharpest possible statement of §5's
finding, and it is worse news than §5 realised: the problem was never that
`f(9) = 81` misses 78 by three, it is that it misses **80** by one, and that one
edge alone accounts for 8 of the 10-edge overshoot.

**And the door is shut, not merely expensive.** `f(9) = 81` is proved *exactly*
— UNSAT at 82 and 83, and an explicit certified 9-regular 81-edge witness (§4).
There is no compute that improves it. This is the cleanest example in the whole
log of a place where the obstruction is mathematical rather than computational,
and it is why the remaining work has to happen at `k = 11, 12` where the chain
is merely 1:1 and every edge must be bought individually.

### 11.5 The chain's ceiling — what would still be needed for 134 and 133

Because the step is `+8` throughout, the requirement inverts exactly:

| goal | needed | status |
|---|---|---|
| `f(16) <= 138` | `f(11) <= 98` | **done** (§11) |
| `f(16) <= 137` | `f(11) <= 97` **or** `f(12) <= 105` | **done** (§13.0) |
| `f(16) <= 136` | `f(11) <= 96` **or** `f(12) <= 104` | run #13 (`--decide 97`) attempts it |
| `f(16) <= 134` | `f(11) <= 94` **or** `f(12) <= 102` **or** `f(13) <= 110` | one run at `-m 11 --decide 95`, if `f(11) <= 94` is true |
| `f(16) <= 133` | `f(11) <= 93` **or** `f(12) <= 101` **or** `f(13) <= 109` | §12.3; needs `f(11) <= 93` |

**The route to 134 is now a single command, if the value permits it.** Because
`--decide T` refutes the whole half-line `>= T`, `f(11) <= 94` follows from one
EXHAUSTED run of `-m 11 --decide 95` — not from four separate refutations. And
`8k+6` at `k=11` is exactly 94, so if the published progression reflects the
truth at `k=11`, that run is UNSAT and **`f(16) <= 134` is reachable
self-containedly at `k=11`**, four levels below where §5 and §6 assumed the work
had to happen. Conversely `f(16) <= 133` needs `f(11) <= 93`, i.e. `f(11) < 94`,
which the same progression says is false.

And here is the part that no amount of compute fixes. The chain can only be
pushed down to the **true** value at whichever level you attack; you cannot
refute a value that is actually achievable. So:

- if `f(11) = 98` (i.e. `11x17 @ 98` is SAT), the `k=11` column of that table is
  closed forever at 138, and everything must come from `k >= 12`;
- if additionally `f(12) = 102` — which is what the published
  `f(13)=110, f(14)=118, f(15)=126` progression `8k+6` extrapolates down to —
  then `f(12) <= 102` is exactly attainable and **`f(16) <= 134` is reachable by
  a single `--decide 103` refutation at `k=12`**, while `f(16) <= 133` would
  need `f(12) <= 101`, which would be **false** and therefore unreachable by
  this route at all.

That is a precise, falsifiable prediction, and it explains the shape of the
published literature from our own side: 134 is the chain's floor, 133 is not,
which is exactly the boundary the 2016 computation stopped at. Reaching 133
requires the extremal-parent enumeration of §6.2, which is separately measured
infeasible here — the density chain is *structurally* incapable of it.

(`8k+6` at `k=11` is 94 and at `k=10` is 86, but we *proved* `f(10) = 90`. So
the arithmetic progression that fits `k=13..15` does **not** extend down to
`k=10`, and there is no reason to assume it holds at `k=11` or `k=12` either.
This is why §13.2's run #4 measures rather than assumes.)

### 11.6 The `--nocanon` R2-free check at `n=17`: killed, and why that was right

`nocanon_9x17_82.out` (`-m 9 --decide 82 --dfloor 8 --nocanon`) was still
running with ~7 min of CPU accumulated. **It was killed, and no result is
claimed from it.** The reason is arithmetic, not impatience: with `--nocanon`
every column is its own partition cell, so level 0 enumerates *every* mask of
degree `>= 8` — that is `sum_{d=8}^{17} C(17,d) = 2^17 - 41 226 = 89 846` row-0
candidates, against the *one mask per admissible degree* (so `<= 10`) that R2
leaves. Level 1 multiplies by a comparable factor, so the level-2 width alone is
`~10^9`, against a 9-level search. This is the same
observation §3.3 already recorded ("`--nocanon` is *itself* infeasible at
`n=17` — even `3x17` did not finish"); adding `--dfloor 8` narrows it by a
constant, not by the eight orders of magnitude needed. R2's validation
therefore stands where §3.3 left it: 7 cells at `n <= 12` with R2 off, all
agreeing, plus 32 cells against the independent `brute`, plus the four `n=17`
values (§3.7) that do not use R2 at all. The core freed by killing it went to
the `k=12` work below.

## 12. The feasibility model, rebuilt around the measured `k=11` datum

§6.1's model was wrong by ~30x in nodes and ~9x in wall time, and — more
importantly — wrong in *shape*. This section replaces it. Everything marked
**measured** is a number this machine produced; everything marked
**projected** is arithmetic on those numbers, and says which numbers.

### 12.1 Why the old model had the wrong shape

§6.1 assumed the tree keeps branching at a constant ~20x per level, so cost
grows like `20^k`. The `k=11` level profile shows that is not what happens.
**Measured**, the two `k=11`-equivalent runs:

| level | `-m 11 --decide 99` | `-m 10 --enum 90 --emax 90 --dfloor 9` |
|---|---|---|
| 0 | 1 | 1 |
| 1 | 9 | 1 |
| 2 | 153 | 9 |
| 3 | 1 836 | 242 |
| 4 | 33 915 | 13 265 |
| 5 | 1 020 778 | 667 671 |
| 6 | 14 347 690 | 12 638 706 |
| 7 | **16 095 541** ← peak | **15 769 672** ← peak |
| 8 | 534 574 | 533 163 |
| 9 | 142 | 142 |
| 10 | 24 | 24 |
| **total** | **32 034 663** | **29 622 896** |

Per-level ratios for the direct run: `9, 17, 12, 18.5, 30.1, 14.1, 1.12,
0.033, 0.00027, 0.17`. The tree is **unimodal**: it branches hard up to level
5–6, flattens at level 7, then falls off a cliff (a factor of 30 at 7→8, then
3 800 at 8→9). The reason is the one §6.4 identified: with the target pinned,
each additional row forces the running edge total into an ever-narrower window,
and past the peak the constraint is tighter than the branching.

Two consequences that the `20^k` model could not express:

1. **Total cost ≈ 2x the peak level width.** Measured: `32.03M / 16.10M = 1.99`
   and `29.62M / 15.77M = 1.88`. So the whole question is where the peak sits
   and how wide it is — not how many levels there are.
2. **The peak level is a property of the constraint, not of `m`.** Both runs
   peak at level 7 despite having 10 and 11 rows. So adding a row does *not*
   multiply the cost by a branching factor; it moves the peak by at most one
   level and rescales it.

This also retires the incidental claim in §6.4 that the ladder reformulation is
"the same search tree" as a *qualitative* observation: it is now **measured**,
and the two trees agree to within 8 % in total nodes and to within 0.3 % at
levels 8–10.

### 12.2 The real growth rate

**Measured** costs of refutations at `n=17` (all EXHAUSTED, all with only this
workstream's own values assumed):

| `k` | probe | nodes | time | nodes/s | note |
|---|---|---|---|---|---|
| 7 | whole level | 21 437 | 0.49 s | 44 k | |
| 8 | whole level | 73 007 | 3.70 s | 20 k | |
| 9 | `>= 83` | 347 899 | 19.3 s | 18 k | chain bound from `f(8)=74`; 2 above true value |
| 9 | `>= 82` | 2 412 355 | 74.9 s | 32 k | `= f(9)+1`, the hard one |
| 10 | `>= 91` | **0** | **0 s** | — | free: chain from `f(9)=81` is tight |
| **11** | **`>= 99`** | **32 034 663** | **3 255.8 s** | **9.8 k** | chain bound from `f(10)=90`; **new** |

There is no single growth rate, because "the refutation at level `k`" is not one
thing — its cost depends on how far the target sits above the true value. Two
honest alignments of the data, both spanning `k=9 -> k=11`:

| alignment | `k=9` | `k=11` | total | per level |
|---|---|---|---|---|
| refute `f(k)+1` (hardest possible) | 2 412 355 | 32 034 663 | 13.3x | **3.6x** |
| refute the chain's bound (first refutation) | 347 899 | 32 034 663 | 92x | **9.6x** |

So the per-level factor in **nodes** is **3.6x–9.6x**, against the 20x assumed.
Throughput also *falls* with level (32 k nodes/s at `k=9`, 9.8 k at `k=11` — the
constraints reject deeper inside the row enumeration, §7), a factor of `0.55`
per level, so the per-level factor in **time** is **~6.5x–17x**, against the
~21x per level the old table implied (`8 h -> 7 d -> 5 mo`). Note that the old
table was therefore not far wrong *per level* in time; where it went wrong was
its absolute anchor at `k=11`, which it put 9x too high.

Projected forward on that basis, for **one** refutation at the chain's bound:

| `k` | projected nodes | projected nodes/s | projected 1-core time | old (WRONG) estimate |
|---|---|---|---|---|
| 11 | *measured* 3.2e7 | *measured* 9 800 | *measured* **0.9 h** | ~8 h |
| 12 | 1.2e8 – 3.1e8 | ~5 500 | **6 h – 16 h** | ~7 days |
| 13 | 4e8 – 3.0e9 | ~3 000 | **1.6 d – 12 d** | ~5 months |
| 14 | 1.5e9 – 2.9e10 | ~1 700 | **10 d – 6 mo** | ~8 years |
| 15 | 5e9 – 2.8e11 | ~950 | **2 mo – 9 yr** | ~160 years |

The `k=12` row is the one that matters and it is the one being **measured**
rather than projected — see §13.1. The revision changes the practical verdict
at exactly one level: **`k=12` moves from "a week, don't bother" into "about a
day, worth attempting"**, which is why §13 attempts it. `k=13` moves from
"5 months" to "days to weeks", i.e. from impossible to plausible-with-patience
but still outside a session. `k >= 14` stays out of reach.

### 12.3 The corrected conclusion, which is narrower than the old one

§6.1 concluded that a bottom-up re-derivation of `f(15) = 126` is "out of reach
by roughly 10 orders of magnitude". **That margin was inflated and is
withdrawn.** The corrected statement:

- A *direct* bottom-up refutation ladder to `f(15) = 126` is still out of
  reach here, but the margin is **nothing like 10 orders of magnitude, and it
  cannot honestly be replaced by another single number.** The projection for one
  refutation at `k=15` spans 5e9 to 2.8e11 nodes — 1.7 orders of magnitude of
  spread — because the per-level factor is bracketed only as 3.6x–9.6x from
  *two* data points, and `(9.6/3.6)^4 ≈ 50` by the time that is compounded to
  `k=15`. Against what this machine could actually spend (~2.6e9 nodes = 3 cores
  for a day at the measured rates), that is somewhere between **2x and 100x out
  of reach** — i.e. 0.3 to 2 orders of magnitude, not 10. The previous figure is
  withdrawn; no confident figure replaces it, and the way to narrow it is a
  measured `k=12` datum (run #10), not more extrapolation.
- More to the point, **it is not needed.** §11.4 shows the density chain
  propagates 1:1 (`f(j) <= f(j-1) + 8` throughout this range), so `f(15) <= 126`
  follows from `f(12) <= 102`, and `f(16) <= 134` follows from the same thing.
  There is no need to run anything at `k = 13, 14, 15` at all. The whole
  remaining obstruction to the hand-derived 134 sits at **`k = 11` and
  `k = 12`**, and by §12.2 both are within an order of magnitude of this
  machine's reach.
- What genuinely remains out of reach is **133**, and for a structural reason
  rather than a compute reason: §11.5 shows `f(16) <= 133` needs
  `f(12) <= 101`, and if `f(12) = 102` (the value the published `8k+6`
  progression extrapolates to) then no amount of compute can refute 102. 133
  requires the extremal-parent enumeration of §6.2, whose *exactly measured*
  widths (6, 67, 1395, 43447, 1 966 099, 81 381 805 at levels 1–6) peak far
  above anything here. That part of §6 stands.

This is a real correction to this log's headline pessimism and it should be
read as one: the previous session over-stated the wall by several orders of
magnitude, and the reason was a growth model fitted to the branching phase of a
tree that turns out to be unimodal.

**A caution about this section, stated because the section it replaces failed
in exactly this way.** §12.2's projections rest on **two** refutation data
points (`k=9` and `k=11`) fitted with a one-parameter model. That is barely more
evidence than §6.1 had, and it is enough to bound the answer, not to pin it.
Everything above `k=12` in §12.2 should be read as an order-of-magnitude
bracket, and the brackets should be expected to move again once run #10's
measured `k=12` widths land. The one claim here that does *not* depend on the
model is the second bullet — that `k = 13, 14, 15` need not be run at all — and
that is the load-bearing one.

### 12.4 (R9): measured effect, and the constrained-decide formulation

Two things were added this session to make the `k=12` attempt cheaper. Both
were validated against already-established answers before being used.

**The constrained-decide formulation.** For a target `e` on `m` rows, given a
proved `f(m-1)`:
- *every* row degree is `>= e - f(m-1)` (delete that row; the other `m-1` carry
  `e - d <= f(m-1)`), so `--dfloor (e - f(m-1))` is sound — note this is for
  every row, not just the minimum-degree one;
- deleting an edge from a `K_{3,3}`-free graph leaves it `K_{3,3}`-free, so a
  graph with `>= e` edges exists iff one with **exactly** `e` exists, and
  `--emax e` is sound. This is what makes it legitimate to refute a whole
  half-line `>= e` with a run pinned to `e`.

Validated on cells whose answers are already established:

| run | expected | got |
|---|---|---|
| `-m 9 --decide 82 --emax 82 --dfloor 8` | EXHAUSTED (`f(9)=81`) | **EXHAUSTED**, 2 412 216 nodes (vs 2 412 355 unconstrained) |
| `-m 9 --decide 81 --emax 81 --dfloor 7` | FOUND | **FOUND**, 7 511 462 nodes — *exactly* the logged §4 count |
| `-m 11 --decide 99 --emax 99 --dfloor 9` | EXHAUSTED (§11) | EXHAUSTED (run in progress at write-up; deliberately abandoned as redundant once two routes had concluded) |

**And the honest finding is that it buys almost nothing at `k=9`**: 2 412 216
vs 2 412 355 nodes, a 0.006 % reduction. The existing bounds (R3–R6) already
imply the degree floor and the edge cap almost everywhere, so pinning them
explicitly is nearly redundant. Recorded because it was expected to be a lever
and is not — the same lesson as (R7) in §7.

**(R9), the (R7) hoist.** Regression, as predicted by the soundness argument in
§2 (R9 removes only rows `gen()` would reject, so no `place_level` call
disappears):

| run | nodes before R9 | nodes after R9 |
|---|---|---|
| `-m 9 --decide 83` | 347 899 | **347 899** |
| `-m 9 --decide 82` | 2 412 355 | **2 412 355** |
| `-n 6 -m 5 --enum 22 --emax 22 --dfloor 4 --extend 4` | `solutions=3 ext_success=2`, witness `6 62 61 51 43 23 15` | **identical, all three** |

Node counts unchanged to the digit, and the §3.8 `--extend` unit test returns
the identical witness. So (R9) is a pure time optimisation and every node count
elsewhere in this log remains directly comparable.

**And measured head-to-head, the win is small — 3 %, not the order of magnitude
I expected when I wrote it.** Same binary pair, same arguments, on the one
constrained cell whose answer is already known:

| binary | run | nodes | time |
|---|---|---|---|
| `orderly2` (no R9) | `-m 9 --decide 82 --emax 82 --dfloor 8` | 2 412 216 | 89.6 s |
| `orderly3` (R9) | identical | **2 412 216** | **86.7 s** |

Identical node counts, as the soundness argument requires; 3.2 % less time. The
reason is the same one that made the constrained-decide formulation nearly
redundant above: at `k=9` the existing bounds (R3–R6) already hold `dmax` close
to where (R9) would cap it, so there is almost nothing left to hoist. (R9)
should bite harder where `dfloor` and `emax` bind and the existing bounds do
not — the `k=12` runs cap `dmax` from 17 down to ~10 at the deeper levels — but
**that is an expectation, not a measurement, and given the track record of
expectations in this log (§7, and the two in this very section) it should be
treated as probably wrong until measured.** (R9) is kept because it is free and
provably harmless, not because it was shown to matter.

**Provenance note for §11.2.** The UUID/SHA argument in §11.2 was made against
the pristine `orderly.c` at `HEAD`, SHA-256
`ec365fd840955f7e458e05c0ae2c70fe6def58fff0a6bb41b2b73216b29b55f9`, built as
`orderly2`. (R9) was added *after* that check, and lives in `orderly3`. So:
`orderly2` = the code that produced everything in §1–§11; `orderly3` =
`orderly2` + (R9), byte-identical in behaviour on every unconstrained run.

## 13. Run log for this session, and what is open

Binaries: `orderly2` (pristine `HEAD` source), `orderly3` (`+ R9`). Both are
gitignored. **Peak RSS across every run below was 3.9 MiB** — memory remains a
non-issue (§6.7), which matters because this machine's swap was near-full
throughout and four `kissat` processes from another workstream held four cores.
Self-cap of 3 concurrent `orderly` processes was respected throughout.

| # | run | purpose | outcome |
|---|---|---|---|
| 1 | `orderly2 -n 17 -m 9 --decide 83` | binary-vs-log regression | EXHAUSTED, **347 899** nodes, 19.7 s — matches log exactly |
| 2 | `orderly2 -n 17 -m 9 --decide 82` | binary-vs-log regression | EXHAUSTED, **2 412 355** nodes, 77.3 s — matches log exactly |
| 3 | `orderly2 -n 17 -m 11 --decide 99 --assume 9:81` | **re-run of the claimed `f(11)<=98` result** | **EXHAUSTED, 32 034 663 nodes, all 11 level widths identical to the archived run**, 7 760.2 s (§11.3) |
| 4 | `orderly2 -n 17 -m 11 --decide 98 --assume 9:81` | decides `f(11) = 98` vs `f(11) <= 97` | **EXHAUSTED, 32 035 246 nodes, 7 802.4 s ⇒ `f(11) <= 97`** (§13.0) |
| 5 | `orderly2 -n 17 -m 11 --decide 99 --emax 99 --dfloor 9 --assume 9:81` | third route to `f(11)<=98` | **killed** as redundant once #3 and `rung11_ext` had both concluded; no result claimed |
| 6 | `orderly3 -n 17 -m 9 --decide {83,82}` | (R9) regression | **347 899 / 2 412 355** — identical, see §12.4 |
| 7 | `orderly3 -n 6 -m 5 --enum 22 --emax 22 --dfloor 4 --extend 4` | (R9) vs the §3.8 `--extend` unit test | `solutions=3 ext_success=2`, identical witness |
| 8 | `orderly3 -n 17 -m 9 --decide 82 --emax 82 --dfloor 8` | validates constrained-decide | EXHAUSTED, 2 412 216 nodes, 86.9 s — correct verdict |
| 9 | `orderly3 -n 17 -m 9 --decide 81 --emax 81 --dfloor 7` | validates constrained-decide (positive) | FOUND, **7 511 462** nodes — exactly the §4 count |
| 10 | `orderly3 -n 17 -m 12 --decide 106 --emax 106 --dfloor 8 --assume 9:81 --assume 10:90 --assume 11:98 --countlevel L`, `L = 6,7,8,9` | **exact widths of the `k=12` tree**, to replace §12.2's projection with a measurement | **STILL RUNNING at write-up** (§13.1) |
| 11 | `-m 9 --decide 82 --dfloor 8 --nocanon` (inherited) | R2-free check at `n=17` | **killed**, infeasible by ~8 orders of magnitude (§11.6); no result claimed |
| 12 | `orderly3 -n 17 -m 10 --enum 90 --emax 90 --dfloor 9 --extend 8 --hcap 8 --assume 9:81` | was a probe for `f(11) = 98`; now a consistency check on §13.0 (§13.1a) | **STILL RUNNING at write-up**; must report `ext_success = 0`, anything else is a bug |
| 13 | `orderly2 -n 17 -m 11 --decide 97 --assume 9:81` | `f(11) <= 96`? and measures the predicted cost jump (§13.0) | **STILL RUNNING at write-up** |
| 14 | `orderly2 -n 17 -m 11 --decide 95 --assume 9:81` | **the shot at `f(11) <= 94`, i.e. at `f(16) <= 134`** (§13.1c) | **queued behind run #10's `--countlevel 6`; STILL RUNNING or not yet started at write-up** |

Every `--assume` used anywhere above is one of **this workstream's own proved
values** (`f(9) <= 81`, `f(10) <= 90`, `f(11) <= 98`). No published number
appears in any run that a result is claimed from.

### 13.1 The `k=12` attempt

Target and its derivation, entirely from our own values. The chain gives
`f(12) <= 106` from `f(11) <= 98` for free, so the first value worth a search is
`e = 106`, and refuting it gives `f(12) <= 105` hence `f(16) <= 137`. Because
`--decide 106` accepts `E >= 106`, and because edge deletion preserves
`K_{3,3}`-freeness, one EXHAUSTED run at 106 settles the whole half-line. The
sound narrowing (§12.4): every row degree is `>= 106 - f(11) = 106 - 98 = 8`, so
`--dfloor 8` is sound, and `--emax 106` pins the total.

Structurally this is a **much wider** problem than `k=11 @ 99`, and the reason
is worth writing down because it is the honest cost driver:

| | `k=11 @ 99` | `k=12 @ 106` |
|---|---|---|
| forced degree floor | 9 | 8 |
| degree sum | 99 | 106 |
| slack above `m * dfloor` | `99 - 11*9 =` **0** | `106 - 12*8 =` **10** |
| admissible degree sequences | **1** (9-regular) | **41** (partitions of 10, largest part `<= 9`) |

At `k=11` the tightness argument collapsed the problem to a single degree
sequence, which is exactly why it cost only 3.2e7 nodes. At `k=12` there are 41,
so the naive expectation is tens of times more work on top of the extra level.
Run #10 measures this rather than guessing it.

**Partial result, and it is only a lower bound.** Run #10's `--countlevel 6`
had consumed **64 CPU minutes without completing** when this was written, so no
exact width is available. What that does license is a bound, by comparison with
a run of known size at the same contention on the same machine: the `k=11`
re-run did 32.0e6 nodes in 129 CPU minutes (§11.3), i.e. ~4.1e3 nodes/s, so run
#10 has traversed **at least ~1.6e7 nodes** in levels 0–6 alone. The *entire*
levels 0–6 of the `k=11` tree is 1.54e7 nodes. So:

> levels 0–6 of the `k=12 @ 106` tree already exceed the whole of levels 0–6 of
> the `k=11 @ 99` tree, and were still growing.

That is consistent with the 41-vs-1 degree-sequence expansion and with §12.2's
projected 1.2e8–3.1e8 total, but it does **not** confirm it — a lower bound of
1.6e7 on one level is compatible with a wide range of totals. §12.2's `k=12` row
therefore remains a projection, and the honest statement is that the measurement
was attempted, produced a bound rather than a value, and was then cancelled in
favour of the cheaper `k=11` route (§13.1c). Anyone resuming it should note that
`--countlevel` prints nothing until it finishes, which makes it a poor choice for
a run of uncertain length; `--split` shards or a node limit would give partial
visibility.

### 13.0 `f(11) <= 97`: a second refutation at `k=11`, and it was almost free

Run #4 concluded, and the answer is the better of the two possibilities:

```
./orderly2 -n 17 -m 11 --decide 98 --assume 9:81
  level nodes: 0:1 1:9 2:156 3:1880 4:33956 5:1021053 6:14347875 7:16095576
               8:534574 9:142 10:24
  RESULT ... target=98 dfloor=0 emax=-1 status=EXHAUSTED nodes=32035246
         solutions=0 ext_success=0 secs=7802.354 rss_mib=3.7
```

> **`z(11,17;3) <= 97`.** No `11 x 17` `K_{3,3}`-free graph has 98 or more edges.

Same soundness conditions as §11.1: `--decide` accepts `E >= target`, so one
EXHAUSTED run at 98 refutes the whole half-line; `dfloor=0`, `emax=-1`,
no sharding, no node limit; the sole assumption is our own `f(9) <= 81`.
So `f(11)` is now pinned into `[90, 97]`, and **`f(11) = 98` is refuted, not
merely unproven** — §13.1a's probe is thereby answered before it finishes.

**The striking part is the cost: it was free.** 32 035 246 nodes against
32 034 663 for the target-99 run — **583 more nodes, 0.0018 %.** That badly
breaks the model in §12.2, which had the per-unit-of-target factor at 3x–7x
(measured at `k=9`, where `83 -> 82` cost 6.9x). Understanding why matters more
than the datum, because it says where the next edge gets expensive.

Compare the two level profiles:

| level | target 99 | target 98 | difference |
|---|---|---|---|
| 2 | 153 | 156 | +3 |
| 3 | 1 836 | 1 880 | +44 |
| 4 | 33 915 | 33 956 | +41 |
| 5 | 1 020 778 | 1 021 053 | +275 |
| 6 | 14 347 690 | 14 347 875 | +185 |
| 7 | 16 095 541 | 16 095 576 | +35 |
| 8 | 534 574 | **534 574** | **0** |
| 9 | 142 | **142** | **0** |
| 10 | 24 | **24** | **0** |

The tail is *identical*, and there is an exact reason. Rows are ordered by
non-increasing degree (R1), so the last row's degree is at most the previous
one's. A 10-row prefix can only reach 98 if `E_10 + d_10 >= 98` with
`d_10 <= d_9`:

- `E_10 = 90`: **every** 90-edge `10x17` `K_{3,3}`-free graph is 9-regular —
  delete its minimum-degree row, `90 - d <= f(9) = 81` forces `d >= 9`, and ten
  degrees `>= 9` summing to 90 are all exactly 9. So these are precisely the 24
  graphs of §11.3, and `d_10 <= 9` gives at most 99.
- `E_10 = 89`: such a prefix has minimum degree `<= 8` (it is below the maximum
  90), and by R1 that minimum *is* `d_9`, so `d_10 <= 8` and the total is at
  most 97 — **below 98.** Pruned at level 9, exactly as before.

So dropping the target from 99 to 98 opens *nothing* at the bottom of the tree;
it only relaxes a few suffix bounds higher up, which is the +583. **The next
step down is where this stops being free:** at target 97 the `E_10 = 89`
prefixes become viable (`89 + 8 = 97`), so the level-10 population jumps from 24
to the whole of `Ext(10,17,89)`, which is not a single degree sequence. Run #13
(`--decide 97`, launched) measures that jump. This is the first genuinely
predictive statement this log has been able to make about its own cost, and it
is falsifiable: if `--decide 97` also comes back at ~3.2e7 nodes, the reasoning
above is wrong and should be re-examined.

### 13.1a A cheap sufficient probe for `f(11) = 98` — answered, and now a cross-check

**Superseded by §13.0 before it finished.** `--decide 98` EXHAUSTED means no
98-edge `11x17` graph exists at all, so this probe *must* report
`ext_success = 0`. It is therefore no longer a probe but a **consistency check
on a brand-new refutation**, and a useful one: `ext_success >= 1` would directly
contradict §13.0 and expose a bug in either the `--extend` path or the main
search. It was left running for exactly that reason. The original framing
follows.

Run #4 (`-m 11 --decide 98`, unconstrained) settles `f(11)` either way but is
projected at 1.6e8–3.2e8 nodes (§12.2), i.e. 5–10 h. A much cheaper *sufficient*
test exists and was launched alongside it, run #12:

```
./orderly3 -n 17 -m 10 --enum 90 --emax 90 --dfloor 9 --extend 8 --hcap 8 --assume 9:81
```

This asks whether any of the 24 nine-regular `10x17` graphs of §11.3 admits an
extra row of degree **8** rather than 9. If one does, that graph plus that row
is a 98-edge `11x17` `K_{3,3}`-free graph, so `f(11) = 98` immediately, with a
witness to certify through `verify/checker.py` — at the cost of the same ~3e7
nodes as `rung11_ext`, about 20x cheaper than run #4.

**It is sufficient but not necessary, and the asymmetry must not be misread.**
The correct necessary-and-sufficient reduction for `e = 98` is weaker than the
one for `e = 99`: the min degree is `<= floor(98/11) = 8` and deleting it leaves
`98 - d <= f(10) = 90`, so `d = 8` and the parent is again extremal at 90 edges
— but the parent's ten degrees are then only forced `>= 8`, not `>= 9`. Ten rows
summing to 90 with each `>= 8` leaves 10 units of slack, hence **41** degree
sequences rather than one. So `--dfloor 9` covers only the 9-regular slice.
Therefore: `ext_success >= 1` **proves** `f(11) = 98`; `ext_success = 0` proves
**nothing** and run #4 (or a `--dfloor 8` rerun) is still needed.

### 13.1b Runs still in flight at write-up, and exactly what to do with each

Recorded in this form deliberately: a previous session died mid-run and its
result survived only as an unrecorded remark in a final message. Everything
below is the instruction for whoever finds these files.

Progress at write-up (22:34), for whoever needs to judge how far each got — all
three were still advancing, all three niced (`RN`) by the OS under load, and
none had written a byte:

| run | CPU consumed at write-up |
|---|---|
| #3 `verify_m11_T99.out` | 73 min 42 s |
| #4 `sat_m11_T98.out` | 72 min 48 s |
| #10 `width_m12_T106.out` (at `--countlevel 6`) | 64 min 24 s, no output — see the partial bound in §13.1 |

| file | command | what to do when it lands |
|---|---|---|
| ~~`verify_m11_T99.out`~~ **CONCLUDED** | run #3 | **Done: EXHAUSTED, 32 034 663 nodes, every level width identical. Recorded in §11.3.** Retained for the record: expect `status=EXHAUSTED nodes=32034663`. Put its `RESULT` line into §11.3's third table, replacing the IN PROGRESS row. **If `nodes != 32034663`, stop and treat it as a blocking bug** — the two routes would still stand but the binary/source provenance argument in §11.2 would not. Note it has already consumed **74 min of CPU against the original run's 54 min 16 s for identical work.** That is expected to be per-node slowdown, not extra work — seven heavy processes now share the 8 cores with swap near-full, and CPU seconds inflate with memory-stall cycles while the instruction count does not. But it is an *assumption* until the node count lands, and if the node count differs it is the first thing to abandon. |
| ~~`sat_m11_T98.out`~~ **CONCLUDED** | run #4 | **Done: EXHAUSTED ⇒ `f(11) <= 97`, `f(16) <= 137`. Recorded in §13.0**, and §4/§11.4/§11.5/the headline table are updated. |
| `width_m12_T106.out` | run #10 | **Cancelled** once its slot was wanted for §13.1c's `k=11` route; only the lower bound in §13.1 came out of it. If resumed: read off `level nodes:` for each `L`; total cost ≈ 2x the peak width (§12.1), which would replace the projected `k=12` row of §12.2 with a measurement. Use `--split` or a node limit rather than `--countlevel`, so a long run yields partial visibility. |
| `ext8_from_9reg.out` | run #12 | Now a cross-check, not a probe (§13.1a). It **must** report `ext_success = 0`, because §13.0 already refuted every 98-edge `11x17` graph. `ext_success >= 1` would contradict §13.0 and is a **blocking bug** in either `--extend` or the main search — investigate before trusting anything at `k=11`. |
| `sat_m11_T95.out` | run #14 | **The important one.** `EXHAUSTED` ⇒ `f(11) <= 94` ⇒ **`f(16) <= 134` self-contained** — update §11.4/§11.5, `test_reduction.py` and the headline table, and note that nothing at `k = 12..15` is then needed. `FOUND` ⇒ certify the 11-row 95-edge witness through `verify/checker.py`; `f(11) >= 95`, and 134 goes back to `k >= 12`. `ABORTED`/empty ⇒ **no verdict**; report the level profile as a partial. |
| `sat_m11_T97.out` | run #13 | `EXHAUSTED` ⇒ `f(11) <= 96` and `f(16) <= 136`; propagate through §11.4/§11.5 and `test_reduction.py`. `FOUND` ⇒ **`f(11) = 97` exactly** — certify the 11-row 97-edge `WITNESS_ROWS` through `verify/checker.py`, and note that `k=11` is then closed at `f(16) <= 137`, so 134 must come from `k >= 12`. Either way, compare its node count against §13.0's prediction that this is the step where cost jumps. |

An empty or truncated file means the run did not finish. A missing result is
never evidence of a refutation.

### 13.1c Priority change: `k=11`, not `k=12`, is now the route to 134

§13.0 changes the plan, and the reasoning should be explicit because §5, §6 and
§12 all assumed the opposite.

Everything above assumed the remaining edges had to be bought at `k = 11, 12, 13`
with the expensive ones at 12 and 13. But the inverse table in §11.5 says
`f(16) <= 134` follows from **`f(11) <= 94`** alone, and `--decide` refutes a
half-line, so that is **one command**: `-m 11 --decide 95`. Compare the two
routes to the same goal:

| route | requirement | levels | slack in the forced degree sequence |
|---|---|---|---|
| via `k=12` | `f(12) <= 102`, i.e. `-m 12 --decide 103` | 12 | 10 (41 degree sequences, §13.1) |
| via `k=11` | `f(11) <= 94`, i.e. `-m 11 --decide 95` | 11 | fewer rows, one level shallower |

The `k=11` route is one level shallower and was measured at 3.2e7 nodes for its
first two rungs. So the `k=12` width measurement (run #10) was cancelled after
its `--countlevel 6` datum — enough to correct §12.2's projection, which is what
it was for — and the freed core went to `-m 11 --decide 95` (run #14).

**What each outcome means.** `EXHAUSTED` ⇒ `f(11) <= 94` ⇒ **`f(16) <= 134`,
fully self-contained, matching the hand-derived bound of §5 and needing nothing
at `k = 12..15`.** `FOUND` ⇒ a 95-edge `11x17` witness, so `f(11) >= 95`, the
`k=11` route is capped at `f(16) <= 136`, and 134 must return to `k >= 12`.
Either outcome is worth having; the second is the cheaper one to obtain, since
the search stops at the first witness.

**The honest risk.** Cost per unit of target decrease is unmeasured below 98,
and §13.0 predicts the *next* step is where it jumps (the `Ext(10,17,89)`
prefixes become viable at target 97). Three units below 98 could be anywhere
from ~1e8 to ~1e10 nodes. Run #13 (`--decide 97`) is running alongside precisely
to calibrate that, and if run #14 has not converged it should be reported as a
partial with its level profile, never as a refutation.

### 13.2 Open

- **`f(11)`: exactly 98, or `<= 97`?** Runs #4 and #12 settle it. FOUND gives
  `f(11) = 98` — the first *exact* `n=17` value above `k=10`, and it would
  *close* the `k=11` column of §11.5 permanently, forcing all further progress
  to `k >= 12`. EXHAUSTED gives `f(11) <= 97` and hence `f(16) <= 137` for free.
- **`f(12) <= 105`**, i.e. one refutation at `k=12` (run #10 sizes it).
- **`f(12) <= 102`**, which by §11.4's 1:1 propagation is *exactly equivalent to*
  the hand-derived `f(16) <= 134` and needs no work at `k = 13, 14, 15` at all.
  This is the single highest-value target this workstream has, and §12.2 now
  puts it within a few orders of magnitude rather than ten.
- `f(16) <= 133` is **not** reachable by the density chain if `f(12) = 102`
  (§11.5). It needs §6.2's extremal-parent enumeration, still infeasible.
- The unexploited "any column pair lies in at most 5 rows once every degree is
  `>= 8`" look-ahead (§10) is now more attractive than when it was written,
  because the constraint it needs (`dfloor >= 8`) is *exactly* what the `k=12`
  runs impose. It was analysed but **deliberately not implemented**; the
  analysis is recorded in §13.3 because it both sharpens and partly corrects
  what §10 claimed for it.

### 13.3 The column-pair look-ahead: analysed, corrected, not implemented

§10 recorded the rule `sum_{r contains {a,b}} (d_r - 2) <= 2(n-2)` — hence at
most 5 rows per column pair once every degree is `>= 8` — as "logically implied
by the triple constraint but invisible to the raw counters", and as the most
promising unexploited lever. Working it through:

**The derivation is right.** Each row `r` containing both `a` and `b`
contributes `d_r - 2` triples `{a,b,c}`; each of the `n-2` such triples has
multiplicity `<= 2`; so `sum_{r} (d_r - 2) = sum_c mult({a,b,c}) <= 2(n-2) = 30`
at `n=17`. With all degrees `>= 8` each term is `>= 6`, giving `<= 5` rows.

**But "invisible to the raw counters" is too strong, and this matters.** The
quantity in question is exactly

> `pairload[a][b] = popcount(one[a][b]) + 2 * popcount(two[a][b])`

which is an `O(1)` function of state (R0) *already maintains*. So the rule is
not new information — it is the per-triple caps summed — and the saturated case
is already caught: if `pairload[a][b] = 30` then every `two[a][b]` bit is set
and `append_col` rejects any third column outright.

**What is genuinely available is a look-ahead, and it is narrower than §10
implied.** The win is not extra pruning power but *earlier* rejection inside the
row enumeration, which is where §7 says all the time goes. While building a row
at a level with minimum admissible degree `dmin`, appending column `c` to a
partial row already containing `a` can be rejected immediately if
`pairload[a][c] + (dmin - 2) > 30`, because the completed row will have degree
`>= dmin`. Today that pair is only rejected once enough further columns have
been added to actually saturate some triple `{a,c,x}`. Cost is `O(j)` per
append, the same order as the existing incremental `forb` update.

**Not implemented, on purpose.** It is a new pruning rule on the critical path,
and its failure mode is the one this project treats as unacceptable: a false
UNSAT. Unlike (R9) — whose correctness argument guarantees *identical* node
counts, so the regression is exact to the digit — this rule deliberately changes
the tree, so it can only be validated by verdict agreement, which is a much
weaker net. Shipping it would mean re-running `validate.py`'s whole grid plus the
`--nocanon` cells before any result could be trusted, and that is more than the
remaining budget. Recorded here with the implementation sketch so the next
session can take it up with the validation it needs, and with the expectation
management that follows from the paragraph above: it is a constant-factor time
win on row enumeration, not an order-of-magnitude reduction in the tree.
- `WRITEUP.md` (§1 status, §3 program inventory, §4 run log) and `REDUCTION.md`
  still carry the pre-`f(11)` numbers (`f(16) <= 144`) and the superseded §6.1
  feasibility table. They are outside this workstream's directory and were not
  edited; they need the §11.4 chain and the §12.2 table folded in.
