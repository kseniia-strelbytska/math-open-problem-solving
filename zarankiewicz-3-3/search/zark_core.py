"""
Shared core for the local-search / constructive attack on Z(16,17,3,3).

This module is NOT the arbiter of correctness -- verify/checker.py is (see
README.md, "Independent verification": "No single script is allowed to
both generate and certify a result"). Everything in here is search-side
bookkeeping: a fast *incremental* K_{3,3}-conflict tracker used as the SA
energy function, plus I/O helpers. Any candidate this module's search
reports as "0 conflicts" MUST be re-checked with verify.checker.verify()
before being believed -- see `certify()` below, which is the only function
in this file that touches the real checker, and which every search script
calls before reporting a result.

Incremental conflict model
---------------------------
Represent each row as a Python int bitmask over the 17 columns (bit j =
column j). For a fixed triple of rows (r_i, r_j, r_k), a K_{3,3} exists on
that triple iff popcount(r_i & r_j & r_k) >= 3 (any 3 of those common
columns complete the K_{3,3} -- see checker.py's docstring for the same
lemma, verified there independently). Define the "conflict energy" of a
triple as max(0, popcount(r_i & r_j & r_k) - 2): 0 if safe, and growing
with how far over the K_{3,3} threshold the triple is (this gives the
annealer gradient information, not just a 0/1 signal). Total energy is the
sum over all C(m,3) row-triples.

Toggling a single cell (i, j) only changes triples that include row i
(C(m-1, 2) of them for m=16, i.e. 105). So a toggle is done by first
subtracting each such triple's OLD contribution, flipping the bit, then
adding back each triple's NEW contribution -- O(m^2) per toggle, not
O(m^3), and no full rescan.
"""
from __future__ import annotations

import csv
import itertools
import pathlib
import random
import sys
from dataclasses import dataclass, field

import numpy as np

_HERE = pathlib.Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from verify import checker as _checker  # noqa: E402

M_ROWS = 16
N_COLS = 17
TARGET_EDGES = 133

KNOWN_WITNESS_PATH = _REPO_ROOT / "data" / "known_witnesses" / "z16_17_132_witness_seed201.csv"


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_matrix_csv(path) -> np.ndarray:
    with open(path) as f:
        rows = list(csv.reader(f))
    rows = [r for r in rows if r]  # drop blank lines
    return np.array(rows, dtype=int)


def save_matrix_csv(matrix: np.ndarray, path) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        for row in matrix:
            w.writerow(int(x) for x in row)


def matrix_to_rowmasks(matrix: np.ndarray) -> list[int]:
    m, n = matrix.shape
    rows = []
    for i in range(m):
        mask = 0
        for j in range(n):
            if matrix[i, j]:
                mask |= 1 << j
        rows.append(mask)
    return rows


def rowmasks_to_matrix(rows: list[int], n_cols: int = N_COLS) -> np.ndarray:
    m = len(rows)
    out = np.zeros((m, n_cols), dtype=np.uint8)
    for i, mask in enumerate(rows):
        for j in range(n_cols):
            if (mask >> j) & 1:
                out[i, j] = 1
    return out


def load_known_witness_rowmasks() -> list[int]:
    M = load_matrix_csv(KNOWN_WITNESS_PATH)
    assert M.shape == (16, 17), f"unexpected witness shape {M.shape}"
    assert int(M.sum()) == 132, f"unexpected witness edge count {int(M.sum())}"
    return matrix_to_rowmasks(M)


# ---------------------------------------------------------------------------
# Certification -- the only bridge to the real checker
# ---------------------------------------------------------------------------

def certify(rows: list[int], n_cols: int = N_COLS, expected_edges: int | None = None) -> dict:
    """
    Run the candidate through the REAL, independent checker
    (verify/checker.py). This is the only trust boundary in this file --
    every search script must call this before reporting a "0 conflict"
    result as real. Returns the checker's result dict; raises
    CheckerDisagreement if the checker's own internal methods disagree
    (which would itself be news -- see task instructions).
    """
    M = rowmasks_to_matrix(rows, n_cols=n_cols)
    return _checker.verify(M, expected_edges=expected_edges)


# ---------------------------------------------------------------------------
# Incremental K_{3,3}-conflict state
# ---------------------------------------------------------------------------

