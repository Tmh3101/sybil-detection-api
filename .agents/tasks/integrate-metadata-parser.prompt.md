---
description: "Tích hợp hàm parse_metadata của user để trích xuất bio và picture_url từ cột chuỗi JSON/Dict trong BigQuery."
agent: "agent"
tools: ["editFiles", "codebase"]
---

# Integrate Metadata Parser into Modal Worker

Người dùng đã phát hiện ra rằng các trường `bio` và `picture` không tồn tại dưới dạng cột vật lý trong BigQuery, mà nằm ẩn dưới dạng chuỗi (Stringified Dict) trong cột `metadata` (hoặc tương tự) với cấu trúc `{'lens': {'bio': '...', 'picture': '...'}}`.

## Nhiệm vụ (Task)

Hãy sửa file `modal_worker/app.py` để lấy toàn bộ chuỗi metadata về, sau đó dùng đoạn code Pandas mà người dùng cung cấp để tách ra thành các cột `bio` và `picture_url`.

## Hướng dẫn chi tiết (Instructions)

### 1. Cập nhật câu SQL (`query_nodes`)

- Xóa các dòng cố gắng lấy trực tiếp `meta.bio` hay `meta.picture` (vì chúng gây lỗi).
- Thay bằng việc kéo cột metadata dạng chuỗi về:
  ```sql
  ANY_VALUE(meta.metadata) as raw_metadata,
  ```
  _(Lưu ý: Nếu bảng metadata dùng tên cột khác để chứa chuỗi này, hãy linh hoạt điều chỉnh, nhưng thường là `metadata` hoặc `raw_metadata`)._

### 2. Tích hợp code xử lý của User vào `fetch_bigquery_data`

- Ngay sau khi dòng `df_nodes = client.query(query_nodes, ...).to_dataframe()` thực thi thành công (bên trong khối `try...except`), hãy thêm module `import ast` và chèn đúng hàm của user vào:

  ```python
  import ast

  def parse_metadata(meta_str):
      if pd.isna(meta_str) or not meta_str:
          return pd.Series(["", ""])
      try:
          # Đảm bảo parse chuỗi an toàn
          meta = ast.literal_eval(str(meta_str)).get('lens', {})
          return pd.Series([meta.get('bio', '') or "", meta.get('picture', '') or ""])
      except:
          return pd.Series(["", ""])

  # Apply hàm lên dataframe
  if "raw_metadata" in df_nodes.columns:
      df_nodes[['bio', 'picture_url']] = df_nodes['raw_metadata'].apply(parse_metadata)
      # Cập nhật lại cột has_avatar dựa trên picture_url
      df_nodes['has_avatar'] = df_nodes['picture_url'].apply(lambda x: 1 if x != "" else 0)
  else:
      # Fallback an toàn nếu không tìm thấy cột
      df_nodes['bio'] = ""
      df_nodes['picture_url'] = ""
      df_nodes['has_avatar'] = 0
  ```

### 3. Cập nhật Feature Engineering (`build_pyg_graph`)

- Đảm bảo hàm `build_pyg_graph` sử dụng đúng cột `df_nodes['bio']` mới được tạo ra để ghép nối với `handle` và `display_name` khi chạy `SentenceTransformer`.
- Cột `has_avatar` đã được tính toán lại một cách chính xác, đảm bảo mô hình GAE nhận được đúng giá trị 0 hoặc 1.

## Định dạng Output

Dùng công cụ `editFiles` để ghi trực tiếp thay đổi vào `modal_worker/app.py`.
