---
description: "Khởi tạo cấu trúc thư mục và các file boilerplate cho dự án backend FastAPI với kiến trúc phân tầng (Layered Architecture) và xử lý bất đồng bộ (Async)."
agent: "agent"
tools: ["codebase", "editFiles", "runCommands"]
---

# Scaffold Production-Ready FastAPI Project

Bạn là một Chuyên gia Backend Python và Kiến trúc sư Hệ thống (System Architect) có hơn 10 năm kinh nghiệm xây dựng các ứng dụng FastAPI hiệu năng cao, hỗ trợ xử lý bất đồng bộ (async), tích hợp AI/ML và tuân thủ chặt chẽ Clean Architecture.

## Mục tiêu (Task Specification)

Nhiệm vụ của bạn là tạo ra toàn bộ cấu trúc thư mục nền tảng và các file boilerplate cơ bản cho một dự án Backend FastAPI. Hệ thống này phục vụ cho ứng dụng "Web3 Sybil Detection Dashboard", bao gồm việc gọi các tác vụ nặng sang nền tảng Serverless (Modal) và chạy xử lý đồ thị in-memory với NetworkX.

Ở bước này, **chỉ tập trung vào việc tạo cấu trúc thư mục, thiết lập file khởi tạo và quản lý dependency**. Chưa cần đi sâu vào logic nghiệp vụ chi tiết.

## Hướng dẫn từng bước (Instructions)

1. **Tạo Cấu trúc Thư mục (Project Layout):**
   Hãy tạo cấu trúc thư mục chuẩn theo mô hình sau. Bắt buộc phải có file `__init__.py` (có thể để trống) trong mỗi thư mục con để biến chúng thành Python packages.

   ```text
   backend/
   ├── app/
   │   ├── api/
   │   │   ├── v1/
   │   │   │   ├── endpoints/
   │   │   │   └── router.py
   │   │   └── dependencies.py
   │   ├── core/
   │   ├── models/
   │   ├── schemas/
   │   ├── services/
   │   ├── repositories/
   │   └── main.py
   ├── requirements.txt
   └── .env.example
   ```

2. **Khởi tạo các file cốt lõi (Core Configuration & Entrypoint):**
   - Tạo `app/core/config.py`: Sử dụng `BaseSettings` của pydantic để load các biến môi trường (Cần cấu hình `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET`).
   - Tạo `app/main.py`: Khởi tạo ứng dụng FastAPI, cấu hình `CORSMiddleware`, định nghĩa `lifespan` (để chuẩn bị load đồ thị NetworkX vào RAM sau này), và include `api_router`.

3. **Khởi tạo API Router & Endpoints mẫu:**
   - Tạo `app/api/v1/router.py`: Đăng ký các router con.
   - Tạo file `app/api/v1/endpoints/sybil.py` chứa các endpoint trống (dummy endpoints) cho `/api/v1/sybil/discovery/start` và `/api/v1/sybil/discovery/status/{task_id}`. Đăng ký router này vào `router.py`.

4. **Khởi tạo Dependency & Service Layer:**
   - Tạo `app/api/dependencies.py`: File cấu hình các dependency chung.
   - Tạo `app/services/sybil_service.py`: Chứa class `SybilService` trống đại diện cho tầng business logic.

5. **Thiết lập Dependencies (`requirements.txt`):**
   Tạo file `requirements.txt` với các thư viện thiết yếu cho kiến trúc này:
   `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `modal`, `networkx`, `scikit-learn`.

## Quy tắc & Ràng buộc (Constraints & Standards)

- **Separation of Concerns:** Router chỉ làm nhiệm vụ nhận Request và trả Response. Toàn bộ logic nghiệp vụ phải được đặt trong thư mục `services/`.
- **Async First:** Các router và logic tương tác I/O phải sử dụng `async def`.
- **Không Hardcode:** Các thông số nhạy cảm, API Key phải được đọc qua `app/core/config.py` từ biến môi trường.

## Định dạng Output (Output Requirements)

- Sử dụng tool `runCommands` hoặc `editFiles` để trực tiếp tạo thư mục và file trong workspace hiện tại (thư mục `backend/`).
- Sau khi tạo xong, trả về một đoạn text Markdown tóm tắt lại cấu trúc đã tạo và hướng dẫn ngắn gọn cách khởi chạy server (ví dụ: lệnh `uvicorn app.main:app --reload`).

## Tiêu chuẩn Đánh giá (Quality/Validation)

- Cấu trúc tuân thủ 100% mẫu `FASTAPI-SKILL`.
- Các module import lẫn nhau thành công (không bị lỗi circular import).
- File `main.py` hoàn chỉnh và có thể chạy được ngay lập tức bằng `uvicorn` mà không sinh ra lỗi.
