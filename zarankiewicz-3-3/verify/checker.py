"""
Independent K_{3,3}-freeness / edge-count checker for the Z(16,17,3,3)
problem (and small test cases of the same shape).

Design goal (per zarankiewicz-3-3/README.md, "Independent verification"):
this module must be trustworthy on its own, without relying on whatever
code generated a candidate matrix. It answers exactly one question:

    Given an m x n 0/1 matrix, does it have exactly N ones, and does it
    contain a K_{3,3} (3 rows and 3 columns that are all 1 -- i.e. 3
    vertices on the row side and 3 vertices on the column side that are
    pairwise fully connected)?

To avoid a single bug silently producing a wrong "yes/no", the K_{3,3}
check is implemented THREE separate, structurally different ways, and the
public API (`verify`) requires all three to agree -- any disagreement is
raised loudly as an AssertionError/RuntimeError rather than resolved by
picking a "trusted" method. Likewise edge-counting is done two
structurally different ways.

Method 1 (`has_k33_row_triples`): iterate over all C(m,3) row-triples;
    for each, intersect the three rows' 1-columns; if >=3 columns survive,
    a K_{3,3} exists. Traverses "row-major".

Method 2 (`has_k33_col_triples`): the dual, transposed formulation --
    iterate over all C(n,3) column-triples; for each, intersect the three
    columns' 1-rows; if >=3 rows survive, a K_{3,3} exists. Traverses
    "column-major" over an actually-transposed array, so a transposition
    or axis off-by-one bug in one method is very unlikely to be mirrored
    in the other.

Method 3 (`has_k33_networkx`): build the actual bipartite graph as a
    networkx.Graph (independent library, independent adjacency
    representation -- adjacency dict / neighbor views, not raw array
    indexing), then check row-triples against networkx's own neighbor
    sets. Serves as a tie-breaker / library sanity cross-check: even
    though it enumerates the same row-triples as Method 1, it never reads
    the numpy array directly once the graph is built, so a numpy indexing
    bug in Method 1 would not be reproduced here.

Edge counting is done via `count_ones_numpy` (numpy .sum()) and
`count_ones_manual` (explicit Python-int double loop, immune to any
numpy dtype/overflow surprise -- moot at 16x17 scale, but free to check).

KNOWN LIMITATION -- read this before trusting the three-way agreement.
All three methods above test the same underlying mathematical fact:

    a K_{3,3} exists  <=>  some 3 rows have >= 3 columns in common
                      <=>  some 3 columns have >= 3 rows in common

Methods 1 and 3 both enumerate row-triples; Method 2 is the transposed
dual. They are independent in *implementation* -- different libraries,
different data structures, different traversal order -- which is what
catches an indexing, axis, or off-by-one bug in any one of them. They are
NOT independent in the *mathematics*: if the characterisation above were
itself wrong, all three would be wrong together and their agreement would
prove nothing. Their agreement is therefore evidence about the code, not
about the lemma.

What actually guards the lemma is external to this file: the test suite
carries a fourth, deliberately code-independent brute-force ground truth
(plain Python, no numpy, no networkx, written from the definition of a
complete bipartite subgraph rather than from the characterisation above)
and cross-checks it against this module over hundreds of random matrices.
A reviewer wanting to attack this module's correctness should attack that
lemma and that fourth implementation, not the three-way agreement.
"""

from __future__ import annotations

import itertools
from typing import Sequence

import numpy as np

try:
    import networkx as nx
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "networkx is required by verify/checker.py's Method 3 cross-check; "
        "install it in the project venv (see SETUP.md)."
    ) from exc


