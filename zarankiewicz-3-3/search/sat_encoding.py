"""
SAT encoding for: "does an m x n bipartite graph with exactly K edges and
no K_{3,3} subgraph exist?"

Variables: x[i][j] for i in 0..m-1, j in 0..n-1 (True = edge present between
row-vertex i and column-vertex j).

Three families of clauses are produced:

  1. Exactly-K cardinality constraint over all x[i][j], via pysat's
     CardEnc.equals (a proper, well-tested cardinality encoding -- NOT
     hand-rolled here).
  2. K_{3,3}-freeness clauses, one per (3 rows) x (3 columns) combination.
  3. Optional symmetry-breaking clauses: rows sorted lex-non-increasing,
     columns sorted lex-non-increasing (independently).

See SAT_LOG.md for the validation performed on family 3 (the highest-risk
piece) before it was trusted, and on the pipeline as a whole.
"""

from __future__ import annotations

import itertools
from typing import Sequence

from pysat.formula import CNF, IDPool
from pysat.card import CardEnc, EncType


# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------

def build_vars(m: int, n: int, vpool: IDPool | None = None):
    """Allocate one boolean SAT variable per matrix cell x[i][j]."""
    vpool = vpool if vpool is not None else IDPool()
    x = [[vpool.id(("x", i, j)) for j in range(n)] for i in range(m)]
    return x, vpool


# ---------------------------------------------------------------------------
# K_{3,3}-freeness
# ---------------------------------------------------------------------------

def k33_clauses(x: list[list[int]], m: int, n: int) -> list[list[int]]:
    """
    K_{3,3}-freeness clauses.

    Lemma (this is just the definition of K_{3,3} unrolled, not a deep
    result -- but we state and confirm it explicitly per the working
    discipline rather than taking it on faith):

        Fix any 3 distinct row indices r1<r2<r3 and any 3 distinct column
        indices c1<c2<c3. The 9 cells {(ri, cj) : i,j in {1,2,3}} host a
        K_{3,3} subgraph (3 row-vertices all pairwise-fully-connected to 3
        column-vertices) IFF all 9 corresponding edge variables are True.

        Hence the clause
            (-x[r1][c1] OR -x[r1][c2] OR ... OR -x[r3][c3])   [9 literals]
        is violated (all literals False, i.e. clause = False) exactly when
        all 9 x-variables are True, i.e. exactly when this specific
        3-rows-by-3-columns block is a complete K_{3,3}.

        NECESSITY: if the resulting graph contains any K_{3,3} at all, that
        K_{3,3} picks out *some* 3 row indices and *some* 3 column indices,
        so the clause for exactly that combination is violated -- hence
        "no K_{3,3} anywhere" implies "every such clause is satisfied", so
        omitting any clause could miss a real K_{3,3}. We do not omit any:
        we iterate over ALL C(m,3) x C(n,3) combinations.

        SUFFICIENCY: if every one of these clauses is satisfied, then for
        every triple of rows and every triple of columns, at least one of
        the 9 cross cells is 0 -- i.e. no 3-by-3 block is fully connected --
        i.e. no K_{3,3} exists anywhere in the graph (a K_{3,3} is, by
        definition, some 3-by-3 fully-connected block).

        So enumerating every row-triple x column-triple combination and
        forbidding "all 9 True" is both necessary and sufficient to forbid
        every possible K_{3,3} -- confirmed by direct unrolling of the
        definition, not an external citation.
    """
    clauses = []
    for r1, r2, r3 in itertools.combinations(range(m), 3):
        row1, row2, row3 = x[r1], x[r2], x[r3]
        for c1, c2, c3 in itertools.combinations(range(n), 3):
            clauses.append([
                -row1[c1], -row1[c2], -row1[c3],
                -row2[c1], -row2[c2], -row2[c3],
                -row3[c1], -row3[c2], -row3[c3],
            ])
    return clauses


