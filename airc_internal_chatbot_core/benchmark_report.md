# Báo cáo đánh giá Chunking & Retrieval Accuracy

**Thời gian chạy:** 2026-07-06

## 1. Kết quả Retrieval (Retrieval Metrics)
- **Tổng số ca kiểm thử (Gold Q&A Cases):** 6
- **Hit@5 Ratio:** 100.00%
- **MRR (Mean Reciprocal Rank):** 0.9167

## 2. Chỉ số chất lượng phân mảnh (Chunk Quality Metrics)
- **Tổng số chunks đã tạo:** 9
  - Parent chunks: 1
  - Child chunks: 2
  - Standalone chunks: 6
- **Độ dài Parent chunk lớn nhất:** 449 ký tự (Giới hạn cap thành công!)
- **Số chunks rác bị gắn cờ (Junk chunks):** 0
- **Số lượng bảng tài chính chia nhỏ lặp lại header:** 1

✅ **Tất cả các kiểm tra chất lượng chunk (Quality constraints) đều đạt chuẩn.**

## 3. Chi tiết kết quả kiểm thử
| Tài liệu | Câu hỏi | Hit@5 | MRR |
| --- | --- | --- | --- |
| legal_vietnamese_01 | Phạm vi điều chỉnh của Quyết định 123 là gì? | ✅ Có | 1.0000 |
| legal_vietnamese_01 | Đối tượng nào phải tuân theo quyết định này? | ✅ Có | 1.0000 |
| financial_english_01 | What was the total revenue in Quarter 4? | ✅ Có | 1.0000 |
| financial_english_01 | How much was the tax payable in Q4? | ✅ Có | 0.5000 |
| faq_mixed_01 | Cách thay đổi mật khẩu tài khoản thế nào? | ✅ Có | 1.0000 |
| faq_mixed_01 | Forgot password how to reset? | ✅ Có | 1.0000 |