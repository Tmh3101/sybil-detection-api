---
description: "Sửa lỗi thiếu dữ liệu On-chain trong câu SQL và sửa lỗi thiếu Feature Concatenation khi build PyG Data."
agent: "agent"
tools: ["codebase", "editFiles"]
---

# Fix Data Ingestion & Feature Engineering in Modal Worker

Hệ thống `modal_worker/app.py` đang hoạt động tốt về luồng, nhưng bị thiếu sót nghiêm trọng về mặt dữ liệu so với thiết kế `docs/module1_detailed_workflow.md`. Hãy sửa lại 2 hàm sau:

### 1. Sửa hàm `fetch_bigquery_data`

- Bỏ `LIMIT 50` ở cả 2 câu query.
- Trong `query_nodes`: Bắt buộc phải JOIN hoặc subquery để lấy thêm các cột: `follower_count`, `following_count`, `total_posts`, `total_comments`, `total_mirrors`, `total_collects` (tham chiếu file `docs/colab-code/build_datasets.py` để xem bảng tương ứng của Lens Protocol).
- Trong `query_edges`: Cập nhật logic SQL để lấy dữ liệu `INTERACT` (từ bảng publication) và `FOLLOW` thực tế thay vì dùng `UNION ALL` mock. (Giữ điều kiện lọc theo `start_date` và `end_date`).

### 2. Sửa hàm `build_pyg_graph`

Mô hình hiện tại chỉ dùng `x = tensor_text` (384 chiều) là sai. Yêu cầu:

- Trích xuất các cột on-chain thành mảng numpy (bao gồm: `has_avatar` (0/1), `follower_count`, `following_count`, `total_posts`, `total_comments`, `total_mirrors`, `total_collects`).
- Chuẩn hóa (Normalize) mảng on-chain này bằng `sklearn.preprocessing.MinMaxScaler` (hoặc Z-score). Chuyển thành `tensor_onchain`.
- Nối (Concatenate) `tensor_text` và `tensor_onchain` theo `dim=1` để tạo thành `x` tổng hợp.
- Cập nhật biến `in_channels` của mô hình GAE trong hàm `train_gae_pipeline` thành `data.num_features` (tương đương 384 + số lượng cột onchain).

Dùng `editFiles` để lưu các thay đổi này vào `modal_worker/app.py`.
