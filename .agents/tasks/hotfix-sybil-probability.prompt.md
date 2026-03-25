---
description: "Hotfix lỗi logic lấy sai index xác suất (probability) từ mô hình Random Forest trong Module 2 (Inference Service)."
agent: "software-engineer"
---

# Hotfix: Correct Sybil Probability Indexing in Inference Service

Bạn là một Kỹ sư Machine Learning / Backend (Python & FastAPI) nhạy bén. Hệ thống "Sybil Engine" của chúng ta đang gặp một lỗi logic nghiêm trọng ở tầng API trả kết quả.

## 🚨 Mô tả Lỗi (The Bug)

Mô hình `Random Forest` hiện tại có 4 classes (0: BENIGN, 1: LOW_RISK, 2: HIGH_RISK, 3: MALICIOUS).
Khi gọi `predict_proba()`, nó trả về một mảng 4 phần tử tương ứng với xác suất của 4 classes này.

Tuy nhiên, trong code hiện tại, biến `sybil_prob` (thể hiện mức độ tự tin/rủi ro) lại đang bị **hardcode lấy index `[0][0]` (tức là luôn lấy xác suất của class 0 - BENIGN)**. Điều này dẫn đến kết quả trả về API cực kỳ mâu thuẫn: Hệ thống dán nhãn là `HIGH_RISK` nhưng lại báo độ tự tin (confidence) rất thấp (chính là phần % an toàn).

Ví dụ lỗi từ JSON API:

```json
"analysis": {
  "sybil_probability": 0.23, // Sai! Đây là % Benign.
  "risk_label": "HIGH_RISK", // Label thì đúng.
  "reasoning": [
    "AI model detected strong Sybil-like behavior (Confidence: 23.0%)." // Mâu thuẫn!
  ]
}
```

## 🎯 Task Objective (Yêu cầu)

1. Xác định vị trí lỗi trong file `app/services/inference_service.py` (tập trung vào hàm `evaluate_subgraph`).
2. Sửa lại logic lấy `sybil_prob` sao cho nó phản ánh đúng **độ tự tin (Confidence) của nhãn rủi ro (Risk Label) lớn nhất** mà mô hình vừa dự đoán, CHỨ KHÔNG PHẢI luôn lấy index `0`.

## 📋 Hướng dẫn Sửa code (Step-by-Step Fix)

Mở file `app/services/inference_service.py` và tìm khối code sau:

```python
    # Predict
    probs = rf_model.predict_proba(scaled_embedding)
    sybil_prob = float(probs[0][0])  # <--- ĐÂY LÀ DÒNG BỊ LỖI
    rf_pred_class = rf_model.predict(scaled_embedding)[0]
```

**Hãy thay thế nó bằng logic an toàn và chuẩn xác sau:**

```python
    # Predict
    probs = rf_model.predict_proba(scaled_embedding)
    # Lấy class dự đoán (chuyển sang int an toàn)
    rf_pred_class = int(rf_model.predict(scaled_embedding)[0])

    # [HOTFIX]: Lấy xác suất tương ứng với class vừa được dự đoán
    # probs[0] là mảng xác suất của sample đầu tiên.
    sybil_prob = float(probs[0][rf_pred_class])
```

## 🛑 Quality Constraints (Ràng buộc Chất lượng)

- KHÔNG thay đổi kiến trúc mô hình hay cách gọi các file `.pkl`.
- Đảm bảo biến `rf_pred_class` là kiểu `int` trước khi dùng nó làm index để truy cập vào mảng `probs[0]`.
- Output cuối cùng trả về vẫn phải giữ nguyên cấu trúc dict `{ "label": ..., "risk_score": ..., "reasoning": ... }`.

Xin hãy thực hiện Hotfix này ngay lập tức!
