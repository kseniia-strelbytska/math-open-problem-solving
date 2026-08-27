"""Tests for verify/chain_ceiling.py.

The module states a *negative* result, which is a genre that fails in its own
particular way: a negative result is easy to state too broadly, and no amount
of testing the arithmetic catches an overbroad statement. So the tests here
split into three groups:

  1. The arithmetic (`density_ceiling`, the search window, monotonicity).
  2. The lemma the arithmetic encodes, checked against brute force on small
     cells rather than against itself.
  3. The theorem's own hypotheses -- in particular that the witness it rests
     on is real, and that the ceiling is genuinely *attained* so the result
     is sharp rather than merely an inequality.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

import chain_ceiling as cc
from checker import verify
import lower_bounds as lb


# ---------------------------------------------------------------- arithmetic

def test_density_ceiling_matches_its_definition_by_brute_force():
    """density_ceiling(B,m) really is max{e : e - floor(e/m) <= B}."""
    for m in range(2, 20):
        for B in range(0, 140):
            got = cc.density_ceiling(B, m)
            # Independently: scan a much wider window and take the max.
            admissible = [e for e in range(0, B + 40 * m + 100) if e - e // m <= B]
            assert got == max(admissible), (m, B, got, max(admissible))


def test_search_window_never_binds():
    """The answer is never the top of the window -- so the window is not the answer.

    This test found a genuine bug. The original window was a fixed
    `B + 4m + 8`, which is correct at m=16 (the only m the project uses) but
    truncates the answer for every B > 15 at m=2, where the true answer is
    2B. The window is now derived from `e - floor(e/m) >= e(m-1)/m`, and this
    test sweeps m down to 2 so a window that is right only in the cell we
    care about cannot pass.
    """
    for m in range(2, 20):
        for B in range(0, 140):
            got = cc.density_ceiling(B, m)
            window_top = B * m // (m - 1) + m + 2
            assert got < window_top, f"window bound reached at m={m} B={B}"


def test_density_ceiling_is_nondecreasing_in_its_input():
    """Monotonicity in B, which the theorem's proof uses explicitly."""
    for m in range(2, 20):
        prev = -1
        for B in range(0, 140):
            got = cc.density_ceiling(B, m)
            assert got >= prev
            prev = got


def test_density_ceiling_rejects_degenerate_m():
    with pytest.raises(ValueError):
        cc.density_ceiling(100, 0)
    with pytest.raises(ValueError):
        cc.density_ceiling(100, -3)


def test_density_ceiling_rejects_vacuous_m_equals_1():
    """m=1 must raise, not return a number.

    This test earned its place. `e - floor(e/1) = 0` for every e, so the set
    {e : e - floor(e/1) <= B} is unbounded and has no maximum. The first
    version of `density_ceiling` accepted m=1 and returned the top of its own
    internal search window -- a value produced by an implementation detail
    rather than by mathematics. A function that answers a question with no
    answer is worse than one that raises, because the caller cannot tell.
    """
    with pytest.raises(ValueError, match="vacuous"):
        cc.density_ceiling(100, 1)
    # And confirm the underlying reason, so the test documents the maths.
    for e in (0, 1, 50, 1000):
        assert e - e // 1 == 0


def test_max_input_for_target_is_the_inverse():
    """max_input_for_target inverts density_ceiling, at the boundary too."""
    for m in range(2, 20):
        for target in range(m, 140):
            B = cc.max_input_for_target(target, m)
            if B is None:
                continue
            assert cc.density_ceiling(B, m) <= target
            # And it is maximal: one more input overshoots the target.
            assert cc.density_ceiling(B + 1, m) > target


# --------------------------------------------------------------- the lemma

def _brute_force_z(m: int, n: int) -> int:
    """Exhaustive z(m,n;3) for tiny m,n, over all 2^(mn) matrices.

    Deliberately the dumbest possible implementation, using the checker as
    the K33 oracle. Only viable for m*n <= 12 or so; that is enough to
    validate the lemma the whole module encodes.
    """
    best = 0
    for bits in range(1 << (m * n)):
        matrix = [[(bits >> (r * n + c)) & 1 for c in range(n)] for r in range(m)]
        res = verify(matrix)
        if not res["has_k33"]:
            best = max(best, res["edges"])
    return best


@pytest.mark.parametrize("n", [3, 4])
def test_density_lemma_holds_against_brute_forced_small_values(n):
    """The inference rule is SOUND on cells small enough to solve exactly.

    For each such cell, the bound the lemma licenses from the true value one
    level down must actually hold. This is the test that would catch an
    off-by-one in the rule itself -- something no amount of self-consistent
    arithmetic testing can find.
    """
    values = {m: _brute_force_z(m, n) for m in range(1, 4)}
    for m in range(2, 4):
        licensed = cc.density_ceiling(values[m - 1], m)
        assert values[m] <= licensed, (
            f"density lemma VIOLATED at ({m},{n}): true z={values[m]} "
            f"but lemma licenses only <= {licensed}"
        )


