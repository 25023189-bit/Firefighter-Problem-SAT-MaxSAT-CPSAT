"""
Chạy thí nghiệm cho Firefighter và xuất kết quả ra file CSV chuẩn Tiếng Anh.
Hỗ trợ dừng giữa chừng (Ctrl+C) và chạy tiếp (Resume).
"""
import argparse
import contextlib
import csv
import datetime
import io
import multiprocessing as mp
import os
import platform
import queue
import re
import sys
import time
import glob

from GraphParser import doc_du_lieu_do_thi, liet_ke_file
from Tien_Xu_Li import tien_xu_ly

# ---------------------------------------------------------------------------
# CÁC CỘT CSV ĐƯỢC XUẤT THEO ĐÚNG YÊU CẦU (ĐÃ ĐỔI SANG TIẾNG ANH)
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
    "Convergence Time"
]

# ---------------------------------------------------------------------------
# 0. Hàm trung gian: gọi code có sẵn của bạn và trả về format chuẩn
# ---------------------------------------------------------------------------
def chay_maxsat(G, V, Binit, T, D, seed, bao_cao, T_ht):
    from Max_SAT import tim_can_tren
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):             
        kq = tim_can_tren(G, V, Binit, T, D)
    if kq is False:                                   
        return dict(status="ERROR", objective="-", loi="SAI")
    
    trang_thai, so_chay = kq
    m = re.search(r"\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|", buf.getvalue())
    so_bien, t_enc, t_solve = (m.group(3), m.group(4), m.group(5)) if m else ("-", "-", "-")
    
    return {
        "Status": "OPTIMAL" if trang_thai == "optimal" else ("SAT" if trang_thai == "sat" else "UNKNOWN"),
        "Burned Nodes Found": so_chay,
        "Encoding Time": t_enc,
        "Solving Time": t_solve,
        "Variables": so_bien,
        "Clauses": "-", 
        "Convergence Time": T_ht
    }


def chay_sat_thuong(G, V, Binit, T, D, seed, bao_cao, T_ht):
    from Sat_Thuong import giai_sat_thuong
    with contextlib.redirect_stdout(io.StringIO()):
        found, K, t_enc, t_solve, so_bien = giai_sat_thuong(G, V, Binit, T, D)
        
    return {
        "Status": "OPTIMAL" if found else "UNKNOWN",
        "Burned Nodes Found": K if found else "-",
        "Encoding Time": round(t_enc, 4) if t_enc != "-" else "-",
        "Solving Time": round(t_solve, 4) if t_solve != "-" else "-",
        "Variables": so_bien,
        "Clauses": "-", 
        "Convergence Time": T_ht
    }

PHUONG_PHAP = {
    "MaxSAT": chay_maxsat,
    "SAT_thuong": chay_sat_thuong,
}

# ---------------------------------------------------------------------------
# 1. Tiến trình con (Tránh tràn RAM hoặc quá thời gian Timeout)
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
# 2. Xử lý CSV và Chạy tiếp (Resume)
# ---------------------------------------------------------------------------
def doc_da_xong(duong_dan):
    """Đọc file CSV cũ để biết những (tên file, số lính cứu hỏa) nào đã chạy xong để bỏ qua."""
    if not os.path.exists(duong_dan):
        return set()
    xong = set()
    with open(duong_dan, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                if r.get("Status") == "ERROR": # Nếu dòng cũ bị lỗi thì không tính là xong, sẽ chạy lại
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
        "Convergence Time": T_ht
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

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="BBGRL")
    ap.add_argument("--phuong-phap", nargs="+", default=list(PHUONG_PHAP), choices=list(PHUONG_PHAP))
    ap.add_argument("--D", type=int, nargs="+", default=[2])
    ap.add_argument("--so-lan", type=int, default=1)
    ap.add_argument("--gioi-han", type=float, default=600)
    ap.add_argument("--T", default="n")
    ap.add_argument("--n", type=int, nargs="*", default=None)
    ap.add_argument("--limit-files", type=int, default=None)
    ap.add_argument("--thu-muc-ket-qua", default="ket_qua")
    ap.add_argument("--tiep-tuc", default=None, help="Đường dẫn file CSV cũ muốn chạy tiếp")
    args = ap.parse_args(argv)

    kiem_tra_import(args.phuong_phap)

    ngay = datetime.date.today().isoformat()
    duong_dan_csv = {
        pp: os.path.join(args.thu_muc_ket_qua, f"{pp}_KQ_{ngay}.csv")
        for pp in args.phuong_phap
    }

    # Đọc lại các ca đã xong từ MỌI file CSV cũ (mọi ngày) để không chạy lại
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
    print("Đã có sẵn:", {pp: len(s) for pp, s in da_xong.items()}, "dòng (sẽ bỏ qua)\n")
    print("---------------------------------------------------------")

    try:
        for duong_dan in ds:
            ten_file = os.path.basename(duong_dan)
            G, V, Binit = doc_du_lieu_do_thi(duong_dan)
            
            if G is None or (args.n and len(V) not in args.n):
                continue
                
            T_val = len(V) if args.T == "n" else int(args.T)
            
            for D in args.D:
                # Tính thời gian hội tụ từ hàm tien_xu_ly
                txl_dict = tien_xu_ly(G, V, Binit, D)
                T_ht = txl_dict.get("T_ht", "-") if not txl_dict.get("xong", False) else 0

                for lan in range(1, args.so_lan + 1):
                    for pp in args.phuong_phap:
                        # Kiểm tra xem file này đã chạy ở phương pháp này chưa
                        khoa = (ten_file, D)
                        if khoa in da_xong[pp]:
                            continue
                            
                        seed = lan
                        kq, tien_do, het_gio, loi, t_wall = chay_mot_lan(
                            pp, G, V, Binit, T_val, D, seed, args.gioi_han, T_ht
                        )
                        
                        dong = tao_dong(pp, ten_file, G, T_val, D, kq, het_gio, loi, t_wall, T_ht)
                        ghi_dong(duong_dan_csv[pp], dong)
                        da_xong[pp].add(khoa) # Đánh dấu đã xong
                        
                        print(f"[{pp:<10}] {ten_file:<20} D={D} | TT: {dong.get('Status'):<8} | "
                              f"Cháy: {str(dong.get('Burned Nodes Found')):<4} | T.Hội Tụ: {T_ht:<3} | T.Gian: {t_wall:.2f}s", flush=True)
                        if dong.get("Status") == "ERROR":
                            print("   => LỖI:", loi, flush=True)
                            
    except KeyboardInterrupt:
        print("\nĐã dừng. Nhấn Ctrl+C.")
        print("Chạy lại CÙNG LỆNH (hoặc dùng tham số --tiep-tuc) để chạy tiếp các file chưa xong.")
        sys.exit(130)
    print("\nHoàn tất chạy thực nghiệm!")

if __name__ == "__main__":
    mp.freeze_support()
    main()
