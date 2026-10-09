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
a_var = {}
h_var = {}

# Khai báo biến
for v in V:
    for t in range(T + 1):
        b_var[(v, t)] = vpool.id(f'b_{v}_{t}')
        d_var[(v, t)] = vpool.id(f'd_{v}_{t}')
        a_var[(v, t)] = vpool.id(f'a_{v}_{t}')
        h_var[(v, t)] = vpool.id(f'h_{v}_{t}')  

# Ràng buộc ban đầu (khi t = 0)

for v in V:
    if v in Binit:
        solver.add_clause([b_var[(v, 0)]]) # Phép 1 
    else :
        solver.add_clause([-b_var[(v, 0)]]) # Phép 2
    solver.add_clause([-d_var[(v, 0)]]) # Phép 3

# Duy trì trạng thái khi t >= 1

for v in V:
    for t in range(1, T + 1):
        solver.add_clause([-b_var[(v, t-1)], b_var[(v, t)]]) #Phép 4
        solver.add_clause([-d_var[(v, t-1)], d_var[(v, t)]]) #Phép 5

# Loại trừ tương khắc (không thể vừa cháy vừa được bảo vệ)

for v in V:
    for t in range (1, T + 1):
        solver.add_clause([-b_var[(v, t)], -d_var[(v, t)]]) #Phép 6


# Cài đặt biến a mới (khi 1 có thằng lính được đặt tại t thì đánh dấu a)
# Đổi cái phép tương đương thành 3 mệnh đề 

for v in V:
    for t in range (1, T + 1):
        # Nếu có lính mới ở v thì v đang được bảo vệ ở bước này
        solver.add_clause([-a_var[(v, t)], d_var[(v, t)]]) #Phép 7
        # Nếu có lính mới ở v thì v chưa được bảo vệ ở bước trước
        solver.add_clause([-a_var[(v, t)], -d_var[(v, t-1)]]) #Phép 7
        # Nếu bây giờ v được bảo vệ mà bước trước chưa, thì a phải đúng
        solver.add_clause([a_var[(v, t)], -d_var[(v, t)], d_var[(v, t-1)]]) #Phép 7

    # Mỗi bước chỉ được đặt tối đa D lính mới
    lits = [a_var[(v, t)] for v in V]
    card = CardEnc.atmost(lits=lits, bound=D, vpool=vpool, encoding=EncType.seqcounter)
    for clause in card.clauses:
        solver.add_clause(clause)   #Phép 8

    
# Cài đặt cái lan truyền lửa, xét theo cả 2 chiều là (u,v) và (v,u)

for u,v in E:
    for t in range (1, T + 1):
        solver.add_clause([-b_var[(u, t-1)], b_var[(v, t)], d_var[(v, t)]]) #Phép 9



# Đã xong những cái ràng buộc cơ bản cũ, vẫn như vậy
# Giờ có mấy cái mới bắt đầu làm 

