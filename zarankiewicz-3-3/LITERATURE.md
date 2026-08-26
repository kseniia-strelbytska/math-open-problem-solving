# Literature notes — `z(m,n;3)` and the (16,17) cell

Findings from a dedicated survey (2026-08-26). Everything technical below
was extracted from a paper actually fetched and read, not from memory; where
a claim could not be substantiated it is marked as such rather than
asserted, per the project's "no citation without certainty" rule.

## Status of the target

`Z(16,17,3,3)` is **still open** as of 2026-08-26. The most recent paper
touching the cell is Afrasyab, arXiv:2608.08154 (8 Aug 2026), which itself
reports `132 <= Z(16,17,3,3) <= 133` as open. Nothing newer found; one
adjacent August 2026 paper (arXiv:2608.11554, tripartite Zarankiewicz
numbers and norm graphs) is a different problem.

## The method behind the published 133 bound

Collins, Riasanovsky, Wallace, Radziszowski, "Zarankiewicz Numbers and
Bipartite Ramsey Numbers," arXiv:1604.01257 (2016).

**Lemma 2 (star counting).** For a `(m,n,e+)_s`-graph with left degree
sequence `(a_i)` and `e = m*d_L + r_L` (`0 <= r_L < m`):

```
(m - r_L)*C(d_L, s) + r_L*C(d_L + 1, s)  <=  sum_i C(a_i, s)  <=  (s-1)*C(n, s)
```

The middle term counts left-centred `K_{1,s}` stars; exceeding
`(s-1)*C(n,s)` forces, by pigeonhole, some `s` columns to be the leaves of
`s` such stars, i.e. a `K_{s,s}`. Mirror statement holds right-to-left.
(For `s=3, n=17` the right-hand bound is `2*C(17,3) = 1360`. This project
re-derived the same budget independently, from the observation that
`K_{3,3}`-freeness says exactly that every 3-subset of columns lies in the
neighbourhood of at most 2 rows, so counting (row, column-triple)
incidences two ways gives `sum_r C(d_r,3) <= 2*C(17,3)`. The derivation is
one line and is reproduced here rather than cited, so this document does
not depend on any file outside this PR.)

**Lemma 3 (density).** Removing a minimum-left-degree vertex from an
`(m,n,e+)_P`-graph leaves an induced `(m-1,n,f+)_P`-subgraph with
`f = e - floor(e/m)`.

**Lemma 4.** If `z(m-1,n;s) < z <= w - floor(w/m)` then `z(m,n;s) < w`.
Chaining Lemma 4 over a table from `(1,1)` up to `(m,n)` is their
`z_bound` algorithm — pure arithmetic, no enumeration.

**Backwards path extensions** (their §2). A step `(m,n,e+) |> (a,b,f+)`
means every `(m,n,e+)_P`-graph contains an induced `(a,b,f+)_P`-subgraph;
chaining single-vertex-removal steps back to a small base case gives a
"backwards path". Their `extend` algorithm then works *forwards* from an
exhaustively generated (nauty-based) set of `(a,b,f+)`-graphs, adding one
vertex at a time in all admissible ways, filtering, and de-duplicating up
to isomorphism at each step. The paper gives exactly one fully worked
backwards path (their Fig. 1, for the `b(2,5)` Ramsey computation) — **no
worked path is given for the (16,17;3) cell.**

**Which method produced 133 — verified independently, twice.** Their table
legend: bold = exact value, italic = "determined with exhaustive
computations", undecorated = from Lemmas 2-4 alone. Embedded PDF font names
for Table 4 were extracted independently on two separate occasions in this
project, both times finding the `133` cell set in `PJYSJE+CMTI10`
(italic) => exhaustive computation, and *not* bold => never claimed exact.
Across the row `z(k,17;3)` for `13 <= k <= 17`: `110` (k=13, italic),
`118` (k=14, roman), `126` (k=15, roman), `133` (k=16, italic), `141`
(k=17, roman). So the authors' own remark that `z(k,17;3)` for
`13 <= k <= 17` contains "weak-looking bounds" (their p.12) is about
numeric looseness relative to known constructions, not about proof rigour;
the row mixes both proof types.

## The hand-derivable bound, and why it matters

Applying Lemma 3 directly with `z(15,17;3) = 126`. **Only half of that
equality is independently established here.** The lower bound
`z(15,17;3) >= 126` rests on the 126-edge witness in
`data/known_witnesses/z15_17_126_witness.csv`, which this project
re-verified from scratch with `verify/checker.py`. The upper bound
`z(15,17;3) <= 126` — which is the half the derivation below actually
uses — is **cited from Afrasyab and has not been re-derived here**. So the
`<= 134` conclusion below is conditional on a published result, exactly
like the `<= 133` bound it is meant to help certify:

```
e - floor(e/16) <= 126
  e = 135 -> 135 - 8 = 127 > 126   contradiction
  e = 134 -> 134 - 8 = 126         consistent
```

