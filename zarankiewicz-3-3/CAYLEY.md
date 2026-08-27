# A `K_{s,s}`-freeness criterion for bipartite Cayley graphs

## The gap this fills

Collins–Riasanovsky–Wallace–Radziszowski (arXiv:1604.01257, §3) define the
**bipartite Cayley graph** `X(G,S)` for a group `G` and a subset
`S ⊆ G`: rows and columns are both indexed by `G`, with

```
row_g  =  g·S  =  { g·s : s in S }
```

They prove (their **Proposition 5**):

> `X(G,S)` is `K_{2,2}`-free **iff** `S` is a **Sidon set**.

Then they stop. Immediately afterwards they remark that for `Γ = Z_15` and
`S_2 = {5,6,8,9,10,11,14}`, "`S_2` yields a `K_{3,3}`-free graph" — a fact
they use without giving any criterion for it. A literature survey found **no
source stating the `s >= 3` criterion as a theorem**; the general shape is
asserted only informally, in Füredi–Simonovits' survey (arXiv:1306.5167,
p. 35): *"we would need that any `a` of them intersect in at most `a - 1`
points. Then we would be home."*

This document states and proves that criterion. It is the natural `s = 3`
companion to their Proposition 5, in their own notation.

## Theorem

> Let `G` be a group of order `n`, let `S ⊆ G` with `|S| = d`, and let
> `s >= 2`. Then `X(G,S)` is `K_{s,s}`-free **if and only if**
>
> ```
> | S ∩ a_1 S ∩ a_2 S ∩ ... ∩ a_{s-1} S |  <=  s - 1
> ```
>
> for every `(s-1)`-tuple `(a_1, ..., a_{s-1})` of **distinct non-identity**
> elements of `G`.

Abelian case, written additively: `|S ∩ (S + a_1) ∩ ... ∩ (S + a_{s-1})| <= s-1`.

### Proof

A `K_{s,s}` in `X(G,S)` is a choice of `s` distinct rows `g_1, ..., g_s` and
`s` distinct columns `c_1, ..., c_s` with `c_j` adjacent to `g_i` for all
`i, j`. Now `c` is adjacent to `g` exactly when `c ∈ g·S`, so the set of
columns adjacent to **all** of `g_1, ..., g_s` is

```
C(g_1, ..., g_s)  =  ∩_{i=1}^{s} g_i·S .
```

Hence `X(G,S)` contains a `K_{s,s}` on those rows iff
`|C(g_1, ..., g_s)| >= s`.

Left translation by `g_1^{-1}` is a bijection of `G`, so it preserves
cardinality:

```
|∩_i g_i·S|  =  |g_1^{-1} · ∩_i g_i·S|  =  |∩_i (g_1^{-1} g_i)·S|
             =  |S ∩ a_1 S ∩ ... ∩ a_{s-1} S|,     a_i := g_1^{-1} g_{i+1}.
```

The `g_i` are distinct iff the `a_i` are distinct and non-identity, and every
such `(s-1)`-tuple arises from some choice of distinct `g_i` (take `g_1 = e`,
`g_{i+1} = a_i`). So

```
X(G,S) contains a K_{s,s}
  <=>  some tuple of distinct non-identity a_i has
       |S ∩ a_1 S ∩ ... ∩ a_{s-1} S| >= s,
```

which is the contrapositive of the statement. **∎**

### Sanity: `s = 2` recovers Proposition 5

At `s = 2` the condition reads `|S ∩ aS| <= 1` for all `a != e`. In an
abelian group that says every non-zero difference `x - y` with `x, y ∈ S` has
exactly one representation — i.e. `S` is Sidon. So the theorem specialises to
Collins et al.'s Proposition 5, which is the check that the general statement
is normalised correctly.

### Design-theoretic reformulation

`X(G,S)` is `K_{s,s}`-free iff the **development** `dev(S) = { g·S : g ∈ G }`
is an **`s-(n, d, s-1)` packing** — a family of `d`-subsets of an `n`-set in
which every `s`-subset is contained in at most `s-1` blocks. For `s = 3`:
every 3-subset in at most 2 blocks.

This is the native idiom for the object, and it is worth stating because the
surrounding design-theory literature (difference families, optical orthogonal
codes, relative difference sets) is almost entirely at **strength `t = 2`**:
a `(v,k,λ)` difference family develops to a 2-design, and an OOC's
auto-correlation constraint `|S ∩ (S + δ)| <= λ_a` again characterises
`K_{2, λ_a + 1}`-freeness. The survey found no strength-3 single-base-block
theory. So the condition here has **no established name**; the two defensible
options grounded in existing vocabulary are "*`S` is a base block for a
`3-(n,d,2)` packing*" or, extending the "rectangle-free"/"parallelogram-free"
terminology of Rué–Serra–Vena (arXiv:1602.01992), "*`S` is `3x3`-grid-free*".

