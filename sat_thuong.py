import os
import time
import threading

from pysat.card import CardEnc, EncType, ITotalizer
from pysat.formula import IDPool
from pysat.solvers import Solver

from GraphParser import doc_du_lieu_do_thi, liet_ke_file
from Tien_Xu_Li import tien_xu_ly, menh_de_don

def tao_buoc(solver, vpool, V, dinh_ke, Binit, D, b_var, d_var, a_var, t_tu, t_den):
# Khai báo biến
    for v in V:
        for t in range(t_tu, t_den + 1):
            b_var[(v, t)] = vpool.id(f'b_{v}_{t}')
            d_var[(v, t)] = vpool.id(f'd_{v}_{t}')
            a_var[(v, t)] = vpool.id(f'a_{v}_{t}')

# Ràng buộc ban đầu (khi t = 0)
    if t_tu == 0:
        for v in V:
            if v in Binit:
                solver.add_clause([b_var[(v, 0)]]) # Phép 1 
            else :
                solver.add_clause([-b_var[(v, 0)]]) # Phép 2
            solver.add_clause([-d_var[(v, 0)]]) # Phép 3

# Duy trì trạng thái khi t >= 1

    for v in V:
        for t in range(max(1, t_tu), t_den + 1):
            solver.add_clause([-b_var[(v, t-1)], b_var[(v, t)]]) #Phép 4
            solver.add_clause([-d_var[(v, t-1)], d_var[(v, t)]]) #Phép 5

# Loại trừ tương khắc (không thể vừa cháy vừa được bảo vệ)
    for v in V:
        for t in range (max(1, t_tu), t_den + 1):
            solver.add_clause([-b_var[(v, t)], -d_var[(v, t)]]) #Phép 6


# Cài đặt biến a mới (khi 1 có thằng lính được đặt tại t thì đánh dấu a)
# Đổi cái phép tương đương thành 3 mệnh đề 

    for v in V:
        for t in range (max(1, t_tu), t_den + 1):
            # Nếu có lính mới ở v thì v đang được bảo vệ ở bước này
            solver.add_clause([-a_var[(v, t)], d_var[(v, t)]]) #Phép 7
            # Nếu có lính mới ở v thì v chưa được bảo vệ ở bước trước
            solver.add_clause([-a_var[(v, t)], -d_var[(v, t-1)]]) #Phép 7
            # Nếu bây giờ v được bảo vệ mà bước trước chưa, thì a phải đúng
            solver.add_clause([a_var[(v, t)], -d_var[(v, t)], d_var[(v, t-1)]]) #Phép 7


# Mỗi bước chỉ được đặt tối đa D lính mới
    for t in range (max(1, t_tu), t_den + 1): # Cho thằng này ra ngoài để không bị lặp lại với mỗi cặp v,t
        lits = [a_var[(v, t)] for v in V]
        card = CardEnc.atmost(lits=lits, bound=D, vpool=vpool, encoding=EncType.seqcounter)
            
        for clause in card.clauses:
            solver.add_clause(clause)   #Phép 8

    for v in V: 
        for u in dinh_ke[v]:    
            for t in range (max(1, t_tu), t_den + 1):
                solver.add_clause([-b_var[(u, t-1)], d_var[(v, t)], b_var[(v, t)]])  #Phép 9
    
    for v in V:
        for t in range (max(1, t_tu), t_den + 1):
            solver.add_clause([-b_var[(v, t)], b_var[(v, t-1)]] + [b_var[(u, t-1)] for u in dinh_ke[v]]) #Phép 10


def them_khong_che(solver, vpool, V, dinh_ke, b_var, d_var, h_var, T):
    h_var[T] = vpool.id(f'h_{T}')  
    for v in V:
        for u in dinh_ke[v]:
            solver.add_clause([-h_var[T], -b_var[(u, T)], b_var[(v, T)], d_var[(v, T)]]) #Phép 11


def them_totalizer(solver, vpool, V, b_var, T, UB):
    lits =  [b_var[(v,T)] for v in V ]
    it = ITotalizer(lits = lits, ubound = UB, top_id = vpool.top)
    for clause in it.cnf.clauses :
        solver.add_clause(clause)
    if it.top_id > vpool.top:
        vpool.occupy(vpool.top + 1, it.top_id)
    return it


