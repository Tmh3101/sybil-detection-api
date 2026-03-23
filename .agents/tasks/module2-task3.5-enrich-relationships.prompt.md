---
description: "Cập nhật fallback_service.py để tự động thiết lập 2 tầng quan hệ logic: CO-OWNER và SIMILARITY cho node mới."
agent: "agent"
tools: ["editFiles", "codebase"]
---

# Task 3.5: Enrich Fallback Node Relationships (Co-owner & Similarity)

Bạn là một chuyên gia Backend & AI. Trong hệ thống hiện tại, hàm `fetch_and_embed_node` trong `fallback_service.py` đang thiếu logic tạo các cạnh (edges) dạng `CO-OWNER` và `SIMILARITY` khi một node mới được nạp vào RAM. Điều này làm giảm độ chính xác của mô hình AI phía sau.

## Nhiệm vụ

Hãy mở file `app/services/fallback_service.py` và bổ sung logic "Graph Enrichment" ngay sau khi node mới và các cạnh vật lý (Follow, Interact) đã được nạp vào `app.state.graph`.

## Hướng dẫn chi tiết

### 1. Bổ sung logic tạo cạnh CO-OWNER

- Ngay sau khối code `G.add_node(...)`, hãy lấy giá trị `owned_by` của node mới (đảm bảo nó không None hoặc rỗng).
- Viết một vòng lặp duyệt qua toàn bộ các nodes hiện có trong Đồ thị tham chiếu trên RAM:
  ```python
  new_owned_by = node_data.get("owned_by")
  if new_owned_by:
      for n_id, attrs in G.nodes(data=True):
          if n_id != profile_id and attrs.get("owned_by") == new_owned_by:
              # Tạo cạnh 2 chiều hoặc có hướng tùy thiết kế ban đầu, trọng số cao nhất
              G.add_edge(profile_id, n_id, type="CO-OWNER", weight=5.0)
              G.add_edge(n_id, profile_id, type="CO-OWNER", weight=5.0)
  ```

### 2. Bổ sung logic tạo cạnh SIMILARITY (Tính toán NLP)

- Để so sánh sự giống nhau về Bio/Profile, chúng ta cần so sánh với các node lân cận. Việc so sánh vector với toàn bộ 8345 nodes trong RAM mỗi lần Fallback có thể gây chậm API (Latency cao).
- **Giải pháp tối ưu Realtime:** Chúng ta chỉ tính `SIMILARITY` giữa node mới và các node lân cận bậc 1 và bậc 2 của nó (những node vừa được nối bằng Follow/Interact/Co-owner).
- **Logic:**
  1. Sử dụng thư viện `sentence-transformers` (như đã dùng ở Module 1) để load model `all-MiniLM-L6-v2`. _(Lưu ý: Nên load model này ở mức global/lifespan để không phải load lại mỗi lần gọi request)._
  2. Lấy chuỗi `bio` của node mới.
  3. Lấy tập hợp các node lân cận (Neighbors) của node mới trong đồ thị `G`.
  4. Lấy chuỗi `bio` của các lân cận này.
  5. Tính Cosine Similarity. Nếu `score > 0.85` (hoặc ngưỡng bạn đã định nghĩa), tạo thêm cạnh:
     ```python
     G.add_edge(profile_id, neighbor_id, type="SIMILARITY", weight=3.0)
     G.add_edge(neighbor_id, profile_id, type="SIMILARITY", weight=3.0)
     ```

## Yêu cầu chất lượng

- Cập nhật an toàn, không làm hỏng luồng kéo BigQuery cũ.
- Tối ưu hóa hiệu năng vòng lặp. Nếu model NLP chưa có sẵn trong RAM, hãy thêm hướng dẫn import và load model một cách thông minh (singleton) để tránh OOM (Out of Memory).
