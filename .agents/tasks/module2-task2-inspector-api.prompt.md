---
description: "Xây dựng Router API cho Inspector và logic trích xuất Ego-Graph (Cache Hit) từ NetworkX."
agent: "agent"
tools: ["editFiles", "codebase"]
---

# Task 2: Inspector API & Ego-Graph Extraction

Bạn là một Chuyên gia Backend Engineer. Hệ thống FastAPI đã có sẵn đối tượng đồ thị `app.state.graph` (NetworkX) chứa hàng ngàn nodes được nạp từ lúc khởi động.
Nhiệm vụ của bạn là tạo API endpoint để nhận yêu cầu từ người dùng, kiểm tra xem Profile ID có trong RAM hay không, và trích xuất đồ thị lân cận (Ego-graph).

## 1. Mục tiêu (Objectives)

- Tạo router mới cho Module 2 tại `app/api/v1/endpoints/inspector.py`.
- Viết API `GET /profile/{profile_id}`.
- Trích xuất Ego-graph bằng NetworkX và format kết quả trả về chuẩn JSON.
- Đăng ký router này vào ứng dụng FastAPI chính (`app/main.py`).

## 2. Hướng dẫn chi tiết (Instructions)

### Bước 1: Khởi tạo Router (`app/api/v1/endpoints/inspector.py`)

- Tạo file `inspector.py` trong thư mục `app/api/v1/endpoints/`.
- Import `APIRouter`, `Request`, và `HTTPException` từ FastAPI.
- Khởi tạo router: `router = APIRouter()`

### Bước 2: Viết Endpoint `GET /profile/{profile_id}`

- Xây dựng endpoint nhận tham số đường dẫn `profile_id` (chuỗi hex).
- Lấy đối tượng đồ thị từ state: `G = request.app.state.graph`.
- **Logic rẽ nhánh (Traffic Controller):**
  - **Kiểm tra Cache Hit:** `if profile_id in G:`
    - Sử dụng `nx.ego_graph(G, profile_id, radius=1, undirected=False)` để lấy đồ thị con (subgraph).
    - **Format JSON trả về theo chuẩn API Spec:**
      - Trích xuất thông tin node gốc (Profile được query) từ subgraph để điền vào `profile_info`.
      - Chuyển đổi subgraph thành mảng `nodes` và `links` để điền vào `local_graph`.
      - Phần `analysis` tạm thời mock dữ liệu hoặc để rỗng (sẽ hoàn thiện khi tích hợp AI model).
    - Cấu trúc JSON trả về (Dùng Pydantic schema hoặc trả thẳng Dict):
      ```json
      {
        "profile_info": {
          "id": profile_id,
          "handle": G.nodes[profile_id].get("handle", "unknown"),
          "picture_url": G.nodes[profile_id].get("picture_url", "")
          "owned_by": G.nodes[profile_id].get("owned_by", "")
        },
        "analysis": {
          "sybil_probability": null,
          "classification": "PENDING_AI_INFERENCE",
          "reasoning": []
        },
        "local_graph": {
          "nodes": [
            {
              "id": "...",
              "attributes": {"handle": "...", "picture_url": "...", "owned_by": "..."}
            }
          ],
          "links": [
            {"source": "...", "target": "...", "edge_type": "...", "weight": 2.0}
          ]
        }
      }
      ```
  - **Kiểm tra Cache Miss:** `else:`
    - Tạm thời ném ra `HTTPException(status_code=404, detail="Profile not found in Backbone. Fallback pipeline will be implemented here.")`.

### Bước 3: Đăng ký Router (`app/main.py`)

- Mở file `app/main.py`.
- Import router vừa tạo: `from app.api.v1.endpoints import inspector` (đảm bảo file `__init__.py` tồn tại và đúng chuẩn import).
- Bổ sung vào cấu hình ứng dụng: `app.include_router(inspector.router, prefix="/api/v1/inspector", tags=["Inspector"])`.

## 3. Quản lý lỗi & Validation

- Đảm bảo xử lý lỗi an toàn nếu `app.state.graph` chưa sẵn sàng (trả về 503 Service Unavailable).
- Xử lý các node trong Ego-graph bị thiếu thuộc tính (dùng `.get()` với giá trị mặc định để tránh KeyError).

## 4. Định dạng Output

- Tạo file `app/api/v1/endpoints/inspector.py`.
- Sửa đổi file `app/main.py`.
