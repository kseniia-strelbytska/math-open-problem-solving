/* brute.c -- DELIBERATELY INDEPENDENT exhaustive decision procedure for
 * "does an m x n K_{3,3}-free bipartite graph with >= T edges exist?"
 *
 * Its whole purpose is to cross-check orderly.c on small cells. It therefore
 * shares NO logic with orderly.c on purpose:
 *
 *   - Canonicity: ONLY "rows in non-increasing integer-mask order". That is
 *     trivially sound (permuting rows preserves edge count and
 *     K_{3,3}-freeness) and uses NO column symmetry at all -- so it cannot
 *     reproduce a bug in orderly.c's column-orbit canonicity rule (R2), which
 *     is the single riskiest rule in the whole pipeline.
 *   - K_{3,3} test: the ROW-triple formulation. When row k is added, check
 *     every pair (i,j) of earlier rows for popcount(R_i & R_j & R_k) >= 3.
 *     orderly.c instead maintains capped COLUMN-triple counters. Different
 *     data structure, different traversal.
 *   - No density lemma, no h(j,d) table, no knapsack. The only bound is the
 *     trivial "each remaining row has at most n edges".
 *
 * Necessarily much slower; usable up to about n=8.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static int n, m, T;
static unsigned int row[32];
static long long nodes = 0;
static int found = 0;

static int ok_with_prev(int k, unsigned int r) {
    for (int i = 0; i < k; i++)
        for (int j = i + 1; j < k; j++)
            if (__builtin_popcount(row[i] & row[j] & r) >= 3) return 0;
    return 1;
}

static int rec(int k, int edges, unsigned int cap) {
    nodes++;
    if (k == m) return edges >= T;
    /* trivial suffix bound: each remaining row has at most n edges */
    if (edges + (m - k) * n < T) return 0;
    /* iterate candidate masks in DECREASING order, <= cap (row-sorted) */
    for (long long msk = cap; msk >= 0; msk--) {
        unsigned int r = (unsigned int)msk;
        int d = __builtin_popcount(r);
        if (edges + d + (m - k - 1) * __builtin_popcount(r) < T) {
            /* every later row is <= r as an integer, but that does not bound
             * its degree, so we may only use n as the per-row bound here. */
        }
        if (!ok_with_prev(k, r)) continue;
        row[k] = r;
        if (rec(k + 1, edges + d, r)) return 1;
    }
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 4) { fprintf(stderr, "usage: brute n m T\n"); return 2; }
    n = atoi(argv[1]); m = atoi(argv[2]); T = atoi(argv[3]);
    struct timespec a, b;
    clock_gettime(CLOCK_MONOTONIC, &a);
    found = rec(0, 0, (1u << n) - 1);
    clock_gettime(CLOCK_MONOTONIC, &b);
    double secs = (b.tv_sec - a.tv_sec) + 1e-9 * (b.tv_nsec - a.tv_nsec);
    printf("BRUTE n=%d m=%d T=%d %s nodes=%lld secs=%.3f", n, m, T,
           found ? "FOUND" : "EXHAUSTED", nodes, secs);
    if (found) { printf(" rows"); for (int i = 0; i < m; i++) printf(" %u", row[i]); }
    printf("\n");
    return 0;
}
