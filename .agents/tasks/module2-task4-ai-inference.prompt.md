---
description: "Tích hợp mô hình Hybrid AI (GAT + RF) - Đồng bộ tuyệt đối với Data Pipeline lúc huấn luyện (Feature Order, 2-Stage Scaling, Text Embedding)."
agent: "agent"
tools: ["editFiles", "codebase"]
---

# Task 4: Hybrid AI Inference - The Final Pipeline

Bạn là AI Expert. Hệ thống đang bị lệch phân phối dữ liệu và sai chiều Tensor giữa lúc Train và Inference. Bạn cần code lại `model_loader.py` và `inference_service.py` để tuân thủ 100% quy trình sau:

## 1. Nạp Models (app/core/model_loader.py)

Cập nhật class `GATClassifier` (trả về embeddings, không có layer phân loại) và hàm `load_models`. Bạn cần load tổng cộng **5 thành phần**, với vai trò rõ ràng như sau:

1. `feature_scaler` (load từ `scaler.bin`): Dùng để chuẩn hóa các giá trị stats (on-chain metrics) trong node trước khi kết hợp với NLP embedding để tạo thành vector đầu vào 396 chiều cho GAT.
2. `nlp_model`: Load `SentenceTransformer('all-MiniLM-L6-v2', device='cpu')`.
3. `gat_model`: Khởi tạo `GATClassifier(in_channels=396, embedding_dim=16, num_classes=4)` và load state_dict. Mô hình này đóng vai trò Feature Extractor.
4. `embedding_scaler` (load từ `scaler_gat_ml.pkl`): Dùng để scale dữ liệu đầu vào của ML truyền thống (ở đây là chuẩn hóa vector 16 chiều output của GAT trước khi đưa vào Random Forest).
5. `rf_model`: Load từ `random_forest_gat.pkl`. Đây là mô hình phân loại cuối cùng.

## 2. Tiền xử lý Dữ liệu Node (app/services/inference_service.py)

Trong hàm `evaluate_subgraph`, duyệt qua các nodes trong `subgraph` để tạo 2 ma trận song song (Đảm bảo đúng thứ tự index):

**A. Numeric Features (Ma trận Nx12):**
Trích xuất đúng 12 cột theo thứ tự: `['trust_score', 'total_tips', 'total_posts', 'total_quotes', 'total_reacted', 'total_reactions', 'total_reposts', 'total_collects', 'total_comments', 'total_followers', 'total_following', 'days_active']`.
_Lưu ý: `days_active` tính bằng: `(datetime.now(timezone.utc) - created_on).days`. Xử lý an toàn NaN/None thành 0.0._

- Đẩy ma trận này qua `feature_scaler.transform()`.
- Chuyển thành Tensor: `numeric_tensor` (Shape: `[N, 12]`).

**B. Text Embeddings (Ma trận Nx384):**

- Với mỗi node, ghép chuỗi theo CÚ PHÁP BẮT BUỘC:
  `text = f"Handle: {handle}. Name: {display_name}. Bio: {bio}"`
  _(Nếu Name không có, thay bằng khoảng trắng hoặc handle, đảm bảo không bị hiện chữ 'None')_
- Đưa list các chuỗi này qua `nlp_model.encode(texts, convert_to_tensor=True)`.
- Kết quả: `text_tensor` (Shape: `[N, 384]`).

**C. Gộp Node Features (X):**

- Nối 2 tensor theo chiều ngang để tạo vector 396 chiều: `x = torch.cat([numeric_tensor, text_tensor], dim=1)`
- Kiểm tra Shape: `x` phải có kích thước **[N, 396]**.

## 3. Tạo Edges & Inference

- `edge_index`: [2, E]
- `edge_attr`: [E, 1] (Lấy từ từ điển `EDGE_WEIGHTS` của hệ thống, ép kiểu float32).
- **Forward Pass:**

  ```python
  with torch.no_grad():
      # 1. Trích xuất đặc trưng bằng GAT
      embeddings = models["gat"](x, edge_index, edge_attr) # Output [N, 16]
      target_emb = embeddings[target_idx].cpu().numpy().reshape(1, -1)

      # 2. Chuẩn hóa Embedding cho ML
      scaled_emb = models["embedding_scaler"].transform(target_emb)

      # 3. Phân loại bằng Random Forest
      rf_probs = models["rf_model"].predict_proba(scaled_emb)[0]
      rf_pred_class = models["rf_model"].predict(scaled_emb)[0]
      sybil_prob = float(rf_probs[3])
  ```

## 4. Reasoning

Dựa trên classification (0,1,2,3), quét đồ thị `subgraph` (cạnh kết nối trực tiếp với node mục tiêu) đếm các mối quan hệ rủi ro (`CO-OWNER`, `SIM_BIO`, `COLLECT`...) để sinh chuỗi lý giải (reasoning).
