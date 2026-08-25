# Progress log

Dated, honest log of what was tried, what worked, what didn't, and why.
Negative results and abandoned approaches are kept here, not deleted —
they're part of the evidence trail for the reviewer and for anyone picking
this up later. Follow the working discipline in `README.md` — in
particular, check this log before starting a new approach so a dead end
isn't silently repeated.

### Entry template for any attempted approach

```
### <date> — <approach name>

- What it is / what it's trying to establish.
- Lemmas or results invoked, with exact hypotheses, and confirmation each
  hypothesis actually holds here (or an explicit "unverified assumption"
  flag if it doesn't hold or can't be checked).
- What was checked to try to break it (small cases, boundary cases,
  counterexample search) before trusting it further.
- Outcome: refined / recombined-with-<X> / abandoned / promising, pending.
- Confidence: overall __%, weakest step (name it) __%. If these diverge,
  say why.
- Next rotation: refine this / recombine with <earlier attempt> / try a
  genuinely different strategy (name the area).
```

## 2026-08-25

- Selected `Z(16,17,3,3)` as the primary target after a broader survey of
  open math problems (see repo history / PR description for the survey).
  Known bounds at selection time: `132 <= Z(16,17,3,3) <= 133`
  (arXiv:2608.08154, Aug 2026; upper bound explicitly flagged by its own
  authors as not independently verified).
- Wrote acceptance criteria and plan (`README.md`) before writing any
  search or verification code.
- Local environment check: Python 3.14 available, `z3` installed via
  Homebrew, no SAT solver binaries (kissat/cadical/minisat/glucose) or
  Python packages (numpy, python-sat, networkx) installed yet — these are
  next steps, not assumptions.
