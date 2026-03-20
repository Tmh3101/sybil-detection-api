---
description: "Sửa lỗi xung đột thư viện (NumPy 2, SentenceTransformers) và lỗi xác thực Google Service Account (String vs File path) trên Modal."
agent: "agent"
tools: ["editFiles", "codebase"]
---

# Fix Dependency & Authentication Errors in Modal Worker

Hệ thống `modal_worker/app.py` đang gặp 3 lỗi runtime nghiêm trọng trên Modal:

1. `numpy` phiên bản 2.x không tương thích với `torch==2.1.2`.
2. `sentence-transformers` bản mới nhất yêu cầu `torch>=2.4`.
3. Biến môi trường `GOOGLE_APPLICATION_CREDENTIALS` chứa nội dung JSON thay vì file path, khiến `bigquery.Client` văng lỗi `DefaultCredentialsError`.

## Nhiệm vụ (Task)

Hãy sửa file `modal_worker/app.py` để giải quyết dứt điểm các lỗi trên.

## Hướng dẫn chi tiết (Instructions)

### 1. Sửa danh sách thư viện (Dependencies)

- Tìm biến định nghĩa `image` bằng `modal.Image.debian_slim(...)`.
- Trong hàm `.pip_install(...)` thứ hai, hãy thêm/sửa các thư viện thành các phiên bản được ghim (pinned) sau đây:
  - `"numpy<2.0.0"`
  - `"sentence-transformers==2.7.0"` (Phiên bản này tương thích tốt với Torch 2.1.2)
  - Giữ nguyên các thư viện khác (`torch_geometric`, `scikit-learn`, `networkx`, `google-cloud-bigquery`, `db-dtypes`, `pandas`).

### 2. Sửa phương thức xác thực BigQuery

- Tìm hàm `fetch_bigquery_data`.
- Thay vì gọi `client = bigquery.Client(location="US")` (mặc định đọc file từ biến môi trường), hãy sửa logic thành đọc chuỗi JSON từ biến môi trường và nạp thông qua `service_account`:

```python
    import os
    import json
    import pandas as pd
    from google.cloud import bigquery
    from google.oauth2 import service_account

    # Đọc nội dung JSON từ Modal Secret
    creds_json_str = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    if creds_json_str:
        try:
            creds_dict = json.loads(creds_json_str)
            credentials = service_account.Credentials.from_service_account_info(creds_dict)
            client = bigquery.Client(credentials=credentials, project=creds_dict.get("project_id"), location="US")
        except json.JSONDecodeError:
            print("[Error] GOOGLE_APPLICATION_CREDENTIALS không phải là JSON hợp lệ.")
            client = bigquery.Client(location="US")
    else:
        client = bigquery.Client(location="US")
```

## Định dạng Output

Sử dụng công cụ `editFiles` để lưu các thay đổi này trực tiếp vào `modal_worker/app.py`.
