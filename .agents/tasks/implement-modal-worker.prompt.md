---
description: "Khởi tạo Modal Worker (Nhà máy AI) để huấn luyện Graph Autoencoder (GAE) và K-Means phân cụm với PyTorch Geometric trên nền tảng Serverless GPU."
agent: "agent"
tools: ["codebase", "editFiles"]
---

# Build Module 1 AI Worker on Modal Serverless

Bạn là một Chuyên gia AI/MLOps và Kiến trúc sư Hệ thống với kinh nghiệm sâu rộng về triển khai các mô hình Machine Learning phân tán trên nền tảng Serverless GPU (đặc biệt là Modal).

## Mục tiêu (Task Specification)

Nhiệm vụ của bạn là xây dựng "Nhà máy AI" độc lập cho Module 1 của ứng dụng "Web3 Sybil Detection Dashboard". Bạn cần tạo một ứng dụng Modal định nghĩa hạ tầng container (chứa thư viện PyTorch, PyTorch Geometric) và hàm pipeline xử lý sẽ được thực thi trên GPU (Train GAE -> K-Means -> Trả về GraphData JSON).

Backend FastAPI hiện đã được cấu hình ở `app/services/sybil_service.py` để gọi tới hàm `train_gae_pipeline` thuộc Modal app `sybil-discovery-engine` thông qua cơ chế bất đồng bộ `.spawn()`.

## Hướng dẫn từng bước (Instructions)

### Bước 1: Khởi tạo cấu trúc độc lập

Tạo một thư mục mới có tên `modal_worker` ở cấp thư mục gốc của dự án (cùng cấp với thư mục `backend` hoặc thư mục chứa `app`).
Bên trong `modal_worker`, tạo file script `app.py`.

### Bước 2: Khai báo Môi trường Container (Modal Image)

Trong file `modal_worker/app.py`:

- Import thư viện `modal`.
- Định nghĩa Container Image tối ưu cache theo chuẩn `modal-serverless-gpu/SKILL.md`. Cài đặt Torch tương thích CUDA trước, sau đó mới cài PyG và Scikit-Learn:

  ```python
  image = (
      modal.Image.debian_slim(python_version="3.11")
      .pip_install(
          "torch==2.1.2",
          index_url="[https://download.pytorch.org/whl/cu121](https://download.pytorch.org/whl/cu121)"
      )
      .pip_install("torch_geometric", "scikit-learn", "networkx")
  )
  ```

- Khởi tạo App: `app = modal.App("sybil-discovery-engine", image=image)`

### Bước 3: Triển khai Hàm Huấn luyện GPU (The Worker)

- Tạo một hàm tên là `train_gae_pipeline(payload: dict) -> dict` và gắn decorator cho phép chạy trên GPU: `@app.function(gpu="T4", timeout=1800)`.
- **QUAN TRỌNG (Lazy Loading):** Import các thư viện AI (`torch`, `torch_geometric`, `sklearn`, `networkx`) ở _bên trong_ hàm này. Nếu import bên ngoài, local client sẽ bị báo lỗi do không có sẵn môi trường ML khi gọi CLI.
- Viết khung logic (skeleton) cho quá trình học không giám sát:
  1. Đọc `time_range` và `max_nodes` từ `payload`.
  2. Tạo một đồ thị mẫu (dummy graph) nhỏ (< 50 nodes) bằng NetworkX để mô phỏng dữ liệu giao dịch Web3.
  3. Xây dựng class mô hình `GAE` với `GATConv` đơn giản (hoặc tạo Tensor giả lập embeddings trực tiếp để kiểm thử luồng trước).
  4. Chạy thuật toán `KMeans(n_clusters=3).fit_predict()` trên vector embeddings.
  5. Trả về kết quả dưới dạng dictionary (gồm 2 mảng `nodes` và `links`). Cấu trúc trả về bắt buộc phải map chính xác với `GraphDataSchema` trong `app/schemas/sybil.py` của Backend.

## Ngữ cảnh & Tham chiếu (Context/Input Section)

- Backend đang gọi tác vụ bằng cách truyền vào một dictionary `payload` được convert từ `DiscoveryRequest`.
- Kết quả của hàm này sẽ được phương thức `call.get(timeout=0)` ở Backend đón nhận và gửi thẳng cho UI render.

## Ràng buộc & Tiêu chuẩn (Constraints & Standards)

- **Decoupling (Tính Tách biệt):** File `modal_worker/app.py` TUYỆT ĐỐI KHÔNG import bất kỳ module nào từ thư mục `app/` của FastAPI. Modal script phải tự định nghĩa mọi thứ nó cần để có thể deploy lên cloud một cách trơn tru.
- **Tuân thủ Timeout:** Sử dụng `timeout=1800` (30 phút) để đảm bảo Job không bị cắt ngang nếu dữ liệu đầu vào lớn.
- Mã nguồn phải rõ ràng, tuân thủ PEP 8 và có comment chú thích các bước của Pipeline học máy.

## Định dạng Output (Output Section)

- Tạo và ghi nội dung hoàn chỉnh vào file `modal_worker/app.py`.
- In ra một thông báo tóm tắt quá trình, kèm theo dòng lệnh mẫu để người dùng có thể tự gõ vào terminal nhằm đưa nhà máy AI này lên mây (ví dụ: `modal deploy modal_worker/app.py`).

## Tiêu chuẩn Đánh giá (Quality/Validation)

- File script độc lập, không dính lỗi circular import hay import từ môi trường local chưa cài PyTorch.
- Cấu trúc file đúng chuẩn khai báo của Modal (App, Image, Function).
