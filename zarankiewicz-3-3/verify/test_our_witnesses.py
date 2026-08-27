"""Re-verify the witnesses this project produced itself.

Separate from `test_known_witnesses.py`, which checks matrices copied from a
third party. These four came out of `search/orderly/orderly.c` in this
repository, so the thing being guarded against is different: not "did we
transcribe someone else's matrix correctly" but "does our own generator emit
what it claims to emit".

Every assertion here goes through `verify/checker.py`, which shares no code
with the generator and was merged before it.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from checker import verify

OUR_WITNESS_DIR = Path(__file__).resolve().parent.parent / "data" / "our_witnesses"

# cell -> (rows, cols, edges). These are the values EXACT_VALUES.md claims,
# hardcoded here on purpose: the file names alone could drift from the
# contents, and this pins the claim rather than the filename.
EXPECTED = {
    "z8_17_74.csv": (8, 17, 74),
    "z9_17_81.csv": (9, 17, 81),
    "z10_17_90.csv": (10, 17, 90),
    "z11_17_96.csv": (11, 17, 96),
    # Not an n=17 cell, and not from the generator: this one comes from the
    # Z_4 x Z_4 translate construction in verify/constructions.py, and it
    # establishes z(16,16;3) >= 128, which discharges Theorem B's hypothesis
    # in CHAIN_CEILING.md. Registered here because this file's
    # test_no_unexpected_witness_files guard requires every CSV in the
    # directory to carry an explicit claim -- and that guard is what caught its
    # omission. Its construction-specific properties (biregularity, membership
    # in the 96-solution family) are tested in test_constructions.py.
    "z16_16_128.csv": (16, 16, 128),
}


def load(path: Path) -> list[list[int]]:
    with open(path, newline="") as fh:
        rows = [[int(x) for x in row] for row in csv.reader(fh) if row]
    if not rows:
        raise ValueError(f"{path}: empty")
    width = len(rows[0])
    for i, row in enumerate(rows):
        if len(row) != width:
            raise ValueError(f"{path}: row {i} has width {len(row)}, expected {width}")
        for x in row:
            if x not in (0, 1):
                raise ValueError(f"{path}: entry {x!r} not 0/1")
    return rows


def test_all_expected_witnesses_are_present():
    """Guard against the parametrised tests passing vacuously."""
    present = {p.name for p in OUR_WITNESS_DIR.glob("*.csv")}
    missing = set(EXPECTED) - present
    assert not missing, f"missing witness files: {sorted(missing)}"


def test_no_unexpected_witness_files():
    """Every CSV in the directory must be one this file makes a claim about.

    Prevents a stray matrix sitting in the data directory looking official
    while no test covers it.
    """
    present = {p.name for p in OUR_WITNESS_DIR.glob("*.csv")}
    extra = present - set(EXPECTED)
    assert not extra, f"uncovered witness files: {sorted(extra)}"


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_witness_has_the_claimed_shape_and_edge_count_and_is_k33_free(name):
    """The whole lower-bound half of EXACT_VALUES.md, one cell at a time.

    `expected_edges` is passed explicitly rather than read off the matrix.
    That matters: an all-zero matrix is trivially K_{3,3}-free, so checking
    freeness alone would accept a vacuous "witness". This project actually
    produced such a matrix once, from a shell loop that passed an empty
    `--decide` argument, and the edge-count assertion is what caught it.
    """
    m, n, e = EXPECTED[name]
    matrix = load(OUR_WITNESS_DIR / name)
    res = verify(matrix, expected_edges=e)
    assert res["shape"] == (m, n)
    assert res["edges"] == e
    assert res["is_k33_free"] is True
    # All three detectors must have agreed -- verify() raises otherwise, but
    # assert it explicitly so the intent is visible in the test.
    assert set(res["methods"].values()) == {False}


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_witness_is_not_vacuous(name):
    """A witness must actually be dense enough to be interesting.

    Specifically: every row has positive degree, and the edge count is at
    least 4 per row on average. This rules out the degenerate matrices that
    pass a freeness check trivially.
    """
    m, n, e = EXPECTED[name]
    matrix = load(OUR_WITNESS_DIR / name)
    degrees = [sum(row) for row in matrix]
    assert all(d > 0 for d in degrees), f"{name} has an all-zero row"
    assert sum(degrees) == e
    assert e >= 4 * m, f"{name} is suspiciously sparse for a claimed extremal graph"


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_every_row_triple_shares_at_most_two_columns(name):
    """The K33-free condition, re-checked here from its definition.

    Deliberately re-derived in this file rather than delegating: a K_{3,3}
    is exactly three rows sharing three columns, so no row triple may have
    an intersection of size 3 or more. This is a fourth opinion on top of
    the checker's three, written from the definition rather than imported.
    """
    import itertools

    matrix = load(OUR_WITNESS_DIR / name)
    m = len(matrix)
    n = len(matrix[0])
    masks = [sum(1 << c for c in range(n) if matrix[r][c]) for r in range(m)]
    for a, b, c in itertools.combinations(range(m), 3):
        shared = (masks[a] & masks[b] & masks[c]).bit_count()
        assert shared <= 2, (
            f"{name}: rows {a},{b},{c} share {shared} columns -- that is a K_3,3"
        )


def test_degree_sequences_match_the_document():
    """Pins the degree sequences quoted in EXACT_VALUES.md.

    These are load-bearing in the document's argument that 74 breaks the
    `9k` pattern, so they should not be able to drift silently.
    """
    expected = {
        "z8_17_74.csv": [10, 10, 9, 9, 9, 9, 9, 9],
        "z9_17_81.csv": [9] * 9,
        "z10_17_90.csv": [9] * 10,
        "z11_17_96.csv": [9, 9, 9, 9, 9, 9, 9, 9, 8, 8, 8],
    }
    for name, degs in expected.items():
        matrix = load(OUR_WITNESS_DIR / name)
        got = sorted((sum(row) for row in matrix), reverse=True)
        assert got == degs, f"{name}: degrees {got}, document says {degs}"


def test_74_is_two_above_the_9k_line():
    """The specific arithmetic the document flags as worth chasing.

    z(8,17;3) = 74 while 9*8 = 72, so this cell sits two above the pattern
    that holds at k=9 and k=10. Asserted so the observation stays true.
    """
    matrix = load(OUR_WITNESS_DIR / "z8_17_74.csv")
    edges = sum(sum(row) for row in matrix)
    assert edges == 74
    assert edges - 9 * 8 == 2


def test_provenance_labels_match_the_actual_literature_file():
    """A [CITED] label must be true of LITERATURE.md as it stands right now.

    This test exists because the same defect occurred three times. A provenance
    label is a claim about repository *state*, so it goes stale precisely when
    the repository changes -- and that is the one moment nobody re-reads it.
    Concretely: these rows were labelled [CITED, NOT LANDED] on the grounds
    that LITERATURE.md did not record them. That was true when written, then
    the literature PR landed those exact cells (written by the same author),
    and the label was never revisited. A reviewer refuted it with a grep.

    So: for every cell this document labels [CITED], LITERATURE.md must
    actually contain it. And the document must not claim any of them is absent.
    """
    root = Path(__file__).resolve().parent.parent
    lit = (root / "LITERATURE.md").read_text()
    doc = (root / "EXACT_VALUES.md").read_text()

    # Cells EXACT_VALUES.md presents as [CITED] must be present in LITERATURE.md.
    for cell, value in (("z(9,17;3)", "81"), ("z(10,17;3)", "90"),
                        ("z(11,17;3)", "96")):
        assert cell in lit, f"{cell} labelled [CITED] but absent from LITERATURE.md"
        # and with the right value on the same line
        line = next(l for l in lit.splitlines() if cell in l and value in l)
        assert value in line, f"{cell} in LITERATURE.md without value {value}"

    # The stale scope sentence must not come back.
    forbidden = [
        "covers the `k >= 13` cells and the `(16,17)` cell only",
        "none of them is recorded in this repo's `LITERATURE.md`",
    ]
    for phrase in forbidden:
        idx = doc.find(phrase)
        while idx != -1:
            window = doc[max(0, idx - 500):idx + 300]
            assert ("was false" in window or "Correction" in window
                    or "earlier version" in window), (
                f"EXACT_VALUES.md asserts {phrase!r} without marking it as a "
                "retracted claim -- LITERATURE.md does record those cells"
            )
            idx = doc.find(phrase, idx + 1)


def test_cross_check_sweep_range_is_stated_consistently():
    """Every statement of the sweep range must match the Makefile.

    A prior round flagged '6..20' against the Makefile's actual '6..24'. That
    fix patched only the GitHub PR description, leaving the landed file wrong
    -- the same 'fixed the site I was pointed at' failure this project keeps
    hitting. Pinned here so the file and the Makefile cannot drift.
    """
    root = Path(__file__).resolve().parent.parent
    makefile = (root / "search" / "orderly" / "Makefile").read_text()
    targets = [t for t in ("6", "8", "10", "12", "14", "16", "18", "20", "24")
               if t in makefile]
    assert "24" in targets, "Makefile no longer sweeps up to 24"
    n_cells = 4 * 4 * len(targets)
    for fname in ("EXACT_VALUES.md", "search/orderly/SOUNDNESS.md"):
        text = (root / fname).read_text()
        if "cross-check" not in text:
            continue
        assert "6..20" not in text, f"{fname} still says targets 6..20"
        if "144 cells" in text:
            assert n_cells == 144, (
                f"Makefile now yields {n_cells} cells but {fname} says 144"
            )