# ---------------------------------------------------------------------------
# Symmetry breaking: lexicographic ordering gadget
# ---------------------------------------------------------------------------
#
# LEMMA (permutation invariance -- stated explicitly, confirmed below):
#
#   If M is an m x n 0/1 matrix with exactly K ones and no K_{3,3}
#   submatrix, and P is any permutation of the m rows and Q is any
#   permutation of the n columns, then M' = P * M * Q (rows permuted by P,
#   columns permuted by Q) also has exactly K ones and is also K_{3,3}-free.
#
#   WHY: permuting rows/columns is a relabeling of the row-vertices and
#   column-vertices of the underlying bipartite graph -- it changes no
#   adjacency relationship, only which index refers to which vertex. Edge
#   count is a sum over all cells, invariant under any reordering of rows
#   and/or columns (it's the same multiset of cell values, just
#   relocated). K_{3,3}-freeness asks "do there exist 3 rows and 3 columns
#   that are all pairwise connected" -- an existential statement over SETS
#   of row/column indices, not sequences; relabeling indices cannot create
#   or destroy such a set's existence, it can only rename which indices
#   are in it.
#
#   CONSEQUENCE: if ANY K-edge K_{3,3}-free m x n matrix exists, then in
#   particular one exists whose rows are sorted lexicographically
#   non-increasing (as binary numbers, most-significant bit = column 0)
#   AND whose columns are independently sorted lexicographically
#   non-increasing (as binary numbers, most-significant bit = row 0) --
#   namely, sort the rows of any witness, then sort the columns of the
#   result. (Sorting columns after sorting rows does not un-sort the rows,
#   since column permutation acts within each row independently of row
#   order -- it permutes the same j-th entry across all rows uniformly, so
#   whichever row was lexicographically largest before column-sorting is
#   still made of the same multiset of row content, now just re-indexed
#   by column, and the row order established by row-sorting depended only
#   on which VALUES appear in which relative row order, not on column
#   labels, and applying the SAME column permutation to every row
#   preserves every pairwise row-vs-row lexicographic comparison... this
#   requires care: does column-sorting preserve the row order established
#   by row-sorting?)
#
#   The subtlety flagged above is real, so here is the careful argument
#   instead of a hand-wave: row-sorting and column-sorting are applied to
#   two DIFFERENT copies of the constraint, not composed on top of each
#   other in a way that could interfere. We add BOTH constraint families to
#   the SAME SAT instance: "row i >=_lex row i+1 for all consecutive i" AND
#   "column j >=_lex column j+1 for all consecutive j", simultaneously, as
#   independent clause sets over the SAME x variables. We do not need to
#   prove that sorting rows-then-columns of one fixed witness satisfies
#   both simultaneously (it need not, in general -- column-sorting can
#   disturb row order). What we actually need, and what is actually
#   provided by a full double-sort algorithm (not proven here, we don't
#   rely on it), OR more simply: it suffices to prove the SAT clauses are
#   individually sound and jointly satisfiable by SOME K_{3,3}-free
#   K-edge matrix whenever one exists at all. We get that for free from a
#   cleaner argument, given directly below, that does not require a
#   combined double-sort construction:
#
#   CLEANER ARGUMENT (what this code actually relies on): consider the
#   *canonical form* of any witness M under the finite group action of
#   (row permutations) x (column permutations). This is a finite group
#   acting on a finite set of 0/1 matrices; take a witness M and consider
#   its orbit under this group. Pick ANY matrix M* in that orbit that
#   simultaneously has lex-non-increasing rows AND lex-non-increasing
#   columns -- such an M* is guaranteed to exist because the orbit is
#   finite and non-empty, and the following procedure terminates at one:
#   repeatedly sort rows (if not already row-sorted) OR sort columns (if
#   not already column-sorted); each such sort strictly increases the
#   matrix in the standard lexicographic order on the flattened
#   row-major (or column-major) reading of the WHOLE matrix restricted to
#   ties... concretely: define Phi(M) = (rows of M read as a sorted
#   non-increasing sequence of row-bitstrings, compared lexicographically
#   as a sequence, i.e. sort-rows-then-compare). Sorting the rows of M
#   maximizes Phi among all row-permutations of M and doesn't change M's
#   multiset of columns' content-per-row, so it doesn't decrease the
#   analogous column potential by "much" -- rather than push this further
#   by hand, we anchor the claim in something checkable per the working
#   discipline: EXHAUSTIVE VERIFICATION on small cases (see
#   test_lex_ge_gadget and test_symmetry_breaking_preserves_sat_status_*
#   in test_sat_encoding.py) that adding BOTH row- and BOTH column-ordering clause
#   families together, simultaneously, to the same instance never flips
#   SAT to UNSAT relative to the unconstrained instance, across many small
#   full-enumeration cases. That empirical, exhaustive small-case check is
#   the actual load-bearing justification used here, not the hand-wave
#   above -- the hand-wave motivates WHY we expect it to hold, the
#   exhaustive test is what actually licenses trusting it. (Standard
#   double lex ordering for 0/1 matrix symmetry breaking is well known in
#   the SAT/CP literature under "double lex" constraints for matrix models;
#   we do not cite a specific theorem for it without having verified it
#   ourselves here, per "no citation without certainty" -- we verify
#   instead.)
#
# IMPLEMENTATION: standard lex-leader chain via an "equal-so-far" auxiliary
# indicator built by Tseitin-transforming the recursive definition of
# lexicographic comparison. See lex_ge_clauses() docstring for the exact
# derivation.


