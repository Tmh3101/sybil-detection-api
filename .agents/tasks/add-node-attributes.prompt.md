---
description: "Bổ sung thuộc tính picture_url và owned_by vào dữ liệu nodes trả về của Modal Worker."
agent: "agent"
tools: ["editFiles", "codebase"]
---

# Add New Attributes to Node JSON Output

Người dùng muốn bổ sung 2 thuộc tính là `picture_url` và `owned_by` vào bên trong dictionary `attributes` của từng node được trả về từ hàm `train_gae_pipeline`.

## Nhiệm vụ (Task)

Sửa file `modal_worker/app.py` để cập nhật câu SQL và định dạng JSON đầu ra.

## Hướng dẫn chi tiết (Instructions)

### 1. Cập nhật câu truy vấn SQL (`fetch_bigquery_data`)

- Tìm câu `query_nodes` bên trong hàm `fetch_bigquery_data`.
- Ngay phía trên hoặc dưới dòng `ANY_VALUE(meta.picture_uri) IS NOT NULL as has_avatar,`, hãy bổ sung thêm dòng lệnh để lấy trực tiếp chuỗi URL:
  ```sql
  ANY_VALUE(meta.picture_uri) as picture_uri,
  ```
- Đảm bảo biến `owned_by` đã có sẵn trong câu SELECT (`ANY_VALUE(meta.owned_by) as owned_by,`).

### 2. Cập nhật Format Output (`train_gae_pipeline`)

- Kéo xuống cuối hàm `train_gae_pipeline`, phần `Phase 5: Output Formatting`.
- Tìm đoạn gán giá trị cho mảng `nodes`. Bổ sung `picture_url` và `owned_by` vào trong dictionary `attributes`.
- Sử dụng `pd.isna` hoặc check `None` để tránh lỗi đối với các giá trị Null.
- Cụ thể, sửa dictionary `attributes` thành như sau:
  ```python
  "attributes": {
      "handle": node_row["handle"] or "unknown",
      "trust_score": float(node_row["trust_score"]) if pd.notnull(node_row["trust_score"]) else 0.0,
      "follower_count": int(node_row["follower_count"]) if pd.notnull(node_row["follower_count"]) else 0,
      "post_count": int(node_row["total_posts"]) if pd.notnull(node_row["total_posts"]) else 0,
      "picture_url": str(node_row["picture_uri"]) if pd.notnull(node_row["picture_uri"]) else None,
      "owned_by": str(node_row["owned_by"]) if pd.notnull(node_row["owned_by"]) else None,
  }
  ```
- LƯU Ý: Phải đảm bảo `import pandas as pd` (nếu chưa có) hoặc dùng hàm check null tương đương vì giá trị từ DataFrame có thể là `NaN`.

## Định dạng Output

Sử dụng công cụ `editFiles` để lưu trực tiếp các thay đổi này vào `modal_worker/app.py`.
