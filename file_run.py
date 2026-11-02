"""
Chạy thí nghiệm cho Firefighter (MaxSAT + SAT thường) và xuất kết quả ra file CSV.
Hỗ trợ dừng giữa chừng (Ctrl+C) và chạy tiếp (Resume).
Mặc định chỉ chạy SAT thường, với D (số lính cứu hỏa) từ 1 đến 10 trong một lần chạy.
Cột Status trong CSV chỉ có 3 giá trị: OPTIMAL, SAT, UNKNOWN.
"""
import argparse
import contextlib
import csv
import datetime
import glob
import io
import multiprocessing as mp
import os
import queue
import sys
import time

from GraphParser import doc_du_lieu_do_thi, liet_ke_file
from Tien_Xu_Li import tien_xu_ly

# ---------------------------------------------------------------------------
# CẤU HÌNH THỜI GIAN
# ---------------------------------------------------------------------------
TIME_LIMIT = float(os.environ.get("FF_TIME_LIMIT", 1200))   # giây (tiến trình con spawn đọc qua biến môi trường)
# Thời gian dư thêm cho tiến trình con (encode + dọn dẹp).
# SAT thường tự timeout ở TIME_LIMIT (chỉ tính solve) nên cần dư để nó kịp trả K tốt nhất.
# MaxSAT không có timeout bên trong nên bị kill đúng TIME_LIMIT.
GRACE = {"MaxSAT": 0, "SAT_thuong": 60}

# ---------------------------------------------------------------------------
# CÁC CỘT CSV
# ---------------------------------------------------------------------------
COT = [
    "File",
    "Method",
    "Nodes",
    "Edges",
    "Firefighters",
    "Variables",
    "Clauses",
    "Encoding Time",
    "Solving Time",
    "Total Time",
    "Status",
    "Burned Nodes Found",
    "Convergence Time",
]

# ---------------------------------------------------------------------------
# 0. Hàm trung gian: gọi code solver và trả về dict chuẩn
# ---------------------------------------------------------------------------
def chay_maxsat(G, V, Binit, T, D, seed, bao_cao, T_ht):
    from Max_SAT import tim_can_tren
    with contextlib.redirect_stdout(io.StringIO()):
        kq = tim_can_tren(G, V, Binit, T, D)
    if kq is False:
        return {"Status": "ERROR", "Burned Nodes Found": "-"}

    trang_thai, so_chay, so_menh_de, so_bien, t_enc, t_solve = kq
    if trang_thai == "optimal":
        status = "OPTIMAL"
    else:
        status = "UNKNOWN"

    return {
        "Status": status,
        "Burned Nodes Found": so_chay,
        "Encoding Time": t_enc,
        "Solving Time": t_solve,
        "Variables": so_bien,
        "Clauses": so_menh_de,
        "Convergence Time": T_ht,
    }


def chay_sat_thuong(G, V, Binit, T, D, seed, bao_cao, T_ht):
    from Sat_Thuong import giai_sat_thuong
    with contextlib.redirect_stdout(io.StringIO()):
        trang_thai, K, t_enc, t_solve, so_bien, so_menh_de = giai_sat_thuong(
            G, V, Binit, D, time_limit=TIME_LIMIT)

    status = "OPTIMAL" if trang_thai.startswith("optimal") else "SAT"
    return {
        "Status": status,
        "Burned Nodes Found": K,          # khi hết giờ: K tốt nhất tìm được
        "Encoding Time": round(t_enc, 4),
        "Solving Time": round(t_solve, 4),
        "Variables": so_bien,
        "Clauses": so_menh_de,
        "Convergence Time": T_ht,
    }


PHUONG_PHAP = {
    "MaxSAT": chay_maxsat,
    "SAT_thuong": chay_sat_thuong,
}

# ---------------------------------------------------------------------------
# 1. Tiến trình con (tránh tràn RAM / quá thời gian)
# ---------------------------------------------------------------------------
def _worker(ten_pp, G, V, Binit, T, D, seed, q, T_ht):
    try:
        ham = PHUONG_PHAP[ten_pp]

        def bao_cao(**thong_tin):
            q.put(("tien_do", thong_tin))
        q.put(("xong", ham(G, V, Binit, T, D, seed, bao_cao, T_ht)))
    except BaseException as e:
        q.put(("loi", f"{type(e).__name__}: {e}"))


def _giet(p):
    if p.is_alive():
        try:
            import psutil
            for con in psutil.Process(p.pid).children(recursive=True):
                con.kill()
        except Exception:
            pass
        p.kill()
    p.join(timeout=5)