## Verification

The theorem is proved above, and separately **checked by exhaustion**
(`verify/test_cayley.py`): for every group in a family of small groups, every
subset `S`, and `s = 2, 3, 4`, the criterion's verdict is compared against
direct `K_{s,s}` detection on the constructed matrix. Any disagreement fails
the suite. The `s = 2` specialisation is additionally checked against an
independent Sidon-set test.

That matters more than usual here: the proof is three lines, which is exactly
the regime where an off-by-one in "distinct non-identity" or in `<= s-1`
versus `< s-1` slips through unnoticed.

## Consequences: lower bounds on the diagonal

Searching `S` exhaustively (up to translation, so WLOG `e ∈ S`) over `Z_n` and
`Z_a x Z_b` gives the largest `d` for which a `K_{s,s}`-free `X(G,S)` exists,
and hence `z(n,n;3) >= d·n`. All witnesses below are re-verified by
`verify/checker.py`.

| `n` | best `d` | `z(n,n;3) >=` | group | published status of the cell |
|---|---|---|---|---|
| 14 | 7 | 98 | `Z_14` | **closed at 105** — construction falls 7 short |
| 15 | 8 | **120** | `Z_15` | **closed at 120** — construction is *optimal* |
| 16 | 8 | **128** | `Z_4 x Z_4`, `Z_2 x Z_8` | **closed at 128** — construction is *optimal* |
| 17 | 8 | **136** | `Z_17` | **open**, `<= 141`; best published lower bound **132** |
| 18 | 8 | **144** | `Z_18` | **open**, `<= 156`; best published lower bound **132** |
| 19 | 8 | **152** | `Z_19` | **open**; no upper bound tabulated |
| 20 | 9 | **180** | `Z_20` | **open**; no upper bound tabulated |

Published values from Collins et al. Table 4 (diagonal read at glyph level:
`105`, `120`, `128` boldface = exact; `141`, `156` undecorated = from their
Lemmas 2–4 without enumeration) and Tan arXiv:2203.02283 Table 3, which also
publishes explicit extremal matrices for `n = 13..16`.

### Honest assessment of novelty

**Not new:** `n = 15, 16` match closed exact values; `n = 14` falls short of
one. These are independent re-derivations, useful as verified lower-bound
halves and nothing more.

**Apparently unpublished:** `n = 17, 18, 19, 20`, which exceed the best
lower bounds a survey could locate (132, 132, 136, 146 — themselves not
published as diagonal values but derived from published cells by padding and
block direct sums). Every table located stops at `n = 16` on the diagonal:
Collins' Table 4 has no lower-bound column at all, Tan's Table 3 stops at
`m = 16`, Davies–Gill–Horsley display only `m = 10..16`, Bhan et al. cover
the diagonal only at `(16,16)`, OEIS **A350304** terminates at `n = 16` with
keyword `more`, and Guy's 1967 Table 4 has rows only to `m = 10`.

**But the caveat is large enough that these should not be presented as the
contribution.** They are the plain cyclic-circulant baseline, reproducible
by a one-minute exhaustive search, and at `n = 17` the witness is exactly the
quadratic-residue set `QR(17) = {1,2,4,8,9,13,15,16}` — a classical object,
even if this consequence is unrecorded. More damning: at `n = 13, 14, 16` the
*known exact* optima are **irregular** and beat the circulant baseline by
14, 7 and 16 edges respectively. So the baseline is probably far from optimal
at `17..20` too, and quoting it as a headline would misrepresent how hard the
cells are.

The defensible contribution is the **criterion** — a stated, proved, and
exhaustively checked `iff` where the literature had only the `s = 2` case and
an informal remark — together with the systematic table it makes cheap to
compute.

## Sharpness, self-contained

For a `d`-regular `n x n` `K_{s,s}`-free graph, counting (row, column-triple)
incidences against the `s = 3` condition gives

```
n · C(d,3)  <=  2 · C(n,3),     i.e.    C(d,3) <= (n-1)(n-2)/3 .
```

At `n = 17` this forces `d <= 8` (since `C(9,3) = 84 > 80`), and at `n = 20`
it forces `d <= 9` (since `C(10,3) = 120 > 114`). **The construction attains
both.** So at those two orders no `d`-regular `K_{s,s}`-free `n x n` graph has
more edges than `X(G,S)` — with no citation anywhere in the argument.

The same comparison across `n = 8..21` shows the cap is attained at
`n = 8, 9, 11, 14, 15, 16, 17, 20` and missed by exactly one degree at
`n = 10, 12, 13, 18, 19, 21`. Note this is sharpness **among regular graphs
only** — the irregular optima at `n = 13, 14, 16` show that is a real
restriction, not a technicality.
