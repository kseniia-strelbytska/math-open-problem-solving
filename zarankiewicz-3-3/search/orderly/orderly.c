/* orderly.c -- bottom-up isomorph-reduced exhaustive generation for
 * z(m,n;3) = max edges of an m x n bipartite graph with no K_{3,3}.
 *
 * See SOUNDNESS.md in this directory for the full soundness argument for
 * every pruning / canonicity rule used here. Summary of the rules, each
 * justified there:
 *
 *   (R0) K_{3,3}-freeness  <=>  every 3-subset T of the n columns is
 *        contained in N(r) for at most 2 rows r. Maintained as C(n,3)
 *        counters capped at 2, incremented as a row is built up column by
 *        column and undone on backtrack.
 *   (R1) Rows may be assumed sorted by (degree DESC, mask DESC). Permuting
 *        rows changes neither the edge count nor K_{3,3}-freeness.
 *        NOTE: ordering by *degree* (not by raw integer mask) is what makes
 *        the suffix bound (R4) valid -- mask order alone does NOT imply
 *        degree order.
 *   (R2) Column canonicity: row k must be the lexicographically maximal
 *        element of its orbit under the stabiliser (in the column symmetric
 *        group) of rows 0..k-1. Because that stabiliser is the direct
 *        product of the symmetric groups on the cells of the column
 *        partition induced by rows 0..k-1, and (by induction) those cells
 *        are intervals, this says exactly: within every cell, row k's
 *        columns form a PREFIX of the cell. For k=0 the partition is the
 *        single cell [0,n), so row 0 = 1^{d_0} 0^{n-d_0} -- the "first row
 *        fixed WLOG" rule, here derived rather than assumed.
 *   (R3) Prefix bound: the first k rows form a k x n K_{3,3}-free graph all
 *        of whose degrees are <= d_0, so E_k <= h(k, d_0).
 *   (R4) Suffix bound: rows after k have degree <= d_k, so the remaining
 *        j rows add at most h(j, d_k) edges.
 *   (R5) Triple-budget bound: sum_r C(d_r,3) <= 2*C(n,3), so the remaining
 *        rows' degrees are constrained by a knapsack in the residual
 *        capacity (exact DP table, `knaptab`).
 *   (R6) Density-lemma upper bound (used only as an UPPER bound on h, hence
 *        sound): min row degree <= floor(e/j), and deleting a min-degree row
 *        leaves j-1 rows with degrees still <= d, so
 *        e - floor(e/j) <= h(j-1,d).
 *
 * h(j,d) := max edges of a j x n K_{3,3}-free graph with all row degrees
 * <= d. f(j) = z(j,n;3) = h(j,n). Computed lazily, bottom up, memoised.
 *
 * Nothing here certifies anything: every witness produced is printed as
 * explicit row bitmasks and must be re-checked by verify/checker.py.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <stdint.h>
#include <sys/resource.h>

/* Peak resident set size in MiB. Reported alongside node counts because this
 * machine is under severe memory pressure; the design deliberately keeps only
 * the current search path in RAM (a few KB) and streams enumerated graphs to
 * disk, so this number should stay tiny -- if it does not, that is a bug. */
static double peak_rss_mib(void) {
    struct rusage ru;
    getrusage(RUSAGE_SELF, &ru);
#ifdef __APPLE__
    return ru.ru_maxrss / (1024.0 * 1024.0);   /* bytes on Darwin */
#else
    return ru.ru_maxrss / 1024.0;              /* kilobytes on Linux */
#endif
}

#define MAXN 24
#define MAXM 24

static int N;                 /* number of columns */
static int C3[MAXN + 2];      /* C(d,3) */
static int TRIPLE_CAP;        /* 2*C(N,3) */
static int *knaptab = NULL;
static int hmemo[MAXM + 2][MAXN + 2];
static long long hnodes[MAXM + 2][MAXN + 2];
static double htime[MAXM + 2][MAXN + 2];
static int verbose = 0;
static int use_density = 1;   /* rule R6 */
static int hcap_level = MAXM; /* use exact h(j,.) only for j <= hcap_level */
static int nocanon = 0;       /* 1 = disable R2 entirely (cells become singletons,
                                 so the prefix-in-cell condition is vacuous and
                                 every subset is enumerated). Leaves only R1,
                                 which is trivially sound. Used to verify that R2
                                 is not discarding graphs, at full n=17 scale. */
