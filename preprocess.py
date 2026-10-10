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


  