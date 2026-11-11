import os
import csv
import glob
import datetime
import time

from ortools.sat.python import cp_model

from GraphParser import doc_du_lieu_do_thi, liet_ke_file
from Tien_Xu_Li import tien_xu_ly, menh_de_don


class MoHinh:
    """Bọc CpModel với giao diện giống solver SAT:
    - id(name)      : tạo biến bool, trả về số nguyên dương (như IDPool)
    - add_clause(c) : thêm mệnh đề với literal dạng số nguyên (như pysat)
    Nhờ vậy menh_de_don(...) từ Tien_Xu_Li vẫn dùng được nguyên xi."""

    def __init__(self):
        self.model = cp_model.CpModel()
        self.vars = [None]          # vars[i] ứng với id i (bắt đầu từ 1)
        self.ten = {}

    def id(self, name):
        if name not in self.ten:
            self.vars.append(self.model.NewBoolVar(name))
            self.ten[name] = len(self.vars) - 1
        return self.ten[name]

    def lit(self, l):
        v = self.vars[abs(l)]
        return v if l > 0 else v.Not()

    def add_clause(self, clause):
        self.model.AddBoolOr([self.lit(l) for l in clause])


def tao_mo_hinh(m, V, dinh_ke, Binit, D, b_var, d_var, a_var, T):
    """Dựng toàn bộ mô hình cho chân trời thời gian T (t = 0..T)."""
    for v in V:
        for t in range(0, T + 1):
            b_var[(v, t)] = m.id(f'b_{v}_{t}')
            d_var[(v, t)] = m.id(f'd_{v}_{t}')
            a_var[(v, t)] = m.id(f'a_{v}_{t}')

    # Trạng thái ban đầu
    for v in V:
        m.add_clause([b_var[(v, 0)]] if v in Binit else [-b_var[(v, 0)]])
        m.add_clause([-d_var[(v, 0)]])

    for v in V:
        for t in range(1, T + 1):
            m.add_clause([-b_var[(v, t - 1)], b_var[(v, t)]])        # cháy rồi thì cháy mãi
            m.add_clause([-d_var[(v, t - 1)], d_var[(v, t)]])        # bảo vệ rồi thì giữ mãi
            m.add_clause([-b_var[(v, t)], -d_var[(v, t)]])           # không vừa cháy vừa được bảo vệ
            # a <-> (d_t và không d_{t-1})
            m.add_clause([-a_var[(v, t)], d_var[(v, t)]])
            m.add_clause([-a_var[(v, t)], -d_var[(v, t - 1)]])
            m.add_clause([a_var[(v, t)], -d_var[(v, t)], d_var[(v, t - 1)]])

    # Mỗi bước đặt tối đa D lính: CP-SAT có ràng buộc tuyến tính, không cần seqcounter
    for t in range(1, T + 1):
        m.model.Add(sum(m.vars[a_var[(v, t)]] for v in V) <= D)

    for v in V:
        for u in dinh_ke[v]:
            for t in range(1, T + 1):
                m.add_clause([-b_var[(u, t - 1)], d_var[(v, t)], b_var[(v, t)]])

    for v in V:
        for t in range(1, T + 1):
            m.add_clause([-b_var[(v, t)], b_var[(v, t - 1)]] + [b_var[(u, t - 1)] for u in dinh_ke[v]])


def them_khong_che(m, V, dinh_ke, b_var, d_var, T):
    """Ép lửa bị khống chế tại T (trong bản SAT là literal h_T đưa vào assumptions,
    ở đây là ràng buộc cứng vì mỗi T dựng một mô hình riêng)."""
    for v in V:
        for u in dinh_ke[v]:
            m.add_clause([-b_var[(u, T)], b_var[(v, T)], d_var[(v, T)]])


def giai_cp_sat(G, V, Binit, D, time_limit=1200, num_workers=8):
    t0 = time.perf_counter()

    txl = tien_xu_ly(G, V, Binit, D)
    if txl['xong']:
        return 'optimal(greedy)', txl['UB'], time.perf_counter() - t0, 0, 0, 0

    T = txl['T_init']
    T_ht = txl['T_ht']
    UB = txl['UB']
    LB = txl['LB']

    dinh_ke = {v: list(G.neighbors(v)) for v in V}

    trang_thai = 'optimal'
    K = UB
    t_encode = 0.0
    t_solve = 0.0
    so_bien = 0
    so_menh_de = 0

    while K - 1 >= LB:
        con_lai = time_limit - t_solve
        if con_lai <= 0:
            trang_thai = 'timeout'
            break

        # CP-SAT không có solve tăng dần/assumptions -> dựng lại mô hình cho mỗi T
        te = time.perf_counter()
        m = MoHinh()
        b_var, d_var, a_var = {}, {}, {}
        tao_mo_hinh(m, V, dinh_ke, Binit, D, b_var, d_var, a_var, T)
        them_khong_che(m, V, dinh_ke, b_var, d_var, T)
        menh_de_don(m, V, b_var, txl['delta'], 1, T)

        so_chay = sum(m.vars[b_var[(v, T)]] for v in V)
        m.model.Add(so_chay <= K - 1)      # chỉ tìm nghiệm tốt hơn K hiện tại
        m.model.Add(so_chay >= LB)
        m.model.Minimize(so_chay)
        t_encode += time.perf_counter() - te
        so_bien = len(m.model.Proto().variables)
        so_menh_de = len(m.model.Proto().constraints)

        ts = time.perf_counter()
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = con_lai
        solver.parameters.num_workers = num_workers
        status = solver.Solve(m.model)
        t_solve += time.perf_counter() - ts

        if status == cp_model.OPTIMAL:
            K = int(round(solver.ObjectiveValue()))
            # tối ưu với T này; thử T lớn hơn xem có tốt hơn nữa không
            if T < T_ht:
                T = min(2 * T, T_ht)
            else:
                break
        elif status == cp_model.FEASIBLE:
            K = int(round(solver.ObjectiveValue()))
            trang_thai = 'timeout'
            break
        elif status == cp_model.INFEASIBLE:
            if T < T_ht:
                T = min(2 * T, T_ht)
            else:
                break
        else:  # UNKNOWN: hết giờ mà chưa có nghiệm
            trang_thai = 'timeout'
            break

    return trang_thai, K, t_encode, t_solve, so_bien, so_menh_de