static int countlevel = -1;   /* if >=0: count surviving configs at this level
                                 and cut the search there (exact tree width) */
static int h_exact = 1;       /* 0 = use only the cheap closed-form upper bound */
static int hassume[MAXM + 2]; /* -1 = none; else an ASSUMED upper bound on f(j)=h(j,N) */
static int hub_memo[MAXM + 2][MAXN + 2];

static double now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + 1e-9 * ts.tv_nsec;
}

/* ------------------------------------------------------------------ */
/* R5: knapsack table.
 * knaptab[j][d][R] = max sum of degrees of j rows, each degree <= d, taken
 * in non-increasing order, with sum C(deg,3) <= R.                    */
/* ------------------------------------------------------------------ */
static inline int knapv(int j, int d, int R) {
    if (R < 0 || d < 0) return -1000000;
    if (R > TRIPLE_CAP) R = TRIPLE_CAP;
    if (j < 0) return 0;
    return knaptab[((size_t)j * (N + 1) + d) * (TRIPLE_CAP + 1) + R];
}

static void build_knap(void) {
    size_t sz = (size_t)(MAXM + 1) * (N + 1) * (TRIPLE_CAP + 1);
    knaptab = (int *)malloc(sz * sizeof(int));
    if (!knaptab) { fprintf(stderr, "oom knaptab\n"); exit(1); }
    for (int d = 0; d <= N; d++)
        for (int R = 0; R <= TRIPLE_CAP; R++)
            knaptab[((size_t)0 * (N + 1) + d) * (TRIPLE_CAP + 1) + R] = 0;
    for (int j = 1; j <= MAXM; j++)
        for (int d = 0; d <= N; d++)
            for (int R = 0; R <= TRIPLE_CAP; R++) {
                int best = -1000000;
                for (int t = 0; t <= d; t++) {
                    if (C3[t] > R) break;
                    int v = t + knaptab[((size_t)(j - 1) * (N + 1) + t) *
                                        (TRIPLE_CAP + 1) + (R - C3[t])];
                    if (v > best) best = v;
                }
                knaptab[((size_t)j * (N + 1) + d) * (TRIPLE_CAP + 1) + R] = best;
            }
}

/* ------------------------------------------------------------------ */
/* Search context                                                      */
/* ------------------------------------------------------------------ */
typedef struct {
    int m, dcap, target;
    int dfloor;                 /* every row degree must be >= dfloor */
    int emax;                   /* reject complete graphs with E > emax (-1 = off) */
    int forced0;                /* force row-0 degree (-1 = free) */
    int enumerate;              /* 1 = enumerate all solutions, don't stop */
    int ext_deg;                /* >0: on each complete graph, try to extend
                                   by one row of exactly this degree */
    /* R0 state, bitmask form. For a column pair a<b:
     *   one[a][b] = bitmask of columns c with multiplicity(a,b,c) == 1
     *   two[a][b] = bitmask of columns c with multiplicity(a,b,c) == 2
     * All three pair-views of a triple are kept in sync, so a candidate row
     * S is legal iff for every pair a<b in S, S & two[a][b] has no third
     * column. That check is maintained incrementally in `forb` below at O(d)
     * word-ops per column added, instead of O(d^2) byte increments. */
    unsigned int one[MAXN + 1][MAXN + 1];
    unsigned int two[MAXN + 1][MAXN + 1];
    /* forb[k][j] = union of two[a][b] over all pairs a<b among the first j
     * chosen columns of row k. A column c may be appended iff bit c is clear
     * in forb[k][j]. Indexed by depth, so no undo is needed. */
    unsigned int forb[MAXM + 2][MAXN + 2];
    unsigned int rowmask[MAXM];
    int rowdeg[MAXM];
    int cstart[MAXM + 2][MAXN + 2];
    int ncells[MAXM + 2];
    int E, usedcap;
    long long nodes;
    long long solutions;        /* complete graphs meeting the target */
    long long ext_success;
    /* Per-LEVEL partial-row state. This MUST be per level, not global to the
     * context: gen(k) needs its own column list intact in order to undo its
     * triple-counter increments after the recursion into level k+1 returns.
     * (An earlier version shared one cur[]/ncur across levels; level k+1
     * clobbered level k's list, so backtracking silently failed to decrement
     * counters -- caught by UBSan and by disagreeing with a hand-computed
     * value of f(4) for n=17.) */
    int cur[MAXM + 2][MAXN + 2];
    int ncur[MAXM + 2];
    long long nodelimit;        /* -1 = none */
    int aborted;
    int found;
    unsigned int witness[MAXM + 2];
    int witness_rows;
    FILE *dump;
    long long level_nodes[MAXM + 2];
    int split_level, split_i, split_k;
    long long split_counter;
} Ctx;

