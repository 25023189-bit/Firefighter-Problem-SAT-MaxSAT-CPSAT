# Model and Algorithms

This document describes the propositional model of the Firefighter Problem used by all solvers in this repository, the preprocessing, the search procedure, and how the three back-ends (SAT, MaxSAT, CP-SAT) differ. The encoding and model design are due to Nguyễn Kim Trung Đức; the implementation is by Bùi Thế Dũng.

## 1. Problem

Input: an undirected simple graph $G=(V,E)$ with $n=|V|$ vertices, a non-empty set $B\subseteq V$ of initially burning vertices, and an integer $D\ge 1$ (firefighters per step).

Every vertex is *untouched*, *burning* or *protected*; burning and protected are absorbing. At each step $t\ge 1$:

1. up to $D$ untouched vertices are protected;
2. the fire spreads simultaneously from every vertex that was burning before the step to all of its neighbours that are not protected.

The process ends when no burning vertex has an untouched neighbour. The objective is to minimise the number $K$ of burned vertices at the end (equivalently, maximise the number $n-K$ of saved vertices).

## 2. Notation

| Symbol | Meaning |
|---|---|
| $N(v)$, $N(S)$ | neighbours of a vertex / of a set |
| $\delta(v)$ | distance from $B$ to $v$ (multi-source BFS), $\infty$ if unreachable |
| $L$, $U$ | lower and upper bound on the optimal number of burned vertices |
| $T$ | time horizon, steps $t\in\{0,\dots,T\}$ |
| $K$ | current threshold / incumbent value |
| $T_0$ | number of rounds of the greedy solution that gives $U$ |
| $T_s$, $T_{UB}$, $T_{LB}$ | the three horizon bounds |
| $T_{ht}$ | certified horizon, $\max(1,\min(T_s,T_{UB},T_{LB}))$ |

## 3. Variables

| Variable | Range | Meaning |
|---|---|---|
| `b[v,t]` | $0\le t\le T$ | $v$ is burning after step $t$ |
| `d[v,t]` | $0\le t\le T$ | $v$ is protected after step $t$ |
| `a[v,t]` | $1\le t\le T$ | a firefighter is newly placed on $v$ at step $t$ |
| `h[t]` | $1\le t\le T$ | containment flag for horizon $t$ (incremental SAT only) |
| `o[T,j]` | $1\le j\le U$ | totalizer output: $\sum_v b_{v,T}\ge j$ (incremental SAT only) |

## 4. Constraints

Initial state:

```
(b[v,0])           for v in B
(¬b[v,0])          for v not in B
(¬d[v,0])          for all v
```

State persistence and exclusion (all $v$, $1\le t\le T$):

```
¬b[v,t-1] ∨ b[v,t]            burning is permanent
¬d[v,t-1] ∨ d[v,t]            protection is permanent
¬b[v,t]  ∨ ¬d[v,t]            never both
```

New firefighters:

$$a_{v,t}\iff d_{v,t}\land\lnot d_{v,t-1}$$

```
¬a[v,t] ∨ d[v,t]
¬a[v,t] ∨ ¬d[v,t-1]
a[v,t] ∨ ¬d[v,t] ∨ d[v,t-1]
```

Resource limit (one at-most-$D$ counter per step):

$$\sum_{v\in V} a_{v,t}\le D,\qquad 1\le t\le T$$

Fire propagation, both directions of every edge $\{u,v\}\in E$:

```
¬b[u,t-1] ∨ d[v,t] ∨ b[v,t]
```

No spontaneous burning:

```
¬b[v,t] ∨ b[v,t-1] ∨ OR_{u in N(v)} b[u,t-1]
```

Containment at horizon $T$, both directions of every edge (guarded by the flag `h[T]` in the incremental SAT solver, a hard constraint in CP-SAT):

```
¬h[T] ∨ ¬b[u,T] ∨ b[v,T] ∨ d[v,T]
```

Distance-based unit clauses (preprocessing, section 5.1):

```
¬b[v,t]   for 1 ≤ t < δ(v)
```

Objective: minimise $\sum_v b_{v,T}$.

**Size.** The model has $3n(T+1)$ semantic variables plus cardinality auxiliaries, and $O((n+m)\,T)$ clauses. For example, a 50-vertex instance with $D=1$ has $T_{ht}=25$ and $3\cdot 50\cdot 26=3{,}900$ variables, which is exactly the value reported in the CP-SAT result files.

## 5. Preprocessing

Implemented in `Tien_Xu_Li.py`; used by the SAT and CP-SAT solvers (the MaxSAT solver uses none of it).

### 5.1 Distances and unit clauses
A multi-source BFS from $B$ gives $\delta(v)$. Fire cannot reach $v$ before step $\delta(v)$, hence `¬b[v,t]` for all $1\le t<\delta(v)$.

### 5.2 Lower bound

$$L=|B|+\max\bigl(0,\;|N(B)\setminus B|-D\bigr)$$

All vertices of $B$ burn, and the first protection step can save at most $D$ of the $|N(B)\setminus B|$ threatened vertices.

### 5.3 Greedy upper bound
Start with $F=B$ (burning), $P=\emptyset$ (protected), $r=0$. Repeat:

