import argparse
import math
import os
import random
import time
from itertools import combinations

import networkx as nx
from pysat.card import CardEnc, EncType
from pysat.formula import IDPool
from pysat.solvers import Solver

vpool = IDPool()
b_var = {}
d_var = {}

for t in range (T + 1):
    for v in V:
        b_var[(v, t)] = vpool.id(f'b_{v}_{t}')
        d_var[(v, t)] = vpool.id(f'd_{v}_{t}')

for v in V:
    if v in Binit:
        clauses.append([b_var[(v, 0)]])
    else:
        clauses.append([-b_var[(v, 0)]])
    clauses.append([-d_var[(v, 0)]])

for t in range (1, T + 1):
    for v in V:
        clauses.append([-b_var[(v, t-1)], b_var[(v, t)]])
        clauses.append([-d_var[(v, t-1)], d_var[(v, t)]])

for t in range (T + 1):
    for v in V:
    clauses.append([-b_var[(v, t)], -d_var[(v, t)]])

for v in V:
    for u in G.neighbors(v):
        for t in range (1, T + 1):
            clauses.append([-b_var[(v, t-1)], b_var[(u, t)], d_var[(u, t)]])

for t in range (1, T + 1):
    moi_duoc_bao_ve_tai_t = []
    for v in V:
        x_vt = vpool.id(f'x_{v}_{t}')
        d_vt = d_var[(v, t)]
        d_vt_truoc = d_var[(v, t - 1)]

        clauses.append([-x_vt, d_vt])
        clauses.append([-x_vt, -d_vt_truoc])
        clauses.append([x_vt, -d_vt, d_vt_truoc])

        moi_duoc_bao_ve_tai_t.append(x_vt)

    cnf_atmost = CardEnc.atmost(lits=moi_duoc_bao_ve_tai_t, bound=D, vpool=vpool, encoding=EncType.seqcounter)

    clauses.extend(cnf_atmost.clauses)
    
for v in V:
    for u in G.neighbors(v):
        for t in range (1, T + 1):
            clauses.append([-b_var[(v, t-1)], b_var[(u, t)], d_var[(u, t)]])




#Thay đổi mới thử xem như thế nào 