def giai_sat_thuong(G, V, Binit, D, time_limit = 1200):
    thoi_gian_bat_dau_encode = time.perf_counter()
    
    txl = tien_xu_ly(G,V,Binit,D)
    if txl['xong']:
        t_encode = time.perf_counter() - thoi_gian_bat_dau_encode
        return 'optimal(greedy)', txl['UB'], t_encode,0,0,0 
    T = txl['T_init']
    UB = txl['UB']
    LB = txl['LB']
    
    solver = Solver( name= 'glucose3')
    vpool = IDPool()
    b_var = {}
    d_var = {}
    a_var = {}
    h_var = {}
    it = None
    trang_thai = 'optimal'
    K = UB
    t_encode = 0
    t_solve = 0
    so_bien = 0
    so_menh_de = 0

    try:
# Set up 1 cái đỉnh kề v để dùng 
        dinh_ke = {}
        for v in V:
            dinh_ke[v] = list(G.neighbors(v))

        tao_buoc(solver, vpool, V, dinh_ke, Binit, D, b_var, d_var, a_var, 0, T)
        them_khong_che(solver, vpool, V, dinh_ke, b_var, d_var, h_var, T)
        menh_de_don(solver, V, b_var, txl['delta'], 1, T)
        
        it = them_totalizer(solver, vpool, V, b_var, T, UB)

        t_encode =  time.perf_counter() - thoi_gian_bat_dau_encode
        thoi_gian_bat_dau_solve = time.perf_counter()
        
        T_ht = txl['T_ht']
        cac_T_da_xet = [T]
        while K - 1 >= LB:
            con_lai = time_limit - (time.perf_counter() - thoi_gian_bat_dau_solve)
            if con_lai <= 0:
                trang_thai = 'timeout'
                break
            h_assumptions = [h_var[T]] + [-h_var[t] for t in cac_T_da_xet if t < T]
            k_assumption = [-it.rhs[K - 1]]  
            timer = threading.Timer(con_lai, solver.interrupt)
            timer.start()
            try:
                ket_qua = solver.solve_limited(assumptions=h_assumptions + k_assumption, expect_interrupt=True)
            finally:
                timer.cancel()
            if ket_qua is None:
                trang_thai = 'timeout'
                break
            elif ket_qua:
                model = solver.get_model()
                dung = set(l for l in model if l > 0)              
                K = sum(1 for v in V if b_var[(v, T)] in dung)         
            elif T < T_ht:
                T_cu = T
                T = min(2 * T, T_ht)
                it.delete()
                tao_buoc(solver, vpool, V, dinh_ke, Binit, D, b_var, d_var, a_var, T_cu + 1, T)
                them_khong_che(solver, vpool, V, dinh_ke, b_var, d_var, h_var, T)
                menh_de_don(solver, V, b_var, txl['delta'], T_cu + 1, T)
                it = them_totalizer(solver, vpool, V, b_var, T, UB)
                cac_T_da_xet.append(T)
            else:
                break

        t_solve = time.perf_counter() - thoi_gian_bat_dau_solve
        so_bien = max(vpool.top, it.top_id)
        so_menh_de = solver.nof_clauses()
    finally:
        if it is not None:
            it.delete()
        solver.delete()
    return trang_thai, K, t_encode, t_solve, so_bien, so_menh_de



if __name__ == "__main__":
    thu_muc_du_lieu = "uuuu"
    danh_sach_file = liet_ke_file(thu_muc_du_lieu)
    TIME_LIMIT = 1200
    D_LIST = range(1, 11)

    rong = 124
    print("=" * rong)
    print("BẢNG THỐNG KÊ CẤU TRÚC VÀ THỜI GIAN GIẢI SAT")
    print(f"(timeout = {TIME_LIMIT}s, chỉ tính t(solve); khi timeout, objective là K tốt nhất tìm được)")
    print("=" * rong)
    print(f"{'Instance':<25} | {'D':<3} | {'|V|':<5} | {'|E|':<5} | {'vars':<8} | {'clauses':<9} | "
          f"{'t(encode)':<10} | {'t(solve)':<10} | {'status':<16} | {'objective':<9}")
    print("-" * rong)

    for duong_dan in danh_sach_file:
        ten_file = os.path.basename(duong_dan)
        G, V, Binit = doc_du_lieu_do_thi(duong_dan)
        if G is None:
            continue

        so_canh = G.number_of_edges()
        for D in D_LIST:
            trang_thai, K, t_encode, t_solve, so_bien, so_menh_de = giai_sat_thuong(
                G, V, Binit, D, time_limit=TIME_LIMIT)

            print(f"{ten_file:<25} | {D:<3} | {len(V):<5} | {so_canh:<5} | {so_bien:<8} | {so_menh_de:<9} | "
                  f"{t_encode:<10.4f} | {t_solve:<10.4f} | {trang_thai:<16} | {K:<9}")
        print("-" * rong)