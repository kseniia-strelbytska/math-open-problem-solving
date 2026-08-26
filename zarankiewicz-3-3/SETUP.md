# Environment setup

This records exactly how the Python environment for this problem was built,
so results are reproducible from scratch.

## Platform

- macOS-14.8.2-arm64-arm-64bit-Mach-O (Apple Silicon)
- `python3` on this machine: Python 3.14.6 (`/opt/homebrew/bin/python3`)
- Homebrew 6.0.18 available at `/opt/homebrew/bin/brew` (ended up not being
  needed — see below)

## Steps taken

```bash
cd zarankiewicz-3-3
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install numpy networkx
pip install "python-sat[pblib,aiger]"
pip install pytest
```

`pip install "python-sat[pblib,aiger]"` succeeded on the first try (it built
`pypblib` from source via a pyproject build backend, no issues) — no
Homebrew fallback (`brew install cadical` / `brew install kissat`) was
needed. This bundles native solver binaries as compiled extensions, so no
separate system-level SAT solver install is required.

Sanity-checked that the bundled SAT solvers actually load and solve on this
Python/platform combination (native extensions can be finicky across Python
versions):

```python
from pysat.solvers import Glucose3, Cadical153, Minisat22
for cls in [Glucose3, Cadical153, Minisat22]:
    s = cls()
    s.add_clause([1, 2])
    s.add_clause([-1])
    assert s.solve() is True
    s.delete()
```

All three (`Glucose3`, `Cadical153`, `Minisat22`) loaded and solved
correctly.

## Exact installed versions (`pip freeze` inside `.venv`)

```
attrs==26.1.0
bidict==0.22.1
funcy==1.18
iniconfig==2.3.0
networkx==3.6.1
numpy==2.5.2
packaging==26.3
pluggy==1.6.0
py-aiger==6.2.3
py-aiger-cnf==5.0.8
Pygments==2.21.0
pypblib==0.0.4
pyrsistent==0.19.3
pytest==9.1.1
python-sat==1.9.dev15
six==1.17.0
sortedcontainers==2.4.0
```

## Reproducing

```bash
cd zarankiewicz-3-3
python3 -m venv .venv
source .venv/bin/activate
pip install numpy==2.5.2 networkx==3.6.1 "python-sat[pblib,aiger]==1.9.dev15" pytest==9.1.1
```

(Note: `python-sat` 1.9.dev15 is a dev release pulled from PyPI at install
time; pin to whatever is latest if `==1.9.dev15` is no longer resolvable —
the SAT-solving toolchain is not yet used by the verification code in
`verify/`, only `numpy` and `networkx` are required to run
`verify/checker.py` and `verify/test_checker.py`. `python-sat` and `pytest`
are installed in preparation for the SAT-based upper-bound search planned
as follow-up work.)

## Running the checker's test suite

```bash
cd zarankiewicz-3-3
source .venv/bin/activate
python -m pytest verify/test_checker.py -v
# or, without pytest:
python verify/test_checker.py
```
