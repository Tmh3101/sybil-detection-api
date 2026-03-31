---
description: "Tái cấu trúc Fallback Pipeline: Xây dựng Đồ thị Đa tầng (Multi-layer Graph) với Trọng số, Cạnh Có Hướng và Vô Hướng."
agent: "agent"
tools: ["editFiles", "codebase"]
---

# Task 3.8: Refactor Multi-Layer Edge Architecture

Bạn là một Data Architect và Backend Engineer. Hệ thống đang sử dụng `NetworkX MultiDiGraph` để lưu trữ đồ thị.
Nhiệm vụ của bạn là tái cấu trúc toàn bộ logic tạo cạnh (edges) trong file `app/services/fallback_service.py` để tuân thủ thiết kế 4 tầng quan hệ, tích hợp hệ thống trọng số (weights), và phân định rõ cạnh Có hướng (Directed) / Vô hướng (Undirected).

## 1. Khai báo Bảng Trọng Số (System Weights)

Hãy thêm hằng số sau vào đầu file `app/services/fallback_service.py` (ngay dưới phần import):

```python
EDGE_WEIGHTS = {
      // Follow Layer (có hướng)
      'FOLLOW': 2.0,

      // Interact Layer (có hướng)
      'UPVOTE': 1.0, 'REACTION': 1.0, 'COMMENT': 2.0,
      'QUOTE': 2.0, 'MIRROR': 3.0, 'COLLECT': 4.0,

      // Co-Owner Layer (vô hướng)
      'CO-OWNER': 5.0,

      // Similarity Layer (vô hướng)
      'SAME_AVATAR': 3.0, 'FUZZY_HANDLE': 2.0, 'SIM_BIO': 3.0, 'CLOSE_CREATION_TIME': 2.0
}
```

## 2. Tái cấu trúc SQL (Physical Edges - Có Hướng)

Hệ thống lấy Physical Edges từ BigQuery. Đây là các hành vi 1 chiều (A tác động lên B), nên **chỉ tạo 1 cạnh duy nhất** từ `source` đến `target`.

Hãy thay thế các câu lệnh SQL lấy edges hiện tại bằng cấu trúc `UNION ALL` sau. (Lưu ý: BẮT BUỘC phải loại bỏ `is_mention = TRUE`):

```sql
-- 1. Tầng FOLLOW
SELECT
    `lens-protocol-mainnet.app.FORMAT_HEX`(account_follower) as source,
    `lens-protocol-mainnet.app.FORMAT_HEX`(account_following) as target,
    'FOLLOW' as edge_type
FROM `lens-protocol-mainnet.account.follower`
WHERE `lens-protocol-mainnet.app.FORMAT_HEX`(account_follower) = '{profile_id}'
   OR `lens-protocol-mainnet.app.FORMAT_HEX`(account_following) = '{profile_id}'

UNION ALL

-- 2. Tầng INTERACT (Comment, Quote, Mirror)
SELECT
    `lens-protocol-mainnet.app.FORMAT_HEX`(p.account) as source,
    `lens-protocol-mainnet.app.FORMAT_HEX`(parent.account) as target,
    CASE
        WHEN p.is_mirror = TRUE THEN 'MIRROR'
        WHEN p.quoted_post IS NOT NULL THEN 'QUOTE'
        WHEN p.parent_post IS NOT NULL THEN 'COMMENT'
    END as edge_type
FROM `lens-protocol-mainnet.post.record` p
JOIN `lens-protocol-mainnet.post.record` parent
  ON (p.parent_post = parent.id OR p.quoted_post = parent.id OR p.mirror_of = parent.id)
WHERE (`lens-protocol-mainnet.app.FORMAT_HEX`(p.account) = '{profile_id}'
   OR `lens-protocol-mainnet.app.FORMAT_HEX`(parent.account) = '{profile_id}')
   AND p.is_mention = FALSE

-- Lưu ý: Nếu có các bảng riêng cho UPVOTE, REACTION, COLLECT, hãy UNION ALL tương tự.
```

**Logic Python xử lý kết quả SQL:**

- Duyệt qua dataframe trả về.
- Xác định `neighbor` (là `source` nếu `target == profile_id`, ngược lại).
- **Quy tắc Vàng (Anti-Bloat):** `if neighbor in G.nodes:`
- Thêm cạnh: `G.add_edge(source, target, type=edge_type, weight=EDGE_WEIGHTS.get(edge_type, 1.0))`

## 3. Tái cấu trúc Logic Python (Logical Edges - Vô Hướng)

Tầng Co-Owner và Similarity được tính toán logic trực tiếp trên RAM.
**Quy tắc Vô Hướng (Undirected):** Vì dùng `MultiDiGraph`, khi 2 node thỏa mãn điều kiện, BẮT BUỘC phải tạo 2 chiều ngược nhau.
Ví dụ:
`G.add_edge(profile_id, n_id, type=..., weight=...)`
`G.add_edge(n_id, profile_id, type=..., weight=...)`

Hãy viết vòng lặp duyệt qua các `n_id` lân cận (hoặc toàn bộ Graph nếu tối ưu được) và kiểm tra 5 điều kiện sau ĐỘC LẬP (nếu thỏa mãn nhiều cái thì nối nhiều cạnh):

1. **`CO-OWNER`**:
   - Điều kiện: `new_owned_by == G.nodes[n_id].get('owned_by')` (và không rỗng).
2. **`SAME_AVATAR`**:
   - Điều kiện: `new_picture_url == G.nodes[n_id].get('picture_url')` (và không rỗng).
3. **`FUZZY_HANDLE`**:
   - Sử dụng `import difflib`.
   - Điều kiện: `difflib.SequenceMatcher(None, new_handle, n_handle).ratio() >= 0.85` (Cả 2 phải không rỗng và dài hơn 3 ký tự).
4. **`SIM_BIO`**:
   - Logic cũ: Cosine Similarity >= 0.8 (Sử dụng SentenceTransformer).
5. **`CLOSE_CREATION_TIME`**:
   - Điều kiện: Cả 2 có `created_on`. Parse datetime và tính khoảng cách tuyệt đối `abs(time1 - time2).total_seconds() <= 3600` (Cách nhau dưới 1 tiếng).

## 4. Ghi chú Debug

- Ghi log rõ ràng tổng số lượng cạnh được nối cho mỗi loại.
- Đảm bảo xử lý an toàn lỗi Parse Datetime hoặc lỗi NLP để luồng không bị crash.
