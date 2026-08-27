# Build the search programs.
#
# `orderly` is the real generator; `brute` is a deliberately independent and
# deliberately simple searcher kept only to cross-check `orderly` on small
# cells. They are built from separate sources on purpose -- a shared helper
# would defeat the point of the cross-check.
#
# No optimisation beyond -O2: the searches are branch-bound, not
# arithmetic-bound, and -O3/-march=native produced no measurable difference
# while making the binary less portable for anyone reproducing a node count.

CC      ?= cc
CFLAGS  ?= -O2 -Wall -Wextra -std=c11

all: orderly brute

orderly: orderly.c
	$(CC) $(CFLAGS) -o $@ $<

brute: brute.c
	$(CC) $(CFLAGS) -o $@ $<

# Reproduce every claim in ../../EXACT_VALUES.md. Node counts, not seconds,
# are the invariant to compare -- wall-clock is not comparable across
# machines or across load conditions on the same machine.
verify-claims: orderly
	@echo "== lower bounds (expect FOUND + WITNESS_ROWS) =="
	./orderly -n 17 -m 8  --decide 74
	./orderly -n 17 -m 9  --decide 81
	./orderly -n 17 -m 10 --decide 90
	./orderly -n 17 -m 11 --decide 96
	@echo
	@echo "== upper bounds (expect EXHAUSTED) =="
	./orderly -n 17 -m 8  --decide 75
	./orderly -n 17 -m 9  --decide 82
	./orderly -n 17 -m 10 --decide 91 --assume 9:81
	./orderly -n 17 -m 11 --decide 97 --assume 9:81

# Agreement between the two independent searchers on small cells.
#
# NOTE ON A BUG THIS TARGET USED TO HAVE. An earlier version invoked
# `./brute -n $$n -m $$m --decide $$t`, but brute.c parses argv POSITIONALLY
# (`n=argv[1] m=argv[2] T=argv[3]`), so every cell silently ran as n=0,
# m=<n>, T=0. It also grepped brute's output for `status=`, a substring
# brute never prints. Either bug alone made the target print
# "agree on every small cell" unconditionally, no matter what the two
# programs computed -- a validation that validated nothing, while being
# cited as load-bearing evidence. Fixed: correct positional invocation, and
# both verdicts parsed from the tokens each program actually emits.
#
# Guards so it cannot silently pass again:
#   * counts cells compared and FAILS if that count is zero;
#   * requires BOTH verdicts to be non-empty for every cell, and fails on a
#     missing verdict rather than skipping the cell;
#   * asserts both FOUND and EXHAUSTED actually occur in the sweep, so a
#     degenerate range that only ever produces one verdict is rejected.
cross-check: orderly brute
	@cmp=0; agree=0; nfound=0; nexh=0; \
	for n in 4 5 6 7; do \
	  for m in 3 4 5 6; do \
	    for t in 6 8 10 12 14 16 18 20 24; do \
	      a=$$(./orderly -n $$n -m $$m --decide $$t 2>/dev/null | grep -o 'status=[A-Z]*' | sed 's/status=//'); \
	      b=$$(./brute $$n $$m $$t 2>/dev/null | awk '{print $$5}'); \
	      if [ -z "$$a" ] || [ -z "$$b" ]; then \
	        echo "FAIL: missing verdict n=$$n m=$$m t=$$t orderly='$$a' brute='$$b'"; exit 1; \
	      fi; \
	      cmp=$$((cmp+1)); \
	      if [ "$$a" != "$$b" ]; then \
	        echo "DISAGREEMENT n=$$n m=$$m t=$$t: orderly=$$a brute=$$b"; exit 1; \
	      fi; \
	      agree=$$((agree+1)); \
	      [ "$$a" = "FOUND" ] && nfound=$$((nfound+1)); \
	      [ "$$a" = "EXHAUSTED" ] && nexh=$$((nexh+1)); \
	    done; \
	  done; \
	done; \
	if [ "$$cmp" -eq 0 ]; then echo "FAIL: compared 0 cells"; exit 1; fi; \
	if [ "$$nfound" -eq 0 ]; then echo "FAIL: no FOUND verdict in sweep -- range is degenerate"; exit 1; fi; \
	if [ "$$nexh" -eq 0 ]; then echo "FAIL: no EXHAUSTED verdict in sweep -- range is degenerate"; exit 1; fi; \
	echo "cross-check PASSED: $$cmp cells compared, $$agree agreed ($$nfound FOUND, $$nexh EXHAUSTED)"

clean:
	rm -f orderly brute

.PHONY: all verify-claims cross-check clean
