<div align="center">

<<<<<<< HEAD
# Firefighter Problem: SAT, MaxSAT & CP-SAT Solvers
=======
# 🔥 Firefighter Problem — SAT, MaxSAT & CP-SAT Solvers
>>>>>>> fd728c25e55b03a65986966a2443d87c7f520939

**Exact solving of the Firefighter Problem through propositional encodings, with bound-based preprocessing and incremental horizon search.**

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![SAT](https://img.shields.io/badge/SAT-Glucose3-orange)
![MaxSAT](https://img.shields.io/badge/MaxSAT-EvalMaxSAT-purple)
![CP-SAT](https://img.shields.io/badge/CP--SAT-OR--Tools-4285F4?logo=google&logoColor=white)
<<<<<<< HEAD
![License](https://img.shields.io/badge/License-All%20Rights%20Reserved-red)
=======
![License](https://img.shields.io/badge/License-MIT-green)
>>>>>>> fd728c25e55b03a65986966a2443d87c7f520939

</div>

---

## Table of Contents

1. [Overview](#overview)
2. [The Problem](#the-problem)
3. [Method](#method)
   - [Variables](#variables)
   - [Constraints](#constraints)
   - [Preprocessing](#preprocessing)
   - [Search Procedure](#search-procedure)
4. [Implemented Solvers](#implemented-solvers)
5. [Repository Structure](#repository-structure)
6. [Installation](#installation)
7. [Usage](#usage)
8. [Input & Output Formats](#input--output-formats)
9. [Experimental Results](#experimental-results)
10. [Scope & Limitations](#scope--limitations)
11. [Authors](#authors)
12. [License](#license)

---

## Overview

This project solves the **Firefighter Problem** *exactly* by reducing it to propositional logic and handing the result to modern solvers. Three back-ends share one underlying model:

| Back-end | File | Idea |
|---|---|---|
| **SAT** (incremental) | `Sat_Thuong.py` | Glucose3 + totalizer + assumptions; tightens the burned-vertex threshold one step at a time. |
| **MaxSAT** | `Max_SAT.py` | Hard clauses for the dynamics, soft units `¬b(v,T)` for the objective, solved by EvalMaxSAT. |
| **CP-SAT** | `cpSat.py` | The same Boolean model plus native linear constraints and a real objective, solved by Google OR-Tools. |

The SAT and CP-SAT solvers share a common **preprocessing** stage (distance-based unit propagation, lower bound, greedy upper bound, horizon bounds) that often shrinks the instance substantially or solves it outright.

Results are validated against the reference values of the **BBGRL** benchmark set (`results-BBGRL.csv`).

## The Problem

Given an undirected graph $G=(V,E)$, a set $B\subseteq V$ of initially burning vertices and an integer $D$:

- At every time step, the fire spreads from each burning vertex to all of its **unprotected, non-burning** neighbours.
- Before the fire spreads, the firefighter may **protect up to $D$ new vertices**. A protected vertex can never burn, and a burning vertex can never be protected.
- The process stops when the fire can no longer spread.

**Goal:** choose the protection schedule that minimises the number of burned vertices at the end.

## Method

### Variables

Time is discretised as $t \in \{0,1,\dots,T\}$.

| Variable | Range | Meaning |
|---|---|---|
| `b[v,t]` | 0 ≤ t ≤ T | vertex *v* is burning at time *t* |
| `d[v,t]` | 0 ≤ t ≤ T | vertex *v* is protected at time *t* |
| `a[v,t]` | 1 ≤ t ≤ T | a firefighter is **newly** placed on *v* at step *t* |
| `h[t]` | 1 ≤ t ≤ T | "fire is contained at step *t*" flag (SAT solver only) |
| `o[T,j]` | 1 ≤ j ≤ UB | totalizer output: $\sum_v b_{v,T} \ge j$ (SAT solver only) |

### Constraints

| # | Clause | Meaning |
|---|---|---|
| 1–3 | `b(v,0)` for v∈B · `¬b(v,0)` for v∉B · `¬d(v,0)` | Initial state |
| 4 | `¬b(v,t-1) ∨ b(v,t)` | Burning is permanent |
| 5 | `¬d(v,t-1) ∨ d(v,t)` | Protection is permanent |
| 6 | `¬d(v,t) ∨ ¬b(v,t)` | Never both burning and protected |
| 7–8 | `a(v,t) ⇔ d(v,t) ∧ ¬d(v,t-1)` (3 clauses) | Marks a *newly* placed firefighter |
| 9 | `Σ_v a(v,t) ≤ D` | Resource limit per step (sequential counter in SAT/MaxSAT, linear constraint in CP-SAT) |
| 10 | `¬b(u,t-1) ∨ d(v,t) ∨ b(v,t)`  ∀{u,v}∈E | Fire spreads unless the target is protected |
| 11 | `¬b(v,t) ∨ b(v,t-1) ∨ ⋁_{u∈N(v)} b(u,t-1)` | Vertices burn only for a reason |
| 12 | `¬h(t) ∨ ¬b(u,t) ∨ b(v,t) ∨ d(v,t)`  ∀{u,v}∈E | Containment: no further spread possible at *t* |
| 13 | `¬b(v,t)` for 1 ≤ t < δ(v) | Distance-based unit clauses (see below) |

The objective is to minimise $\sum_{v} b_{v,T}$.

<<<<<<< HEAD
> Full details: [`docs/MODEL_AND_ALGORITHMS.md`](docs/MODEL_AND_ALGORITHMS.md). Reading the output files and reproducing the comparison: [`docs/RESULTS.md`](docs/RESULTS.md).
=======
> The full formal write-up of the encoding (version 4, final) is in [`docs/Encode.pdf`](docs/Encode.pdf).
>>>>>>> fd728c25e55b03a65986966a2443d87c7f520939

### Preprocessing

Implemented in `Tien_Xu_Li.py` and shared by the SAT and CP-SAT solvers.

| Step | Description |
|---|---|
| **Distance map δ(v)** | Multi-source BFS from *B*. Fire cannot reach *v* before step δ(v), so `¬b(v,t)` is added as a unit clause for all `1 ≤ t < δ(v)`. Unreachable vertices have δ = ∞ and never burn. |
<<<<<<< HEAD
| **Lower bound** | `LB = \|B\| + max(0, \|N(B)∖B\| − D)` — the first wave of fire threatens `N(B)∖B`, and at most *D* of those vertices can be saved. |
| **Upper bound** | Greedy simulation with three selection rules: **C1** lowest id, **C2** highest degree, **C3** random (20 runs, fixed seed). `(UB, T₀)` is the lexicographic minimum of `(burned, rounds)`. |
| **Early exit** | If `UB = LB` the greedy answer is provably optimal; no solver call is made (reported as `optimal(greedy)`). |
| **Horizon bounds** | `T_s = ⌈(n−\|B\|)/(D+1)⌉`, `T_UB = UB − \|B\|`, `T_LB = ⌊(n−LB)/D⌋ + 1`, and `T_ht = max(1, min(T_s, T_UB, T_LB))` — a horizon beyond which no improvement is possible. The solver starts at `T_init = min(T_ht, ⌈1.5·n⌉)`; since `T_ht ≤ n`, this always equals `T_ht` (see the note below the search procedure). |
=======
| **Lower bound** | `LB = |B| + max(0, |N(B)∖B| − D)` — the first wave of fire threatens `N(B)∖B`, and at most *D* of those vertices can be saved. |
| **Upper bound** | Greedy simulation with three selection rules: **C1** lowest id, **C2** highest degree, **C3** random (20 runs, fixed seed). `(UB, T₀)` is the lexicographic minimum of `(burned, rounds)`. |
| **Early exit** | If `UB = LB` the greedy answer is provably optimal; no solver call is made (reported as `optimal(greedy)`). |
| **Horizon bounds** | `T_s = ⌈(n−|B|)/(D+1)⌉`, `T_UB = UB − |B|`, `T_LB = ⌊(n−LB)/D⌋ + 1`, and `T_ht = max(1, min(T_s, T_UB, T_LB))` — a horizon beyond which no improvement is possible. The starting horizon is `T_init = min(T_ht, ⌈1.5·n⌉)`. |
>>>>>>> fd728c25e55b03a65986966a2443d87c7f520939

### Search Procedure

```text
<<<<<<< HEAD
K ← UB,  T ← T_init                  # in the current code T_init = T_ht
=======
K ← UB,  T ← T_init
>>>>>>> fd728c25e55b03a65986966a2443d87c7f520939
build steps 0..T, unit clauses (13), containment flag, totalizer on {b(v,T)}
loop:
    if K − 1 < LB:                       return K              # proven optimal
    r ← Solve( assumptions: h(T), ¬h(t<T), ¬o(T, K) )         # "is there a solution with ≤ K−1 burned?"
    if r = SAT:                          K ← #{v : b(v,T)}    # improve incumbent
    elif r = UNSAT and T < T_ht:         T ← min(2T, T_ht)    # extend horizon incrementally
                                         add steps, new totalizer
    else:                                return K              # UNSAT at T = T_ht → optimal
```

<<<<<<< HEAD
> **Note on the horizon.** The horizon-extension branch (`T < T_ht`) is implemented, but it is **never taken** with the current preprocessing: `T_init = min(T_ht, ⌈1.5·n⌉)` and `T_ht ≤ T_s ≤ n`, so `T_init = T_ht` and the solver encodes the full certified horizon from the start. The number of greedy rounds `T0` is computed but is not used to choose `T_init`. Starting from a shorter horizon (for example `⌈1.5·T0⌉`) would keep the first formulas smaller and is a natural improvement; it has not been evaluated here.

Key design points:

- **Incremental solving.** Glucose3 keeps its learnt clauses; the threshold *K* and the horizon flag `h(T)` are enforced through **assumptions**, never by rebuilding the formula.
- **Certified horizon.** `T_ht` is a horizon beyond which no better solution can exist, so UNSAT at `T = T_ht` proves optimality.
=======
Key design points:

- **Incremental solving.** Glucose3 keeps its learnt clauses; the threshold *K* and the horizon flag `h(T)` are enforced through **assumptions**, never by rebuilding the formula.
- **Horizon doubling.** Starting with a short horizon keeps the formula small; the horizon grows geometrically only when the current one cannot be proven sufficient.
>>>>>>> fd728c25e55b03a65986966a2443d87c7f520939
- **Timeout handling.** On timeout the best incumbent *K* found so far is reported with status `TIMEOUT` (an upper bound, not a proof).

## Implemented Solvers

### 1. SAT (`Sat_Thuong.py`)
Incremental Glucose3 (PySAT) with sequential-counter cardinality constraints, an `ITotalizer` for the objective, and the full preprocessing pipeline. The default 1200 s limit applies to solving time only.

### 2. MaxSAT (`Max_SAT.py`)
Plain model with fixed horizon `T = n`, hard clauses for the dynamics and one weight-1 soft clause `¬b(v,T)` per vertex, solved by **EvalMaxSAT** (via `hermax`). It performs **no preprocessing** and has no internal timeout (the experiment runner kills it at the limit). It also contains a built-in **schedule verifier** that re-checks the returned model against every rule of the problem.

### 3. CP-SAT (`cpSat.py`) — added after SAT and MaxSAT
Same Boolean dynamics, but with OR-Tools CP-SAT:

- At-most-*D* is a native **linear constraint** (no sequential counter).
- The objective `Minimize Σ b(v,T)` is bounded by `LB ≤ Σ b(v,T) ≤ K−1`.
<<<<<<< HEAD
- Uses 8 workers. CP-SAT has no assumptions / incremental solving, so the model is **rebuilt** whenever it is solved again; with the current `T_init = T_ht` it is normally built once and solved to optimality (or until the time limit).
=======
- Uses 8 workers; the model is **rebuilt for each horizon** because CP-SAT has no assumptions / incremental solving.
>>>>>>> fd728c25e55b03a65986966a2443d87c7f520939
- Containment (`¬b(u,T) ∨ b(v,T) ∨ d(v,T)`) is a hard constraint at the final step.

## Repository Structure

```text
.
├── BBGRL/                  # Benchmark instances (*.in)
├── ket_qua/                # Output CSV files (created automatically)
├── docs/
<<<<<<< HEAD
│   ├── MODEL_AND_ALGORITHMS.md   # Model, preprocessing, search, back-ends
│   ├── RESULTS.md                # Output format, reference file, reproduction
│   └── Encode.pdf                # Formal description of the encoding (v4)
=======
│   └── Encode.pdf          # Formal description of the encoding (v4)
>>>>>>> fd728c25e55b03a65986966a2443d87c7f520939
├── GraphParser.py          # .in reader → networkx graph, burning set
├── Tien_Xu_Li.py           # Preprocessing: δ, LB, UB (greedy), T bounds
├── Sat_Thuong.py           # Incremental SAT solver (Glucose3)
├── Max_SAT.py              # MaxSAT solver (EvalMaxSAT) + schedule verifier
├── cpSat.py                # CP-SAT solver (OR-Tools)
├── file_run.py             # Experiment runner (SAT / MaxSAT), isolated subprocess per run
├── results-BBGRL.csv       # Reference results used for comparison
├── LICENSE
└── README.md
```

## Installation

```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install networkx python-sat ortools psutil
pip install hermax               # only needed for the MaxSAT solver
```

Requires **Python 3.10+**.

## Usage

### Run the SAT or MaxSAT experiments

```bash
# SAT (default), D = 1..10, all instances in BBGRL/
python file_run.py --dir BBGRL

# Only graphs with 50 and 100 vertices, 20-minute limit
python file_run.py --dir BBGRL --n 50 100 --gioi-han 1200

# Choose methods and values of D
python file_run.py --phuong-phap SAT_thuong MaxSAT --D 1-5 8 10
```

| Option | Default | Description |
|---|---|---|
| `--dir` | `xyz` | Folder with `.in` instances (use `BBGRL`) |
| `--phuong-phap` | `SAT_thuong` | `SAT_thuong`, `MaxSAT`, or both |
| `--D` | `1-10` | Firefighters per step; accepts `2`, `1 2 3`, `1-10`, `1,2,5-7` |
| `--n` | all | Keep only instances with these vertex counts |
| `--gioi-han` | `1200` | Time limit per case (seconds) |
| `--so-lan` | `1` | Repetitions |
| `--limit-files` | – | Run only the first *k* files |
| `--thu-muc-ket-qua` | `ket_qua` | Output folder |
| `--tiep-tuc` | – | Resume from an existing CSV |

Each run executes in an **isolated subprocess** that is killed on timeout, so a memory blow-up or hang in one case cannot stop the whole experiment.

### Run CP-SAT

```bash
python cpSat.py
```

Reads `BBGRL/`, runs `D = 1..10` with a 1200 s limit, and writes `ket_qua/CP_SAT_KQ_<date>.csv`.

### Resume after interruption

All runners append one row per finished `(instance, D)` pair and skip pairs already present in any earlier CSV. Press `Ctrl+C` at any time and re-run the same command to continue.

### Use as a library

```python
from GraphParser import doc_du_lieu_do_thi
from Sat_Thuong import giai_sat_thuong

G, V, Binit = doc_du_lieu_do_thi("BBGRL/50_ep0.1_0_gilbert_1.in")
status, burned, t_enc, t_solve, n_vars, n_clauses = giai_sat_thuong(G, V, Binit, D=2)
print(status, burned)            # e.g. optimal 7
```

## Input & Output Formats

### Instance format (`.in`)

Whitespace-separated integers:

```text
graph_id  n  m  param4  |B|
<|B| burning vertices>
<m edges: u v>
```

Vertex numbering can be 0-based or 1-based; 1-based files are detected and converted automatically. Self-loops and duplicate burning vertices are removed with a warning.

### Output CSV

| Column | Description |
|---|---|
| `File`, `Method` | Instance name and solver (`SAT_thuong`, `MaxSAT`, `CP_SAT`) |
| `Nodes`, `Edges` | Graph size |
| `Firefighters` | *D* |
| `Variables`, `Clauses` | Model size (0 if solved by preprocessing) |
| `Encoding Time`, `Solving Time`, `Total Time` | Seconds |
| `Status` | `OPTIMAL`, or `SAT` / `TIMEOUT` / `UNKNOWN` when optimality was not proven |
| `Burned Nodes Found` | Best number of burned vertices found |
| `Convergence Time` | `T_ht`, the horizon bound (0 if solved by preprocessing) |

## Experimental Results

The reference file `results-BBGRL.csv` contains BBGRL values (columns `n, result, instance, D, runtime`) for graphs with 50, 100, 500 and 1000 vertices, `D = 1..10`, 30 graphs per size. The `result` column is compared with `Burned Nodes Found` (**lower is better**). All solvers used a **1200 s** limit on solving time. A result is **proven** when the solver reports `OPTIMAL`; otherwise it is only an upper bound.

### Coverage and optimality

| Solver | Graph size | Cases run | Proven optimal | Not proven |
|---|---:|---:|---:|---:|
| **CP-SAT** | 50 | 300 | **300** | 0 |
| | 100 | 300 | 271 | 29 |
| | 500 | 300 | 92 | 208 |
| **SAT** (incremental) | 50 | 300 | 276 | 24 |
| | 100 | 300 | 201 | 99 |
| | 500 | 40 | 10 | 30 |
| | 1000 | 30 | 8 | 22 |
| **MaxSAT** (EvalMaxSAT) | 50 | 147 | 128 | 19 |

MaxSAT was only run on part of the 50-vertex set (no preprocessing, `T = n`), and 19 of those cases produced no result within the limit.

### Comparison with BBGRL

| Solver | Size | Better than BBGRL | Equal | Worse | No value |
|---|---:|---:|---:|---:|---:|
| **CP-SAT** | 50 | 2 | 298 | 0 | 0 |
| | 100 | 42 | 257 | 1 | 0 |
| | 500 | 3 | 126 | 171 | 0 |
| **SAT** | 50 | 0 | 280 | 20 | 0 |
| | 100 | 3 | 206 | 85 | 6 |
| | 500 | 1 | 13 | 25 | 1 |
| | 1000 | 0 | 9 | 20 | 1 |
| **MaxSAT** | 50 | 1 | 127 | 0 | 19 |

Key observations:

- **Every proven-optimal result is at least as good as BBGRL.** No proven-optimal result of any solver is worse than the reference.
- **The solvers agree with each other.** Wherever two solvers both proved optimality on the same case (487 cases CP-SAT vs SAT, 128 cases CP-SAT vs MaxSAT), the burned-vertex counts were identical — no disagreement at all. This is strong evidence that the encodings are correct.
- **CP-SAT is the strongest back-end.** It proves all 300 cases at 50 vertices and 271/300 at 100 vertices, versus 276 and 201 for incremental SAT. At 100 vertices it improves on the reference in 42 cases (23 of them proven optimal); the largest gaps are 33 (`100_ep0.1_0_gilbert_2`, D = 7), 19 (`100_ep0.1_0_gilbert_5`, D = 9) and 13 (`100_ep0.075_0_gilbert_3`, D = 6).
- **Every "worse" result is a timeout.** At 50 vertices all 20 cases where SAT is worse than BBGRL are unproven; at 100 vertices all 85 are unproven for SAT and the single one for CP-SAT is a timeout (`100_ep0.1_0_gilbert_1`, D = 6).
- **Beyond 100 vertices the exact approach breaks down.** At 500 vertices CP-SAT proves only 92/300 cases and is worse than BBGRL in 171 cases; at 1000 vertices SAT proves 8/30.

### Running time (solving time, seconds)

| Solver | Size | Mean | Max |
|---|---:|---:|---:|
| CP-SAT | 50 | 2.0 | 39.8 |
| CP-SAT | 100 | 211 | 1620 |
| CP-SAT | 500 | 841 | 1344 |
| SAT | 50 | 152 | 1214 |
| SAT | 100 | 398 | 1250 |
| MaxSAT | 50 | 67 | 952 |
| BBGRL (reference) | 50 / 100 / 500 / 1000 | 2.8 / 7.5 / 54 / 111 | 8.4 / 16.9 / 86 / 172 |

Means include the many easy cases that preprocessing solves in about zero time, so medians are far lower. The reference runtimes are capped at roughly 17 s for 100 vertices, which suggests a time-limited method, whereas the exact solvers here may run for up to 20 minutes per case.

Raw results are in `ket_qua/` (`CP_SAT_KQ_*.csv`, `SAT_thuong_KQ_*.csv`, `MaxSAT_KQ_*.csv`).

## Scope & Limitations

- **Intended scale: up to ~100 vertices.** At 100 vertices CP-SAT already times out on about 10 % of the cases (29/300, mostly mid-range *D*, where the search space is largest).
- **500 vertices and beyond:** the models grow to hundreds of thousands of variables and clauses, and solution quality degrades — at 500 vertices CP-SAT proves only 92/300 cases and its time-limited upper bounds are worse than the reference in 171 cases. These sizes are outside the practical range of the exact approach.
- A `TIMEOUT` / `SAT` / `UNKNOWN` status means the reported value is an **upper bound only**.
<<<<<<< HEAD
- The CP-SAT solver does not support incremental solving, so any re-solve rebuilds the model.
- Wall-clock overhead (model construction, worker start-up) can make a measured solving time exceed the configured limit (one CP-SAT case reached 1620 s against a 1200 s limit).
=======
- The CP-SAT solver does not support incremental solving, so it rebuilds the model for every horizon.
- Wall-clock overhead (model construction, worker start-up) can make a measured solving time slightly exceed the configured limit.
>>>>>>> fd728c25e55b03a65986966a2443d87c7f520939

## Authors

| Contributor | Role |
|---|---|
| **Nguyễn Kim Trung Đức** | Problem formulation and the SAT encoding (original idea and model design) |
| **Bùi Thế Dũng** | Implementation of all solvers (SAT, MaxSAT, CP-SAT), preprocessing code, and experimental evaluation |

The CP-SAT solver was added after the initial SAT and MaxSAT experiments.

## License

<<<<<<< HEAD
This repository is published for **viewing and reference only**. Copyright © 2026 Nguyễn Kim Trung Đức and Bùi Thế Dũng. **All rights reserved.** You may not copy, modify, redistribute or use the code, or derived work, without written permission from the authors. See [LICENSE](LICENSE) for details.

The benchmark instances (`BBGRL/`) and the reference file `results-BBGRL.csv` belong to their original authors and are **not** covered by this license; obtain them from the original source.
=======
Released under the [MIT License](LICENSE).
>>>>>>> fd728c25e55b03a65986966a2443d87c7f520939

If you use this work in academic research, please cite it:

```bibtex
@software{firefighter_sat,
  author  = {Nguyễn Kim Trung Đức and Bùi Thế Dũng},
  title   = {Firefighter Problem: SAT, MaxSAT and CP-SAT Solvers},
  year    = {2026},
  url     = {https://github.com/<your-username>/<repo-name>}
}
```