1. $W=N(F)\setminus(F\cup P)$ (threatened vertices);
2. if $W=\emptyset$, stop and return $(|F|,r)$;
3. choose $S\subseteq W$ with $|S|=\min(D,|W|)$;
4. $P\leftarrow P\cup S$, $F\leftarrow F\cup(W\setminus S)$, $r\leftarrow r+1$.

Selection rules: **C1** lowest vertex id, **C2** highest degree (ties by id), **C3** random (20 runs, fixed seed). $(U,T_0)$ is the lexicographic minimum of $(|F|,r)$ over all runs.

### 5.4 Early exit
If $U=L$, the greedy solution is optimal and no solver is called (status `optimal(greedy)`).

### 5.5 Horizon bounds

$$T_s=\Bigl\lceil\frac{n-|B|}{D+1}\Bigr\rceil,\quad T_{UB}=U-|B|,\quad T_{LB}=\Bigl\lfloor\frac{n-L}{D}\Bigr\rfloor+1,\quad T_{ht}=\max\bigl(1,\min(T_s,T_{UB},T_{LB})\bigr)$$

Justification sketch (for an optimal solution that is *canonical*, i.e. protects exactly $D$ untouched vertices in every step before the last one, which never hurts):

- **$T_s$.** Each step before the last burns at least one new vertex and protects $D$. After $T-1$ steps at least $|B|+(D+1)(T-1)$ vertices are burning or protected, and at least one vertex is still untouched.
- **$T_{UB}$.** An improving solution has $K\le U-1$, and $K\ge |B|+T-1$ because each of the first $T-1$ steps burns a new vertex.
- **$T_{LB}$.** The $D(T-1)$ protected vertices are disjoint from the final burned set, which has at least $L$ vertices, so $L+D(T-1)\le n$.

Consequently, if a solution better than the incumbent exists, one exists that is contained within $T_{ht}$ steps. **An UNSAT answer at $T=T_{ht}$ therefore proves the incumbent optimal.**

## 6. Search procedure (incremental SAT)

```text
K ← U,  T ← T_init
build steps 0..T, unit clauses, containment flag h[T], totalizer on {b[v,T]}
loop:
    if K − 1 < L:                    return K           # optimal
    r ← Solve( h[T], ¬h[t] for t<T, ¬o[T,K] )           # ≤ K−1 burned?
    if r = SAT:                      K ← #{v : b[v,T]}  # new incumbent
    elif r = UNSAT and T < T_ht:     T ← min(2T, T_ht)  # extend horizon
                                     add steps, containment, new totalizer
    else:                            return K           # UNSAT at T = T_ht
```

Implementation facts:

- The solver is **Glucose3** (PySAT). The threshold $K$ and the containment flag are passed as **assumptions**, so learnt clauses are preserved across queries.
- Output $o_{T,j}$ of the totalizer means $\sum_v b_{v,T}\ge j$; assuming $\lnot o_{T,K}$ enforces "at most $K-1$ burned".
- Time limit: solving time only (default 1200 s). On timeout the best incumbent $K$ is returned with status `TIMEOUT`/`SAT`, which is an upper bound without proof.
- **Initial horizon.** The code uses $T_{init}=\min(T_{ht},\lceil 1.5\,n\rceil)$. Because $T_{ht}\le T_s\le n$, this always equals $T_{ht}$, so the horizon-extension branch is implemented but not exercised: the full certified horizon is encoded from the start. Choosing a smaller start, for example $\lceil 1.5\,T_0\rceil$, would be a straightforward way to keep the first formulas smaller.

## 7. The three back-ends

| | SAT (`Sat_Thuong.py`) | MaxSAT (`Max_SAT.py`) | CP-SAT (`cpSat.py`) |
|---|---|---|---|
| Solver | Glucose3 (PySAT) | EvalMaxSAT (`hermax`) | OR-Tools CP-SAT, 8 workers |
| Horizon | $T_{init}=T_{ht}$ (extension implemented) | fixed $T=n$ | $T_{init}=T_{ht}$ (extension implemented) |
| Preprocessing | full (sections 5.1–5.5) | none | full |
| Objective | threshold via totalizer + assumptions | one soft clause `¬b[v,T]` per vertex | `Minimize Σ b[v,T]`, with $L\le\sum\le K-1$ |
| At-most-$D$ | sequential counter | sequential counter | native linear constraint |
| Containment | guarded by flag `h[T]` | not needed (T = n) | hard constraint at step $T$ |
| Incremental | yes (assumptions) | no | no (model rebuilt if re-solved) |
| Timeout | internal, solve time only | none; killed by the runner | internal, `max_time_in_seconds` |
| Result check | – | built-in schedule verifier | – |

The MaxSAT back-end is intentionally the plainest model and serves as a baseline; the CP-SAT back-end was added later, after the SAT and MaxSAT experiments.

## 8. Correctness evidence

No solver output is trusted on its own:

- On every case where two solvers both proved optimality, the burned-vertex counts were identical (487 cases CP-SAT vs SAT, 128 cases CP-SAT vs MaxSAT; zero disagreements).
- `Max_SAT.py` re-checks the returned model against every rule of the dynamics (initial state, monotonicity, exclusion, propagation, resource limit).
- No proven-optimal result is worse than the BBGRL reference.

See [RESULTS.md](RESULTS.md) for the numbers.
