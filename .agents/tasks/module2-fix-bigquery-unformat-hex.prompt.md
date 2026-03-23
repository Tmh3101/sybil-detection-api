---
description: "Sửa lỗi Function not found UNFORMAT_HEX trong các câu truy vấn BigQuery của fallback_service.py"
agent: "agent"
tools: ["editFiles", "codebase"]
---

# Fix BigQuery Custom Function Error

Trong file `app/services/fallback_service.py`, các câu truy vấn SQL đang bị lỗi vì sử dụng hàm custom của Lens Protocol là `lens-protocol-mainnet.app.UNFORMAT_HEX`. Hàm này không tồn tại trong dataset hiện tại.

## Nhiệm vụ

Hãy mở file `app/services/fallback_service.py`, tìm tất cả các câu lệnh SQL (cả query cho Node và query cho Edges).

1. Xóa bỏ hàm `lens-protocol-mainnet.app.UNFORMAT_HEX`.
2. Thay thế bằng logic xử lý chuỗi chuẩn (Native) của BigQuery. Tùy thuộc vào cách bạn đang truyền tham số:
   - Nếu bạn đang so sánh với một trường kiểu String: Chỉ cần truyền thẳng biến string vào, dùng `LOWER()`. Ví dụ: `WHERE address = LOWER(@profile_id)`
   - Nếu bạn đang so sánh với một trường kiểu BYTES, hãy dùng hàm native của BigQuery: `FROM_HEX(SUBSTR(@profile_id, 3))` (nếu profile_id có chứa '0x').

\*Lưu ý: Nếu trong code đang format chuỗi kiểu f-string (ví dụ `{profile_id}`), hãy sửa lại:
Từ: `lens-protocol-mainnet.app.UNFORMAT_HEX('{profile_id}')`
Thành: `LOWER('{profile_id}')` (nếu cột trong BigQuery là String).

Hãy ưu tiên đổi về `LOWER('{profile_id}')` trước vì đa số các ID của Lens (như profile_id) được lưu dưới dạng String.