static Ctx *X = NULL;

static int hval(int j, int d);

/* hub(j,d): a cheap, SOUND upper bound on h(j,d) using only closed-form
 * arguments -- no search. Used when --hmode ub is given, so that a big
 * refutation run does not have to recurse into expensive exact sub-searches.
 * Because every term is an upper bound, using hub in place of h keeps every
 * pruning rule sound (pruning only ever needs an over-estimate of what the
 * remaining rows can contribute).
 *   - j*d                        : trivial
 *   - knap(j,d,2C(n,3))          : triple budget (R5)
 *   - hub(j-1,d) + d             : delete any row
 *   - density (R6)               : e - floor(e/j) <= hub(j-1,d)
 *   - hub(j,N)                   : h is monotone in d
 *   - hassume[j]                 : an explicitly declared assumption (d = N)
 */
static int hub(int j, int d) {
    if (j <= 0 || d <= 0) return 0;
    if (d > N) d = N;
    if (j <= 2 || d <= 2) return j * d;
    if (hub_memo[j][d] >= 0) return hub_memo[j][d];
    hub_memo[j][d] = j * d;          /* provisional, guards re-entry */
    int b = j * d;
    int k1 = knapv(j, d, TRIPLE_CAP);
    if (k1 < b) b = k1;
    int hp = hub(j - 1, d);
    if (hp + d < b) b = hp + d;
    while (b > 0 && b - (b / j) > hp) b--;      /* density lemma */
    if (d < N) { int t = hub(j, N); if (t < b) b = t; }
    else if (hassume[j] >= 0 && hassume[j] < b) b = hassume[j];
    hub_memo[j][d] = b;
    return b;
}

/* ------------------------------------------------------------------ */
/* combined suffix bound for `j` further rows, degrees <= dmax, residual
 * triple capacity R.  min( h(j,dmax) , knap(j,dmax,R) ).              */
/* ------------------------------------------------------------------ */
static inline int suffix_bound(int j, int dmax, int R) {
    if (j <= 0) return 0;
    int b = knapv(j, dmax, R);
    int a = (h_exact && j <= hcap_level) ? hval(j, dmax) : hub(j, dmax);
    if (a < b) b = a;
    return b;
}

/* ------------------------------------------------------------------ */
/* triple bookkeeping                                                  */
/* ------------------------------------------------------------------ */
/* Append column c to the partial row at level lv. Returns 0 if c would push
 * some triple to multiplicity 3. Cost: O(current degree) word ops. */
static inline int append_col(int lv, int c) {
    int j = X->ncur[lv];
    if ((X->forb[lv][j] >> (N - 1 - c)) & 1u) return 0;
    unsigned int f = X->forb[lv][j];
    const int *cu = X->cur[lv];
    for (int i = 0; i < j; i++) f |= X->two[cu[i]][c];
    X->forb[lv][j + 1] = f;
    X->cur[lv][j] = c;
    X->ncur[lv] = j + 1;
    return 1;
}

static inline void pop_col(int lv) { X->ncur[lv]--; }

/* Fold a completed row (column list cu[0..d-1], bitmask R) into one/two. */
static inline void commit_row(const int *cu, int d, unsigned int R) {
    for (int i = 0; i < d; i++) {
        int a = cu[i];
        unsigned int ra = R & ~(1u << (N - 1 - a));
        for (int j = i + 1; j < d; j++) {
            int b = cu[j];
            unsigned int rest = ra & ~(1u << (N - 1 - b));
            X->two[a][b] |= X->one[a][b] & rest;
            X->one[a][b] ^= rest;
        }
    }
}

/* Exact inverse of commit_row. Uses the fact that a triple never reaches
 * multiplicity 3 (guaranteed by append_col), so the bits this row pushed
 * from 1 to 2 are exactly one_old & rest. */
