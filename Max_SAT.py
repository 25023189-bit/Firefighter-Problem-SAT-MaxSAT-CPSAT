import time
import networkx as nx
from pysat.formula import IDPool
from pysat.card import CardEnc, EncType
from hermax.non_incremental import EvalMaxSAT
import os
from GraphParser import doc_du_lieu_do_thi

def tim_can_tren(G, V, Binit, T, D):
    thoi_gian_bat_dau_encode = time.perf_counter()
    
    solver = EvalMaxSAT()
    vpool = IDPool()

    b_var = {}
    d_var = {}

    for v in V:
        for t in range(T + 1):
            b_var[(v, t)] = vpool.id(f'b_{v}_{t}')
            d_var[(v, t)] = vpool.id(f'd_{v}_{t}')

    for v in V:
        if v in Binit:
            solver.add_clause([b_var[(v, 0)]])
        else:
            solver.add_clause([-b_var[(v, 0)]])
        solver.add_clause([-d_var[(v, 0)]])

    for v in V:
        for t in range(1, T + 1):
            solver.add_clause([-b_var[(v, t-1)], b_var[(v, t)]])
            solver.add_clause([-d_var[(v, t-1)], d_var[(v, t)]])

    for v in V:
        for t in range(1, T + 1):
            solver.add_clause([-b_var[(v, t)], -d_var[(v, t)]])

    for v in V:
        for u in G.neighbors(v):
            for t in range(1, T + 1):
                solver.add_clause([-b_var[(v, t-1)], b_var[(u, t)], d_var[(u, t)]])

    for t in range(1, T + 1):
        linh_moi_duoc_dat_tai_t = []
        for v in V:
            x_vt = vpool.id(f'x_{v}_{t}')
            d_vt = d_var[(v, t)]
            d_vt_truoc = d_var[(v, t - 1)]

            solver.add_clause([-x_vt, d_vt])
            solver.add_clause([-x_vt, -d_vt_truoc])
            solver.add_clause([x_vt, -d_vt, d_vt_truoc])

            linh_moi_duoc_dat_tai_t.append(x_vt)

        cnf_atmost = CardEnc.atmost(
            lits=linh_moi_duoc_dat_tai_t,
            bound=D,
            vpool=vpool,
            encoding=EncType.seqcounter
        )
        for clause in cnf_atmost.clauses:
            solver.add_clause(clause)

    for v in V:
        solver.add_soft_unit(-b_var[(v, T)], 1)

    thoi_gian_encode = time.perf_counter() - thoi_gian_bat_dau_encode

    thoi_gian_bat_dau_solve = time.perf_counter()
    is_sat = solver.solve()
    thoi_gian_solve = time.perf_counter() - thoi_gian_bat_dau_solve

    da_giai_duoc_tot_nhat = None
    so_dinh_bi_chay_it_nhat = "-"
    trang_thai = "unknown"

    if is_sat:
        trang_thai = "optimal"
        da_giai_duoc_tot_nhat = solver.get_model()
        so_dinh_bi_chay_it_nhat = solver.get_cost()
    else:
        trang_thai = "unsat"

    solver.close()

    return ham_kiem_tra_va_in_thong_tin(G, V, Binit, T, D, thoi_gian_encode, thoi_gian_solve, trang_thai, so_dinh_bi_chay_it_nhat, da_giai_duoc_tot_nhat, vpool, b_var, d_var)