def test_density_lemma_is_sound_on_the_cells_this_project_proved():
    """z(10,17) = 90 must satisfy the bound licensed by z(9,17) = 81."""
    licensed = cc.density_ceiling(cc.PROVED_HERE[9], 10)
    assert cc.PROVED_HERE[10] <= licensed
    # And here the lemma happens to be exactly tight, which the log claims.
    assert cc.PROVED_HERE[10] == licensed


# ------------------------------------------------------------- the theorem

def test_the_witness_the_theorem_rests_on_is_real():
    """z(15,17) >= 126 is backed by a matrix, not by a remembered number.

    If this fails, the theorem has no proof -- so it is checked directly
    against the CSV rather than against the module's constant.
    """
    path = lb.WITNESS_DIR / "z15_17_126_witness.csv"
    assert path.exists(), f"missing witness: {path}"
    with open(path, newline="") as fh:
        matrix = [[int(x) for x in row] for row in csv.reader(fh) if row]
    res = verify(matrix, expected_edges=126)
    assert res["is_k33_free"]
    assert res["shape"] == (15, 17)
    assert res["edges"] >= cc.VERIFIED_LOWER_BOUND_15_17


def test_theorem_133_is_unreachable_by_the_chain():
    """The negative result itself."""
    t = cc.theorem_133_unreachable()
    assert t["required_bound_on_z15_17"] == 125
    assert t["verified_lower_bound_on_z15_17"] == 126
    assert t["required_bound_is_false"] is True


def test_the_chain_ceiling_is_134_and_is_attained():
    """Sharpness. Without this the result is just an inequality.

    134 must be reachable (so the ceiling is real and not merely an upper
    estimate of what the chain can do) and 133 must not be.
    """
    assert cc.density_ceiling(126, 16) == 134
    assert cc.density_ceiling(125, 16) == 133
    # Sharp in the other direction too: 126 is exactly the crossover.
    assert cc.density_ceiling(127, 16) == 135


def test_theorem_is_robust_to_the_route_taken_below_level_15():
    """The result does not depend on HOW the chain reaches level 15.

    The proof only uses that the last step happens at m=16 and needs
    B <= 125. This sweeps every conceivable level-15 input and confirms that
    the only ones reaching 133 are the false ones.
    """
    for B in range(1, 200):
        reaches_133 = cc.density_ceiling(B, 16) <= 133
        is_true_bound = B >= cc.VERIFIED_LOWER_BOUND_15_17
        assert not (reaches_133 and is_true_bound), (
            f"B={B} both reaches 133 and is a true bound -- theorem is WRONG"
        )


def test_theorem_would_fail_loudly_if_the_witness_were_weaker():
    """Guards against the theorem quietly surviving a bad premise.

    If z(15,17) >= 126 were ever retracted down to 125, the theorem would
    become false. Asserting that here documents the exact dependency, so the
    result cannot drift into looking stronger than its premise.
    """
    assert cc.density_ceiling(125, 16) == 133, (
        "with only z(15,17) >= 125 the chain WOULD reach 133 -- the theorem "
        "depends entirely on the 126-edge witness"
    )


def test_column_route_IS_now_blocked_by_our_own_data():
    """Theorem B is unconditional. This test previously asserted the opposite.

    Its earlier form asserted `blocked_by_our_own_data is False`, recording
    that our own 16x16 bound (126) was exactly one edge short of the 127
    Theorem B needs. The docstring said: "if someone later strengthens the
    16x16 lower bound to 127, this test fails and forces CHAIN_CEILING.md to
    be updated to claim the stronger, unconditional result -- rather than the
    repo silently holding a proof it no longer states."

    That is exactly what happened. The Z_4 x Z_4 translate construction in
    verify/constructions.py gives z(16,16;3) >= 128, the test failed, and the
    document was upgraded. Recorded here because a test designed to fail on
    good news actually doing so is the mechanism working as intended -- and
    this project has had several claims go stale precisely because nothing
    forced a re-read.
    """
    t = cc.theorem_133_column_route()
    assert t["required_bound_on_z16_16"] == 126
    assert t["verified_lower_bound_on_z16_16"] == 128
    assert t["blocked_by_our_own_data"] is True, (
        "the column route is no longer blocked -- Theorem B has regressed to "
        "conditional and CHAIN_CEILING.md must say so"
    )
    assert t["blocked_if_z16_16_at_least"] == 127
    # An unverified assumption of 128 WOULD discharge it -- recorded, but
    # nothing unconditional may rest on it.
    assert t["unverified_assumed_16_16_would_block"] is True
    assert t["ceiling_from_unverified_assumption"] == 136