static inline void uncommit_row(const int *cu, int d, unsigned int R) {
    for (int i = 0; i < d; i++) {
        int a = cu[i];
        unsigned int ra = R & ~(1u << (N - 1 - a));
        for (int j = i + 1; j < d; j++) {
            int b = cu[j];
            unsigned int rest = ra & ~(1u << (N - 1 - b));
            X->one[a][b] ^= rest;
            X->two[a][b] &= ~(X->one[a][b] & rest);
        }
    }
}

/* ------------------------------------------------------------------ */
/* extension test: is there ANY row of degree exactly `deg` that can be
 * added to the current (complete) configuration keeping K_{3,3}-freeness?
 * Deliberately enumerates ALL such subsets -- no canonicity restriction --
 * because that is the sound over-approximation. Returns 1 and records the
 * row in *out on success.                                             */
/* ------------------------------------------------------------------ */
static int ext_dfs(int lv, int c, int need, unsigned int *out) {
    if (need == 0) {
        unsigned int mk = 0;
        for (int i = 0; i < X->ncur[lv]; i++) mk |= 1u << (N - 1 - X->cur[lv][i]);
        *out = mk;
        return 1;
    }
    if (N - c < need) return 0;
    for (int cc = c; cc <= N - need; cc++) {
        if (!append_col(lv, cc)) continue;
        if (ext_dfs(lv, cc + 1, need - 1, out)) { pop_col(lv); return 1; }
        pop_col(lv);
    }
    return 0;
}

static int try_extend(int deg, unsigned int *out) {
    int lv = X->m;              /* the extension row's own scratch level */
    X->ncur[lv] = 0;
    X->forb[lv][0] = 0;
    return ext_dfs(lv, 0, deg, out);
}

/* ------------------------------------------------------------------ */
static int place_level(int k);

static void build_cells(int k) {
    if (nocanon) {                      /* every column its own cell */
        for (int c = 0; c <= N; c++) X->cstart[k][c] = c;
        X->ncells[k] = N;
        return;
    }
    if (k == 0) {
        X->cstart[0][0] = 0;
        X->cstart[0][1] = N;
        X->ncells[0] = 1;
        return;
    }
    int nc = 0;
    unsigned int mask = X->rowmask[k - 1];
    for (int i = 0; i < X->ncells[k - 1]; i++) {
        int s = X->cstart[k - 1][i], e = X->cstart[k - 1][i + 1];
        int t = 0;
        for (int c = s; c < e; c++)
            if ((mask >> (N - 1 - c)) & 1u) t++;
        if (t > 0) X->cstart[k][nc++] = s;
        if (s + t < e) X->cstart[k][nc++] = s + t;
    }
    X->cstart[k][nc] = N;
    X->ncells[k] = nc;
}

static void record_solution(void) {
    X->solutions++;
    if (!X->found) {
        for (int i = 0; i < X->m; i++) X->witness[i] = X->rowmask[i];
        X->witness_rows = X->m;
        X->found = 1;
    }
    if (X->dump) {
        for (int i = 0; i < X->m; i++)
            fprintf(X->dump, "%u%c", X->rowmask[i], i + 1 == X->m ? '\n' : ' ');
    }
}

