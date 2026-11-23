import os
import re

import networkx as nx

# Dinh dang file .in (suy ra tu parser cu cua ban):
#   graph_id  so_dinh  so_canh  tham_so_4  so_dinh_chay_ban_dau
#   <Binit: so_dinh_chay_ban_dau so nguyen>
#   <so_canh cap (u v)>
# Cac so cach nhau bang khoang trang hoac xuong dong, khong quan trong.


def tim_duong_dan(duong_dan):
    """Tim file theo thu tu: dung nhu da cho, roi tinh tu thu muc chua file .py nay."""
    if os.path.isabs(duong_dan) and os.path.exists(duong_dan):
        return duong_dan
    if os.path.exists(duong_dan):
        return duong_dan
    thu_muc_script = os.path.dirname(os.path.abspath(__file__))
    thu_lai = os.path.join(thu_muc_script, duong_dan)
    return thu_lai if os.path.exists(thu_lai) else duong_dan


def doc_du_lieu_do_thi(filename):
    """Tra ve (G, V, Binit). Loi thi tra ve (None, None, None) kem thong bao ro ly do.
    Thong tin phu nam trong G.graph: 'graph_id', 'tham_so_4', 'one_based'."""
    filename = tim_duong_dan(filename)
    try:
        with open(filename, 'r') as f:
            tokens = f.read().split()
    except OSError as e:
        print(f"[GraphParser] Khong mo duoc file '{filename}': {e}")
        return None, None, None

    if not tokens:
        print(f"[GraphParser] File rong: {filename}")
        return None, None, None

    try:
        so = [int(x) for x in tokens]
    except ValueError as e:
        print(f"[GraphParser] File '{filename}' co gia tri khong phai so nguyen: {e}")
        return None, None, None

    if len(so) < 5:
        print(f"[GraphParser] File '{filename}' qua ngan (chi co {len(so)} so, can >= 5)")
        return None, None, None

    graph_id, so_dinh, so_canh, tham_so_4, so_chay = so[:5]
    can_co = 5 + so_chay + 2 * so_canh
    if len(so) < can_co:
        print(f"[GraphParser] File '{filename}' thieu du lieu: can {can_co} so, chi co {len(so)} "
              f"(so_dinh={so_dinh}, so_canh={so_canh}, so_chay={so_chay}). Kiem tra lai dinh dang.")
        return None, None, None
    if len(so) > can_co:
        print(f"[GraphParser] Canh bao: '{filename}' thua {len(so) - can_co} so o cuoi file, bo qua.")

    binit_tho = so[5:5 + so_chay]
    cap = [(so[5 + so_chay + 2 * i], so[5 + so_chay + 2 * i + 1]) for i in range(so_canh)]

    # Phat hien danh so tu 1 (1..n) thay vi tu 0 (0..n-1)
    moi_id = binit_tho + [x for e in cap for x in e]
    one_based = bool(moi_id) and min(moi_id) >= 1 and max(moi_id) == so_dinh
    if one_based:
        print(f"[GraphParser] '{os.path.basename(filename)}': dinh danh so tu 1 -> doi sang 0..n-1")
        binit_tho = [x - 1 for x in binit_tho]
        cap = [(u - 1, v - 1) for u, v in cap]

    ngoai = [x for x in binit_tho + [y for e in cap for y in e] if not 0 <= x < so_dinh]
    if ngoai:
        print(f"[GraphParser] '{filename}': co chi so dinh ngoai khoang 0..{so_dinh - 1}, vi du {ngoai[:5]}")
        return None, None, None

    G = nx.Graph()
    G.add_nodes_from(range(so_dinh))
    bo_vong = 0
    for u, v in cap:
        if u == v:
            bo_vong += 1
            continue
        G.add_edge(u, v)
    if bo_vong:
        print(f"[GraphParser] Bo {bo_vong} canh khuyen (u,u).")

    Binit = list(dict.fromkeys(binit_tho))          # bo trung, giu thu tu
    if len(Binit) != len(binit_tho):
        print(f"[GraphParser] Canh bao: Binit co phan tu lap, con {len(Binit)}/{len(binit_tho)}.")

    G.graph.update(graph_id=graph_id, tham_so_4=tham_so_4, one_based=one_based)
    return G, list(G.nodes()), Binit


def _khoa_tu_nhien(s):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)]


def liet_ke_file(thu_muc, duoi=".in"):
    """Liet ke cac file du lieu trong thu muc (sap xep theo so trong ten)."""
    thu_muc = tim_duong_dan(thu_muc)
    if not os.path.isdir(thu_muc):
        print(f"[GraphParser] Khong thay thu muc '{thu_muc}'")
        return []
    ten = sorted((f for f in os.listdir(thu_muc) if f.endswith(duoi)), key=_khoa_tu_nhien)
    return [os.path.join(thu_muc, f) for f in ten]


if __name__ == "__main__":
    # Doc thu tat ca file trong thu muc dataset (nam canh file nay) va in thong tin
    thu_muc = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset")
    ds = liet_ke_file(thu_muc)
    print(f"Tim thay {len(ds)} file trong {thu_muc}")
    for duong_dan in ds:
        G, V, Binit = doc_du_lieu_do_thi(duong_dan)
        if G is None:
            continue
        print(f"{os.path.basename(duong_dan):<34} |V|={len(V):<5} |E|={G.number_of_edges():<7} "
              f"|Binit|={len(Binit):<3} tham_so_4={G.graph['tham_so_4']}")