class IncrementalState:
    """
    Tracks a 16x17 0/1 matrix as row-bitmasks, with an incrementally
    maintained conflict energy (see module docstring) and edge count.
    This is SEARCH-SIDE bookkeeping only -- never trusted as a final
    verdict, only as an SA objective. See certify() for the real check.
    """

    __slots__ = ("m", "n", "rows", "energy", "edges", "_triple_pairs")

    def __init__(self, rows: list[int], n_cols: int = N_COLS):
        self.m = len(rows)
        self.n = n_cols
        self.rows = list(rows)
        # Precompute, for each row index i, the list of (a, b) pairs of
        # OTHER row indices (a < b, a != i, b != i) -- these are exactly
        # the triples affected by toggling a cell in row i.
        all_idx = list(range(self.m))
        self._triple_pairs: list[list[tuple[int, int]]] = []
        for i in all_idx:
            others = [x for x in all_idx if x != i]
            self._triple_pairs.append(list(itertools.combinations(others, 2)))

        self.edges = sum(bin(r).count("1") for r in self.rows)
        self.energy = self._full_energy()

    def _full_energy(self) -> int:
        e = 0
        for i, j, k in itertools.combinations(range(self.m), 3):
            c = (self.rows[i] & self.rows[j] & self.rows[k]).bit_count()
            if c > 2:
                e += c - 2
        return e

    def clone(self) -> "IncrementalState":
        new = IncrementalState.__new__(IncrementalState)
        new.m = self.m
        new.n = self.n
        new.rows = list(self.rows)
        new.energy = self.energy
        new.edges = self.edges
        new._triple_pairs = self._triple_pairs  # shared, read-only
        return new

    def conflict_triples(self) -> list[tuple[int, int, int]]:
        """Full (non-incremental) list of currently-violating row-triples.
        Only used for diagnostics / repair heuristics, not the hot loop."""
        out = []
        for i, j, k in itertools.combinations(range(self.m), 3):
            c = (self.rows[i] & self.rows[j] & self.rows[k]).bit_count()
            if c > 2:
                out.append((i, j, k))
        return out

    def toggle(self, i: int, j: int) -> int:
        """
        Flip cell (i, j). Returns the change in energy (new_energy -
        old_energy). Updates self.energy and self.edges in place.
        O(m^2) (105 pair-lookups for m=16), not O(m^3).
        """
        bit = 1 << j
        old_row_i = self.rows[i]
        pairs = self._triple_pairs[i]

        delta = 0
        for a, b in pairs:
            common = old_row_i & self.rows[a] & self.rows[b]
            c = common.bit_count()
            if c > 2:
                delta -= c - 2

        turning_on = not (old_row_i & bit)
        new_row_i = old_row_i ^ bit
        self.rows[i] = new_row_i

        for a, b in pairs:
            common = new_row_i & self.rows[a] & self.rows[b]
            c = common.bit_count()
            if c > 2:
                delta += c - 2

        self.energy += delta
        self.edges += 1 if turning_on else -1
        return delta

    def is_set(self, i: int, j: int) -> bool:
        return bool(self.rows[i] & (1 << j))

    def as_matrix(self) -> np.ndarray:
        return rowmasks_to_matrix(self.rows, n_cols=self.n)


def assert_incremental_matches_full(state: IncrementalState) -> None:
    """Sanity check: incremental energy/edge bookkeeping matches a full
    from-scratch recompute. Used in self-tests and periodically during
    long runs to catch incremental-update bugs early."""
    full_e = state._full_energy()
    full_edges = sum(bin(r).count("1") for r in state.rows)
    if full_e != state.energy or full_edges != state.edges:
        raise RuntimeError(
            f"Incremental bookkeeping drift detected: "
            f"energy incremental={state.energy} full={full_e}, "
            f"edges incremental={state.edges} full={full_edges}"
        )


if __name__ == "__main__":
    # Minimal self-test: load the known witness, confirm 132 edges / 0
    # conflicts via the incremental tracker, cross-check against certify().
    rows = load_known_witness_rowmasks()
    st = IncrementalState(rows)
    print(f"witness: edges(incremental)={st.edges} energy(incremental)={st.energy}")
    assert st.edges == 132
    assert st.energy == 0, "known witness should have 0 conflict energy"

    # Randomized incremental-vs-full consistency check.
    rng = random.Random(12345)
    for trial in range(2000):
        i = rng.randrange(M_ROWS)
        j = rng.randrange(N_COLS)
        st.toggle(i, j)
        if trial % 200 == 0:
            assert_incremental_matches_full(st)
    assert_incremental_matches_full(st)
    print("2000 random toggles: incremental bookkeeping matches full recompute. OK.")

    res = certify(rows, expected_edges=132)
    print("checker.verify on known witness:", res)
    assert res["is_k33_free"] and res["edges"] == 132
    print("Self-test passed.")
