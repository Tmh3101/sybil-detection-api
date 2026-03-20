---
description: "Phân tích mã nguồn Colab và viết tài liệu thiết kế hệ thống chi tiết cho luồng Machine Learning của Module 1, bao gồm các sơ đồ luồng Mermaid."
agent: "agent"
tools: ["codebase", "editFiles"]
---

# Document Module 1: ML Pipeline & Workflow

Bạn là một Technical Writer cấp cao kiêm System Architect và Data Scientist. Nhiệm vụ của bạn là đọc hiểu các mã nguồn thực nghiệm trên Colab và viết một tài liệu kỹ thuật toàn diện mô tả luồng hoạt động (Workflow) của Module 1 (Sybil Discovery Engine).

## Ngữ cảnh & Dữ liệu đầu vào (Context & Input)

Hãy sử dụng công cụ `codebase` để phân tích kỹ 2 file sau trong thư mục `docs/colab-code/`:

1. `build_datasets.py`: Phân tích cách truy vấn BigQuery, cách tạo các node features (thống kê on-chain, nhúng text bằng MiniLM) và cách xây dựng các loại cạnh (Follow, Interact, Co-owner, Similarity).
2. `fullflow.py`: Phân tích quy trình học máy bao gồm: Khởi tạo GAE (Graph Autoencoder), K-Means clustering, gán nhãn giả lập bằng Heuristics (Pseudo-labeling), và cuối cùng là huấn luyện mô hình phân loại (Transformer/GAT).

## Nhiệm vụ (Task Section)

Viết một file tài liệu Markdown mới có tên `docs/module1_detailed_workflow.md`. Tài liệu này phải cực kỳ chi tiết, mang văn phong học thuật và chuyên nghiệp, phù hợp để đưa vào phụ lục luận văn tốt nghiệp.

## Hướng dẫn cấu trúc tài liệu (Instructions & Structure)

Tài liệu của bạn phải bao gồm các phần sau:

### 1. Tổng quan kiến trúc (Architecture Overview)

- Tóm tắt mục tiêu của Module 1.
- **YÊU CẦU BẮT BUỘC:** Vẽ một biểu đồ **Mermaid Sequence Diagram** thể hiện luồng giao tiếp giữa: `User (Frontend)` -> `FastAPI (Backend)` -> `Modal (Serverless GPU Worker)` -> `PyTorch Geometric (ML Engine)`.

### 2. Tiền xử lý dữ liệu & Trích xuất đặc trưng (Data Ingestion & Feature Engineering)

- Mô tả nguồn dữ liệu (Lens Protocol data từ BigQuery).
- Liệt kê chi tiết cấu trúc Nút (Nodes) và Cạnh (Edges).
- Giải thích cách trích xuất đặc trưng ngữ nghĩa (Semantic Text Embedding) và đặc trưng hình ảnh.

### 3. Luồng Học máy cốt lõi (Core ML Pipeline)

**YÊU CẦU BẮT BUỘC:** Vẽ một biểu đồ **Mermaid Flowchart (Đồ thị luồng)** mô tả chuỗi các bước từ Dữ liệu thô -> GAE -> K-Means -> Heuristics -> Supervised Classifier.
Sau đó, diễn giải chi tiết từng bước bằng text:

- **Phase 1: Unsupervised Learning:** Cấu trúc mạng GAE, hàm Loss (Reconstruction Loss), mục tiêu lấy vector nhúng (embeddings).
- **Phase 2: Clustering & Pseudo-labeling:** Cấu hình thuật toán K-Means, và mô tả (bằng lời hoặc công thức) các hệ luật (Heuristics) dùng để gán 4 nhãn (BENIGN, LOW_RISK, HIGH_RISK, MALICIOUS).
- **Phase 3: Supervised Transfer Learning:** Cách sử dụng Graph Transformer / GAT để học phân loại dựa trên các nhãn vừa gán. Đề cập đến hàm Loss (Focal Loss) để xử lý mất cân bằng dữ liệu.

### 4. Kết xuất đầu ra (Output Formatting)

- Giải thích cách dữ liệu từ bước 3 được format thành JSON (chứa mảng `nodes` và `links`) để FastAPI và Frontend tiêu thụ.

## Định dạng Output (Output Format)

- Tạo và ghi nội dung vào file `docs/module1_detailed_workflow.md`.
- Sử dụng cú pháp `mermaid ... ` chuẩn xác để vẽ biểu đồ.
- Đảm bảo các tiêu đề (H1, H2, H3) được tổ chức phân cấp rõ ràng, dễ đọc.
- Sử dụng danh sách (bullet points) hoặc bảng (tables) để trình bày các thuộc tính của Nút/Cạnh.
