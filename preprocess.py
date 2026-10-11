 from collections import deque

# Đầu tiên là cần tìm khoảng cách ngắn nhất từ tập đỉnh cháy đến các đỉnh khác, 
# để biết được cái đỉnh nào có thể bị cháy trong bước tiếp theo
def khoang_cach_ngan_nhat_tu_B(G, Binit):
    # Khởi tạo khoảng cách ban đầu là vô cùng lớn
    delta = {b: 0 for b in Binit} # delta là khoảng cách từ tập đỉnh cháy đến các đinh khác, ban đầu là 0 với đỉnh trong Binit
    hang_doi = deque(Binit)        # Tạo cái hàng đợi dùng BFS, thằng này xe đi xa dần theo lớp 
    while hang_doi:
       v = hang_doi.popleft()
       for u in G[v]:
            if u not in delta:          #tìm thằng chưa được thăm để add nốt vào
                delta[u] = delta[v] + 1     #khoảng cách từ u sẽ là 1 bậc sau v ( cạnh kề v)
                hang_doi.append(u)
    return delta

def menh_de_don (solver, V, b_var, delta, t_bat_dau, t_ket_thuc):
   for v in V:
      gioi_han = delta.get(v, float('inf')) # không chạm vào được thì nó sẽ tiến tới vô cùng
      for t in range (t_bat_dau, t_ket_thuc +1):
         if t < gioi_han:   #điều kiện
            solver.add_clause([-b_var[(v, t)]])   #Phép 14


  # Cận dưới
  def LB (G,Binit,D):
    B = set(Binit) # đổi cái tập đỉnh cháy có nhiều đỉnh gọi chung là B 
    # Tập hợp hàng xóm của B trừ chính nó 
    ke_B = {u for v in B for u in G.neighbors(v)} - B     # N(B) \ B
    return len(B) + max(0, len(ke_B) - D) # phép 15


# Cận trên dùng Greedy

def tham_lam (G, Binit, D, quy_tac, rng=None):
# lấy cái rgn trong cái python random để quy số lúc làm cái bước tham lam cuối
   chay = set(Binit)
   bao_ve = set()
   so_vong = 0

   while True:
      de_doa = {u for v in chay for u in G.neighbors(v) } - chay - bao_ve 
      #tập đỉnh đe dọa sẽ không bao gồm thằng đã cháy hoặc đã bảo vê
      if not de_doa:
         return len(chay), so vong 
      so_chon = min(D,len(de_doa)) 
      
      #Cài tên cho giống cái văn bản ttuowcs còn cái sort bên trong để code khác
      if quy_tac == 'id':
         so_chon = min(D, len(de_doa))
      if quy_tac == 'id':
         chon = sorted(de_doa)[:so_chon]                                    # C1
      elif quy_tac == 'bac':
         chon = sorted(de_doa, key=lambda x: (-G.degree(x), x))[:so_chon]   # C2
         # key là để Tham số chỉ định tiêu chí tùy chỉnh để Python 
         # dùng làm cơ sở so sánh và sắp xếp các phần tử

         # cái lalmda là 1 cái cài cho key để định nghĩa được cái hàm (quy tắc sắp xếp)

      else:
         chon = rng.sample(sorted(de_doa), so_chon)                         # C3

      # Có cài cái 2 chấm trước mấy con số chọn để nó lấy cái phần tử đầu tiên cho đến vị
      #trí của số được chọn -> chỉ lấy đúng số đỉnh cho phép
   
      bao_ve.update(chon)
      chay |= (de_doa - set(chon))               # đỉnh bị đe dọa mà không được bảo vệ thì cháy
      so_vong += 1


   
