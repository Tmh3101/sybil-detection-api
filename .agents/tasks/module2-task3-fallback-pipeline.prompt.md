---
description: "Xây dựng Fallback Pipeline: Truy xuất BigQuery On-demand cho các Profile chưa có trong RAM và nhúng vào NetworkX."
agent: "agent"
tools: ["editFiles", "codebase"]
---

# Task 3: Fallback Pipeline (On-demand Lazy Loading)

Bạn là một Chuyên gia Backend Engineer. Hệ thống của chúng ta đang sử dụng "Đồ thị tham chiếu" (Reference Graph) trên RAM (`app.state.graph`).
Nhiệm vụ của bạn là xử lý trường hợp Cache Miss: Khi người dùng truy vấn một `profile_id` không có trong RAM, hãy gọi BigQuery để kéo dữ liệu của node đó, nhúng nó vào RAM, và trả về kết quả Ego-graph.

## 1. Mục tiêu (Objectives)

- Xây dựng service `fallback_service.py` để tương tác với BigQuery.
- Lấy thông tin Node và Edges của node bị thiếu.
- Cập nhật node và edges vào `app.state.graph`.
- Tích hợp service này vào luồng API của `inspector.py`.

## 2. Hướng dẫn chi tiết (Instructions)

### Bước 1: Xây dựng `app/services/fallback_service.py`

- Tạo file `app/services/fallback_service.py`.
- Import các thư viện cần thiết: `google.cloud.bigquery`, `pandas`, `ast`, và `networkx`.
- Viết hàm `async def fetch_and_embed_node(app, profile_id: str) -> bool:`
  - **Khởi tạo BigQuery Client:** Sử dụng credentials từ biến môi trường `GOOGLE_APPLICATION_CREDENTIALS` (giống cách làm ở Module 1).
  - **Query Node:** Viết câu SQL lấy 1 dòng duy nhất từ bảng `lens-protocol-mainnet.account.metadata` và `account_stats` cho `profile_id` này. Các trường cần lấy: `handle`, `owned_by`, `metadata` (chứa bio, picture dạng dict str).
  - **Parse Metadata:** Dùng `ast.literal_eval` để bóc tách `picture_url` từ chuỗi `metadata` (như đã làm ở Module 1).
  - **Query Edges:** Viết câu SQL lấy các edges từ bảng `follower` và `interact` nơi `source = @profile_id` OR `target = @profile_id`.
  - **Nhúng vào NetworkX (Embed):**
    - Lấy đồ thị: `G = app.state.graph`
    - Thêm node mới: `G.add_node(profile_id, handle=..., picture_url=..., owned_by=..., is_lazy=True)` (Đánh dấu `is_lazy` để biết node này được nạp tự động).
    - Thêm edges: Duyệt qua danh sách edges kéo về. **Rất quan trọng:** Chỉ thực hiện `G.add_edge()` nếu node đối diện (neighbor) **đã tồn tại** trong `G.nodes`. Điều này giúp neo node mới vào khung xương hiện tại mà không làm phình to đồ thị bằng các node rác.
  - Trả về `True` nếu thành công, `False` nếu không tìm thấy profile trên BigQuery. Dùng `asyncio.to_thread` để bọc các thao tác gọi BigQuery đồng bộ.

### Bước 2: Tích hợp vào Router (`app/api/v1/endpoints/inspector.py`)

- Mở file `inspector.py`.
- Import service: `from app.services.fallback_service import fetch_and_embed_node`.
- Trong endpoint `GET /profile/{profile_id}`, cập nhật logic rẽ nhánh:

  ```python
  G = request.app.state.graph

  if profile_id not in G:
      # Cache Miss -> Kích hoạt Fallback Pipeline
      success = await fetch_and_embed_node(request.app, profile_id)
      if not success:
          raise HTTPException(status_code=404, detail="Profile not found on Lens Protocol.")

  # Đến đây, chắc chắn profile_id đã có trong G (hoặc từ đầu, hoặc vừa được Fallback nạp)
  # Thực hiện trích xuất Ego-graph như Task 2
  subgraph = nx.ego_graph(G, profile_id, radius=1, undirected=False)

  # Format và trả về JSON chuẩn
  # Lưu ý: Sắp xếp JSON trả về theo chuẩn phẳng (flattened) ở profile_info
  ```

## 3. Quản lý lỗi & Validation

- Bắt lỗi khi BigQuery credentials không hợp lệ hoặc thiếu bảng.
- Đảm bảo endpoint không bị crash nếu Node trên BigQuery bị khuyết dữ liệu (VD: `metadata` là Null).

## 4. Định dạng Output

- Tạo `app/services/fallback_service.py`.
- Cập nhật `app/api/v1/endpoints/inspector.py`.