/* generate row k over the cells of the level-k column partition */
static int gen(int k, int ci, int dmin, int dmax, const unsigned char *allowed) {
    if (X->aborted) return 1;
    if (ci == X->ncells[k]) {
        int d = X->ncur[k];
        if (d < dmin || d > dmax || !allowed[d]) return 0;
        unsigned int mask = 0;
        for (int i = 0; i < d; i++) mask |= 1u << (N - 1 - X->cur[k][i]);
        if (k > 0) {
            if (d > X->rowdeg[k - 1]) return 0;
            if (d == X->rowdeg[k - 1] && mask > X->rowmask[k - 1]) return 0;
        }
        X->rowdeg[k] = d;
        X->rowmask[k] = mask;
        X->E += d;
        X->usedcap += C3[d];
        int res = 0;
        int ok = 1;
        if (X->emax >= 0 && X->E > X->emax) ok = 0;
        /* Lower-bound complement of the suffix bound: every remaining row has
         * degree >= dfloor, so the remaining m-k-1 rows contribute at least
         * (m-k-1)*dfloor. If that already overshoots emax, prune. This is the
         * rule that forces the degree sequence when target == emax, and
         * without it the 15x17 parent enumeration wanders through degree
         * sequences that cannot possibly sum to the required total. */
        if (ok && X->emax >= 0 && X->dfloor > 0 &&
            X->E + (X->m - k - 1) * X->dfloor > X->emax) ok = 0;
        /* Symmetric: remaining rows also have degree <= d (rows are
         * non-increasing), so they contribute at most (m-k-1)*d. */
        if (ok && X->E + (X->m - k - 1) * d < X->target) ok = 0;
        if (ok && k + 1 < X->m) {
            int d0 = X->rowdeg[0];
            int pb = (h_exact && k + 1 <= hcap_level) ? hval(k + 1, d0)
                                                       : hub(k + 1, d0);
            if (X->E > pb) ok = 0;
        }
        /* Work sharding for parallel runs: at the chosen level, hand out
         * accepted rows round-robin among K shards. The union over
         * i=0..K-1 is exactly the unsharded search, so each shard is a
         * sound partial search and together they are exhaustive. */
        if (ok && k == X->split_level && X->split_k > 1) {
            if ((X->split_counter++ % X->split_k) != X->split_i) ok = 0;
        }
        if (ok) {
            commit_row(X->cur[k], d, mask);
            res = place_level(k + 1);
            uncommit_row(X->cur[k], d, mask);
        }
        X->E -= d;
        X->usedcap -= C3[d];
        return res;
    }
    int s = X->cstart[k][ci], e = X->cstart[k][ci + 1];
    if (X->ncur[k] + (N - s) < dmin) return 0;
    if (gen(k, ci + 1, dmin, dmax, allowed)) return 1;
    int added = 0;
    for (int t = 1; t <= e - s; t++) {
        if (X->ncur[k] >= dmax) break;
        if (!append_col(k, s + t - 1)) break;
        added++;
        if (gen(k, ci + 1, dmin, dmax, allowed)) {
            X->ncur[k] -= added;
            return 1;
        }
    }
    X->ncur[k] -= added;
    return 0;
}

static int place_level(int k) {
    if (X->aborted) return 1;
    X->nodes++;
    X->level_nodes[k]++;
    if (X->nodelimit > 0 && X->nodes > X->nodelimit) { X->aborted = 1; return 1; }

    if (countlevel >= 0 && k == countlevel) return 0;   /* exact width probe */
    if (k == X->m) {
        if (X->E < X->target) return 0;
        if (X->emax >= 0 && X->E > X->emax) return 0;
        if (X->ext_deg > 0) {
            unsigned int extrow = 0;
            if (try_extend(X->ext_deg, &extrow)) {
                X->ext_success++;
                for (int i = 0; i < X->m; i++) X->witness[i] = X->rowmask[i];
                X->witness[X->m] = extrow;
                X->witness_rows = X->m + 1;
                X->found = 1;
                X->solutions++;
                if (X->dump) {
                    for (int i = 0; i <= X->m; i++)
                        fprintf(X->dump, "%u%c", X->witness[i],
                                i == X->m ? '\n' : ' ');
                }
                return X->enumerate ? 0 : 1;
            }
            X->solutions++;   /* a parent was enumerated (extension failed) */
            if (X->dump) {
                for (int i = 0; i < X->m; i++)
                    fprintf(X->dump, "%u%c", X->rowmask[i],
                            i + 1 == X->m ? '\n' : ' ');
            }
            return 0;
        }
        record_solution();
        return X->enumerate ? 0 : 1;
    }

    build_cells(k);

    int dmax = (k == 0) ? X->dcap : X->rowdeg[k - 1];
    if (dmax > X->dcap) dmax = X->dcap;
    int R = TRIPLE_CAP - X->usedcap;
    while (dmax > 0 && C3[dmax] > R) dmax--;

    /* (R9) The (R7) degree-floor/emax complement, HOISTED from a post-row
     * rejection into a cap on the row degree. It is the *same predicate*
     * gen() already applies once the row is complete --
     *     E_before + d + (m-k-1)*dfloor <= emax
     * -- and it depends only on d, never on which columns the row uses. So
     * testing it here cannot change which rows survive; it only stops `gen`
     * from enumerating rows that would be rejected anyway. That matters
     * because the measured bottleneck is the *number of candidate rows
     * enumerated* (§7), not the cost of testing one: without this hoist,
     * `--emax E --dfloor D` prunes the tree but still walks every row of
     * degree up to 17 at every level. Inactive unless --emax is given, so
     * every unconstrained run reproduces its old node count bit-for-bit. */
    if (X->emax >= 0) {
        int cap = X->emax - X->E;
        if (X->dfloor > 0) cap -= (X->m - k - 1) * X->dfloor;
        if (cap < dmax) dmax = cap;
    }

    int j = X->m - k - 1;                  /* rows placed after this one */
    unsigned char allowed[MAXN + 2];
    memset(allowed, 0, sizeof(allowed));
    int dmin = -1;
    int lo = X->dfloor;
    if (k == 0 && X->forced0 >= 0) { lo = X->forced0; if (dmax > X->forced0) dmax = X->forced0; }
    for (int d = lo; d <= dmax; d++) {
        if (C3[d] > R) break;
        int b = X->E + d + suffix_bound(j, d, R - C3[d]);
        if (b >= X->target) {
            /* also respect the prefix bound / emax on the running total */
            allowed[d] = 1;
            if (dmin < 0) dmin = d;
        }
    }
    if (dmin < 0) return 0;
    X->ncur[k] = 0;
    X->forb[k][0] = 0;
    return gen(k, 0, dmin, dmax, allowed);
}

