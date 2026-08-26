"""Lower bounds on z(k,17;3) by row-deletion from verified witnesses.

## What this computes, and why it is sound

The whole content is one lemma, applied mechanically.

**Lemma (row-deletion monotonicity).** Let `G` be a `K_{3,3}`-free bipartite
graph with row set `R` and column set `C`, and let `S` be a subset of `R`.
Then the induced subgraph `G[S union C]` is also `K_{3,3}`-free.

*Proof.* A `K_{3,3}` in `G[S union C]` consists of three rows in `S` and
three columns in `C`, all nine pairs adjacent. Those same nine adjacencies
hold in `G`, since `G[S union C]` is an *induced* subgraph and `S` is a
subset of `R`. So it is a `K_{3,3}` in `G`, contradicting freeness. []

Hypotheses of the lemma, checked explicitly here rather than assumed:

1. `G` is `K_{3,3}`-free. Not taken on trust: every witness this module
   reads is re-verified by `checker.verify`, which cross-checks three
   independent `K_{3,3}` detectors and raises if they disagree.
2. `S` is a subset of the *row* side. This module only ever selects rows,
   never columns, so `C` is preserved intact and the column count `n` is
   unchanged. (Deleting columns is also sound, but it would change which
   `z(k,n;3)` cell the answer bounds, so it is deliberately not done.)
3. The subgraph is *induced* — we copy the selected rows verbatim rather
   than modifying entries.

Because edges are row-additive (each row's edges are disjoint from every
other row's), the edge count of `G[S union C]` is exactly `sum of the
degrees of the rows in S`. Hence, for each `k`, the best bound obtainable
from a given witness is the sum of its `k` largest row degrees.

**Conclusion.** For every witness `G` on `m x 17` and every `k <= m`,

    z(k,17;3)  >=  sum of the k largest row degrees of G.

## What this is NOT

These are *lower* bounds derived from *published* constructions, so they are
not new mathematics. Their value here is twofold, both of which the project
actually needs:

- Paired with an independently proved upper bound of the same value, they
  turn an inequality into an **exact value**. Every exactness claim this
  project makes needs its lower-bound half to come from a matrix we checked
  ourselves rather than from a citation, and this is that half.
- They **bound how much the upper-bound search can possibly achieve**. If
  this module reports `z(k,17;3) >= v`, then any exhaustive search claiming
  to refute `v` edges at that `k` has a bug. That has real operational
  value: it tells us in advance which `--decide` targets can possibly come
  back UNSAT, so we do not spend hours on a run whose answer is already
  determined.

## A caution against reading these as tight

The bounds are only as good as the witnesses. This module reports
`z(10,17;3) >= 86`, but this project separately *proved* `z(10,17;3) = 90`
by exhaustive search — the witnesses' 10-row subgraphs are four edges short
of optimal, because a witness optimised for `m = 14` or `15` need not
contain an optimal 10-row subgraph. So agreement between one of these
bounds and a conjectured value is evidence, not proof, and a gap between
this bound and an upper bound must not be read as "nearly closed".
"""

from __future__ import annotations

import csv
import itertools
import os
from pathlib import Path

from checker import verify

# Directory holding the re-verified witness matrices.
WITNESS_DIR = Path(__file__).resolve().parent.parent / "data" / "known_witnesses"

# The column count this module reports bounds for. Witnesses on a different
# number of columns bound a different cell and are skipped rather than
# silently mixed in.
N_COLS = 17


def load_matrix(path: os.PathLike | str) -> list[list[int]]:
    """Read a 0/1 CSV witness into a list of row lists."""
    with open(path, newline="") as fh:
        rows = [[int(x) for x in row] for row in csv.reader(fh) if row]
    if not rows:
        raise ValueError(f"{path}: empty matrix")
    width = len(rows[0])
    for i, row in enumerate(rows):
        if len(row) != width:
            raise ValueError(f"{path}: row {i} has {len(row)} entries, expected {width}")
        for x in row:
            if x not in (0, 1):
                raise ValueError(f"{path}: entry {x!r} is not 0 or 1")
    return rows


