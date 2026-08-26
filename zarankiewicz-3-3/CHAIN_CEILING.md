# The density chain stops at 134, and that is exactly why 133 is hard

## Result

> **Theorem A (row deletion; unconditional and self-contained).** No sound
> chain whose final step deletes a *row* proves `z(16,17;3) <= 133` —
> regardless of how much computation is spent at levels `k <= 15`, and even
> if every value there is determined exactly.
>
> **Sharpness.** `z(16,17;3) <= 134` *is* reachable that way, so `134` is
> the row chain's exact ceiling for this cell, and it is attained.
>
> **Theorem B (column deletion; conditional).** A chain whose final step
> deletes a *column* (`16x17 -> 16x16`) reaches `133` only from
> `z(16,16;3) <= 126`. So it too fails **provided `z(16,16;3) >= 127`.**

Theorem A needs nothing but this repository: the lemma is re-derived below,
and the one fact it consumes is a 126-edge `K_{3,3}`-free `15x17` matrix
that `verify/checker.py` re-verifies with three independent detectors on
every test run.

**Theorem B's hypothesis is not yet discharged here, and this is stated up
front rather than buried.** The best `16x16` lower bound this project can
produce from its own verified data is exactly **126** — one edge short of
what Theorem B needs. The published value is `z(16,16;3) = 128`, which would
discharge it comfortably, but that is a citation, and this project's
standard is not to rest a result on one. See "The column route, and the one
edge we are missing" below for what was tried and what it would take.

So the combined claim "*the* density chain cannot reach 133" is **fully
proved for the row direction and conditional for the column direction**. It
is not asserted unconditionally anywhere in this document.

## Definitions

`z(m,n) := z(m,n;3,3)` is the maximum number of edges in a bipartite graph
with `m` rows and `n` columns containing no `K_{3,3}`.

By "the chain" we mean the style of argument that derives upper bounds
purely arithmetically from a table of lower levels, with no enumeration —
the `z_bound` algorithm of Collins–Riasanovsky–Wallace–Radziszowski. Its
engine at the top step is:

**Density lemma** (their Lemma 3; re-derived here so nothing rests on the
citation). Let `G` be `K_{3,3}`-free on `m x n` with `e` edges, `m >= 2`.
Its minimum row degree `d` is at most the mean `e/m`, hence at most
`floor(e/m)` since degrees are integers. Deleting that row leaves a
`K_{3,3}`-free `(m-1) x n` graph with `e - d >= e - floor(e/m)` edges.
Therefore

```
e - floor(e/m)  <=  z(m-1, n).
```

Its three hypotheses, each confirmed rather than assumed:

1. **`m >= 2`.** At `m = 1` the lemma is *vacuous*, not merely weak:
   `e - floor(e/1) = 0 <= z(0,n) = 0` for every `e`. See the boundary note
   below — this bit us.
2. **Deletion preserves `K_{3,3}`-freeness.** This is row-deletion
   monotonicity, proved and machine-checked by exhaustion over all `2^16`
   matrices on `4x4` in `test_lower_bounds.py`.
3. **`d <= floor(e/m)`.** A minimum is at most a mean; degrees are integers.
   No further structure required.

As an inference rule, from `z(m-1,n) <= B` it licenses

```
z(m,n)  <=  CEIL(B, m)  :=  max{ e : e - floor(e/m) <= B }.
```

## Proof of Theorem A

Whatever the chain does below, a final step that deletes a row must apply
the rule at `m = 16` to some upper bound `B` on `z(15,17)`, and must obtain
`CEIL(B,16) <= 133`.

**Step 1.** `CEIL(126,16) = 134`, since `134 - floor(134/16) = 134 - 8 = 126
<= 126` while `135 - 8 = 127 > 126`.

**Step 2.** `CEIL` is nondecreasing in `B` (larger `B` admits a superset of
`e`). So `CEIL(B,16) <= 133 < 134 = CEIL(126,16)` forces `B < 126`, i.e.
`B <= 125`. Directly: `CEIL(125,16) = 133`, and `125` is the largest such
input.

**Step 3.** `z(15,17) >= 126`, witnessed by the explicit matrix
`data/known_witnesses/z15_17_126_witness.csv`, verified here. So `B <= 125`
is **not a true upper bound**, and any chain that asserts it is unsound.

Hence no sound chain reaches `133`. Since `CEIL(126,16) = 134` and `126` is
the true value of `z(15,17)`, the ceiling `134` is attained. **[]**

The full sensitivity of the last step:

| input `z(15,17) <=` | chain yields `z(16,17) <=` |
|---|---|
| 124 | 132 |
| **125** | **133** ← would suffice, but is false |
| **126** | **134** ← true value, and the chain's ceiling |
| 127 | 135 |

## The column route, and the one edge we are missing

