---
description: "Thực thi Phase 3, 4 & 5 của Modal Worker: Xây dựng mạng GAE, vòng lặp huấn luyện, phân cụm K-Means, hệ luật Heuristics và format đầu ra."
agent: "agent"
tools: ["codebase", "editFiles"]
---

# Implement Modal Worker - Task 2: GAE Training & Heuristics Labeling

Bạn là một chuyên gia AI/MLOps. Trước đó, bạn đã hoàn thành Task 1 (Kéo dữ liệu BigQuery và dựng đồ thị PyG) cho file `modal_worker/app.py`.

Nhiệm vụ của bạn hiện tại là thực thi **Phase 3, Phase 4 và Phase 5** dựa trên file `.agents/plans/modal_worker_implementation_plan.md`. Bạn cần thay thế hoàn toàn phần dữ liệu mock (random embeddings) bằng logic Machine Learning thực sự được trích xuất từ `docs/colab-code/fullflow.py`.

## Hướng dẫn từng bước (Instructions)

### Bước 1: Xây dựng kiến trúc GAE (Phase 3)

- Bên trong file `modal_worker/app.py`, hãy định nghĩa class `GATEncoder(torch.nn.Module)` (Có thể đặt ngay bên trên hàm `train_gae_pipeline` hoặc bên trong khối lazy import).
- Tham chiếu kiến trúc từ `fullflow.py`:
  - Lớp 1: `GATConv(in_channels, 32, heads=4, dropout=0.3, concat=True)`
  - Lớp 2: `GATConv(32 * 4, 16, heads=1, concat=False, dropout=0.3)`
- Trong hàm `train_gae_pipeline`, sau khi có đối tượng `data` từ `build_pyg_graph`:
  - Khởi tạo `encoder = GATEncoder(in_channels=data.num_features)`
  - Khởi tạo `model = GAE(encoder)` và đẩy model/data lên device (GPU `cuda` nếu có, ngược lại `cpu`).
  - Cấu hình Optimizer: `torch.optim.Adam(model.parameters(), lr=0.005)`.
  - Viết vòng lặp huấn luyện (Train Loop) khoảng 100 epochs. Trong mỗi epoch: gọi `model.train()`, `optimizer.zero_grad()`, lấy `z = model.encode(...)`, tính `loss = model.recon_loss(z, data.edge_index)`, và `loss.backward()`, `optimizer.step()`.
  - Kết thúc vòng lặp, chạy `model.eval()` để lấy `node_embeddings = model.encode(...)`. Đưa vector này về `.cpu().detach().numpy()`.

### Bước 2: Phân cụm & Hệ luật (Phase 4)

- **K-Means:** Chạy `KMeans(n_clusters=3)` (hoặc linh hoạt tùy số nodes) trên `node_embeddings` để lấy mảng `cluster_ids`.
- **Heuristics (Gán nhãn rủi ro):**
  - Khởi tạo mảng `risk_scores` và `labels` cho tất cả các nodes.
  - Chuyển logic hệ luật (Heuristics) từ file `docs/module1_detailed_workflow.md` và `fullflow.py` vào.
  - Gợi ý logic đơn giản hóa cho Agent: Lặp qua từng node, kiểm tra xem node đó có cạnh liên kết loại `SIMILARITY` hoặc `CO-OWNER` hay không (bằng cách tra cứu `df_edges` hoặc `edge_attr`). Tính điểm `risk_score` (từ 0.0 đến 1.0).
  - Ánh xạ điểm ra nhãn: `< 0.3` $\rightarrow$ `BENIGN`, `0.3 - 0.6` $\rightarrow$ `LOW_RISK`, `0.6 - 0.8` $\rightarrow$ `HIGH_RISK`, `> 0.8` $\rightarrow$ `MALICIOUS`.

### Bước 3: Chuẩn hóa Đầu ra (Phase 5)

- Xóa bỏ đoạn code mock tạo `nodes` và `links` cũ.
- Ánh xạ lại các `profile_id` gốc (từ tuple/mapping trả về ở Bước 1) vào dictionary.
- Tạo mảng `nodes` chứa: `id` (profile_id gốc), `label`, `cluster_id`, `risk_score`, và `attributes` (số liệu on-chain cơ bản lấy từ `df_nodes`).
- Tạo mảng `links` chứa: `source`, `target`, `edge_type` (từ `df_edges`), `weight`.
- Trả về dictionary: `{"nodes": nodes, "links": links}`.

## Ràng buộc (Constraints)

- **Lazy Imports:** Đảm bảo class `GATEncoder` và vòng lặp train nếu dùng các thư viện `torch`, `torch_geometric` thì các thư viện này PHẢI được import bên trong `@app.function` hoặc class được định nghĩa bên trong hàm để tránh văng lỗi ở môi trường local khi chạy `modal deploy`.
- Giữ nguyên cấu trúc Decorator `@app.function(gpu="T4", timeout=1800)`.

## Định dạng Output

Dùng tool `editFiles` để ghi đè các logic mới này vào `modal_worker/app.py`. Giữ lại các comment giải thích các bước để code dễ bảo trì.