**`z(16,17;3) <= 134`, provable by hand in one line, no computer** — but
only *given* the cited `z(15,17;3) <= 126`. It is a one-line derivation,
not a from-scratch proof.

The structural consequence is the useful part:

- **At `e = 134`:** the remainder has `>= 126 = z(15,17;3)` edges, i.e.
  *exactly* extremal. So any 134-edge 16x17 graph contains an **extremal
  126-edge** 15x17 `K_{3,3}`-free graph, and the deleted row has degree
  exactly 8.
- **At `e = 133`:** the remainder has `>= 125` edges, so a 15x17 graph with
  125 or 126 edges.

Both cases therefore reduce to an **extension problem**: enumerate
near-extremal 15x17 graphs up to isomorphism, then test single-row
extensions — far smaller than searching all 16x17 graphs. This is exactly
the backwards-path-extension technique, and it is the current plan. (The
plan's own idea ledger, which tracks this line of attack alongside the
abandoned ones, is not part of this PR and lands in a later PR in this
series; nothing in this document depends on it.)

Note the ladder this creates:
- `134` refuted => `z(16,17;3) <= 133`, matching the published bound, which
  has never been certified by anyone (acceptance criterion (C)).
- `133` refuted => `z(16,17;3) = 132` exactly, full resolution.

**A caveat on the word "independent" here.** Refuting `134` by this route
earns the label only if the enumeration of `Ext(15,17,126)` is itself done
from scratch — which entails re-deriving `z(15,17;3) <= 126` rather than
citing it, since an exhaustive enumeration at 126 edges that found a
127-edge graph would refute the input. If instead the cited value is used
as a shortcut, the result is a *conditional* re-derivation: correct, but
resting on the same published computation whose independence is the point.
Which of the two this project delivers is a fact about the eventual
enumeration code, not something this document can assert in advance.

## Approaches confirmed *not* to work for this cell

- **LP / ILP relaxation bounds are too weak.** Roman's bound (S. Roman,
  1975), the standard general upper bound for `s >= 3`, gives **142** for
  (16,17). Davies, Gill & Horsley, "Improved upper bounds on Zarankiewicz
  numbers" (arXiv:2411.18842, *Discrete Mathematics* 2025) strengthen
  Roman's LP with extra constraints, typically gaining 1 (rarely 2); their
  Table 2 gives **141** for (16,17). Both are far above the established
  133, so no formulaic/LP method reaches the frontier here. Two
  independent sources cross-corroborate (Jeremy Tan, arXiv:2203.02283,
  tabulates Roman's raw value for the same cell as 142). Real search is
  genuinely required.
- **Flag algebras / SDP:** no result applicable to a specific finite small
  cell was found. Flag algebras are used in this literature for
  asymptotic/density Turán-type bounds, not finite exact values.
  arXiv:2602.07844 relates SOS-rank of biquadratic forms to Zarankiewicz
  numbers but proves `BSR(m,n) >= z(m,n)` — the wrong direction to help,
  and it could not be confirmed whether it addresses `s=t=3` at all
  (flagged unconfirmed, not asserted).
- **A "de Caen bound" for finite `K_{3,3}` cells:** searched for and **not
  found**. Only a tangential de Caen–Székely construction for a different
  problem (C6-free density) surfaced. Explicitly not asserting such a
  bound exists.

## Progress on the flagged cells since 2016

Afrasyab (arXiv:2608.08154, Aug 2026) proves `Z(14,17,3,3) = 118` and
`Z(15,17,3,3) = 126` as **exact** values, matching lower-bound witnesses
this project has independently re-verified. So two of the five
"weak-looking" cells are now closed, and in both the 2016 upper bound
turned out **tight, not loose**. That is weak but real evidence about our
own cell (2 for 2 resolved as exact) — not proof in either direction.
`z(13,17;3) = 110` and `z(17,17;3) = 141` remain open, as does k=16.

## Worth reading further

Jeremy Tan, arXiv:2203.02283 (2022) — an independent SAT-based
Zarankiewicz project, architecturally similar to this project's own SAT
workstream: permutation-symmetry exploitation plus a "graph packing"
formulation giving exact values at table edges. It does not appear to have
attempted the (16,17;3) cell, but may contain encoding and
symmetry-breaking techniques relevant to our stalled solvers.

## No maintained authoritative table exists

No dedicated dynamic survey for small Zarankiewicz numbers (analogous to
Radziszowski's DS1 for Ramsey numbers) could be substantiated — a search
result hinted at one but no URL or maintainer was confirmable, so its
existence is *not* asserted here. The de facto reference remains Collins
et al. 2016 Table 4, patched piecemeal by scattered 2022-2026 preprints
(Tan; Davies-Gill-Horsley; Afrasyab; Hou), each correcting or extending a
handful of cells.