def lex_ge_clauses(
    a_lits: Sequence[int],
    b_lits: Sequence[int],
    vpool: IDPool,
    tag,
) -> list[list[int]]:
    """
    Return CNF clauses enforcing "a >=_lex b" where a_lits/b_lits are two
    equal-length literal sequences representing bitstrings MSB-first
    (index 0 = most significant bit).

    DERIVATION. a >=_lex b holds iff, scanning bit positions left to right,
    at the first position where a and b differ, a has 1 and b has 0 (or
    they never differ, i.e. a == b). Define an "equal-so-far" indicator
    chain:
        eq_0 := True (constant -- the empty prefix is trivially equal)
        eq_{j+1} := eq_j AND (a_j <-> b_j)     for j = 0..n-1

    Two clause families implement this via Tseitin transformation:

    (1) Ordering constraint at position j (for all j = 0..n-1):
            eq_j -> (a_j OR NOT b_j)
        i.e. "if the prefix before position j was equal, position j itself
        cannot have a_j=0 while b_j=1" (that would make a <_lex b via a
        first-difference at j). Clause: (-eq_j, a_j, -b_j); for j=0, eq_0
        is the constant True so the clause simplifies to (a_0, -b_0).

    (2) Definition of eq_{j+1} (for j = 0..n-2 -- eq_n is never needed
        since nothing looks past the last position), both directions of
        the biconditional eq_{j+1} <-> (eq_j AND (a_j<->b_j)):
          - eq_{j+1} -> eq_j:                    (-eq_{j+1}, eq_j)
          - eq_{j+1} -> (a_j<->b_j), i.e. both:
                (-eq_{j+1}, -a_j, b_j)
                (-eq_{j+1}, a_j, -b_j)
          - (eq_j AND a_j AND b_j) -> eq_{j+1}:   (-eq_j, -a_j, -b_j, eq_{j+1})
          - (eq_j AND -a_j AND -b_j) -> eq_{j+1}: (-eq_j, a_j, b_j, eq_{j+1})
        (the last two together give "eq_j AND (a_j<->b_j) -> eq_{j+1}",
        case-split over the two ways a_j<->b_j can hold, since (a_j<->b_j)
        is itself a disjunction of two conjunctions and is not a single
        literal, so it cannot appear directly in one clause.)
        For j=0, eq_0 is the constant True, so all four clauses above drop
        their (-eq_0 / eq_0) literal accordingly.

    WHY BOTH DIRECTIONS OF (2) ARE NEEDED (not just one):
      - The "eq_{j+1} -> ..." direction (soundness) ensures that whenever a
        model sets eq_{j+1}=True, the prefix truly matches -- otherwise
        constraint (1) at position j+1 could fire on a bogus "equal so far"
        claim and impose a wrong restriction, OR fail to impose a needed
        one elsewhere; either way, without this direction the gadget could
        allow models that don't actually correspond to a>=_lex b.
      - The "... -> eq_{j+1}" direction (completeness) ensures that
        whenever the prefix genuinely does match in some assignment of
        a,b, there EXISTS a satisfying extension to the aux eq variables.
        Without this direction, a real a>=_lex b assignment might have NO
        valid extension to the eq variables, making the whole gadget
        UNSAT even though a>=_lex b legitimately holds -- exactly the
        silent-UNSAT failure mode this task explicitly warns about.

    This function creates n-1 fresh auxiliary variables (eq_1..eq_{n-1})
    tagged with `tag` to keep them namespaced/unique across multiple calls
    (e.g. one call per consecutive row pair).
    """
    n = len(a_lits)
    assert len(b_lits) == n, "lex_ge_clauses: a and b must have equal length"
    clauses: list[list[int]] = []
    eq_prev = None  # None represents the constant True (eq_0)
    for j in range(n):
        a_j, b_j = a_lits[j], b_lits[j]
        # (1) ordering constraint at position j
        if eq_prev is None:
            clauses.append([a_j, -b_j])
        else:
            clauses.append([-eq_prev, a_j, -b_j])
        # (2) define eq_{j+1}, needed only if there's a position j+1 to use it
        if j < n - 1:
            eq_next = vpool.id((tag, "eq", j + 1))
            if eq_prev is None:
                clauses.append([-eq_next, -a_j, b_j])
                clauses.append([-eq_next, a_j, -b_j])
                clauses.append([-a_j, -b_j, eq_next])
                clauses.append([a_j, b_j, eq_next])
            else:
                clauses.append([-eq_next, eq_prev])
                clauses.append([-eq_next, -a_j, b_j])
                clauses.append([-eq_next, a_j, -b_j])
                clauses.append([-eq_prev, -a_j, -b_j, eq_next])
                clauses.append([-eq_prev, a_j, b_j, eq_next])
            eq_prev = eq_next
    return clauses


