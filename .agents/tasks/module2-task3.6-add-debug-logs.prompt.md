---
description: "Thêm debug logging chi tiết vào fallback_service.py để theo dõi logic tạo edges giữa node mới và đồ thị tham chiếu."
agent: "agent"
tools: ["editFiles", "codebase"]
---

# Task 3.6: Add Comprehensive Debug Logging for Edge Creation

Bạn là một Backend Engineer. Người dùng cần kiểm tra kỹ lưỡng logic tạo các cạnh (edges) khi một Node mới được kéo từ BigQuery về và nhúng vào NetworkX (Reference Graph).
Nhiệm vụ của bạn là bổ sung các dòng `logger.info` với định dạng dễ đọc vào file `app/services/fallback_service.py`.

## 1. Mục tiêu

- Làm rõ bao nhiêu cạnh vật lý (Follow/Interact) từ BigQuery thực sự được nối với các node đang có trong RAM.
- Làm rõ quá trình tìm kiếm và nối cạnh CO-OWNER.
- Làm rõ quá trình lấy hàng xóm, tính điểm Cosine Similarity và nối cạnh SIM_BIO.

## 2. Hướng dẫn chi tiết (Sửa file `app/services/fallback_service.py`)

### Bước 1: Log thông tin đồ thị ban đầu

- Ngay sau dòng `G = app.state.graph`, thêm log:
  `logger.info(f"========== BẮT ĐẦU FALLBACK PIPELINE CHO {profile_id} ==========")`
  `logger.info(f"[GRAPH STATE] Hiện có {G.number_of_nodes()} nodes trong RAM.")`

### Bước 2: Log logic nạp Physical Edges (Follow/Interact)

- Trước vòng lặp duyệt `df_edges`, thêm:
  `logger.info(f"[BIGQUERY EDGES] Kéo về {len(df_edges)} raw edges từ BigQuery.")`
- Thay thế vòng lặp `for _, row in df_edges.iterrows():` hiện tại bằng cấu trúc log chi tiết:
  Tạo 2 biến đếm: `attached_edges = 0` và `ignored_edges = 0`.
  Trong vòng lặp:
  - Nếu `neighbor` CÓ trong `G.nodes`: Tăng `attached_edges`, gọi `G.add_edge(...)`, và in log (chỉ in tối đa 10 dòng để khỏi trôi terminal):
    `if attached_edges <= 10: logger.info(f"   -> [LINKED] Nối cạnh {edge_type} với node trong RAM: {neighbor}")`
  - Nếu `neighbor` KHÔNG có: Tăng `ignored_edges`.
    Sau vòng lặp:
    `logger.info(f"[PHYSICAL EDGES SUMMARY] Đã nối: {attached_edges} edges. Bỏ qua (ngoài RAM): {ignored_edges} edges.")`

### Bước 3: Log logic CO-OWNER

- Ngay chỗ kiểm tra `owned_by`:
  `logger.info(f"[CO-OWNER CHECK] Node mới có ví: {new_owned_by}")`
- Khi tìm thấy một node trùng ví và tạo cạnh, hãy log ra:
  `logger.info(f"   -> [CO-OWNER FOUND] Nối với {n_id}")`

### Bước 4: Log logic SIM_BIO

- Trước khi tính NLP:
  `logger.info(f"[SIM_BIO CHECK] Bio của node mới: '{bio[:50]}...'")`
  `logger.info(f"[SIM_BIO CHECK] Đã tìm thấy {len(valid_neighbors)} hàng xóm (bậc 1 & 2) có bio hợp lệ để đem đi so sánh.")`
- Khi lặp qua mảng `cosine_scores` để kiểm tra `score >= 0.8`:
  Thêm log để in ra điểm số thực tế của TỪNG hàng xóm (dù rớt hay đậu):
  `logger.info(f"   -> So sánh với {n_id} | Score: {score:.4f} | Kết quả: {'PASS (Tạo cạnh)' if score >= 0.8 else 'FAIL'}")`

### Bước 5: Chốt chặn cuối

- Ở cuối hàm `fetch_and_embed_node` (trước khi return True), thêm:
  `logger.info(f"========== KẾT THÚC FALLBACK PIPELINE ==========")`

## 3. Ràng buộc

- Tuyệt đối KHÔNG làm thay đổi logic hoạt động hiện tại của code, chỉ CHÈN THÊM các dòng `logger.info`.
- Format log rõ ràng để Developer có thể đọc trực tiếp trên Terminal lúc API đang chạy.
