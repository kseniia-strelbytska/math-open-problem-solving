"""
Cross-check checker.py against literature-derived witness matrices whose
claimed values are independently traced in PROGRESS.md and
data/known_witnesses/SOURCES.md.

Per the project's working discipline ("ground the riskiest step in
something checkable"): these files were fetched from a third-party GitHub
repository, but this test does not trust that fetch -- it re-runs the
full independent checker pipeline against the raw matrix data and asserts
the result matches what was claimed, exactly like any other input to
checker.py. If any of these ever fails, that is a serious finding (either
our checker has a bug, or the third-party data/claim does not hold up)
and should stop all downstream work until resolved.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import checker  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "known_witnesses"

# (filename, claimed edge count) -- claimed values from SOURCES.md, traced
# back to arXiv:2608.08154 / arXiv:2608.08549 / the underlying GitHub repo.
KNOWN_WITNESSES = [
    ("z13_18_116_witness.csv", 116),
    ("z14_17_118_witness.csv", 118),
    ("z14_18_124_witness.csv", 124),
    ("z15_17_126_witness.csv", 126),
    ("z15_18_132_witness.csv", 132),
    ("z16_17_132_witness_seed201.csv", 132),  # our primary lower-bound witness
]


def _load_csv(path: Path) -> list[list[int]]:
    with open(path) as f:
        return [[int(x) for x in row] for row in csv.reader(f) if row]


def test_all_known_witnesses_verify():
    assert DATA_DIR.is_dir(), f"expected data directory at {DATA_DIR}"
    for fname, claimed_edges in KNOWN_WITNESSES:
        path = DATA_DIR / fname
        assert path.is_file(), f"missing known-witness file: {path}"
        rows = _load_csv(path)
        result = checker.check_against_known_exact_value(rows, published_value=claimed_edges)
        assert result["is_k33_free"] is True
        assert result["edges"] == claimed_edges


def test_primary_target_witness_shape_is_16x17():
    # The one witness this whole project's lower bound rests on: confirm
    # its shape matches the target cell Z(16,17,3,3), not just its edge
    # count -- a file swapped for a same-edge-count matrix of the wrong
    # shape would silently prove the wrong thing.
    path = DATA_DIR / "z16_17_132_witness_seed201.csv"
    rows = _load_csv(path)
    assert len(rows) == 16, f"expected 16 rows, got {len(rows)}"
    assert len(rows[0]) == 17, f"expected 17 columns, got {len(rows[0])}"
    result = checker.verify(rows, expected_edges=132)
    assert result["is_k33_free"] is True


if __name__ == "__main__":
    test_all_known_witnesses_verify()
    print("PASS  test_all_known_witnesses_verify")
    test_primary_target_witness_shape_is_16x17()
    print("PASS  test_primary_target_witness_shape_is_16x17")