MatrixLike = "np.ndarray | Sequence[Sequence[int]] | Sequence[int]"


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def normalize_matrix(matrix: MatrixLike, n_cols: int | None = None) -> np.ndarray:
    """
    Normalize an input matrix representation into a 2D numpy array of
    dtype uint8 containing only 0/1 entries.

    Accepted input forms:
      - a 2D numpy array (or anything np.asarray can turn into one), with
        entries that are 0/1 (or booleans, or any values equal to 0 or 1
        after int conversion).
      - a list of lists of 0/1 (row-major).
      - a list of row-bitmasks (python ints), where bit j of row i encodes
        whether column j is a 1 in row i (bit 0 = column 0, i.e. the
        least-significant bit is the first column). Because a bitmask does
        not reveal trailing zero columns, `n_cols` MUST be supplied
        explicitly in this case -- we refuse to guess the intended width
        of the graph from the data, since silently guessing wrong (e.g.
        inferring 16 columns when the real graph is 17 wide because the
        last column happened to be all-zero) is exactly the kind of
        silent bug this checker exists to prevent.

    Raises ValueError if the input contains anything other than 0/1
    entries, or if a bitmask list is given without n_cols.
    """
    arr = np.asarray(matrix)

    if arr.dtype == object or arr.ndim == 1:
        # Could be a list of row-bitmasks (ints) -- 1D array of python ints.
        if arr.ndim == 1 and all(isinstance(x, (int, np.integer)) for x in np.asarray(matrix)):
            if n_cols is None:
                raise ValueError(
                    "Row-bitmask input requires an explicit n_cols argument "
                    "(bitmasks cannot reveal trailing all-zero columns)."
                )
            rows = list(matrix)
            m = len(rows)
            out = np.zeros((m, n_cols), dtype=np.uint8)
            for i, bits in enumerate(rows):
                if bits < 0 or bits >= (1 << n_cols):
                    raise ValueError(
                        f"row {i} bitmask {bits!r} does not fit in n_cols={n_cols} bits"
                    )
                for j in range(n_cols):
                    out[i, j] = (bits >> j) & 1
            return out
        else:
            raise ValueError(f"Could not interpret matrix input of dtype {arr.dtype!r}")

    if arr.ndim != 2:
        raise ValueError(f"Expected a 2D matrix, got array of shape {arr.shape}")

    # Validate strictly 0/1 (allow bool arrays too).
    if arr.dtype == bool:
        out = arr.astype(np.uint8)
    else:
        int_arr = arr.astype(np.int64)
        if not np.array_equal(int_arr, arr.astype(np.float64)):
            raise ValueError("Matrix entries must be integers (0/1)")
        bad = ~np.isin(int_arr, [0, 1])
        if bad.any():
            bad_vals = np.unique(int_arr[bad])
            raise ValueError(f"Matrix must be strictly 0/1; found other values: {bad_vals}")
        out = int_arr.astype(np.uint8)

    if n_cols is not None and out.shape[1] != n_cols:
        raise ValueError(f"Matrix has {out.shape[1]} columns, expected n_cols={n_cols}")

    return out


# ---------------------------------------------------------------------------
# Edge counting -- two independent implementations
# ---------------------------------------------------------------------------

def count_ones_numpy(matrix: np.ndarray) -> int:
    """Edge count via numpy's vectorized sum."""
    return int(np.asarray(matrix).astype(np.int64).sum())


def count_ones_manual(matrix: np.ndarray) -> int:
    """
    Edge count via an explicit Python-int double loop over every cell.
    Deliberately avoids numpy accumulation entirely (uses a plain Python
    int accumulator, which has unbounded precision) so it cannot suffer
    from any numpy dtype/overflow surprise, however implausible at 16x17
    scale. Structurally the simplest possible independent count.
    """
    m, n = matrix.shape
    total = 0
    for i in range(m):
        for j in range(n):
            v = int(matrix[i, j])
            if v not in (0, 1):
                raise ValueError(f"Non-0/1 entry at ({i},{j}): {v!r}")
            total += v
    return total


# ---------------------------------------------------------------------------
# K_{3,3} detection -- three independent implementations
# ---------------------------------------------------------------------------

def has_k33_row_triples(matrix: np.ndarray) -> bool:
    """
    Method 1 ("row-triple" formulation): for every triple of rows, compute
    the set of columns that are 1 in all three rows. If that set has size
    >= 3, those 3 rows together with any 3 of those columns form a
    K_{3,3}.
    """
    m, n = matrix.shape
    bool_mat = matrix.astype(bool)
    for r0, r1, r2 in itertools.combinations(range(m), 3):
        common = bool_mat[r0] & bool_mat[r1] & bool_mat[r2]
        if int(common.sum()) >= 3:
            return True
    return False


def has_k33_col_triples(matrix: np.ndarray) -> bool:
    """
    Method 2 ("column-triple" formulation, dual/transposed): for every
    triple of columns, compute the set of rows that are 1 in all three
    columns. If that set has size >= 3, those 3 columns together with any
    3 of those rows form a K_{3,3}.

    This deliberately operates on the TRANSPOSE of the matrix and iterates
    over columns-as-if-rows, so an axis-order or off-by-one bug that
    happened to affect Method 1 would need to independently also affect
    the transposed traversal here to go undetected -- structurally a
    different code path, not just a renamed copy of Method 1.
    """
    transposed = matrix.T  # now shape (n, m): "rows" of this array are the original columns
    n, m = transposed.shape
    bool_mat = transposed.astype(bool)
    for c0, c1, c2 in itertools.combinations(range(n), 3):
        common = bool_mat[c0] & bool_mat[c1] & bool_mat[c2]
        if int(common.sum()) >= 3:
            return True
    return False


def _build_bipartite_graph(matrix: np.ndarray) -> "nx.Graph":
    """Build the bipartite graph corresponding to `matrix` as a networkx.Graph."""
    m, n = matrix.shape
    G = nx.Graph()
    row_nodes = [("row", i) for i in range(m)]
    col_nodes = [("col", j) for j in range(n)]
    G.add_nodes_from(row_nodes, bipartite=0)
    G.add_nodes_from(col_nodes, bipartite=1)
    ones = np.argwhere(matrix.astype(bool))
    for i, j in ones:
        G.add_edge(("row", int(i)), ("col", int(j)))
    return G


