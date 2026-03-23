---

# MASTER PLAN: Triển Khai Backend Module 2 (Profile Inspector)
**Kiến trúc: Lazy Loading & Hybrid Cache (Đồ thị tham chiếu)**

## 1. Tổng quan (Context & Architecture)
Module 2 đóng vai trò là "Kính hiển vi thời gian thực" phục vụ quản trị viên. Điểm đột phá của kiến trúc này là sử dụng **Đồ thị tham chiếu (Reference Graph)** kết hợp với **Truy vấn dự phòng (On-demand Fallback)**.

- **Đồ thị tham chiếu (Cached Backbone):** Nạp sẵn file Tensor (`.pt`) từ Module 1 vào RAM bằng thư viện `NetworkX` khi server khởi động.
- **Cache Hit (Xử lý tức thì):** Nếu Profile ID nằm trong Backbone $\rightarrow$ Cắt lân cận $\rightarrow$ Đẩy qua AI $\rightarrow$ Trả kết quả (Độ trễ < 50ms).
- **Cache Miss (Xử lý Lazy Load):** Nếu Profile ID là mới $\rightarrow$ Kéo data từ BigQuery (chỉ node đó) $\rightarrow$ Tính toán đặc trưng $\rightarrow$ Gắn vào Backbone $\rightarrow$ Đẩy qua AI.

---

## 2. Lộ trình triển khai (Phased Roadmap)

### Phase 1: Nạp Đồ Thị Tham Chiếu (The Backbone Setup)

- **Mục tiêu:** Nạp file `.pt` (PyG Data) và Metadata (CSV) vào NetworkX khi FastAPI startup.
- **Công việc:**
  - Khởi tạo `app.state.graph = nx.MultiDiGraph()`.
  - Viết hàm `load_graph_from_pt`: Mapping các Node (kèm `handle`, `picture_url`, `owned_by`) và Edges từ Tensor index sang Profile ID thực tế.
  - **Ràng buộc:** TUYỆT ĐỐI không gọi BigQuery ở bước này. Chỉ dùng dữ liệu đã có sẵn từ Module 1.

### Phase 2: Router & Logic Rẽ Nhánh (The Traffic Controller)

- **Mục tiêu:** Viết API `GET /inspector/profile/{id}` và xử lý luồng logic.
- **Công việc:**
  - Kiểm tra: `if node_id in app.state.graph:` $\rightarrow$ Chuyển sang Phase 4.
  - `else:` $\rightarrow$ Gọi Service Fallback (Phase 3).

### Phase 3: Fallback Pipeline (Xử lý Out-of-Vocabulary Node)

- **Mục tiêu:** Kéo dữ liệu của node mới và nhúng (embed) vào đồ thị tham chiếu.
- **Công việc (Chỉ chạy khi Cache Miss):**
  - **Truy vấn siêu nhỏ (Micro-Query):** Gọi BigQuery lấy metadata của `node_id` mới. Lấy các edges mà `source = node_id` hoặc `target = node_id` VÀ node đối diện phải nằm trong `app.state.graph`.
  - **Feature Engineering:** Dùng `SentenceTransformer` nhúng Text (Bio) và `MinMaxScaler` chuẩn hóa On-chain stats để tạo vector 391 chiều.
  - **Cập nhật RAM:** Thêm node và edges mới này vào `app.state.graph` (Có thể đánh dấu `is_lazy=True` để dọn dẹp sau này nếu cần).

### Phase 4: AI Inference & Giải thích (Ego-Graph to PyG)

- **Mục tiêu:** Chấm điểm Sybil và xuất JSON.
- **Công việc:**
  - Trích xuất lân cận: `nx.ego_graph(app.state.graph, node_id, radius=1 or 2)`.
  - **Converter:** Chuyển đổi cái Subgraph (NetworkX) vừa cắt trở lại thành định dạng `torch_geometric.data.Data` (Tensor).
  - **Inference:** Đẩy Tensor này qua mô hình `TransformerClassifier` đã train để lấy `sybil_probability`.
  - **Lý luận (Reasoning):** Tính tỷ lệ `CO-OWNER`, `SIMILARITY` trong Ego-graph để sinh ra lý do giải thích (Ví dụ: "Phát hiện 3 tài khoản dùng chung ví trong mạng lưới lân cận").

---

## 3. Thiết kế API Spec (Module 2)

| Phương thức | Endpoint                             | Mô tả & Cách hoạt động                                                                                                     |
| :---------- | :----------------------------------- | :------------------------------------------------------------------------------------------------------------------------- |
| **GET**     | `/api/v1/inspector/search?q={query}` | Tìm kiếm Profile. Ưu tiên search trong `app.state.graph` (RAM). Nếu không có, search trên BigQuery (chỉ lấy ID và Handle). |
| **GET**     | `/api/v1/inspector/profile/{id}`     | Trả về thông tin chi tiết, Subgraph lân cận, và AI Score. (Tự động trigger Phase 2, 3, 4).                                 |

---

## 4. Cấu trúc thư mục định hướng

```text
backend/app/
├── api/v1/endpoints/
│   └── inspector.py          <-- Router API Module 2
├── services/
│   ├── inspector_service.py  <-- Quản lý RAM Graph (NetworkX) và luồng Hit/Miss
│   └── fallback_service.py   <-- Kéo data BigQuery và chạy Transform (Phase 3)
└── core/
    └── model_loader.py       <-- Load weights của Graph Transformer
```

## 5. Ghi chú tối quan trọng cho AI Agent

- Hàm trích xuất Ego-graph phải dùng `undirected=False` để giữ đúng chiều tương tác.
- Ở **Phase 3 (Fallback)**, việc gọi mô hình NLP `SentenceTransformer` phải được cache model để không tải lại nhiều lần gây nghẽn API.
- Kết quả API trả về phải tuân thủ nghiêm ngặt `GraphDataSchema` (giống Module 1) để Frontend dễ dàng vẽ đồ thị thống nhất.

---