The bipartite problem is symmetric under transposition, so the density lemma
applies equally to columns. A `16x17` graph with `e` edges has minimum
*column* degree at most `floor(e/17)`, and deleting that column leaves a
`K_{3,3}`-free `16x16` graph. This gives a second, genuinely different final
step:

```
e - floor(e/17)  <=  z(16,16).
```

I originally stated Theorem A as covering "the density chain" without
qualification. That was **wrong** — it silently assumed the last step
deletes a row. The column step is a real alternative and had to be analysed
separately.

Doing so:

| input `z(16,16) <=` | column step yields `z(16,17) <=` |
|---|---|
| 125 | 132 |
| **126** | **133** ← the column route *would* reach 133 |
| 127 | 134 |
| 128 | 136 |

So the column route reaches `133` **iff** `z(16,16;3) <= 126`, and is
blocked exactly when `z(16,16;3) >= 127`.

**What we can prove ourselves: `z(16,16;3) >= 126`. Exactly one short.**

Column deletion is monotone for the same reason row deletion is, so deleting
any column from our verified 132-edge `16x17` witness gives a `K_{3,3}`-free
`16x16` graph. Its column degrees are

```
[6, 6, 6, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 9, 9]
```

so the best single deletion removes a degree-6 column and leaves **126**
edges — verified `K_{3,3}`-free by the checker. That is precisely the
threshold value, and therefore **does not block the column route**.

**What was tried to close the gap, and failed.** Greedy edge augmentation
with 60 randomised restarts on each of the 17 possible column deletions
(1,020 runs): every one saturated at **126**, never reaching 127. That is a
negative search result, not a proof — a better search, or a different seed
witness, may well find 127. It is recorded so the attempt is not silently
repeated.

**What would discharge the hypothesis.** Any one of:

1. An explicit 127-edge `K_{3,3}`-free `16x16` matrix, verified here. This is
   the cheapest and most likely route — the published `z(16,16;3) = 128`
   implies such a matrix exists, so this is a search problem, not an open
   one.
2. An exhaustive refutation of `z(16,16;3) <= 126` by the project's own
   generator.
3. Accepting the published `z(16,16;3) = 128` as an input, which discharges
   it immediately but makes the combined claim conditional on a citation.

Until one of these lands, this document claims Theorem A unconditionally and
Theorem B conditionally, and does **not** claim that the density chain as a
whole is blocked.

## Corollary: the published 133 did not come from their arithmetic

The 2016 paper tabulates `133` for this cell and separately describes the
arithmetic `z_bound` algorithm, which chains Lemmas 2–4 over a table of
lower cells. That algorithm cannot output `133` here, by **both** routes:

- **Row step.** Theorem A, unconditionally. It would need
  `z(15,17;3) <= 125`, and `126` is witnessed.
- **Column step.** It would need `z(16,16;3) <= 126`. **Their own table
  gives `z(16,16;3) = 128`**, so their algorithm cannot derive `<= 126`
  from it.

The column half of this corollary is on firmer footing than Theorem B,
and for a reason worth being explicit about: the corollary is a claim about
what *their* algorithm could derive from *their* table, so using their
`z(16,16;3) = 128` is internally consistent rather than a borrowed
assumption. Theorem B, by contrast, is a claim about what is actually true,
so it may not lean on an unverified citation — which is why it stays
conditional while this corollary does not.

Therefore the `133` entry must have come from their exhaustive computation,
not from their arithmetic.

This is worth stating because it reaches, by a completely different route, a
conclusion this project had previously argued from **typography**: the
paper's table legend distinguishes bold (exact) from italic (exhaustive
computation) from upright (lemmas only), and the embedded PDF font for the
`133` cell was found to be `PJYSJE+CMTI10`, i.e. italic. That is a fact
about a PDF file, established by parsing it. The argument here is a fact
about arithmetic, needs no access to the paper at all, and agrees.

**Scope, stated precisely.** The corollary concludes *only* that the `133`
entry did not come from chaining the density lemma. It does **not**
establish that `133` is correct, nor that their exhaustive computation was
correct, nor anything about the true value of `z(16,17;3)`. The upper bound
remains uncertified by anyone — which is exactly why certifying it is a
target of this project rather than an input to it.

## Where the chain is tight, and where it is not

Running `CEIL` on the values this project proved from scratch together with
the published ones:

| `m` | input `z(m-1,17)` | source of input | chain gives `z(m,17) <=` | true value | gap |
|---|---|---|---|---|---|
| 10 | 81  | **proved here** | 90  | 90  | **0** |
| 14 | 110 | published | 118 | 118 | **0** |
| 15 | 118 | published | 126 | 126 | **0** |
| 16 | 126 | published | **134** | **133** | **1** |

The density lemma is **exactly tight at every step where a comparison is
possible, and loses exactly one edge at `m = 16`** — which is the single
cell on this row still open.

