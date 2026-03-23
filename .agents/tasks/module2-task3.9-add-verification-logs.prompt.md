---
description: "Thêm Diagnostic Logging vào Fallback Pipeline để verify dữ liệu Node, Stats, Embedding Dimension và thống kê Edges theo Layer."
agent: "agent"
tools: ["editFiles", "codebase"]
---

# Task 3.9: Add Diagnostic Logging for Data Verification

Bạn là một Data Engineer. Trước khi hệ thống bước vào giai đoạn AI Inference, chúng ta cần xác minh (verify) nghiêm ngặt dữ liệu đồ thị được tạo ra từ `fallback_service.py` có khớp với thiết kế trong tài liệu huấn luyện hay không.

## Nhiệm vụ

Hãy mở file `app/services/fallback_service.py` và chỉ **THÊM** các dòng `logger.info` (không sửa logic core).

### Bước 1: Log Thông tin Node & Stats

Ngay sau khi dictionary `node_data` được tạo thành công (sau khi lấy dòng đầu tiên từ `df_node`), hãy thêm đoạn log sau:

```python
logger.info(f"--- [NODE VERIFICATION: {profile_id}] ---")
logger.info(f"1. Info: Handle='{node_data.get('handle')}', OwnedBy='{node_data.get('owned_by')}', HasAvatar={'Yes' if node_data.get('picture_url') else 'No'}")
logger.info(f"2. Stats: TrustScore={node_data.get('trust_score')}, Posts={node_data.get('total_posts')}, Followers={node_data.get('total_followers')}, Following={node_data.get('total_following')}")
```

### Bước 2: Log Số chiều Embedding

Trong phần tính toán `SIM_BIO`, ngay sau dòng `embeddings1 = model.encode([new_bio], convert_to_tensor=True)`, hãy thêm log kiểm tra số chiều (Dimension):

```python
logger.info(f"3. Embedding: Bio NLP vector shape = {embeddings1.shape} (Expected: [1, 384])")
```

### Bước 3: Thống kê Edges theo Layer & Type

Trước dòng `logger.info(f"========== KẾT THÚC FALLBACK PIPELINE ==========")` ở cuối hàm `fetch_and_embed_node`, hãy viết một đoạn code ngắn để đếm và thống kê tất cả các cạnh gắn với `profile_id` trong đồ thị `G`.
In ra một bảng thống kê đẹp mắt theo cấu trúc sau:

```python
# --- Đoạn code cần thêm vào ---
try:
    edge_counts = {}
    for u, v, data in G.edges(profile_id, data=True):
        e_type = data.get('type', 'UNKNOWN')
        edge_counts[e_type] = edge_counts.get(e_type, 0) + 1

    # Ánh xạ Edge Type sang Layer
    layers = {
        'FOLLOW': 'Follow Layer (Directed)',
        'UPVOTE': 'Interact Layer (Directed)', 'REACTION': 'Interact Layer (Directed)',
        'COMMENT': 'Interact Layer (Directed)', 'QUOTE': 'Interact Layer (Directed)',
        'MIRROR': 'Interact Layer (Directed)', 'COLLECT': 'Interact Layer (Directed)',
        'CO-OWNER': 'Co-Owner Layer (Undirected)',
        'SAME_AVATAR': 'Similarity Layer (Undirected)', 'FUZZY_HANDLE': 'Similarity Layer (Undirected)',
        'SIM_BIO': 'Similarity Layer (Undirected)', 'CLOSE_CREATION_TIME': 'Similarity Layer (Undirected)'
    }

    layer_counts = {}
    for e_type, count in edge_counts.items():
        layer = layers.get(e_type, 'Unknown Layer')
        layer_counts[layer] = layer_counts.get(layer, 0) + count

    logger.info(f"--- [EDGES VERIFICATION: {profile_id}] ---")
    logger.info(f"Tổng số Edges kết nối: {sum(edge_counts.values())}")
    logger.info(f"Thống kê theo Tầng (Layers):")
    for layer, count in layer_counts.items():
        logger.info(f"  - {layer}: {count} edges")

    logger.info(f"Chi tiết theo Loại (Types):")
    for e_type, count in edge_counts.items():
        weight = EDGE_WEIGHTS.get(e_type, 1.0)
        logger.info(f"  - [{e_type}] (Weight: {weight}): {count} edges")

except Exception as e:
    logger.error(f"Lỗi khi thống kê Edges: {e}")
```

### Ràng buộc

- Tuyệt đối không xóa bất kỳ dòng logic nào đang chạy (ví dụ như code gọi BigQuery, thêm node, thêm cạnh).
- Code thống kê Edge phải nằm an toàn trong khối `try...except` để không làm sập luồng API.
