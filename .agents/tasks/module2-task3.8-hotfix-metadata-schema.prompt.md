---
description: "Hotfix: Cập nhật SQL Schema để sử dụng trực tiếp các cột native 'bio' và 'picture', loại bỏ logic parse JSON cồng kềnh."
agent: "agent"
tools: ["editFiles", "codebase"]
---

# Hotfix: Refactor Node Metadata Extraction

Bạn là một Backend Engineer. Dựa trên schema thực tế của BigQuery, bảng `account.metadata` đã cung cấp sẵn các cột `bio` và `picture`. Chúng ta không cần parse chuỗi JSON từ `raw_metadata` nữa.
Hãy mở file `app/services/fallback_service.py` và thực hiện 2 nhiệm vụ sau:

## 1. Cập nhật câu SQL `query_node`

Thay thế đoạn mệnh đề SELECT lấy metadata cũ bằng các cột native.
**Sửa từ:**

```sql
ANY_VALUE(meta.metadata) as raw_metadata,
```

**Thành:**

```sql
ANY_VALUE(meta.bio) as bio,
ANY_VALUE(meta.picture) as picture_url,
```

## 2. Xóa bỏ logic Parse JSON trong Python

- Tìm và **XÓA HOÀN TOÀN** khối code định nghĩa hàm `parse_metadata(meta_str)` hoặc `parse_bio` (nếu có dùng `ast.literal_eval` hay `json.loads`).
- Tìm đoạn code gán `node_data` từ dataframe trả về (thường là `df_node.iloc[0]`).
- Hãy map trực tiếp giá trị vào dictionary (nhớ xử lý an toàn giá trị `None` hoặc `NaN` từ Pandas):

```python
row = df_node.iloc[0]
node_data = {
    "profile_id": profile_id,
    "handle": str(row.get("handle", "")),
    "picture_url": str(row.get("picture_url", "")) if pd.notna(row.get("picture_url")) else "",
    "owned_by": str(row.get("owned_by", "")),
    "bio": str(row.get("bio", "")) if pd.notna(row.get("bio")) else "",
    "trust_score": float(row.get("trust_score", 0.0)) if pd.notna(row.get("trust_score")) else 0.0,
    # Thêm các chỉ số on-chain khác nếu cần thiết cho node features
    "total_posts": int(row.get("total_posts", 0)) if pd.notna(row.get("total_posts")) else 0,
    "total_followers": int(row.get("total_followers", 0)) if pd.notna(row.get("total_followers")) else 0,
    "total_following": int(row.get("total_following", 0)) if pd.notna(row.get("total_following")) else 0,
}
```

## 3. Ràng buộc

- Đảm bảo việc thêm Node vào Graph (`G.add_node`) sử dụng đúng các key của `node_data` vừa được cập nhật.
- Không làm ảnh hưởng đến phần truy xuất Edges (Cạnh) đã làm ở Task 3.8.
