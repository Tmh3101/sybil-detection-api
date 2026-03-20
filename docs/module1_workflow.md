# Tài liệu Kiến trúc & Luồng Hoạt Động - Module 1 (Sybil Discovery Engine)

## 1. Tổng quan (Overview)

**Module 1 (Sybil Discovery Engine)** là phân hệ Macro View dành cho Admin hoặc Data Scientist. Mục tiêu của module này là tự động hóa quá trình khám phá, phân cụm và gán nhãn rủi ro (Data Annotation) cho hàng ngàn tài khoản trên mạng xã hội Web3 (Lens Protocol) trong một khoảng thời gian nhất định.

Khác với các hệ thống kiểm duyệt truyền thống, Module 1 sử dụng phương pháp **Học chuyển giao (Transductive Learning)**. Nghĩa là hệ thống không dùng một mô hình học máy tĩnh (pre-trained), mà sẽ khởi tạo và huấn luyện mô hình đồ thị từ đầu (Train-on-the-fly) ngay trên tập dữ liệu vừa được truy vấn nhằm nắm bắt các hành vi tấn công Sybil mới nhất.

## 2. Kiến trúc Hạ tầng (Infrastructure)

Module 1 được xây dựng theo kiến trúc **Hybrid Asynchronous (Lai & Bất đồng bộ)** để giải quyết bài toán thắt nút cổ chai (Bottleneck) khi tính toán AI nặng:

- **API Gateway (FastAPI - VPS/Local):** Tiếp nhận yêu cầu, quản lý trạng thái tiến trình (Polling) và giao tiếp với Frontend.
- **AI Worker (Modal Serverless GPU):** Đóng vai trò là "Nhà máy AI". Khi có yêu cầu, Modal sẽ cấp phát một container chứa GPU (NVIDIA T4), nạp thư viện PyTorch Geometric, huấn luyện mô hình và tự hủy khi hoàn thành.

## 3. Luồng Thực Thi Chi Tiết (Detailed Workflow)

Quá trình từ lúc người dùng thao tác đến khi hiển thị đồ thị WebGL trải qua 6 bước:

### Bước 1: Khởi tạo Yêu cầu (Frontend $\rightarrow$ FastAPI)

- Người dùng chọn `TimeRange` (ví dụ: tuần đầu tiên của tháng 12/2025) và `max_nodes` trên giao diện.
- Frontend gửi POST request tới `API Gateway`.
- **FastAPI** sử dụng lệnh `modal_func.spawn(payload)` để đẩy tác vụ sang Modal mà không chờ kết quả (Non-blocking I/O). API lập tức trả về một `task_id` cho Frontend.

### Bước 2: Nạp và Tiền Xử Lý Dữ Liệu (Data Ingestion - Trên Modal)

- Container Modal được khởi động, nhận tham số và truy xuất dữ liệu thô (từ Cloud Storage hoặc file tĩnh).
- Tiến hành rút trích đặc trưng nút (Node Features):
  - **Đặc trưng thống kê (On-chain):** Số lượng giao dịch, Gas tiêu thụ, v.v.
  - **Đặc trưng ngữ nghĩa (Semantic Text):** Gom chuỗi (Handle, Name, Bio) và nhúng qua mô hình ngôn ngữ `all-MiniLM-L6-v2` tạo thành vector 384 chiều.
  - **Đặc trưng hình ảnh:** Nhị phân hóa biến Avatar (1 có, 0 không).
- Xây dựng đồ thị `torch_geometric.data.Data` với các loại cạnh đặc thù: Follow, Interact, Co-owner, Similarity.

### Bước 3: Học Biểu Diễn Đồ Thị (Unsupervised GAE Training)

- Modal khởi tạo mô hình **Graph Autoencoder (GAE)** với mạng nơ-ron nền tảng là GAT (Graph Attention Network).
- Thực hiện vòng lặp huấn luyện (Train Loop) khoảng 100-200 epochs ngay trên tập dữ liệu vừa tạo.
- **Mục tiêu:** Ép mô hình học cách tái tạo lại cấu trúc liên kết của đồ thị. Kết thúc bước này, mạng GAE trích xuất ra được tập hợp các vector nhúng (Node Embeddings). Các tài khoản thuộc cùng một mạng lưới Sybil (tương tác chéo, chuyển tiền vòng tròn) sẽ có vector nhúng rất gần nhau trong không gian vector.

### Bước 4: Phân Cụm & Gán Nhãn Giả Lập (Clustering & Pseudo-labeling)

- **K-Means Clustering:** Sử dụng thuật toán K-Means gom cụm tập vector nhúng. Số lượng cụm `K` có thể cấu hình hoặc tính toán tự động.
- **Hệ luật suy diễn (Heuristics):** Áp dụng bộ luật nghiệp vụ Web3 (đánh giá cấu trúc vòng tròn, mức độ hoàn thiện profile, mật độ tương tác) lên từng cụm để tính điểm rủi ro.
- Căn cứ vào điểm số, tự động phân loại các nút thành 4 nhãn: `MALICIOUS`, `HIGH_RISK`, `LOW_RISK`, `BENIGN`.

### Bước 5: Đóng Gói và Trả Kết Quả

- Đồ thị PyTorch cùng các nhãn rủi ro được ánh xạ ngược (map) thành chuẩn `GraphDataSchema` (JSON) gồm danh sách `nodes` và `links`.
- Dữ liệu này được Modal lưu lại trạng thái hoàn thành.

### Bước 6: Cơ Chế Polling & Hiển Thị (FastAPI $\leftrightarrow$ Frontend)

- Trong suốt quá trình từ Bước 2 đến 5, Frontend liên tục gọi `GET /api/v1/sybil/discovery/status/{task_id}` mỗi 2 giây.
- API Gateway dùng `call.get(timeout=0)` để hỏi Modal:
  - Nếu gặp `TimeoutError`, API trả về trạng thái `"PROCESSING"` để UI cập nhật thanh tiến trình.
  - Nếu có kết quả, API trả về trạng thái `"COMPLETED"` kèm cục dữ liệu JSON.
- Frontend nhận JSON, giải mã và render trực quan lên màn hình bằng WebGL (`react-force-graph`).

---

## 4. Quyết định Thiết kế Cốt Lõi (Architecture Decisions)

1. **Tại sao lại "Train-on-the-fly" (Transductive) thay vì dùng mô hình Pre-trained?**
   - **Lý do:** Khắc phục triệt để hiện tượng **Concept Drift**. Hành vi của các bầy đàn Sybil (Sybil Farms) thay đổi chiến thuật liên tục theo từng tuần. Việc train trực tiếp trên dữ liệu truy vấn giúp GAE bắt chính xác các mẫu hình liên kết mới (Dense Subgraphs) vừa xuất hiện thay vì dựa vào trí nhớ cũ.
2. **Tại sao dùng Modal Serverless GPU?**
   - **Lý do:** Huấn luyện mạng nơ-ron đồ thị là tác vụ CPU/GPU-bound cực nặng. Đẩy tác vụ này sang kiến trúc Serverless giúp hệ thống API Gateway (VPS 4GB) không bị quá tải (Out-of-memory) và không bị block Event Loop, cho phép phục vụ hàng ngàn người dùng khác cùng lúc ở Module 2.