def best_k_row_subgraph(matrix: list[list[int]], k: int) -> tuple[int, tuple[int, ...]]:
    """Return (max edges, row indices) over all k-row induced subgraphs.

    Brute-forces every one of the C(m,k) subsets rather than assuming that
    taking the k highest-degree rows is optimal. It is optimal -- edges are
    row-additive, so the sum of degrees over a subset is maximised by the k
    largest degrees -- but the brute force costs nothing at these sizes and
    removes the need to trust that reasoning. `test_lower_bounds.py` asserts
    the two agree, which is the real check on the argument.
    """
    m = len(matrix)
    if not 1 <= k <= m:
        raise ValueError(f"k={k} out of range for a {m}-row matrix")
    best_edges = -1
    best_rows: tuple[int, ...] = ()
    for rows in itertools.combinations(range(m), k):
        edges = sum(sum(matrix[r]) for r in rows)
        if edges > best_edges:
            best_edges, best_rows = edges, rows
    return best_edges, best_rows


def bounds_from_witness(path: os.PathLike | str, k_min: int = 9) -> dict:
    """Verify one witness, then report its k-row subgraph lower bounds.

    Every reported bound is backed by a subgraph that is itself passed
    through `checker.verify`, so the claim rests on a checked matrix and not
    only on the lemma in this module's docstring. That is redundant given
    the lemma -- and deliberately so: it is a live cross-check that the
    lemma is being applied correctly, and it would fire if, say, this code
    ever accidentally selected columns instead of rows.
    """
    matrix = load_matrix(path)
    parent = verify(matrix)
    if not parent["is_k33_free"]:
        raise ValueError(f"{path}: witness is NOT K_3,3-free -- refusing to use it")
    m, n = parent["shape"]
    if n != N_COLS:
        raise ValueError(f"{path}: {n} columns, expected {N_COLS}")

    results = []
    for k in range(k_min, m + 1):
        edges, rows = best_k_row_subgraph(matrix, k)
        sub = [matrix[r] for r in rows]
        checked = verify(sub, expected_edges=edges)
        if not checked["is_k33_free"]:
            raise AssertionError(
                f"{path}: {k}-row subgraph on rows {rows} contains a K_3,3. "
                "This contradicts row-deletion monotonicity and means either "
                "the checker or this module is broken -- do not trust the bound."
            )
        results.append({"k": k, "edges": edges, "rows": rows})

    return {
        "path": str(path),
        "shape": (m, n),
        "edges": parent["edges"],
        "degrees": sorted((sum(r) for r in matrix), reverse=True),
        "bounds": results,
    }


def best_known_lower_bounds(witness_dir: os.PathLike | str = WITNESS_DIR) -> dict[int, int]:
    """Best lower bound on z(k,17;3) for each k, over all 17-column witnesses."""
    best: dict[int, int] = {}
    for name in sorted(os.listdir(witness_dir)):
        if not name.endswith(".csv"):
            continue
        matrix = load_matrix(Path(witness_dir) / name)
        if len(matrix[0]) != N_COLS:
            continue
        info = bounds_from_witness(Path(witness_dir) / name)
        for row in info["bounds"]:
            k, e = row["k"], row["edges"]
            if e > best.get(k, -1):
                best[k] = e
    return best


def main() -> None:
    print(f"Lower bounds on z(k,{N_COLS};3) from row-deletion of verified witnesses")
    print(f"witness directory: {WITNESS_DIR}\n")
    for name in sorted(os.listdir(WITNESS_DIR)):
        if not name.endswith(".csv"):
            continue
        matrix = load_matrix(WITNESS_DIR / name)
        if len(matrix[0]) != N_COLS:
            print(f"{name}: {len(matrix[0])} columns -- skipped (different cell)\n")
            continue
        info = bounds_from_witness(WITNESS_DIR / name)
        m, n = info["shape"]
        print(f"{name}: {m}x{n}, {info['edges']} edges, degrees={info['degrees']}")
        for row in info["bounds"]:
            print(f"    z({row['k']},{n};3) >= {row['edges']:3d}   rows={row['rows']}")
        print()
    print("Best over all witnesses:")
    for k, e in sorted(best_known_lower_bounds().items()):
        print(f"    z({k},{N_COLS};3) >= {e}")


if __name__ == "__main__":
    main()