/* ------------------------------------------------------------------ */
typedef struct {
    int sat;                /* 1 = found, 0 = exhausted, -1 = aborted */
    long long nodes;
    long long solutions;
    long long ext_success;
    unsigned int witness[MAXM + 2];
    int witness_rows;
    double secs;
} Res;

typedef struct {
    int m, dcap, target, dfloor, emax, forced0, enumerate, ext_deg;
    int split_level, split_i, split_k;
    long long nodelimit;
    FILE *dump;
    int report_levels;
} Job;

static Res run_search(Job *jb) {
    Ctx *saved = X;
    Ctx *c = (Ctx *)calloc(1, sizeof(Ctx));
    if (!c) { fprintf(stderr, "oom ctx\n"); exit(1); }
    X = c;
    c->m = jb->m;
    c->dcap = jb->dcap > N ? N : jb->dcap;
    c->target = jb->target;
    c->dfloor = jb->dfloor;
    c->emax = jb->emax;
    c->forced0 = jb->forced0;
    c->enumerate = jb->enumerate;
    c->ext_deg = jb->ext_deg;
    c->nodelimit = jb->nodelimit;
    c->dump = jb->dump;
    c->split_level = jb->split_level;
    c->split_i = jb->split_i;
    c->split_k = jb->split_k;
    double t0 = now();
    int r = place_level(0);
    double t1 = now();
    Res out;
    memset(&out, 0, sizeof(out));
    out.sat = c->aborted ? -1 : (c->found ? 1 : 0);
    out.nodes = c->nodes;
    out.solutions = c->solutions;
    out.ext_success = c->ext_success;
    out.witness_rows = c->witness_rows;
    for (int i = 0; i < c->witness_rows; i++) out.witness[i] = c->witness[i];
    out.secs = t1 - t0;
    if (jb->report_levels) {
        fprintf(stderr, "    level nodes:");
        for (int i = 0; i <= c->m; i++)
            if (c->level_nodes[i]) fprintf(stderr, " %d:%lld", i, c->level_nodes[i]);
        fprintf(stderr, "\n");
    }
    (void)r;
    X = saved;
    free(c);
    return out;
}

