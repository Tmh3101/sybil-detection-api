---
description: "Sửa lỗi AttributeError liên quan đến phương thức lookup của thư viện Modal trong SybilService."
agent: "agent"
tools: ["editFiles", "codebase"]
---

# Fix Modal SDK Version Incompatibility

Bạn là một Backend Developer. Trong phiên bản mới nhất của thư viện `modal`, phương thức `modal.Function.lookup()` đã bị loại bỏ và thay thế bằng `modal.Function.from_name()`. Điều này đang gây ra lỗi `AttributeError` khi chạy API Gateway.

## Nhiệm vụ (Task)

Hãy cập nhật file `app/services/sybil_service.py` để tương thích với API mới của thư viện Modal.

## Hướng dẫn chi tiết (Instructions)

### 1. Cập nhật phương thức `start_discovery`

- Mở file `app/services/sybil_service.py`.
- Tìm dòng code đang sử dụng `.lookup`:
  ```python
  modal_func = modal.Function.lookup("sybil-discovery-engine", "train_gae_pipeline")
  ```
- Thay thế nó bằng `.from_name`:
  ```python
  modal_func = modal.Function.from_name("sybil-discovery-engine", "train_gae_pipeline")
  ```

### 2. Kiểm tra phương thức `get_discovery_status` (Bảo trì dự phòng)

- Đảm bảo việc phục hồi hàm (Restore Call) cũng sử dụng đúng syntax của Modal phiên bản mới.
- Tìm dòng có `modal.functions.FunctionCall.from_id(task_id)` hoặc tương tự.
- Hãy chắc chắn nó được gọi chuẩn xác là `modal.FunctionCall.from_id(task_id)` (Import từ gói gốc `modal` thay vì module con `functions`).

## Định dạng Output

- Sử dụng tool `editFiles` để lưu trực tiếp các thay đổi vào `app/services/sybil_service.py`.
- Giữ nguyên các phần xử lý lỗi (try/except) và logic fallback trả về mock data.
