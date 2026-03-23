---
description: "Thiết lập NetworkX In-memory Graph (Cached Backbone) trên FastAPI bằng cách nạp dữ liệu từ file PyG (.pt) và Metadata."
agent: "agent"
tools: ["editFiles", "codebase"]
---

# Task 1: Setup Reference Graph Backbone (NetworkX + PyG)

Bạn là một Chuyên gia Backend Engineer. Nhiệm vụ của bạn là triển khai **Phase 1** của Module 2 (Profile Inspector).

Chúng ta sử dụng kiến trúc "Cached Backbone". Thay vì gọi BigQuery, FastAPI server khi khởi động sẽ nạp sẵn một "Đồ thị tham chiếu" (được huấn luyện từ Module 1) trực tiếp từ file PyTorch Geometric (`.pt`) và file Metadata (`.csv`) vào RAM thông qua thư viện `NetworkX`.

## 1. Nhiệm vụ (Task)

- Khởi tạo Global State cho FastAPI sử dụng `lifespan` context manager.
- Viết service đọc file `.pt` và `.csv`, map dữ liệu index sang Profile ID thực tế.
- Khởi tạo và lưu trữ đối tượng `nx.MultiDiGraph()` vào bộ nhớ của ứng dụng.
- **Ràng buộc TUYỆT ĐỐI:** Không import hay sử dụng BigQuery trong task này. Chỉ dùng dữ liệu file cục bộ.

## 2. Hướng dẫn chi tiết (Instructions)

### Bước 1: Khởi tạo Global State với Lifespan (`app/main.py`)

- Mở file `app/main.py` (hoặc tạo mới nếu chưa có, cấu trúc chuẩn FastAPI).
- Import `networkx as nx` và `contextlib.asynccontextmanager`.
- Viết hàm `lifespan`:

  ```python
  from contextlib import asynccontextmanager
  from fastapi import FastAPI
  import networkx as nx
  from app.services.inspector_service import load_reference_graph
  import logging

  logger = logging.getLogger(__name__)

  @asynccontextmanager
  async def lifespan(app: FastAPI):
      # Startup
      logger.info("Initializing Graph Backbone...")
      # Tạm thời hardcode đường dẫn file data để test, sau này sẽ đưa vào config
      pt_path = "data/graph_data.pt"
      meta_path = "data/metadata.csv"

      app.state.graph = await load_reference_graph(pt_path, meta_path)
      logger.info(f"Backbone ready! Nodes: {app.state.graph.number_of_nodes()}, Edges: {app.state.graph.number_of_edges()}")

      yield # Ứng dụng chạy

      # Shutdown
      app.state.graph.clear()
      logger.info("Graph Backbone cleared.")

  app = FastAPI(lifespan=lifespan)
  ```

### Bước 2: Viết Service nạp dữ liệu (`app/services/inspector_service.py`)

- Tạo hoặc mở file `app/services/inspector_service.py`.
- Viết hàm `async def load_reference_graph(pt_path: str, meta_path: str) -> nx.MultiDiGraph:`
- **Logic bên trong hàm:**
  1. Kiểm tra file tồn tại (`os.path.exists`). Nếu không có, khởi tạo graph rỗng và log cảnh báo.
  2. Dùng `asyncio.to_thread` để bọc các thao tác I/O đồng bộ (đọc file) nhằm tránh block event loop của FastAPI:
     - Load Tensor: `data = torch.load(pt_path, map_location="cpu")`
     - Load CSV: `df_meta = pd.read_csv(meta_path)`
  3. Khởi tạo `G = nx.MultiDiGraph()`.
  4. **Nạp Nodes:** Duyệt vòng lặp qua `df_meta`. Lấy `profile_id` làm key của Node. Lấy `handle`, `picture_url`, `owned_by` làm attributes. Đưa vào đồ thị: `G.add_node(profile_id, handle=..., picture_url=..., owned_by=...)`.
  5. **Nạp Edges:** Đọc `data.edge_index` (kích thước [2, num_edges]).
     - Lấy tensor `source_indices = data.edge_index[0]` và `target_indices = data.edge_index[1]`.
     - Lấy `profile_id` thực tế từ `df_meta` dựa vào các index này.
     - Đưa vào đồ thị: `G.add_edge(source_profile_id, target_profile_id)`.

## 3. Quản lý lỗi & Validation

- Nếu số lượng Node trong `.pt` (`data.num_nodes`) không khớp với số dòng trong file `.csv`, phải log ra lỗi (`logger.error`) và nạp đồ thị rỗng để an toàn.
- Đảm bảo xử lý lỗi thư mục (tạo thư mục `data/` trống nếu cần để Agent không bị crash khi test).

## 4. Định dạng Output

- Cập nhật/Tạo `app/main.py`.
- Cập nhật/Tạo `app/services/inspector_service.py`.
- Cấu trúc thư mục phải tuân thủ chuẩn FastAPI.