def test_our_16x16_lower_bound_is_backed_by_a_real_matrix():
    """z(16,16) >= 126 must come from a matrix, derived here, not remembered.

    Column deletion is monotone for the same reason row deletion is, so
    dropping any column of the verified 132-edge 16x17 witness yields a
    K33-free 16x16 graph. This reproduces the best such deletion and checks
    it, rather than trusting the constant in the module.
    """
    path = lb.WITNESS_DIR / "z16_17_132_witness_seed201.csv"
    with open(path, newline="") as fh:
        matrix = [[int(x) for x in row] for row in csv.reader(fh) if row]
    assert verify(matrix, expected_edges=132)["is_k33_free"]
    m, n = len(matrix), len(matrix[0])
    best = -1
    for drop in range(n):
        sub = [[matrix[r][c] for c in range(n) if c != drop] for r in range(m)]
        res = verify(sub)
        assert res["is_k33_free"], "column deletion created a K33 -- impossible"
        assert res["shape"] == (16, 16)
        best = max(best, res["edges"])
    # Column deletion alone gives 126 -- one edge short of Theorem B's 127.
    # That is why the algebraic construction was needed; the module's constant
    # is now 128, from verify/constructions.py, not from this route.
    assert best == 126, f"best 16x16 column-deletion subgraph has {best} edges"
    assert cc.VERIFIED_LOWER_BOUND_16_16 == 128, (
        "the module's 16x16 bound should come from the Z_4 x Z_4 construction "
        "(128), not from column deletion (126)"
    )
    assert cc.VERIFIED_LOWER_BOUND_16_16 > best, (
        "the construction must beat column deletion, else Theorem B is "
        "conditional again"
    )


def test_unverified_16_16_assumption_supports_no_provable_claim():
    """The 128 ASSUMPTION must not underwrite anything we assert as proved.

    Note the constant is now doubly redundant: Theorem B is discharged by our
    own construction (z(16,16;3) >= 128, verify/constructions.py), so nothing
    needs the assumed value at all. It is kept only so the historical record
    of what was once leaned on stays legible, and this test still pins that
    nothing provable moves when it changes.

    An earlier version of this module named it PUBLISHED_16_16 and let it
    underwrite the corollary's column-deletion half, which the document then
    framed as unconditional -- while no source for the value had ever been
    established in this project. A reviewer caught that. It is now named
    UNVERIFIED_ASSUMED_16_16, and this test recomputes the whole column-route
    analysis with it set to an absurd value: every field describing what we
    can *prove* must be unchanged.
    """
    saved = cc.UNVERIFIED_ASSUMED_16_16
    try:
        cc.UNVERIFIED_ASSUMED_16_16 = 9999
        t = cc.theorem_133_column_route()
        assert t["required_bound_on_z16_16"] == 126
        # Our own established bound, now from the construction -- unaffected
        # by whatever the unverified constant is set to.
        assert t["verified_lower_bound_on_z16_16"] == 128
        assert t["blocked_by_our_own_data"] is True
        assert t["blocked_if_z16_16_at_least"] == 127
    finally:
        cc.UNVERIFIED_ASSUMED_16_16 = saved


def test_entry_level_map_matches_the_committed_log():
    """The 'how deep must you go' table in CHAIN_CEILING.md.

    Strengthens Theorem A: not only can the final step not deliver 133, no
    entry point into the chain can. Asserted because it drives which level
    the expensive enumeration must target.
    """
    rows = {r["k"]: r for r in cc.entry_level_map(133)}
    for k in range(9, 16):
        assert rows[k]["reachable"] is False, (
            f"133 appears reachable from k={k} -- contradicts Theorem A"
        )
    # The shallowest level from which each weaker target is reachable.
    shallowest = {}
    for target in (136, 135, 134):
        ks = [r["k"] for r in cc.entry_level_map(target) if r["reachable"]]
        shallowest[target] = min(ks)
    assert shallowest == {136: 11, 135: 12, 134: 13}


def test_chain_from_each_true_value_matches_the_log():
    """The 'start at k, get what at 16' column."""
    expected = {9: 144, 10: 144, 11: 136, 12: 135, 13: 134, 14: 134, 15: 134}
    got = {r["k"]: r["chain_from_true_value"] for r in cc.entry_level_map(133)}
    assert got == expected


def test_133_is_blocked_at_every_level_by_a_strict_shortfall():
    """Each level's required input is STRICTLY below its true value.

    Not merely 'not reachable' -- the required input is false with room to
    spare at every level, which is what makes the strengthened claim robust
    rather than resting on a boundary case.
    """
    for r in cc.entry_level_map(133):
        assert r["required_input"] is not None
        assert r["required_input"] < r["true_value"], (
            f"k={r['k']}: required {r['required_input']} vs true "
            f"{r['true_value']} -- not a strict shortfall"
        )