def symmetry_breaking_clauses(x: list[list[int]], m: int, n: int, vpool: IDPool) -> list[list[int]]:
    """
    Row i >=_lex row i+1 for all consecutive rows (0..m-2), and
    column j >=_lex column j+1 for all consecutive columns (0..n-2),
    independently -- "double lex" style symmetry breaking. See the module
    docstring above this section for the soundness argument and its
    empirical validation.
    """
    clauses: list[list[int]] = []
    for i in range(m - 1):
        clauses.extend(lex_ge_clauses(x[i], x[i + 1], vpool, ("row_ge", i)))
    for j in range(n - 1):
        col_j = [x[i][j] for i in range(m)]
        col_j1 = [x[i][j + 1] for i in range(m)]
        clauses.extend(lex_ge_clauses(col_j, col_j1, vpool, ("col_ge", j)))
    return clauses


# ---------------------------------------------------------------------------
# Full instance builder
# ---------------------------------------------------------------------------

def build_instance(
    m: int,
    n: int,
    K: int,
    symmetry_breaking: bool = True,
    card_encoding: int = EncType.seqcounter,
):
    """
    Build the full CNF for "m x n, exactly K edges, K_{3,3}-free [,
    symmetry-broken]".

    Returns (cnf, x, vpool):
      cnf   -- pysat.formula.CNF with all clauses
      x     -- x[i][j] variable-id matrix
      vpool -- the IDPool used (for decoding models / extending further)
    """
    vpool = IDPool()
    x, vpool = build_vars(m, n, vpool)
    cnf = CNF()

    all_lits = [x[i][j] for i in range(m) for j in range(n)]
    card = CardEnc.equals(lits=all_lits, bound=K, vpool=vpool, encoding=card_encoding)
    cnf.extend(card.clauses)

    cnf.extend(k33_clauses(x, m, n))

    if symmetry_breaking:
        cnf.extend(symmetry_breaking_clauses(x, m, n, vpool))

    return cnf, x, vpool


def model_to_matrix(model: Sequence[int], x: list[list[int]], m: int, n: int) -> list[list[int]]:
    """Decode a SAT model (list of signed ints) into an m x n 0/1 matrix."""
    true_lits = set(lit for lit in model if lit > 0)
    return [[1 if x[i][j] in true_lits else 0 for j in range(n)] for i in range(m)]