def ham_kiem_tra_va_in_thong_tin(G, V, Binit, T, D, thoi_gian_encode, thoi_gian_solve, trang_thai, so_dinh_bi_chay_it_nhat, da_giai_duoc_tot_nhat, vpool, b_var, d_var):
    if trang_thai == "optimal" or trang_thai == "sat":
        b = {}
        d = {}
        tap_mo_hinh = set(da_giai_duoc_tot_nhat)
        
        for v in V:
            for t in range(T + 1):
                b[(v, t)] = b_var[(v, t)] in tap_mo_hinh
                d[(v, t)] = d_var[(v, t)] in tap_mo_hinh

        for v in V:
            if v in Binit:
                if not b[(v, 0)]:
                    print("SAI")
                    return False
            else:
                if b[(v, 0)]:
                    print("SAI")
                    return False
            if d[(v, 0)]:
                print("SAI")
                return False

        for t in range(1, T + 1):
            linh_moi_trong_buoc = 0
            for v in V:
                if b[(v, t - 1)] and not b[(v, t)]:
                    print("SAI")
                    return False
                if d[(v, t - 1)] and not d[(v, t)]:
                    print("SAI")
                    return False

            for v in V:
                if b[(v, t)] and d[(v, t)]:
                    print("SAI")
                    return False

            for v in V:
                for u in G.neighbors(v):
                    if b[(v, t - 1)] and not (b[(u, t)] or d[(u, t)]):
                        print("SAI")
                        return False

            for v in V:
                if d[(v, t)] and not d[(v, t - 1)]:
                    linh_moi_trong_buoc += 1
            if linh_moi_trong_buoc > D:
                print("SAI")
                return False
    
    so_canh = G.number_of_edges() if hasattr(G, 'number_of_edges') else len(list(G.edges()))
    so_bien = vpool.top
    ten_instance = "graph_1"

    print("\n" + "="*85)
    print(f"BẢNG 1: THỐNG KÊ CẤU TRÚC VÀ THỜI GIAN GIẢI SAT")
    print("="*85)
    print(f"{'Instance':<12} | {'|V|':<5} | {'|E|':<5} | {'vars':<6} | {'t(encode)':<10} | {'t(solve)':<10} | {'status':<10} | {'objective':<9}")
    print("-" * 85)
    print(f"{ten_instance:<12} | {len(V):<5} | {so_canh:<5} | {so_bien:<6} | {thoi_gian_encode:<10.4f} | {thoi_gian_solve:<10.4f} | {trang_thai:<10} | {str(so_dinh_bi_chay_it_nhat):<9}")
    print("="*85)

    if da_giai_duoc_tot_nhat is not None:
        tap_mo_hinh = set(da_giai_duoc_tot_nhat)
        print("\nCHI TIẾT LỊCH TRÌNH:")
        for t in range(T + 1):
            dinh_bi_chay = [v for v in V if b_var[(v, t)] in tap_mo_hinh]
            dinh_duoc_bao_ve = [v for v in V if d_var[(v, t)] in tap_mo_hinh]
            
            if t > 0:
                linh_moi = [v for v in V if (d_var[(v, t)] in tap_mo_hinh) and (d_var[(v, t-1)] not in tap_mo_hinh)]
            else:
                linh_moi = []

            print(f"Bước t = {t}:")
            print(f"  - Đỉnh cháy: {dinh_bi_chay}")
            print(f"  - Đỉnh bảo vệ: {dinh_duoc_bao_ve} (Lính mới đặt tại: {linh_moi})")

    return trang_thai, so_dinh_bi_chay_it_nhat


from GraphParser import doc_du_lieu_do_thi


if __name__ == "__main__":
    # Tất cả các dòng bên dưới câu lệnh 'if' này phải được thụt vào 1 Tab (4 dấu cách)
    thu_muc_du_lieu = "BBGRL"
    ten_file = "50_ep0.1_0_gilbert_1.in"
    
    duong_dan_hoan_chinh = os.path.join(thu_muc_du_lieu, ten_file)
    
    G, V, Binit = doc_du_lieu_do_thi(duong_dan_hoan_chinh)
    
    if G is not None:
        # Các dòng bên trong 'if G is not None:' thụt vào tiếp 1 Tab nữa (8 dấu cách)
        print(f"Đã đọc xong đồ thị từ: {duong_dan_hoan_chinh}")
        
        T = 50
        D = 2
        
        print(f"Bắt đầu giải với T={T}, D={D}...\n")
        
        tim_can_tren(G, V, Binit, T, D)