/* ------------------------------------------------------------------ */
/* h(j,d), lazily, bottom-up.                                          */
/* ------------------------------------------------------------------ */
static int hval(int j, int d) {
    if (j <= 0 || d <= 0) return 0;
    if (d > N) d = N;
    /* j<=2: K_{3,3} needs 3 rows, so no constraint. d<=2: a row of degree
     * <=2 contains no 3-subset, so no constraint. */
    if (j <= 2 || d <= 2) return j * d;
    if (hmemo[j][d] >= 0) return hmemo[j][d];

    int ub = j * d;
    int k1 = knapv(j, d, TRIPLE_CAP);
    if (k1 < ub) ub = k1;
    int hp = hval(j - 1, d) + d;
    if (hp < ub) ub = hp;
    if (use_density) {
        int hprev = hval(j - 1, d);
        while (ub > 0 && ub - (ub / j) > hprev) ub--;
    }

    double t0 = now();
    long long tot = 0;
    int res = 0;
    for (int T = ub; T >= 0; T--) {
        Job jb;
        memset(&jb, 0, sizeof(jb));
        jb.m = j; jb.dcap = d; jb.target = T; jb.dfloor = 0;
        jb.emax = -1; jb.forced0 = -1; jb.nodelimit = -1;
        Res r = run_search(&jb);
        tot += r.nodes;
        if (verbose >= 2)
            fprintf(stderr, "      h(%d,%d) probe T=%d -> %s  nodes=%lld %.2fs\n",
                    j, d, T, r.sat ? "SAT" : "UNSAT", r.nodes, r.secs);
        if (r.sat == 1) { res = T; break; }
    }
    hmemo[j][d] = res;
    hnodes[j][d] = tot;
    htime[j][d] = now() - t0;
    if (verbose >= 1)
        fprintf(stderr, "  h(%d,%d) = %d   [nodes=%lld  %.3fs]\n", j, d, res,
                tot, htime[j][d]);
    return res;
}

/* ------------------------------------------------------------------ */
static void print_witness(const char *tag, unsigned int *w, int nr) {
    printf("%s_ROWS %d", tag, nr);
    for (int i = 0; i < nr; i++) printf(" %u", w[i]);
    printf("\n");
}

static void usage(void) {
    fprintf(stderr,
        "usage: orderly -n N -m M [options]\n"
        "  modes:\n"
        "    --hcurve            compute f(k)=h(k,N) for k=1..M (bottom-up)\n"
        "    --decide T          decision: does an M x N K33-free graph with >=T edges exist\n"
        "    --enum T            enumerate all canonical M x N graphs with edges in [T,emax]\n"
        "  options:\n"
        "    --dcap D            cap all row degrees at D\n"
        "    --dfloor D          require all row degrees >= D\n"
        "    --emax E            require total edges <= E\n"
        "    --forced0 D         force row 0 degree = D (for parallel splitting)\n"
        "    --extend D          for each enumerated graph, try adding a row of degree exactly D\n"
        "    --dump FILE         write enumerated graphs (row bitmasks) to FILE\n"
        "    --limit NODES       abort after NODES search nodes\n"
        "    --split L:I:K       shard I of K, splitting the level-L subtrees\n"
        "    --hcap L            use exact h(j,.) bounds only for j<=L\n"
        "    --nodensity         disable the density-lemma upper bound (R6)\n"
        "    --hmode ub          use only cheap closed-form h upper bounds (no sub-searches)\n"
        "    --assume k:v        DECLARE the assumption f(k) <= v (logged loudly)\n"
        "    --countlevel L      cut the search at level L; level_nodes[L] is then the\n"
        "                        EXACT number of surviving L-row configurations\n"
        "    --nocanon           disable column canonicity (R2) -- slow, for validation\n"
        "    -v / -vv            verbosity\n");
    exit(2);
}

