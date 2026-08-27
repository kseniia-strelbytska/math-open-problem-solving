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
cross-check: orderly brute
	@for n in 4 5 6 7; do \
	  for m in 3 4 5 6; do \
	    for t in 6 8 10 12 14 16 18 20; do \
	      a=$$(./orderly -n $$n -m $$m --decide $$t 2>/dev/null | grep -o 'status=[A-Z]*'); \
	      b=$$(./brute   -n $$n -m $$m --decide $$t 2>/dev/null | grep -o 'status=[A-Z]*'); \
	      if [ -n "$$a" ] && [ -n "$$b" ] && [ "$$a" != "$$b" ]; then \
	        echo "DISAGREEMENT n=$$n m=$$m t=$$t: orderly=$$a brute=$$b"; exit 1; \
	      fi; \
	    done; \
	  done; \
	done; echo "orderly and brute agree on every small cell tried"

clean:
	rm -f orderly brute

.PHONY: all verify-claims cross-check clean