def has_k33_networkx(matrix: np.ndarray) -> bool:
    """
    Method 3 (networkx cross-check): build the actual bipartite graph with
    networkx, then for every triple of row-nodes, intersect their
    neighbor sets (obtained via G.neighbors(), networkx's own adjacency
    machinery -- not by re-reading the numpy array). If the intersection
    has size >= 3, a K_{3,3} exists.

    This is intentionally similar in *shape* to Method 1 (it also
    enumerates row-triples), but it is a genuinely independent code path:
    once the graph is built, it never touches the numpy array again, so
    it cannot reproduce a numpy-indexing bug from Method 1, and it
    exercises an entirely different library (networkx's dict-of-sets
    adjacency representation) as an independent sanity check on the graph
    construction itself.
    """
    G = _build_bipartite_graph(matrix)
    m, n = matrix.shape
    row_nodes = [("row", i) for i in range(m)]
    for r0, r1, r2 in itertools.combinations(row_nodes, 3):
        common = set(G.neighbors(r0)) & set(G.neighbors(r1)) & set(G.neighbors(r2))
        if len(common) >= 3:
            return True
    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class CheckerDisagreement(AssertionError):
    """Raised when the independent methods disagree. This should never be
    silently swallowed -- a disagreement means there is a bug in at least
    one method (or in matrix normalization) and any claimed result must
    be treated as unverified until resolved."""


def verify(
    matrix: MatrixLike,
    expected_edges: int | None = None,
    n_cols: int | None = None,
) -> dict:
    """
    The main entry point. Normalizes `matrix`, then:
      1. Counts edges two independent ways and asserts they agree (and,
         if `expected_edges` is given, that the count matches it).
      2. Checks K_{3,3}-freeness three independent ways and asserts all
         three agree.

    Returns a dict:
        {
          "shape": (m, n),
          "edges": int,
          "has_k33": bool,
          "is_k33_free": bool,
          "methods": {"row_triples": bool, "col_triples": bool, "networkx": bool},
        }

    Raises CheckerDisagreement if the independent methods disagree with
    each other, or ValueError if expected_edges is given and doesn't
    match, or if the matrix is malformed. This function is deliberately
    conservative: it never returns a result when its own internal checks
    disagree.
    """
    M = normalize_matrix(matrix, n_cols=n_cols)
    m, n = M.shape

    e_numpy = count_ones_numpy(M)
    e_manual = count_ones_manual(M)
    if e_numpy != e_manual:
        raise CheckerDisagreement(
            f"Edge count methods disagree: numpy={e_numpy} manual={e_manual}"
        )
    if expected_edges is not None and e_numpy != expected_edges:
        raise ValueError(
            f"Matrix has {e_numpy} edges, expected {expected_edges}"
        )

    r1 = has_k33_row_triples(M)
    r2 = has_k33_col_triples(M)
    r3 = has_k33_networkx(M)
    if not (r1 == r2 == r3):
        raise CheckerDisagreement(
            f"K_3,3 detection methods disagree on a {m}x{n} matrix with "
            f"{e_numpy} edges: row_triples={r1} col_triples={r2} networkx={r3}. "
            "This indicates a bug -- do not trust any single method's answer."
        )

    return {
        "shape": (m, n),
        "edges": e_numpy,
        "has_k33": r1,
        "is_k33_free": not r1,
        "methods": {"row_triples": r1, "col_triples": r2, "networkx": r3},
    }


def is_k33_free(matrix: MatrixLike, n_cols: int | None = None) -> bool:
    """Convenience wrapper around verify() returning just the K_{3,3}-free verdict."""
    return verify(matrix, n_cols=n_cols)["is_k33_free"]


def edge_count(matrix: MatrixLike, n_cols: int | None = None) -> int:
    """Convenience wrapper returning just the (double-checked) edge count."""
    return verify(matrix, n_cols=n_cols)["edges"]


# ---------------------------------------------------------------------------
# Known-value cross-check helper.
#
# This is a thin convenience wrapper over verify(); it is fully functional as
# it stands and carries no dependency on any data outside this file. No
# witness data ships in this commit -- the matrices it is intended to be
# pointed at, and the test that does so, are added separately (see the
# project charter's dependency-order rule). Nothing here claims to have been
# run against them yet.
# ---------------------------------------------------------------------------

def check_against_known_exact_value(matrix: MatrixLike, published_value: int, n_cols: int | None = None) -> dict:
    """
    Verify `matrix` reproduces a published exact Zarankiewicz value: raises
    unless `matrix` is K_{3,3}-free with exactly `published_value` edges.
    Returns the underlying `verify()` result dict on success.

    This does not "trust" the word "published" in any way -- it runs the
    exact same independent verify() pipeline as every other matrix checked
    by this module. What makes a call "a known-value cross-check" rather
    than an ordinary verification is purely how the caller uses the
    result, not anything special this function does internally.
    """
    result = verify(matrix, expected_edges=published_value, n_cols=n_cols)
    if result["has_k33"]:
        raise CheckerDisagreement(
            f"Matrix claimed to witness Zarankiewicz value {published_value} "
            f"actually contains a K_3,3 -- the claimed value is wrong or the "
            f"matrix does not match its source."
        )
    return result