def test_no_document_asserts_the_unconditional_combined_claim():
    """Prose consistency between the module docstring and CHAIN_CEILING.md.

    This test exists because a reviewer found the module docstring asserting,
    unconditionally, that the 2016 paper's 133 "must have been obtained by
    their exhaustive computation" -- while CHAIN_CEILING.md in the same commit
    correctly split that into an unconditional row half and a conditional
    column half. The two documents contradicted each other and the docstring
    carried the stronger, false-as-stated version. Nothing in CI inspected
    prose, so nothing caught it.

    The claim is only licensed given z(16,16;3) >= 127, which this project has
    not established. So neither document may assert it bare.
    """
    root = Path(__file__).resolve().parent.parent
    texts = {
        "chain_ceiling.py": (root / "verify" / "chain_ceiling.py").read_text(),
        "CHAIN_CEILING.md": (root / "CHAIN_CEILING.md").read_text(),
    }
    for name, text in texts.items():
        low = text.lower()
        # The forbidden shape: asserting the conclusion without the hedge.
        for phrase in ("must have been obtained by their exhaustive",
                       "must have come from their exhaustive"):
            idx = low.find(phrase)
            while idx != -1:
                window = low[max(0, idx - 400):idx + 200]
                hedged = any(h in window for h in
                             ("not asserted", "conditional", "row-deleting",
                              "row step", "an earlier version"))
                assert hedged, (
                    f"{name}: '{phrase}' appears without nearby scoping -- "
                    "this is the unconditional combined claim, which requires "
                    "the undischarged z(16,16;3) >= 127 premise"
                )
                idx = low.find(phrase, idx + 1)


def test_the_16x16_degree_6_column_count_is_stated_correctly():
    """Three columns have degree 6, not one.

    Both documents said "the unique minimum-degree (6) column". The witness's
    column degrees are [8,6,8,8,8,9,8,9,8,8,6,8,6,8,8,8,8] -- three 6s, at
    indices 1, 10 and 12. The value 126 is unaffected (deleting any of the
    three gives 126), but the wording was false. Pinned so it cannot recur.
    """
    path = lb.WITNESS_DIR / "z16_17_132_witness_seed201.csv"
    with open(path, newline="") as fh:
        matrix = [[int(x) for x in row] for row in csv.reader(fh) if row]
    m, n = len(matrix), len(matrix[0])
    col_deg = [sum(matrix[r][c] for r in range(m)) for c in range(n)]
    sixes = [c for c, d in enumerate(col_deg) if d == 6]
    assert len(sixes) == 3, f"expected 3 degree-6 columns, got {len(sixes)}"
    assert sixes == [1, 10, 12]
    # And every one of them yields exactly 126 on deletion.
    for c in sixes:
        sub = [[matrix[r][cc] for cc in range(n) if cc != c] for r in range(m)]
        res = verify(sub, expected_edges=126)
        assert res["is_k33_free"] and res["shape"] == (16, 16)
    # So "unique" is wrong in both documents.
    for f in ("verify/chain_ceiling.py", "CHAIN_CEILING.md"):
        text = (Path(__file__).resolve().parent.parent / f).read_text()
        assert "unique minimum-degree" not in text, f"{f} still says 'unique'"


def test_gap_table_matches_the_committed_log():
    """The tight/loose pattern quoted in CHAIN_CEILING.md."""
    gaps = {row["m"]: row["gap"] for row in cc.tight_gaps()}
    assert gaps == {10: 0, 14: 0, 15: 0, 16: 1}


def test_chain_propagation_from_k11_matches_the_recorded_values():
    """The 94/95/96/97 -> 134/135/136/137 table, machine-asserted here too."""
    for start, expected in [(94, 134), (95, 135), (96, 136), (97, 137)]:
        assert cc.chain(start, 11, 16)[-1] == expected


def test_chain_rejects_a_backwards_range():
    with pytest.raises(ValueError):
        cc.chain(94, 16, 11)


def test_no_published_value_is_needed_for_the_theorem():
    """Independence check: the theorem uses only the verified lower bound.

    Recomputes the whole result with PUBLISHED emptied out, to confirm no
    citation leaks into the proof. If this ever fails, the result is
    conditional on the literature and must not be described as
    self-contained.
    """
    saved = dict(cc.PUBLISHED)
    try:
        cc.PUBLISHED.clear()
        t = cc.theorem_133_unreachable()
        assert t["required_bound_is_false"] is True
        assert t["ceiling_from_true_value"] == 134
    finally:
        cc.PUBLISHED.clear()
        cc.PUBLISHED.update(saved)
