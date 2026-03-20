---
description: "Thực thi Phase 1 & 2 của Modal Worker: Thiết lập môi trường, kết nối BigQuery kéo dữ liệu và xây dựng đồ thị PyTorch Geometric."
agent: "agent"
tools: ["codebase", "editFiles"]
---

# Implement Modal Worker - Task 1: Data Ingestion & Graph Construction

Bạn là một chuyên gia Data Engineer và MLOps. Nhiệm vụ của bạn là hiện thực hóa Phase 1 và Phase 2 trong file `.agents/plans/modal_worker_implementation_plan.md`.

Hãy chỉnh sửa trực tiếp file `modal_worker/app.py` để thay thế dữ liệu Mock (đồ thị ngẫu nhiên) bằng dữ liệu thật từ Google BigQuery, dựa trên logic đã có tại `docs/colab-code/build_datasets.py`.

## Hướng dẫn từng bước (Instructions)

### Bước 1: Cấu hình Môi trường & Secret (Modal Image)

Trong file `modal_worker/app.py`, hãy cập nhật biến `image` và `app`:

- Thêm các thư viện sau vào `pip_install`: `google-cloud-bigquery`, `db-dtypes`, `pandas`, `sentence-transformers`. (Giữ nguyên `torch==2.1.2`, `torch_geometric`, `scikit-learn`, `networkx`).
- Cập nhật khởi tạo App để nhận Secret từ Modal:
  `app = modal.App("sybil-discovery-engine", image=image, secrets=[modal.Secret.from_name("gcp-sybil-secret")])`

### Bước 2: Viết hàm `fetch_bigquery_data`

- Đặt hàm này ở cấp độ module (hoặc bên trong hàm chính tùy chiến lược lazy load, nhưng khuyến nghị khai báo bên ngoài và chỉ import `bigquery`, `pandas` bên trong hàm để tránh lỗi local).
- Logic:
  - Import `from google.cloud import bigquery` và `import pandas as pd`.
  - Khởi tạo `client = bigquery.Client(location="US")`.
  - Tham khảo `docs/colab-code/build_datasets.py` để viết 2 câu truy vấn SQL cơ bản (có bộ lọc `start_date` và `end_date`):
    1. Lấy danh sách tài khoản (Nodes) từ `lens-protocol-mainnet.account.metadata` (Lấy id, handle, name, bio, và 1-2 stats cơ bản).
    2. Lấy danh sách quan hệ Follow (Edges) từ `lens-protocol-mainnet.account.following_history`.
  - Trả về 2 Pandas DataFrame: `df_nodes` và `df_edges`.

### Bước 3: Viết hàm `build_pyg_graph`

- Logic:
  - Nhận đầu vào là `df_nodes` và `df_edges`.
  - Import `import torch` và `from sentence_transformers import SentenceTransformer`.
  - Khởi tạo `model = SentenceTransformer('all-MiniLM-L6-v2')`.
  - Nối chuỗi cột text của nodes (Handle + Name + Bio) và dùng model để encode thành tensor (kích thước `[num_nodes, 384]`). Đây sẽ là `x` (Node features).
  - Map các `profile_id` từ `df_edges` sang index (0 đến N-1) và tạo `edge_index` (tensor kích thước `[2, num_edges]`).
  - Import `from torch_geometric.data import Data` và trả về đối tượng `Data(x=x, edge_index=edge_index)`. Đồng thời trả về danh sách mapping `profile_id` để sau này map ngược lại.

### Bước 4: Cập nhật hàm chính `train_gae_pipeline`

- Xóa bỏ logic dùng `nx.erdos_renyi_graph` và sinh tensor ngẫu nhiên.
- Lấy `start_date`, `end_date` từ `payload`.
- Gọi hàm `fetch_bigquery_data` $\rightarrow$ Nhận DataFrames.
- Gọi hàm `build_pyg_graph` $\rightarrow$ Nhận đối tượng PyG `Data`.
- **Tạm thời (Mock cho Phase tiếp theo):** Tạo `embeddings = torch.randn(num_nodes, 16)` để hàm KMeans ở bên dưới không bị lỗi.
- Đảm bảo kết quả JSON trả về vẫn đúng cấu trúc của `GraphDataSchema`.

## Ràng buộc (Constraints)

- **CỰC KỲ QUAN TRỌNG:** Tất cả các thư viện nặng (`google.cloud`, `pandas`, `torch`, `sentence_transformers`) PHẢI được import cục bộ (lazy import) bên trong các hàm. Không được import ở trên cùng của file `app.py`. Nếu vi phạm, khi người dùng gõ lệnh `modal deploy` ở máy local sẽ bị văng lỗi thiếu thư viện.

## Định dạng Output

Sử dụng công cụ `editFiles` để ghi đè (overwrite) những thay đổi này thẳng vào file `modal_worker/app.py`.