def chay_mot_lan(ten_pp, G, V, Binit, T, D, seed, gioi_han, T_ht):
    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    p = ctx.Process(target=_worker, args=(ten_pp, G, V, Binit, T, D, seed, q, T_ht), daemon=True)
    bat_dau = time.perf_counter()
    p.start()
    tien_do, ket_qua, loi, het_gio = {}, None, None, False
    try:
        while True:
            con_lai = gioi_han - (time.perf_counter() - bat_dau)
            if con_lai <= 0:
                het_gio = True
                break
            try:
                loai, nd = q.get(timeout=min(0.5, con_lai))
            except queue.Empty:
                if p.is_alive():
                    continue
                try:
                    loai, nd = q.get(timeout=0.5)
                except queue.Empty:
                    loi = f"Tiến trình kết thúc bất thường (exitcode={p.exitcode})"
                    break
            if loai == "tien_do":
                tien_do.update(nd)
            elif loai == "xong":
                ket_qua = nd
                break
            else:
                loi = nd
                break
    finally:
        _giet(p)
    return ket_qua, tien_do, het_gio, loi, time.perf_counter() - bat_dau

# ---------------------------------------------------------------------------
# 2. Xử lý CSV và chạy tiếp (Resume)
# ---------------------------------------------------------------------------
def doc_da_xong(duong_dan):
    """Đọc CSV cũ để biết (File, D) nào đã xong. Dòng ERROR (nếu còn từ bản cũ) sẽ được chạy lại."""
    if not os.path.exists(duong_dan):
        return set()
    xong = set()
    with open(duong_dan, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                if r.get("Status") == "ERROR":
                    continue
                xong.add((r["File"], int(r["Firefighters"])))
            except (KeyError, TypeError, ValueError):
                continue
    return xong


def doc_da_xong_tat_ca(thu_muc, pp, them=None):
    """Gộp các (File, D) đã xong từ MỌI file CSV của phương pháp pp, mọi ngày."""
    cac_file = glob.glob(os.path.join(thu_muc, f"{pp}_KQ*.csv"))
    if them:
        cac_file.append(them)
    xong = set()
    for f in set(cac_file):
        xong |= doc_da_xong(f)
    return xong


def ghi_dong(duong_dan, dong):
    if dong.get("Status") not in ("OPTIMAL", "SAT"):
        dong["Status"] = "UNKNOWN"
    os.makedirs(os.path.dirname(duong_dan) or ".", exist_ok=True)
    moi = not os.path.exists(duong_dan) or os.path.getsize(duong_dan) == 0
    with open(duong_dan, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COT, extrasaction="ignore")
        if moi:
            w.writeheader()
        w.writerow({k: dong.get(k, "") for k in COT})
        f.flush()
        os.fsync(f.fileno())

# ---------------------------------------------------------------------------
# 3. Gom dòng kết quả
# ---------------------------------------------------------------------------
def tao_dong(ten_pp, ten_file, G, T, D, ket_qua, het_gio, loi, t_wall, T_ht):
    dong = {
        "File": ten_file,
        "Method": ten_pp,
        "Nodes": G.number_of_nodes(),
        "Edges": G.number_of_edges(),
        "Firefighters": D,
        "Total Time": round(t_wall, 4),
        "Convergence Time": T_ht,
    }

    if ket_qua is not None:
        dong.update(ket_qua)
    elif loi is not None:
        dong.update({"Status": "ERROR", "Burned Nodes Found": "-"})
    elif het_gio:
        dong.update({"Status": "UNKNOWN", "Burned Nodes Found": "-"})

    return dong

# ---------------------------------------------------------------------------
# 4. Chương trình chính
# ---------------------------------------------------------------------------
def kiem_tra_import(danh_sach):
    can = {"MaxSAT": ("Max_SAT", "tim_can_tren"), "SAT_thuong": ("Sat_Thuong", "giai_sat_thuong")}
    for pp in danh_sach:
        ten_module, ten_ham = can[pp]
        try:
            mod = __import__(ten_module)
            getattr(mod, ten_ham)
        except Exception as e:
            sys.exit(f"[{pp}] Không nạp được {ten_module}.{ten_ham}: {type(e).__name__}: {e}")


def parse_D(ds):
    """Chấp nhận: 2  |  1 2 3  |  1-10  |  1-5 8 10  |  1,2,5-7"""
    kq = []
    for s in ds:
        for phan in str(s).split(","):
            phan = phan.strip()
            if not phan:
                continue
            if "-" in phan:
                a, b = phan.split("-", 1)
                kq.extend(range(int(a), int(b) + 1))
            else:
                kq.append(int(phan))
    return sorted(set(kq))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="xyz")
    ap.add_argument("--phuong-phap", nargs="+", default=["SAT_thuong"], choices=list(PHUONG_PHAP))
    ap.add_argument("--D", nargs="+", default=["1-10"],
                    help="Số lính cứu hỏa, vd: 2 | 1 2 3 | 1-10 | 1-5 8 10 (mặc định 1-10)")
    ap.add_argument("--so-lan", type=int, default=1)
    ap.add_argument("--gioi-han", type=float, default=TIME_LIMIT)
    ap.add_argument("--T", default="n")
    ap.add_argument("--n", type=int, nargs="*", default=None)
    ap.add_argument("--limit-files", type=int, default=None)
    ap.add_argument("--thu-muc-ket-qua", default="ket_qua")
    ap.add_argument("--tiep-tuc", default=None, help="Đường dẫn file CSV cũ muốn chạy tiếp")
    args = ap.parse_args(argv)

    args.D = parse_D(args.D)

    # --gioi-han là giới hạn cho cả hai phương pháp (SAT thường đọc qua TIME_LIMIT)
    os.environ["FF_TIME_LIMIT"] = str(args.gioi_han)   # tiến trình con kế thừa

    kiem_tra_import(args.phuong_phap)

    ngay = datetime.date.today().isoformat()
    duong_dan_csv = {
        pp: os.path.join(args.thu_muc_ket_qua, f"{pp}_KQ_{ngay}.csv")
        for pp in args.phuong_phap
    }

    da_xong = {
        pp: doc_da_xong_tat_ca(
            args.thu_muc_ket_qua, pp,
            args.tiep_tuc if len(args.phuong_phap) == 1 else None,
        )
        for pp in args.phuong_phap
    }

    ds = liet_ke_file(args.dir)
    if args.limit_files:
        ds = ds[:args.limit_files]
    if not ds:
        sys.exit(f"Không có file .in trong {args.dir}")

    print("Ghi vào:", ", ".join(duong_dan_csv.values()))
    print("Đã có sẵn:", {pp: len(s) for pp, s in da_xong.items()}, "dòng (sẽ bỏ qua)")
    print(f"Chạy D = {args.D}")
    print(f"Giới hạn thời gian: {args.gioi_han:.0f}s mỗi ca\n")
    print("---------------------------------------------------------")

    try:
        for duong_dan in ds:
            ten_file = os.path.basename(duong_dan)
            G, V, Binit = doc_du_lieu_do_thi(duong_dan)

            if G is None or (args.n and len(V) not in args.n):
                continue

            T_val = len(V) if args.T == "n" else int(args.T)

            for D in args.D:
                txl_dict = tien_xu_ly(G, V, Binit, D)
                T_ht = txl_dict.get("T_ht", "-") if not txl_dict.get("xong", False) else 0

                for lan in range(1, args.so_lan + 1):
                    for pp in args.phuong_phap:
                        khoa = (ten_file, D)
                        if khoa in da_xong[pp]:
                            continue

                        seed = lan
                        gioi_han_pp = args.gioi_han + GRACE[pp]
                        kq, tien_do, het_gio, loi, t_wall = chay_mot_lan(
                            pp, G, V, Binit, T_val, D, seed, gioi_han_pp, T_ht
                        )

                        dong = tao_dong(pp, ten_file, G, T_val, D, kq, het_gio, loi, t_wall, T_ht)

                        if dong.get("Status") == "ERROR":
                            print(f"[{pp:<10}] {ten_file:<20} D={D:<2} | LỖI, không ghi CSV, "
                                  f"sẽ chạy lại lần sau: {loi}", flush=True)
                            continue

                        ghi_dong(duong_dan_csv[pp], dong)
                        da_xong[pp].add(khoa)

                        print(f"[{pp:<10}] {ten_file:<20} D={D:<2} | TT: {str(dong.get('Status')):<8} | "
                              f"Cháy: {str(dong.get('Burned Nodes Found')):<4} | "
                              f"Vars: {str(dong.get('Variables', '-')):<8} | "
                              f"Clauses: {str(dong.get('Clauses', '-')):<9} | "
                              f"T.Hội Tụ: {str(T_ht):<3} | T.Gian: {t_wall:.2f}s", flush=True)

    except KeyboardInterrupt:
        print("\nĐã dừng (Ctrl+C).")
        print("Chạy lại CÙNG LỆNH (hoặc dùng --tiep-tuc) để chạy tiếp các ca chưa xong.")
        sys.exit(130)
    print("\nHoàn tất chạy thực nghiệm!")


if __name__ == "__main__":
    mp.freeze_support()
    main()