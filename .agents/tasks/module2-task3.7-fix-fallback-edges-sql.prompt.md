---
description: "Sửa lỗi SQL truy xuất Edges trong fallback_service.py bằng cách sử dụng FORMAT_HEX chuẩn."
agent: "agent"
tools: ["editFiles", "codebase"]
---

# Task 3.7: Fix Physical Edges SQL in Fallback Pipeline

Bạn là một Backend Engineer. Hiện tại, luồng Fallback đang không lấy được các cạnh (edges) từ BigQuery vì lỗi ép kiểu dữ liệu giữa STRING và BYTES.

## Nhiệm vụ

Hãy mở file `app/services/fallback_service.py` và sửa lại 2 câu lệnh SQL dùng để kéo physical edges (Follow và Interact) thành cấu trúc chuẩn dưới đây:

### 1. Câu query lấy Follow:

Sửa câu truy vấn lấy cạnh Follow cho `profile_id` thành:

```sql
SELECT
    `lens-protocol-mainnet.app.FORMAT_HEX`(account_follower) as source,
    `lens-protocol-mainnet.app.FORMAT_HEX`(account_following) as target,
    'FOLLOW' as edge_type,
    1.0 as weight
FROM `lens-protocol-mainnet.account.follower`
WHERE `lens-protocol-mainnet.app.FORMAT_HEX`(account_follower) = '{profile_id}'
   OR `lens-protocol-mainnet.app.FORMAT_HEX`(account_following) = '{profile_id}'
```

### 2. Câu query lấy Interact (Comment/Quote):

Sửa câu truy vấn lấy cạnh Interact thành:

```sql
SELECT
    `lens-protocol-mainnet.app.FORMAT_HEX`(p.account) as source,
    `lens-protocol-mainnet.app.FORMAT_HEX`(parent.account) as target,
    CASE WHEN p.parent_post IS NOT NULL THEN 'COMMENT' ELSE 'QUOTE' END as edge_type,
    2.0 as weight
FROM `lens-protocol-mainnet.post.record` p
JOIN `lens-protocol-mainnet.post.record` parent
  ON (p.parent_post = parent.id OR p.quoted_post = parent.id)
WHERE `lens-protocol-mainnet.app.FORMAT_HEX`(p.account) = '{profile_id}'
   OR `lens-protocol-mainnet.app.FORMAT_HEX`(parent.account) = '{profile_id}'
```

### 3. Đảm bảo Log hiển thị

Hãy kiểm tra lại đoạn code xử lý kết quả của 2 câu truy vấn trên (đoạn nối `df_edges` vào đồ thị `G`). **Bắt buộc** phải có các dòng log này:

- Trước khi nối: `logger.info(f"[BIGQUERY EDGES] Kéo về {len(df_edges)} raw edges từ BigQuery.")`
- Khi nối thành công 1 cạnh với Node trong RAM: `logger.info(f"   -> [LINKED] Nối cạnh {{edge_type}} với node trong RAM: {{neighbor}}")`

_Chú ý: Tuyệt đối giữ nguyên logic Anti-bloat (chỉ nối nếu `neighbor` có trong `G.nodes`)._