if __name__ == "__main__":
    thu_muc_du_lieu = "xyz"
    danh_sach_file = liet_ke_file(thu_muc_du_lieu)
    TIME_LIMIT = 1200
    D_LIST = range(1, 11)

    thu_muc_ket_qua = "ket_qua"
    duong_dan_csv = os.path.join(thu_muc_ket_qua, f"CP_SAT_KQ_{datetime.date.today().isoformat()}.csv")
    COT = ["File", "Method", "Nodes", "Edges", "Firefighters", "Variables", "Clauses",
           "Encoding Time", "Solving Time", "Total Time", "Status", "Burned Nodes Found",
           "Convergence Time"]
    os.makedirs(thu_muc_ket_qua, exist_ok=True)
    if not os.path.exists(duong_dan_csv) or os.path.getsize(duong_dan_csv) == 0:
        with open(duong_dan_csv, "w", newline="", encoding="utf-8-sig") as f:
            csv.DictWriter(f, fieldnames=COT).writeheader()

    if not danh_sach_file:
        print(f"KHÔNG TÌM THẤY file .in trong thư mục: {os.path.abspath(thu_muc_du_lieu)}")
        print(f"(thư mục đang chạy: {os.getcwd()})")

    da_xong = set()
    for file_cu in glob.glob(os.path.join(thu_muc_ket_qua, "CP_SAT_KQ*.csv")):
        with open(file_cu, newline="", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                try:
                    da_xong.add((r["File"], int(r["Firefighters"])))
                except (KeyError, TypeError, ValueError):
                    continue

    rong = 124
    print("=" * rong)
    print("BẢNG THỐNG KÊ CẤU TRÚC VÀ THỜI GIAN GIẢI CP-SAT")
    print(f"(timeout = {TIME_LIMIT}s, chỉ tính t(solve); khi timeout, objective là K tốt nhất tìm được)")
    print(f"Ghi vào: {os.path.abspath(duong_dan_csv)} (đã có {len(da_xong)} dòng, sẽ bỏ qua)")
    print("=" * rong)
    print(f"{'Instance':<25} | {'D':<3} | {'|V|':<5} | {'|E|':<5} | {'vars':<8} | {'cons':<9} | "
          f"{'t(encode)':<10} | {'t(solve)':<10} | {'status':<16} | {'objective':<9}")
    print("-" * rong)

    try:
        for duong_dan in danh_sach_file:
            ten_file = os.path.basename(duong_dan)
            G, V, Binit = doc_du_lieu_do_thi(duong_dan)
            if G is None:
                continue

            so_canh = G.number_of_edges()
            for D in D_LIST:
                if (ten_file, D) in da_xong:
                    continue

                txl = tien_xu_ly(G, V, Binit, D)
                T_ht = 0 if txl['xong'] else txl['T_ht']

                trang_thai, K, t_encode, t_solve, so_bien, so_menh_de = giai_cp_sat(
                    G, V, Binit, D, time_limit=TIME_LIMIT)

                print(f"{ten_file:<25} | {D:<3} | {len(V):<5} | {so_canh:<5} | {so_bien:<8} | {so_menh_de:<9} | "
                      f"{t_encode:<10.4f} | {t_solve:<10.4f} | {trang_thai:<16} | {K:<9}", flush=True)

                moi = not os.path.exists(duong_dan_csv) or os.path.getsize(duong_dan_csv) == 0
                with open(duong_dan_csv, "a", newline="", encoding="utf-8-sig") as f:
                    w = csv.DictWriter(f, fieldnames=COT)
                    if moi:
                        w.writeheader()
                    w.writerow({
                        "File": ten_file,
                        "Method": "CP_SAT",
                        "Nodes": len(V),
                        "Edges": so_canh,
                        "Firefighters": D,
                        "Variables": so_bien,
                        "Clauses": so_menh_de,
                        "Encoding Time": round(t_encode, 4),
                        "Solving Time": round(t_solve, 4),
                        "Total Time": round(t_encode + t_solve, 4),
                        "Status": "OPTIMAL" if trang_thai.startswith("optimal") else "TIMEOUT",
                        "Burned Nodes Found": K,
                        "Convergence Time": T_ht,
                    })
                    f.flush()
                    os.fsync(f.fileno())
            print("-" * rong)
    except KeyboardInterrupt:
        print("\nĐã dừng (Ctrl+C). Chạy lại cùng lệnh để chạy tiếp các ca chưa xong.")