int main(int argc, char **argv) {
    int M = 0;
    int mode = 0;   /* 1=hcurve 2=decide 3=enum */
    int T = 0, dcap = -1, dfloor = 0, emax = -1, forced0 = -1, extend = 0;
    long long limit = -1;
    int split_level = 0, split_i = 0, split_k = 1;
    int assume_spec[MAXM + 2][2];
    int n_assume = 0;
    const char *dumpfile = NULL;
    N = 0;

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "-n")) N = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-m")) M = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--hcurve")) mode = 1;
        else if (!strcmp(argv[i], "--decide")) { mode = 2; T = atoi(argv[++i]); }
        else if (!strcmp(argv[i], "--enum")) { mode = 3; T = atoi(argv[++i]); }
        else if (!strcmp(argv[i], "--dcap")) dcap = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--dfloor")) dfloor = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--emax")) emax = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--forced0")) forced0 = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--extend")) extend = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--dump")) dumpfile = argv[++i];
        else if (!strcmp(argv[i], "--limit")) limit = atoll(argv[++i]);
        else if (!strcmp(argv[i], "--split")) {
            /* --split LEVEL:I:K  -> shard I of K, split at row LEVEL */
            if (sscanf(argv[++i], "%d:%d:%d", &split_level, &split_i, &split_k) != 3)
                usage();
        }
        else if (!strcmp(argv[i], "--hcap")) hcap_level = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--nodensity")) use_density = 0;
        else if (!strcmp(argv[i], "--hmode")) h_exact = strcmp(argv[++i], "ub") != 0;
        else if (!strcmp(argv[i], "--countlevel")) countlevel = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--nocanon")) nocanon = 1;
        else if (!strcmp(argv[i], "--assume")) {
            int aj, av;
            if (sscanf(argv[++i], "%d:%d", &aj, &av) != 2) usage();
            if (aj < 0 || aj > MAXM) usage();
            assume_spec[n_assume][0] = aj; assume_spec[n_assume][1] = av;
            n_assume++;
        }
        else if (!strcmp(argv[i], "-v")) verbose = 1;
        else if (!strcmp(argv[i], "-vv")) verbose = 2;
        else usage();
    }
    if (N < 3 || N > MAXN || M < 1 || M > MAXM || !mode) usage();
    if (dcap < 0 || dcap > N) dcap = N;

    for (int d = 0; d <= MAXN + 1; d++)
        C3[d] = (d < 3) ? 0 : d * (d - 1) * (d - 2) / 6;
    TRIPLE_CAP = 2 * C3[N];
    build_knap();
    for (int a = 0; a <= MAXM + 1; a++) {
        hassume[a] = -1;
        for (int b = 0; b <= MAXN + 1; b++) { hmemo[a][b] = -1; hub_memo[a][b] = -1; }
    }
    for (int i = 0; i < n_assume; i++) {
        hassume[assume_spec[i][0]] = assume_spec[i][1];
        printf("ASSUMED f(%d) <= %d   [DECLARED ASSUMPTION, not proved here]\n",
               assume_spec[i][0], assume_spec[i][1]);
    }

    printf("PARAMS n=%d m=%d triple_cap=%d\n", N, M, TRIPLE_CAP);

    if (mode == 1) {
        for (int k = 1; k <= M; k++) {
            double t0 = now();
            int v = hval(k, dcap);
            double el = now() - t0;
            printf("F k=%d dcap=%d value=%d nodes=%lld secs=%.3f cum_secs=%.3f rss_mib=%.1f\n",
                   k, dcap, v, hnodes[k][dcap], htime[k][dcap], el, peak_rss_mib());
            fflush(stdout);
        }
        /* emit a witness for the top level so it can be independently checked */
        {
            Job jb; memset(&jb, 0, sizeof(jb));
            jb.m = M; jb.dcap = dcap; jb.target = hmemo[M][dcap] >= 0 ? hmemo[M][dcap] : hval(M, dcap);
            if (jb.target == 0) jb.target = hval(M, dcap);
            jb.emax = -1; jb.forced0 = -1; jb.nodelimit = -1;
            Res r = run_search(&jb);
            if (r.sat == 1) print_witness("WITNESS", r.witness, r.witness_rows);
        }
        return 0;
    }

    FILE *dump = NULL;
    if (dumpfile) {
        dump = fopen(dumpfile, "w");
        if (!dump) { perror("dump"); return 1; }
    }

    Job jb; memset(&jb, 0, sizeof(jb));
    jb.m = M; jb.dcap = dcap; jb.target = T; jb.dfloor = dfloor;
    jb.emax = emax; jb.forced0 = forced0; jb.nodelimit = limit;
    jb.enumerate = (mode == 3);
    jb.ext_deg = extend;
    jb.split_level = split_level;
    jb.split_i = split_i;
    jb.split_k = split_k;
    jb.dump = dump;
    jb.report_levels = 1;

    Res r = run_search(&jb);
    printf("RESULT mode=%s m=%d n=%d target=%d dcap=%d dfloor=%d emax=%d forced0=%d "
           "split=%d:%d:%d status=%s nodes=%lld solutions=%lld ext_success=%lld secs=%.3f rss_mib=%.1f\n",
           mode == 2 ? "decide" : "enum", M, N, T, dcap, dfloor, emax, forced0,
           split_level, split_i, split_k,
           r.sat == 1 ? "FOUND" : (r.sat == 0 ? "EXHAUSTED" : "ABORTED"),
           r.nodes, r.solutions, r.ext_success, r.secs, peak_rss_mib());
    if (r.witness_rows) print_witness("WITNESS", r.witness, r.witness_rows);
    if (dump) fclose(dump);
    return 0;
}
