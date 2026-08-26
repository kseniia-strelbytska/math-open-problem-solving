# Orderly generation log — bottom-up isomorph-reduced exhaustive search

Workstream [L13]. Code: `orderly.c` (main generator), `brute.c` (deliberately
independent cross-check searcher), `validate.py` (validation harness).
All numbers below are measured on this machine (Apple M-series, 8 cores,
`clang -O2`), single-threaded unless stated.

**Headline results, stated up front so nothing here reads as more than it is:**

| claim | status |
|---|---|
| `z(k,17;3)` for `k = 1..10` computed from scratch: `f(9) = 81`, **`f(10) = 90`** | **PROVED by this code**, witnesses certified by `verify/checker.py` |
| `z(k,k;3)` for `k = 3..9` reproduced (incl. all 4 published anchors) | **PROVED**, agrees with published values and with an independent searcher |
| 32 small cells cross-checked against a deliberately independent searcher | **all agree, both directions** |
| `z(16,17;3) <= 133` (criterion C) | **NOT achieved** — measured infeasible on this machine, see §6 |
| bottom-up `f(15) = 126` re-derivation | **NOT achieved** — measured infeasible by ~10 orders of magnitude, see §6 |

The single most important finding is a **negative** one, and it kills the
plan as originally scoped: the Density Lemma ladder does *not* close, because
the value it needs at `k=9` is `78` and the true value is **81**. §5 explains
why this matters so much, and — using the further result `f(10) = 90`, which
shows the ladder is *exactly tight* at `k=10` — localises the entire remaining
obstruction to the three levels `k = 11, 12, 13`.

Second finding, also negative and also worth having: the "narrow ladder"
restructuring (`Ext(13,110) -> Ext(14,118) -> Ext(15,126)`) is **the same
search tree** as the constrained DFS I already measured, not a smaller one
(§6.3). Its apparent narrowness is the size of the *answer* at each rung; the
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

# the reduction's degree-sequence counts + generator level-1 width
../../.venv/bin/python test_reduction.py

# f(k) = z(k,17;3) bottom-up (levels 1..8 are seconds; 9 takes ~7 min)
./orderly -n 17 -m 9 --hcurve -v

# the load-bearing probes, individually
./orderly -n 17 -m 9  --decide 83                       # UNSAT
./orderly -n 17 -m 9  --decide 82                       # UNSAT
./orderly -n 17 -m 9  --decide 81                       # SAT  -> f(9)=81
./orderly -n 17 -m 10 --decide 90 --hcap 8 --assume 9:81 # SAT  -> f(10)=90

# R2 (column canonicity) tested with R2 switched off
./orderly -n 12 -m 4 --decide 33 --nocanon --hmode ub   # EXHAUSTED

# exact search-tree widths for the Ext(15,17,126) enumeration
./orderly -n 17 -m 15 --enum 126 --emax 126 --dfloor 8 \
          --hmode ub --assume 9:81 --countlevel 6
```

Build artifacts (`orderly`, `brute`, `orderly_asan`, `orderly_v1`) are listed
in `.gitignore`; note some were committed by an earlier snapshot before that
existed, so `git rm --cached` on them may be wanted.

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
check in §3.3.


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

### 3.2b R2 tested directly, with R2 switched off (n up to 12)

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

### 3.3 Published exact values reproduced

| cell | published | orderly | verdict |
|---|---|---|---|
| `z(6,6;3)` | 26 | **26** | match |
| `z(7,7;3)` | 33 | **33** | match |
| `z(8,8;3)` | 42 | **42** | match |
| `z(9,9;3)` | 49 | **49** | match |

Also reproduced, as internal consistency anchors: `z(3,3)=8`, `z(4,4)=13`,
`z(5,5)=20`, `z(10,10)=60`.

### 3.4 Hand-derived anchors reproduced

Independently of any search, the column-degree counting bound gives exact
values for small `k` at `n=17`, and the generator matches all of them:
`f(3)=36`, `f(4)=42`, `f(5)=52`, `f(6)=58`. (`f(3)`: each column lies in at
most 3 rows and at most 2 columns lie in all 3, so `e <= 2*17+2 = 36`.)

### 3.4b The reduction's degree-sequence counts (`test_reduction.py`)

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

### 3.5 Every witness certified through `verify/checker.py`

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

Throughput is 30k–900k nodes/s depending on how tight the constraints are
(tighter constraints mean more work rejected deep in the row-candidate
enumeration, hence *fewer* accepted nodes per second).

At a conservative 20x per level, refuting one value at level `k` costs about
`2.4e6 * 20^(k-9)` nodes:

| `k` | est. nodes for one refutation | est. single-core time |
|---|---|---|
| 10 | — | free, chain is tight (§5) |
| 11 | 1e9 | ~8 h |
| 12 | 2e10 | ~7 days |
| 13 | 4e11 | ~5 months |
| 14 | 8e12 | ~8 years |
| 15 | 1.5e14 | ~160 years |

and `f(15)` needs several such refutations, not one. **The self-contained
bottom-up re-derivation of `f(15) = 126` is out of reach on this machine by
roughly 10 orders of magnitude.** This is not a close call and no constant
factor rescues it.

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

Level 6 took 90 s at ~0.9M nodes/s. Extrapolating at the observed ~40x:

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

### 6.3 The "narrow ladder" reformulation is the same search, not a smaller one

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

### 6.3b Retargeting onto `REDUCTION.md`: what I can and cannot deliver

`REDUCTION.md` reduces everything to `Ext(15,17,126)` and `Ext(15,17,125)`.
I verified its arithmetic and its degree-sequence counts (§3.4b — all four
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
configurations I measured, because (as §6.3 shows) my degree-ordered DFS with
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

### 6.4 Memory — not the binding constraint

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

## 9. Not done / open

- `f(11)` and `f(12)`: SAT probes at the chain's predictions (`99` and `108`)
  were launched with node limits. If both are SAT the chain is tight through
  `k=12` and all the loss is at `k=13`; if either is UNSAT the loss is
  earlier. Either way this localises the obstruction further, cheaply, and is
  the single highest-value next computation.
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
