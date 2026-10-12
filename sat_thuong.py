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
from pysat.card import ITotalizer

from GraphParser import doc_du_lieu_do_thi
from Tien_Xu_Li import tien_xu_ly


def giai_sat_thuong(G, V, Binit, T, D):
    thoi_gian_bat_dau_encode = time.perf_counter()
    solver = Solver(name='glucose3')
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
    for t in range(T + 1):   
        h_var[t] = vpool.id(f'h_{t}')  

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
    #Nếu u đang cháy ở bước trước thì hàng xóm v của nó ở bước này hoặc được bảo vệ 
    # hoặc bị cháy

    for v in V: 
        for u in G.neighbors(v):    
            for t in range (1, T + 1 ):
                solver.add_clause([-b_var[(u, t-1)], d_var[(v, t)], b_var[(v, t)]])  #Phép 9

    # Đã xong những cái ràng buộc cơ bản cũ, vẫn như vậy
    # Giờ có mấy cái mới bắt đầu làm 



    # 1 đỉnh nó chỉ có thể cháy nếu như nó đã cháy ở bước trước mà không được bảo vệ
    # Hoặc là đỉnh kề của nó cháy ở bước trước mà cái đỉnh đó không được bảo vệ ở bước đó


    for v in V:
        for u in G.neighbors(v):
            for t in range (1, T + 1):
                solver.add_clause([-b_var[(v, t)], b_var[(v, t-1)]]+ [b_var[(u, t-1)] for u in G.neighbors(v)]) #Phép 10


    # Đang chưa chắc về cái cách cài assumption cho h 
    #Phép này sử dụng để chốt hội tụ cho lửa lan
    #Khả năng là bước cuối mới bắt đầu cài solver vào trong assumption
    for v in V:
        for u in G.neighbors(v):
            for t in range (1, T + 1):
                solver.add_clause([-h_var[t], -b_var[(u, t)], b_var[(v, t)], d_var[(v, t)]]) #Phép 11


    # Hàm mục tiêu, sài Itotalizer

    T_check = T
    b_lits_at_T = [b_var[(v, T_check)] for v in V]  # Chỉ lấy danh sách b_{v, T}
    max_K = len(V)
    it = ITotalizer(lits=b_lits_at_T, ubound=max_K, top_id=vpool.top)
    for clause in it.cnf.clauses:
        solver.add_clause(clause)

    t_encode = time.perf_counter() - thoi_gian_bat_dau_encode
    thoi_gian_bat_dau_solve = time.perf_counter()

    # Cài cái vòng lặp liên tục để nó tự chạy theo T tự thử 

    h_assumptions = [h_var[T_check]] + [-h_var[t] for t in range(1, T_check)]

    found_opt = False
    best_K = None
    for K in range(0, max_K + 1):
        
        # phủ định lại cái thằng it thì nó sẽ được cái nhỏ hơn haowjc bằng vì cái gốc của nó là lớn hơn
        k_assumption = [-it.rhs[K]] if K < max_K else []
        # Cộng tất cả các assumption lại với nhau
        full_assumptions = h_assumptions + k_assumption

        is_sat = solver.solve(assumptions=full_assumptions)
        
        if is_sat:
            print(f"Số đỉnh cháy tối đa K = {K} tại T = {T_check}")
            model = solver.get_model()
            found_opt = True
            best_K = K
            break
        else:
            print(f"Không thể dập lửa với K = {K}")

    it.delete()  

    t_solve = time.perf_counter() - thoi_gian_bat_dau_solve
    so_bien = vpool.top

    return found_opt, best_K, t_encode, t_solve, so_bien



# Dùng AI viết main

if __name__ == "__main__":
    # Thư mục và tên file
    thu_muc_du_lieu = "BBGRL"
    ten_file = "50_ep0.1_0_gilbert_1.in"
    duong_dan_hoan_chinh = os.path.join(thu_muc_du_lieu, ten_file)
    
    G, V, Binit = doc_du_lieu_do_thi(duong_dan_hoan_chinh)
    
    if G is not None:
    
        T = 50
        D = 2
        
        print(f"Bắt đầu giải với T={T}, D={D}...\n")
        
        # Chạy SAT
        is_sat, K_toi_uu, t_encode, t_solve, so_bien = giai_sat_thuong(G, V, Binit, T, D)
        
        # Gom thông tin để in bảng
        so_canh = G.number_of_edges()
        trang_thai = "optimal" if is_sat else "unsat"
        muc_tieu = str(K_toi_uu) if is_sat else "-"
        ten_instance = "graph_1" # Có thể thay bằng ten_file nếu muốn

        # In bảng định dạng chuẩn
        print("="*95)
        print("BẢNG 1: THỐNG KÊ CẤU TRÚC VÀ THỜI GIAN GIẢI SAT")
        print("="*95)
        print(f"{'Instance':<12} | {'|V|':<5} | {'|E|':<5} | {'vars':<8} | {'t(encode)':<10} | {'t(solve)':<10} | {'status':<10} | {'objective':<9}")
        print("-" * 95)
        print(f"{ten_instance:<12} | {len(V):<5} | {so_canh:<5} | {so_bien:<8} | {t_encode:<10.4f} | {t_solve:<10.4f} | {trang_thai:<10} | {muc_tieu:<9}")
        print("="*95)