**How much to read into that: not much, and deliberately so.** It is a
suggestive coincidence, not evidence about the value of `z(16,17;3)`. The
honest reading is narrow and about *method*, not about the answer: the
cheap arithmetic route is exhausted for this cell, and the frontier of what
is known sits exactly where it stops working. That is a fact about why the
problem is hard, not a hint about which way it resolves. This document makes
no claim in either direction, and the accompanying tests assert the gap
table so the observation cannot silently drift into a stronger claim.

## Consequence for this project's strategy

Combined with `LOWER_BOUNDS.md` (`z(11,17;3) >= 94`, so `f(11) <= 93` is
false), the picture for the density-chain route is now closed:

- `z(16,17;3) <= 134` is the **best** the chain can ever give, at any level.
- Reaching it needs `z(11,17;3) = 94` exactly, the bottom of the proved
  bracket `[94, 97]` — and the evidence at `k = 9, 10`, where the same
  construction undershoots the truth by 3 and 4 edges, argues against it.
- `z(16,17;3) <= 133` is **unreachable** by the chain, twice over: by this
  theorem at the top of the chain, and by the `f(11) >= 94` floor at the
  bottom.

So certifying `<= 133` requires genuine enumeration — the extremal-parent
route of `REDUCTION.md` — and no amount of further chain computation
substitutes for it. That is a negative result, but it is the useful kind: it
removes a whole family of cheap attacks from consideration on proof rather
than on intuition, and it says precisely where the remaining difficulty
lives.

## Boundary cases, and two bugs these tests caught

Both were in code I had already convinced myself was right, and both were
found by sweeping ranges the project never actually uses.

1. **`m = 1` returned a number instead of raising.** `e - floor(e/1) = 0`
   for every `e`, so the set has no maximum — and the function was returning
   the top of its own internal search window, a value manufactured by an
   implementation detail. A function that answers an unanswerable question
   is worse than one that raises, because the caller cannot tell.

2. **The search window was wrong for small `m`.** It was a fixed
   `B + 4m + 8`. Since `e - floor(e/m) >= e(m-1)/m`, the true answer scales
   like `Bm/(m-1)` — so at `m = 2` the answer is `2B` and the window
   truncated it for every `B > 15`. It was correct at `m = 16`, the only
   value the project uses, which is precisely why it survived. The window is
   now *derived* from that inequality rather than guessed, and the test
   sweeps `m` down to 2. A window that is right only where you look is not a
   window, it is a coincidence.

Neither bug affected any claimed result — both were outside the used range —
but the theorem's credibility rests on this arithmetic, so they are recorded
rather than quietly fixed.

## Confidence

- **Theorem A: ~0.98.** Three short steps, each machine-asserted;
  `CEIL` is cross-checked against a brute-force scan over a much wider
  window for all `m` in `[2,20)` and all `B` in `[0,140)`; the density lemma
  itself is validated against exhaustively brute-forced values on small
  cells, so an off-by-one in the *rule* would be caught, not just in its
  implementation.

- **Weakest step: ~0.98 as well, but it is a different kind of risk.** The
  mathematics carries essentially no risk. The exposure is that the theorem
  is a statement about a *class of arguments*, and such statements are easy
  to state too broadly. The scoping is therefore deliberate and narrow: it
  covers chains whose only rule is the density lemma. It says nothing about
  arguments that add the counting budget of Lemma 2, or Roman's LP, or any
  hybrid. Those are separately known to be far weaker here (141–142 against
  133, see `LITERATURE.md`), but that is a separate fact and is not claimed
  as part of this theorem.

  The two scores agree because the one real risk — overbroad phrasing — is
  addressed by scoping rather than by computation, and the computation that
  remains is elementary.

- **Theorem B: ~0.99 as a conditional, but its hypothesis is undischarged
  here.** The arithmetic (`133` reachable iff `z(16,16;3) <= 126`) is as
  solid as Theorem A's and is machine-asserted the same way. The exposure is
  entirely in the premise `z(16,16;3) >= 127`, which this project cannot yet
  prove — its own best is `126`. Given the published `z(16,16;3) = 128` and
  that a 127-edge matrix therefore certainly exists, I'd put ~0.97 on the
  premise being true, but truth is not the standard here: it is undischarged,
  and the document treats it as such.

- **The whole "the chain is blocked" story: not claimed.** That would need
  both theorems unconditionally, and one of them isn't. What *is* claimed
  unconditionally is Theorem A and the corollary about the 2016 paper's
  algorithm — the latter because it reasons from that paper's own table
  rather than from facts we must establish.

**Postscript on how the scoping error was found.** I wrote Theorem A first
as a claim about "the density chain", full stop, and only caught the missing
transposed case when re-reading the statement to look for exactly this
failure. The lesson is specific and worth keeping: a theorem asserting that
*no argument of a certain kind* can succeed is only as good as the
enumeration of that kind, and a bipartite problem has a symmetry that makes
one case look like the whole. The two implementation bugs recorded above
were found by sweeping unused parameter ranges; this one could only be found
by re-reading the claim itself, which is the harder habit.
