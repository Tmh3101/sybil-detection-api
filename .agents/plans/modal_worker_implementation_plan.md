# MASTER PLAN: Yêu Cầu Triển Khai Modal Worker (Module 1)

## 1. Tổng quan Dự án (Project Context)

Chúng ta đang xây dựng `modal_worker/app.py` cho hệ thống **Web3 Sybil Detection Dashboard**. Đây là "Nhà máy AI" chạy trên nền tảng Serverless GPU (Modal).
Nhiệm vụ của Worker này là nhận yêu cầu (thời gian `start_date`, `end_date`), kéo dữ liệu từ BigQuery, xây dựng đồ thị PyTorch Geometric, huấn luyện mạng GAE (Graph Autoencoder) từ đầu, phân cụm bằng K-Means, gán nhãn rủi ro bằng luật (Heuristics) và trả về JSON chuẩn.

**Tài liệu tham chiếu cốt lõi:**

- Kiến trúc tổng thể: `docs/module1_detailed_workflow.md`
- Code thực nghiệm gốc: `docs/colab-code/build_datasets.py` và `docs/colab-code/fullflow.py`

---

## 2. Quy tắc Thực thi cho AI Agent (Execution Rules)

- **Tách biệt hoàn toàn (Decoupling):** File `modal_worker/app.py` chạy trên cloud độc lập. Tuyệt đối không import bất kỳ file nào từ thư mục `backend/` hoặc `app/` của FastAPI.
- **Lazy Loading (Import cục bộ):** Tất cả các thư viện nặng (`torch`, `pandas`, `google.cloud`, `sklearn`) PHẢI được import bên trong hàm `@app.function`. Không import ở global scope để tránh lỗi khi trigger script ở máy local.
- **Giới hạn phạm vi (Strict Scope):** Chỉ implement **Unsupervised Learning (GAE)**. Tuyệt đối KHÔNG implement mạng phân loại có giám sát (TransformerClassifier) hay Focal Loss.

---

## 3. Lộ trình Triển khai Chi tiết (Phased Implementation Plan)

AI Agent sẽ được yêu cầu thực hiện từng Phase một thông qua các prompt riêng biệt. Dưới đây là mô tả chi tiết từng Phase:

### Phase 1: Môi trường & Kéo Dữ Liệu (Data Ingestion)

**Mục tiêu:** Cấu hình container và kết nối thành công Google BigQuery.

- **Bước 1.1:** Định nghĩa `modal.Image` cài đặt đầy đủ: `torch==2.1.2`, `torch_geometric`, `google-cloud-bigquery`, `db-dtypes`, `pandas`, `sentence-transformers`, `scikit-learn`, `networkx`.
- **Bước 1.2:** Khai báo `modal.Secret.from_name("gcp-sybil-secret")` vào App để tự động nạp `GOOGLE_APPLICATION_CREDENTIALS`.
- **Bước 1.3:** Viết hàm `fetch_bigquery_data(start_date, end_date)` mô phỏng lại các truy vấn SQL từ `build_datasets.py`. Lấy về `df_nodes` và `df_edges`.

### Phase 2: Kỹ thuật Đặc trưng & Xây Dựng Đồ Thị (Graph Construction)

**Mục tiêu:** Chuyển đổi Pandas DataFrame thành `torch_geometric.data.Data`.

- **Bước 2.1:** Khởi tạo `SentenceTransformer('all-MiniLM-L6-v2')`. Nhúng văn bản (Handle + Name + Bio) thành tensor 384 chiều.
- **Bước 2.2:** Chuẩn hóa (MinMaxScaler/Z-score) các đặc trưng on-chain (tx_count, followers...). Ghép (Concat) với tensor văn bản tạo thành ma trận đặc trưng `x`.
- **Bước 2.3:** Xây dựng ma trận cạnh `edge_index` (kích thước `[2, num_edges]`) và mảng đặc trưng cạnh `edge_attr` từ `df_edges`.

### Phase 3: Xây dựng & Huấn luyện Graph Autoencoder (GAE Training)

**Mục tiêu:** Mã hóa đồ thị thành vector nhúng.

- **Bước 3.1:** Chuyển class `GATEncoder` (với 2 lớp `GATConv` lấy từ `fullflow.py`) vào file.
- **Bước 3.2:** Khởi tạo mô hình `GAE(GATEncoder(...))` và Optimizer (`Adam`).
- **Bước 3.3:** Viết vòng lặp huấn luyện (Train Loop) khoảng 100 epochs. Tính `model.recon_loss(z, edge_index)` và cập nhật trọng số.
- **Bước 3.4:** Trích xuất ma trận nhúng cuối cùng `node_embeddings = model.encode(x, edge_index)`.

### Phase 4: Phân Cụm & Hệ Luật (Clustering & Heuristics)

**Mục tiêu:** Gán nhãn nghiệp vụ từ vector toán học.

- **Bước 4.1:** Sử dụng `sklearn.cluster.KMeans` để phân cụm `node_embeddings`. Trả về `cluster_ids`.
- **Bước 4.2:** Hiện thực hóa logic Hệ luật (Heuristics Rule Engine) từ tài liệu. Duyệt qua các cụm, đánh giá mật độ cạnh bất thường (đặc biệt là cạnh `SIMILARITY` và `CO-OWNER`) để tính `risk_score`.
- **Bước 4.3:** Gán 4 nhãn cứng: `BENIGN`, `LOW_RISK`, `HIGH_RISK`, `MALICIOUS` dựa trên `risk_score`.

### Phase 5: Chuẩn hóa Đầu ra (Output Formatting)

**Mục tiêu:** Ánh xạ dữ liệu thành JSON theo chuẩn FastAPI mong đợi.

- **Bước 5.1:** Lặp qua các Nút. Format thành dictionary có `id`, `label`, `cluster_id`, `risk_score` và `attributes` (chứa các on-chain stats hiển thị trên UI).
- **Bước 5.2:** Lặp qua các Cạnh. Format thành dictionary có `source`, `target`, `edge_type` và `weight`.
- **Bước 5.3:** Trả về dictionary tổng: `{"nodes": [...], "links": [...]}`. Hàm Modal kết thúc tại đây.
