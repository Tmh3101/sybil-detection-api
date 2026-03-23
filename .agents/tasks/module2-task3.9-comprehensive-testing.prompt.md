---
description: "Thiết lập bộ Unit Test và Integration Test toàn diện cho luồng trích xuất dữ liệu, Fallback Pipeline và API Inspector."
agent: "agent"
tools: ["editFiles", "codebase"]
---

# Task 3.9: Comprehensive Testing for Data Extraction & API

Bạn là một chuyên gia QA Automation và Backend Engineer. Trước khi tích hợp AI Model, chúng ta cần đảm bảo móng dữ liệu cực kỳ vững chắc. Hệ thống hiện sử dụng NetworkX lưu trữ trên RAM, lấy dữ liệu từ file và có Fallback Pipeline gọi BigQuery.

Nhiệm vụ của bạn là sử dụng `pytest`, `pytest-asyncio` và `httpx` để viết bộ test chi tiết, bao phủ các module `inspector_service.py`, `fallback_service.py` và API router.

## 1. Mục tiêu (Objectives)

- Kiểm tra tính chính xác tuyệt đối khi map các trường dữ liệu từ file CSV (như `nodes_full_pruned.csv`) vào các thuộc tính Node của NetworkX (`handle`, `owned_by`, `picture_url`, `trust_score`, v.v.).
- Kiểm tra logic "Graph Enrichment" (tự động tạo cạnh `CO-OWNER` và `SIMILARITY`).
- Kiểm tra cấu trúc JSON trả về của endpoint `GET /profile/{id}`.

## 2. Hướng dẫn chi tiết (Instructions)

### Bước 1: Thiết lập môi trường Test (`tests/conftest.py`)

- Tạo thư mục `tests/` và `tests/fixtures/`.
- Trong `tests/fixtures/`, tạo một file `sample_nodes.csv` giả lập cấu trúc của `nodes_full_pruned.csv` với khoảng 3-5 dòng (đảm bảo có chứa các cột: `profile_id`, `handle`, `picture_url`, `owned_by`, `metadata`).
- Viết `tests/conftest.py`:
  - Tạo fixture `client` sử dụng `httpx.AsyncClient` bọc lấy ứng dụng FastAPI (`app.main.app`).
  - Tạo fixture `mock_graph` nạp sẵn NetworkX graph với một vài node mẫu và gán vào `app.state.graph`.

### Bước 2: Viết Unit Test cho Khâu Nạp Dữ liệu (`tests/test_services.py`)

- Mở/Tạo `tests/test_services.py`.
- **Test 1:** Kiểm tra logic đọc CSV và parse metadata. Đảm bảo thuộc tính `picture_url` lấy từ chuỗi dictionary `metadata` nếu bị khuyết, và `owned_by` được bảo toàn nguyên vẹn.
- **Test 2:** Kiểm tra logic Graph Enrichment trong Fallback:
  - Khởi tạo một Node giả A có `owned_by="0xV1"`.
  - Khởi tạo Node B có `owned_by="0xV1"`.
  - Giả lập việc nạp Node B vào Graph đã có Node A. Kiểm tra `G.has_edge(A, B)` và `edge_data['type'] == 'CO-OWNER'`.

### Bước 3: Viết Integration Test cho API Router (`tests/test_api.py`)

- Mở/Tạo `tests/test_api.py`. Dùng `@pytest.mark.asyncio`.
- **Test Case 1: Cache Hit (Thành công tức thì)**
  - Gọi API `/api/v1/inspector/profile/{id}` với một ID đã có sẵn trong `app.state.graph` (dùng fixture).
  - Assert status_code == 200.
  - Assert cục JSON trả về CÓ ĐÚNG cấu trúc phẳng ở `profile_info` (chứa `id`, `handle`, `picture_url`, `owned_by`).
  - Assert `analysis.classification == "PENDING_AI_INFERENCE"`.
- **Test Case 2: Cache Miss & Fallback Success (Giả lập BigQuery)**
  - Dùng `unittest.mock.patch` để mock hàm `fetch_and_embed_node` trong `fallback_service.py` trả về `True` và tự động nhét 1 node vào Graph.
  - Gọi API với ID mới tinh.
  - Assert status_code == 200 và ID mới xuất hiện trong response JSON.
- **Test Case 3: Cache Miss & Fallback Fail (Profile không tồn tại)**
  - Mock hàm `fetch_and_embed_node` trả về `False`.
  - Gọi API với ID ma.
  - Assert status_code == 404 và có thông báo lỗi "Profile not found".

## 3. Ràng buộc quan trọng

- Khi test `SIMILARITY`, hãy dùng `unittest.mock` để mock thư viện `sentence_transformers` trả về giá trị độ tương đồng (ví dụ: `0.9`), TRÁNH việc tải model AI thật trong lúc chạy test (sẽ làm test suite quá chậm và văng lỗi bộ nhớ).
- Viết code sạch sẽ, rõ ràng, mỗi hàm test chỉ test ĐÚNG 1 mục tiêu.

## 4. Định dạng Output

- Tạo file cấu hình `pytest.ini` nếu cần.
- Sinh ra các file trong thư mục `tests/` (`conftest.py`, `test_services.py`, `test_api.py`, v.v.).
