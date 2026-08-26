#!/bin/bash
# Disk guard for proof-logged SAT runs.
#
# WHY THIS EXISTS. kissat writes a DRAT proof line for every learnt clause,
# so a proof file grows without bound for as long as the solver runs. Measured
# on this machine (2026-08-26): ~1.8 MB/s uncompressed, ~0.94 MB/s through
# gzip, per solver process. With only ~17 GiB of free disk, three concurrent
# proof-logged runs fill the disk in well under two hours. A full disk would
# (a) corrupt every proof in flight, (b) potentially destabilise the machine.
#
# So each run gets an explicit byte budget, in priority order, and a global
# free-space floor. When a run exceeds its budget it is stopped -- its partial
# proof is deleted, because a truncated DRAT proof certifies nothing and only
# consumes space. When free space drops below the floor, runs are stopped in
# REVERSE priority order (stretch goals first) until the floor is cleared.
#
# MEMORY. This machine was under severe memory pressure when these runs were
# launched (12.87 GB of 14.34 GB swap in use). kissat has no --memory option,
# and macOS (Darwin 23.6) does NOT support `ulimit -v` or `ulimit -d` -- both
# refuse to be set ("cannot modify limit: Invalid argument") and a 3 GB
# allocation succeeded under an attempted 500 MB cap, verified directly. So
# there is no way to make the solver self-limit. This guard therefore also
# polls each solver's RSS and stops a run that exceeds its memory budget, so
# an over-large run degrades into an honestly-reported failure rather than
# destabilising the machine.
#
# This guard never claims anything about a proof. It only bounds resource use.
# Verification is a separate, independent step (see CERTIFICATE_LOG.md).

set -u

PROOF_DIR="$(cd "$(dirname "$0")" && pwd)/results/proofs"
LOG="$PROOF_DIR/guard.log"
INTERVAL=60

# Priority order: index 0 = highest priority (killed LAST).
# Fields: <stem> <proof_budget_bytes> <rss_budget_kb>
PRIORITY=(
  "z16_17_134_kissat_proof 7000000000 4000000"   # (a) PRIMARY: UNSAT => z(16,17;3) <= 133
  "z13_18_117_kissat_proof 5000000000 4000000"   # (b) UNSAT => z(13,18;3) = 116 exactly
  "z16_17_133_kissat_proof 2500000000 3000000"   # (c) STRETCH: UNSAT => z(16,17;3) = 132
)

FREE_FLOOR=3000000000   # 3 GB free disk: stop lowest-priority runs below this

say() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" >> "$LOG"; }

free_bytes() { df -k "$PROOF_DIR" | tail -1 | awk '{print $4 * 1024}'; }

# Stop the runner + its kissat child for one stem, and remove the partial proof.
stop_run() {
  local stem="$1" reason="$2"
  local pids
  pids=$(pgrep -f "$stem" || true)
  if [ -n "$pids" ]; then
    say "STOPPING $stem ($reason); pids: $(echo $pids | tr '\n' ' ')"
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null
    sleep 3
    pids=$(pgrep -f "$stem" || true)
    # shellcheck disable=SC2086
    [ -n "$pids" ] && kill -9 $pids 2>/dev/null
  fi
  for f in "$PROOF_DIR/$stem".drat "$PROOF_DIR/$stem".drat.gz; do
    if [ -f "$f" ]; then
      say "  deleting partial proof $f ($(wc -c < "$f") bytes) -- a truncated DRAT proof certifies nothing"
      rm -f "$f"
    fi
  done
}

alive() { pgrep -f "$1" > /dev/null 2>&1; }

say "guard started (interval ${INTERVAL}s, free floor ${FREE_FLOOR} bytes)"

while true; do
  free=$(free_bytes)
  report=""
  any_alive=0

  # Per-run proof-size and RSS budget enforcement.
  for entry in "${PRIORITY[@]}"; do
    set -- $entry
    stem="$1"; budget="$2"; rss_budget="$3"
    sz=0
    for f in "$PROOF_DIR/$stem".drat "$PROOF_DIR/$stem".drat.gz; do
      [ -f "$f" ] && sz=$(( sz + $(wc -c < "$f") ))
    done
    if alive "$stem"; then
      any_alive=1
      # Largest RSS (in KB) among this run's processes -- the kissat child is
      # normally the fat one.
      rss=0
      for p in $(pgrep -f "$stem"); do
        r=$(ps -o rss= -p "$p" 2>/dev/null | tr -d ' ')
        [ -n "$r" ] && [ "$r" -gt "$rss" ] && rss="$r"
      done
      report="$report $stem=${sz}B/${budget}B,rss=${rss}KB"
      if [ "$sz" -gt "$budget" ]; then
        stop_run "$stem" "proof exceeded its ${budget}-byte budget"
      elif [ "$rss" -gt "$rss_budget" ]; then
        stop_run "$stem" "RSS ${rss}KB exceeded its ${rss_budget}KB budget"
      fi
    else
      report="$report $stem=stopped(${sz}B)"
    fi
  done

  say "free=${free}B$report"

  # Global free-space floor: shed lowest priority first.
  if [ "$free" -lt "$FREE_FLOOR" ]; then
    say "FREE SPACE BELOW FLOOR (${free} < ${FREE_FLOOR}) -- shedding in reverse priority order"
    for (( i=${#PRIORITY[@]}-1; i>=0; i-- )); do
      set -- ${PRIORITY[$i]}
      stem="$1"
      if alive "$stem"; then
        stop_run "$stem" "global free-space floor breached"
        sleep 5
        free=$(free_bytes)
        say "  free after shedding $stem: ${free}B"
        [ "$free" -ge "$FREE_FLOOR" ] && break
      fi
    done
  fi

  if [ "$any_alive" -eq 0 ]; then
    say "no proof-logged runs alive; guard exiting"
    exit 0
  fi

  sleep "$INTERVAL"
done
