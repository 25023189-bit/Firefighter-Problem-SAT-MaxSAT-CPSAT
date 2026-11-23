# Reading and Reproducing the Results

## 1. Output files

All runners append one row per finished `(instance, D)` pair to a CSV file in `ket_qua/`:

| Solver | File pattern |
|---|---|
| Incremental SAT | `SAT_thuong_KQ_<date>.csv` |
| MaxSAT | `MaxSAT_KQ_<date>.csv` |
| CP-SAT | `CP_SAT_KQ_<date>.csv` |

Rows already present in any earlier file of the same solver are skipped, so an interrupted run can be resumed by running the same command again. Files are UTF-8 with a BOM (`utf-8-sig`).

## 2. Columns

| Column | Meaning |
|---|---|
| `File` | instance file name, e.g. `100_ep0.1_0_gilbert_3.in` (size, edge probability, graph index) |
| `Method` | `SAT_thuong`, `MaxSAT` or `CP_SAT` |
| `Nodes`, `Edges` | $n$ and $m$ |
| `Firefighters` | $D$ |
| `Variables`, `Clauses` | model size. `0` when the instance was solved by preprocessing alone. For CP-SAT the columns hold the number of variables and constraints in the CP-SAT model |
| `Encoding Time`, `Solving Time`, `Total Time` | seconds; the time limit applies to solving time only |
| `Status` | see section 3 |
| `Burned Nodes Found` | best number of burned vertices $K$ found (**lower is better**) |
| `Convergence Time` | the certified horizon $T_{ht}$ (`0` if solved by preprocessing) |

## 3. Status values

| Status | Written by | Meaning |
|---|---|---|
| `OPTIMAL` | all | $K$ is proven optimal |
| `TIMEOUT` | CP-SAT, `Sat_Thuong.py` | time limit reached; $K$ is the best found (an upper bound) |
| `SAT` | `file_run.py` (SAT) | same as `TIMEOUT` |
| `UNKNOWN` | `file_run.py` (MaxSAT) | no result within the limit; `Burned Nodes Found` may be empty |

Only `OPTIMAL` rows are proofs. All other rows are upper bounds. The files do not record a lower bound or gap; if you need one, `LB` is available from `Tien_Xu_Li.can_duoi`.

A note on timing: a row with `Solving Time` slightly or noticeably above the limit can occur, because model construction and solver start-up sit outside the measured solve window. One CP-SAT row (`100_ep0.1_0_gilbert_1.in`, `D=6`) shows 1619.6 s against a 1200 s limit.

## 4. Reference results

`results-BBGRL.csv` contains the reference values:

| Column | Meaning |
|---|---|
| `set` | benchmark set (`BBGRL`) |
| `n` | graph size (50, 100, 500, 1000) |
| `result` | number of burned vertices obtained by the reference method |
| `instance` | instance file name |
| `D` | number of firefighters |
| `runtime` | reference run time in seconds |
| `seed` | seed of the reference run |

The reference runtimes are capped at around 17 s for 100-vertex graphs, so it appears to be a time-limited method; this is an inference from the numbers, not a statement from the benchmark authors. Each size has 30 graphs and $D=1,\dots,10$, i.e. 300 cases per size.

## 5. Reproducing the comparison

```python
import glob
import pandas as pd

def load(pattern):
    df = pd.concat(
        pd.read_csv(f, encoding="utf-8-sig") for f in sorted(glob.glob(pattern))
    )
    return df.drop_duplicates(["File", "Firefighters"], keep="last")

ref = pd.read_csv("results-BBGRL.csv")
mine = load("ket_qua/CP_SAT_KQ*.csv")          # or SAT_thuong_KQ*, MaxSAT_KQ*

m = mine.merge(ref, left_on=["File", "Firefighters"], right_on=["instance", "D"])
m["K"] = pd.to_numeric(m["Burned Nodes Found"], errors="coerce")
m["diff"] = m["K"] - m["result"]               # < 0: better than the reference
m["proven"] = m["Status"] == "OPTIMAL"

m["cmp"] = m["diff"].apply(
    lambda x: "no value" if pd.isna(x) else "better" if x < 0 else "worse" if x > 0 else "equal"
)
print(m.groupby(["Nodes", "cmp"]).size().unstack(fill_value=0))
print(m.groupby("Nodes")["proven"].agg(["sum", "size"]))
```

Remove duplicate files first: if the same results were saved twice (for example copies with a `_1` suffix), `drop_duplicates` handles it, but the row counts printed by `glob` will be higher than the number of distinct cases.

## 6. Summary of the experiments

Time limit 1200 s per case, 30 graphs per size, $D=1,\dots,10$.

| Solver | Size | Cases run | Proven optimal | Better than ref. | Equal | Worse | No value |
|---|---:|---:|---:|---:|---:|---:|---:|
| CP-SAT | 50 | 300 | 300 | 2 | 298 | 0 | 0 |
| CP-SAT | 100 | 300 | 271 | 42 | 257 | 1 | 0 |
| CP-SAT | 500 | 300 | 92 | 3 | 126 | 171 | 0 |
| SAT | 50 | 300 | 276 | 0 | 280 | 20 | 0 |
| SAT | 100 | 300 | 201 | 3 | 206 | 85 | 6 |
| SAT | 500 | 40 | 10 | 1 | 13 | 25 | 1 |
| SAT | 1000 | 30 | 8 | 0 | 9 | 20 | 1 |
| MaxSAT | 50 | 147 | 128 | 1 | 127 | 0 | 19 |

Main conclusions:

1. Every proven-optimal result is at least as good as the reference; every "worse" result is a timeout upper bound.
2. Solvers agree with one another on all proven cases (no disagreement in 487 + 128 comparisons).
3. CP-SAT is the strongest back-end, proving all 50-vertex cases and 271 of 300 at 100 vertices.
4. The exact approach does not scale to 500 vertices and beyond within 1200 s.
