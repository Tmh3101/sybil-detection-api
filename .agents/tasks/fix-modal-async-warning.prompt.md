---
description: "Cập nhật SybilService để sử dụng giao diện bất đồng bộ (.aio) của Modal, khắc phục cảnh báo AsyncUsageWarning trong FastAPI."
agent: "agent"
tools: ["codebase", "editFiles"]
---

# Fix Modal AsyncUsageWarning in FastAPI

Bạn là một Backend Developer chuyên về FastAPI và Asynchronous Programming. Ứng dụng hiện tại đang gặp cảnh báo `AsyncUsageWarning` do gọi các hàm đồng bộ (blocking) của thư viện `modal` bên trong các async route của FastAPI.

## Nhiệm vụ (Task)

Sửa file `app/services/sybil_service.py` (và các file liên quan nếu cần) để chuyển đổi toàn bộ các lệnh gọi Modal sang giao diện bất đồng bộ (`.aio`).

## Hướng dẫn chi tiết (Instructions)

### 1. Cập nhật `start_discovery`

- Đảm bảo hàm `start_discovery` được định nghĩa là `async def`.
- Thay đổi dòng lấy hàm:
  Từ: `modal_func = modal.Function.from_name(...)`
  Thành: `modal_func = await modal.Function.from_name.aio(...)`
- Thay đổi dòng gọi spawn:
  Từ: `call = modal_func.spawn(payload)`
  Thành: `call = await modal_func.spawn.aio(payload)`

### 2. Cập nhật `get_discovery_status`

- Đảm bảo hàm `get_discovery_status` được định nghĩa là `async def`.
- Thay đổi dòng phục hồi call:
  Từ: `call = modal.FunctionCall.from_id(task_id)`
  Thành: `call = await modal.FunctionCall.from_id.aio(task_id)` (Hoặc giữ nguyên nếu object này không hỗ trợ aio instantiation, nhưng các lệnh lấy data bên dưới BẮT BUỘC phải dùng `.aio`).
- Thay đổi dòng lấy kết quả (Polling):
  Từ: `result = call.get(timeout=0)`
  Thành: `result = await call.get.aio(timeout=0)`

### 3. Cập nhật Router (Nếu cần)

- Nếu việc đổi Service thành `async def` làm ảnh hưởng đến `app/api/v1/endpoints/sybil.py`, hãy mở file đó và thêm `await` vào trước các lời gọi `sybil_service.start_discovery` và `sybil_service.get_discovery_status`.

## Định dạng Output

Sử dụng công cụ `editFiles` để lưu trực tiếp các thay đổi vào mã nguồn. Đảm bảo logic xử lý ngoại lệ (try/except) vẫn được giữ nguyên.
