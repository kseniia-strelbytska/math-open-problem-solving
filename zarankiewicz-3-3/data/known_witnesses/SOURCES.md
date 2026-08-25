# Known-witness matrices: provenance

All files in this directory are 0/1 adjacency matrices (CSV, rows = one
side of the bipartite graph, columns = the other), copied verbatim from a
third-party source and then **independently re-verified** with
`verify/checker.py` before being trusted — see `PROGRESS.md`,
2026-08-25 entry, for the full verification log.

## Source

Repository: https://github.com/KAVentures/z1322-exact
Commit: `47ef9d8893d048b589026b67662490ee6a74ebaa` (2026-08-08T18:09:34Z,
"Publish verified combined manuscript and proof package")
Files fetched from `proof/frontier_closure/data/` via raw.githubusercontent.com
on 2026-08-25 and copied here unmodified (only renamed for consistency;
original filenames preserved where they already matched this convention).

This repository backs arXiv:2608.08154 ("Exact Zarankiewicz Values On Two
Finite Frontier Slices," K. Afrasyab, Aug 2026); several of the matrices
below (the `z13_18` through `z15_18` cells) also match values independently
reported in arXiv:2608.08549 ("Seven Exact Finite Zarankiewicz Numbers from
a Single 13x18 Core," S. Hou, Aug 2026), giving cross-source corroboration.

## Files and independently-verified status

All of the below were checked with `verify/checker.py` directly (see the
test in `verify/test_known_witnesses.py`), not merely copied on trust.

| file | m x n | edges (claimed) | edges (our check) | K_{3,3}-free (our check) |
|---|---|---|---|---|
| `z13_18_116_witness.csv` | 13x18 | 116 | 116 | yes |
| `z14_17_118_witness.csv` | 14x17 | 118 | 118 | yes |
| `z14_18_124_witness.csv` | 14x18 | 124 | 124 | yes |
| `z15_17_126_witness.csv` | 15x17 | 126 | 126 | yes |
| `z15_18_132_witness.csv` | 15x18 | 132 | 132 | yes |
| `z16_17_132_witness_seed201.csv` | 16x17 | 132 | 132 | yes |

`z16_17_132_witness_seed201.csv` is the **primary lower-bound witness**
for this project's target cell, `Z(16,17,3,3)`: it establishes
`Z(16,17,3,3) >= 132` on its own, independent of trusting the paper that
published it, since we re-derived the verdict ourselves from the raw
matrix. The generating method recorded in the source JSON metadata is
"degree-preserving stochastic edge-relocation search," seed 201 — noted
for context, but the checker's verdict does not depend on trusting that
description; it only depends on the matrix itself.

The published upper bound for the same cell, `Z(16,17,3,3) <= 133`, comes
from a different, older, independently-traced source (Collins, Riasanovsky,
Wallace, Radziszowski, arXiv:1604.01257, 2016, Table 4) and has **no**
known matching 133-edge construction as of this writing — see
`PROGRESS.md` for the full citation-chain verification, including
font-level confirmation that the 2016 authors marked this specific bound
as obtained by exhaustive computation without claiming it exact.
