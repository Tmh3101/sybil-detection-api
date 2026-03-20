---
description: "Bổ sung chi tiết kỹ thuật sâu (Deep Dive) vào tài liệu Module 1 bao gồm: Tech stack, SQL Queries thực tế và Kiến trúc chi tiết của mạng GAE/GAT."
agent: "agent"
tools: ["codebase", "editFiles"]
---

# Deep-Dive Technical Specs for Module 1 Workflow

Bạn là một System Architect và Senior Technical Writer. Trước đó, chúng ta đã có file tài liệu `docs/module1_detailed_workflow.md` mô tả luồng cơ bản.

Nhiệm vụ hiện tại của bạn là mở file này ra và **bơm thêm các chi tiết kỹ thuật (Implementation Details)** bằng cách phân tích trực tiếp mã nguồn trong `docs/colab-code/build_datasets.py` và `docs/colab-code/fullflow.py`.

## Hướng dẫn từng bước (Instructions)

Sử dụng công cụ `editFiles` để chỉnh sửa `docs/module1_detailed_workflow.md`. Hãy giữ nguyên cấu trúc các mục chính và các sơ đồ Mermaid hiện tại, nhưng bổ sung/mở rộng nội dung theo các yêu cầu khắt khe sau:

### Bước 1: Thêm mục "1.2. Công nghệ, Thư viện & Điều kiện cần thiết" (Vào dưới sơ đồ Sequence)

- **Thư viện Backend & AI:** Nêu rõ việc sử dụng `fastapi`, `modal` cho hạ tầng. Nêu rõ hệ sinh thái AI: `torch` (PyTorch 2.1.2+cu121), `torch_geometric` (PyG), `sentence-transformers` (dùng `all-MiniLM-L6-v2`), `scikit-learn` (cho K-Means), `networkx`.
- **Hạ tầng Dữ liệu:** `google-cloud-bigquery`, `pandas`.
- **Điều kiện môi trường (Prerequisites):** Nhấn mạnh hệ thống yêu cầu `GOOGLE_APPLICATION_CREDENTIALS` (Service Account Key) để truy vấn BigQuery và Token của Modal (`MODAL_TOKEN_ID`) để kích hoạt Serverless GPU.

### Bước 2: Bổ sung chi tiết SQL Queries vào mục 2 (Data Ingestion)

- Mở file `build_datasets.py`, tìm các biến chứa câu truy vấn BigQuery (ví dụ: `query_profiles`, `query_follows`, `query_comments`, `query_mirrors`, `query_collects`).
- Bổ sung một tiểu mục **"2.1.1. Truy xuất dữ liệu gốc (BigQuery SQL)"** (trước phần cấu trúc Nút).
- Trích dẫn (dưới dạng code block SQL) ít nhất 2-3 câu truy vấn quan trọng nhất mà hệ thống dùng để kéo dữ liệu từ `lens-protocol-mainnet` để minh họa rõ cách lấy raw data.

### Bước 3: Chi tiết hóa Kiến trúc Mô hình GAE vào mục 3.2

- Mở file `fullflow.py`, tìm class `GATEncoder` và việc khởi tạo `GAE`.
- Cập nhật mục **3.2. Phase 1: Unsupervised Learning (GAE)** với các thông số lớp (Layer) cụ thể:
  - **Input:** Số chiều của Node Feature đầu vào (ví dụ: dựa trên `data.num_features`, thường là 384 chiều text + các chiều On-chain = ~391 chiều).
  - **Lớp GATConv 1:** `in_channels` -> `hidden_channels` (ví dụ 64 hoặc 32), số lượng Attention `heads` (ví dụ: 4), `dropout` rate (ví dụ: 0.3), có `concat=True`. Hàm kích hoạt `F.elu`.
  - **Lớp GATConv 2 (Output của Encoder):** `hidden_channels * heads` -> `out_channels` (đây chính là số chiều của vector nhúng cuối cùng, ví dụ: 16 hoặc 8), `heads=1`, `concat=False`.
  - **Decoder:** Giải thích rõ cơ chế Inner Product Decoder của PyG (tính tích vô hướng giữa 2 vector nhúng của 2 node, truyền qua hàm Sigmoid để tái tạo xác suất tồn tại cạnh).

### Bước 4: Kiểm tra Ranh giới (Scope Validation)

- TUYỆT ĐỐI KHÔNG thêm bất kỳ chi tiết nào về `TransformerClassifier`, Supervised Learning, Train/Test Split, hay Focal Loss từ file `fullflow.py`. Tài liệu chỉ dừng ở GAE, K-Means và Heuristics Rule Engine.

## Định dạng Output (Output Format)

- Chỉnh sửa trực tiếp file `docs/module1_detailed_workflow.md` trong workspace hiện tại.
- Đảm bảo các đoạn code SQL và Python mô tả kiến trúc được đặt trong block code markdown (` ```sql ` và ` ```python `) để dễ đọc.
- Văn phong mạch lạc, học thuật.
