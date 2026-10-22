from collections import deque
import random
import math

def khoang_cach_ngan_nhat_tu_B(G, Binit):
    delta = {b: 0 for b in Binit} 
    hang_doi = deque(Binit)      
    while hang_doi:
       v = hang_doi.popleft()
       for u in G[v]:
            if u not in delta:        
                delta[u] = delta[v] + 1  
                hang_doi.append(u)
    return delta

def menh_de_don (solver, V, b_var, delta, t_bat_dau, t_ket_thuc):
   for v in V:
     gioi_han = delta.get(v, float('inf')) 
     for t in range (t_bat_dau, t_ket_thuc +1):
         if t < gioi_han:   #điều kiện
            solver.add_clause([-b_var[(v, t)]])   #Phép 14


# Cận dưới
def can_duoi (G,Binit,D):
  B = set(Binit) # đổi cái tập đỉnh cháy có nhiều đỉnh gọi chung là B 
  # Tập hợp hàng xóm của B trừ chính nó 
  ke_B = {u for v in B for u in G.neighbors(v)} - B     # N(B) \ B
  return len(B) + max(0, len(ke_B) - D) # phép 15

# Cận trên dùng Greedy

def mot_vong_tham_lam (G, Binit, D, quy_tac, rng=None):
# lấy cái rgn trong cái python random để quy số lúc làm cái bước tham lam cuối
   chay = set(Binit)
   bao_ve = set()
   so_vong = 0

   while True:
      de_doa = {u for v in chay for u in G.neighbors(v) } - chay - bao_ve 
      #tập đỉnh đe dọa sẽ không bao gồm thằng đã cháy hoặc đã bảo vê
      if not de_doa:
         return len(chay), so_vong 
      so_chon = min(D,len(de_doa)) 
      
      #Cài tên cho giống cái văn bản ttuowcs còn cái sort bên trong để code khác
      if quy_tac == 'id':
         so_chon = min(D, len(de_doa))
         chon = sorted(de_doa)[:so_chon]                                    # C1
      elif quy_tac == 'bac':
         chon = sorted(de_doa, key=lambda x: (-G.degree(x), x))[:so_chon]   # C2
         # key là để Tham số chỉ định tiêu chí tùy chỉnh để Python 
         # dùng làm cơ sở so sánh và sắp xếp các phần tử

         # cái lamda là 1 cái cài cho key để định nghĩa được cái hàm (quy tắc sắp xếp)

      else:
         chon = rng.sample(sorted(de_doa), so_chon)                         # C3

      # Có cài cái 2 chấm trước mấy con số chọn để nó lấy cái phần tử đầu tiên cho đến vị
      #trí của số được chọn -> chỉ lấy đúng số đỉnh cho phép
   
      bao_ve.update(chon)
      chay |= (de_doa - set(chon))               # đỉnh bị đe dọa mà không được bảo vệ thì cháy
      so_vong += 1

# Bắt đầu chọn cái UB và To, thời gian mà vừa chạy xong 1 lần 
def can_tren_tham_lam (G, Binit, D, so_lan_ngau_nhien=20, seed=0):
   rng = random.Random(seed) # Cái này có thể tạo ra bộ 20 số khác nhau, đã thử in ra ở ngoài
   ket_qua = [mot_vong_tham_lam (G,Binit,D,'id'),mot_vong_tham_lam(G, Binit, D, 'bac')]
   ket_qua += [mot_vong_tham_lam(G, Binit, D, 'ngau_nhien', rng) for _ in range(so_lan_ngau_nhien)]
   return min(ket_qua)


   #Giải thích về cái này 1 chút vì quên quên =)) 
   # min trên các cặp (K, T0)
   # cho đúng quy tắc: K nhỏ nhất, hòa thì T nhỏ nhất, 
   # vì Python so sánh tuple từ trái sang phải. random.Random(seed) 
   # giúp kết quả lặp lại được giữa các lần chạy.
import math

def can_thoi_gian(n, so_B, D, LB, UB):
    Ts = (n - so_B + D) // (D + 1)   
    T_UB = UB - so_B
    T_LB = (n - LB) // D + 1
    T_ht = max(1, min(Ts, T_UB, T_LB))
    T_init = max(1, min(T_ht, math.ceil(1.5 * (n))))
    return T_ht, T_init, Ts, T_UB, T_LB


#Gói lại thành hàm tiền xử lí 
def tien_xu_ly(G, V, Binit, D):
    n = len(V)
    so_B = len(set(Binit))
    delta = khoang_cach_ngan_nhat_tu_B(G, Binit)
    LB = can_duoi(G, Binit, D)
    UB, T0 = can_tren_tham_lam(G, Binit, D)
    if UB == LB:                    # tham lam đã đạt cận dưới: tối ưu, khỏi cần SAT
        return dict(delta=delta, LB=LB, UB=UB, T0=T0, xong=True)
    T_ht, T_init, Ts, T_UB, T_LB = can_thoi_gian(n, so_B, D, LB, UB)
    return dict(delta=delta, LB=LB, UB=UB, T0=T0, Ts=Ts, T_UB=T_UB, T_LB=T_LB,
                T_ht=T_ht, T_init=T_init, xong=False)