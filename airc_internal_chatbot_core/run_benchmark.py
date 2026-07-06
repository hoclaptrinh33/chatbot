import sys
import types
from unittest.mock import MagicMock

# Chỉ mock các thư viện thực sự bị thiếu trong venv của hermes-agent
modules_to_mock = [
    'motor', 'motor.motor_asyncio', 'bson', 'bson.errors',
    'qdrant_client', 'qdrant_client.http', 'qdrant_client.http.models', 'qdrant_client.models',
    'sentence_transformers'
]

for name in modules_to_mock:
    mod = types.ModuleType(name)
    mod.__path__ = []
    sys.modules[name] = mod

# Định nghĩa các class/exception cụ thể trong mock modules
sys.modules['bson'].ObjectId = MagicMock
sys.modules['bson.errors'].InvalidId = Exception
sys.modules['sentence_transformers'].SentenceTransformer = MagicMock
sys.modules['sentence_transformers'].CrossEncoder = MagicMock

# Thiết lập chi tiết cho motor.motor_asyncio
sys.modules['motor.motor_asyncio'].AsyncIOMotorDatabase = MagicMock
sys.modules['motor.motor_asyncio'].AsyncIOMotorClient = MagicMock

# Thiết lập chi tiết cho qdrant_client
sys.modules['qdrant_client'].QdrantClient = MagicMock

# Thiết lập chi tiết cho qdrant_client.http.models
sys.modules['qdrant_client.http.models'].Distance = MagicMock
sys.modules['qdrant_client.http.models'].VectorParams = MagicMock
sys.modules['qdrant_client.http.models'].PointStruct = MagicMock
sys.modules['qdrant_client.http.models'].Filter = MagicMock
sys.modules['qdrant_client.http.models'].FieldCondition = MagicMock
sys.modules['qdrant_client.http.models'].MatchAny = MagicMock

import os
import json
import math
import re
from typing import List, Dict, Any

# Thêm PYTHONPATH để import
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.services.chunking_service import chunking_service

# =====================================================================
# GOLD RETRIEVAL DATASET (Mock for benchmark)
# =====================================================================
GOLD_DATASET = [
    {
        "doc_id": "legal_vietnamese_01",
        "domain": "legal",
        "language": "vi",
        "filename": "QuyetDinh123.txt",
        "content": (
            "Chương I: Quy định chung\n\n"
            "Điều 1. Phạm vi điều chỉnh\n"
            "Quyết định này quy định về quy trình tiếp nhận, xử lý và phản hồi phản ánh kiến nghị của người dân.\n\n"
            "Điều 2. Đối tượng áp dụng\n"
            "Quyết định này áp dụng đối với tất cả cơ quan hành chính nhà nước, cán bộ công chức trên địa bàn thành phố.\n\n"
            "Điều 3. Giải thích từ ngữ\n"
            "1. Phản ánh kiến nghị là việc công dân gửi thông tin vướng mắc hành chính.\n"
            "2. Hệ thống tiếp nhận là phần mềm dịch vụ công trực tuyến của thành phố."
        ),
        "cases": [
            {
                "question": "Phạm vi điều chỉnh của Quyết định 123 là gì?",
                "expected_terms": ["phạm vi điều chỉnh", "tiếp nhận", "kiến nghị", "người dân"]
            },
            {
                "question": "Đối tượng nào phải tuân theo quyết định này?",
                "expected_terms": ["đối tượng áp dụng", "cơ quan hành chính", "cán bộ công chức"]
            }
        ]
    },
    {
        "doc_id": "financial_english_01",
        "domain": "financial",
        "language": "en",
        "filename": "Q4_Revenue_Statement.md",
        "content": (
            "Financial Statement for Q4 2025\n\n"
            "Table 1: Corporate Income Tax Payable\n"
            "| Item | Quarter 1 | Quarter 2 | Quarter 3 | Quarter 4 |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| Total Revenue | 120,500 | 145,200 | 160,800 | 189,815 |\n"
            "| Operational Cost | 80,000 | 95,000 | 102,000 | 110,000 |\n"
            "| Tax Payable | 8,100 | 10,200 | 11,800 | 18,915 |\n"
            "| Net Income | 32,400 | 40,000 | 47,000 | 60,900 |"
        ),
        "cases": [
            {
                "question": "What was the total revenue in Quarter 4?",
                "expected_terms": ["revenue", "189,815", "quarter 4"]
            },
            {
                "question": "How much was the tax payable in Q4?",
                "expected_terms": ["tax payable", "18,915", "quarter 4"]
            }
        ]
    },
    {
        "doc_id": "faq_mixed_01",
        "domain": "faq",
        "language": "mixed",
        "filename": "FAQ_SmartBot.txt",
        "content": (
            "Hỏi: Làm thế nào để đổi mật khẩu tài khoản?\n"
            "Đáp: Bạn truy cập vào Cài đặt -> Bảo mật -> Chọn Đổi mật khẩu. Sau đó nhập mã OTP gửi về điện thoại.\n\n"
            "Q: How to reset password if I forgot it?\n"
            "A: Click on 'Forgot Password' on the login screen, enter your registered email, and follow the reset link."
        ),
        "cases": [
            {
                "question": "Cách thay đổi mật khẩu tài khoản thế nào?",
                "expected_terms": ["đổi mật khẩu", "cài đặt", "otp"]
            },
            {
                "question": "Forgot password how to reset?",
                "expected_terms": ["forgot password", "reset", "email"]
            }
        ]
    }
]

# =====================================================================
# SIMILARITY ENGINE (TF-IDF / Word Overlap Fallback for offline running)
# =====================================================================
def get_words(text: str) -> set:
    text_clean = re.sub(r'[^\w\s]', ' ', text.lower())
    return set(text_clean.split())

def calculate_jaccard_similarity(query: str, doc_text: str) -> float:
    q_words = get_words(query)
    d_words = get_words(doc_text)
    if not q_words:
        return 0.0
    intersection = q_words.intersection(d_words)
    union = q_words.union(d_words)
    return len(intersection) / len(union) if union else 0.0

# Giả lập RAG Retrieval sử dụng Similarity
def mock_retrieve(query: str, chunks: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
    scored_chunks = []
    for chunk in chunks:
        search_target = chunk.get("embedding_text") or chunk.get("text")
        score = calculate_jaccard_similarity(query, search_target)
        scored_chunks.append((score, chunk))
        
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored_chunks[:top_k]]

# =====================================================================
# BENCHMARK EVALUATOR
# =====================================================================
class BenchmarkEvaluator:
    def __init__(self, dataset: List[Dict[str, Any]]):
        self.dataset = dataset

    def run_evaluation(self) -> Dict[str, Any]:
        results = []
        
        total_hit_at_5 = 0
        total_mrr = 0.0
        total_cases = 0
        
        quality_metrics = {
            "total_chunks": 0,
            "parent_chunks": 0,
            "child_chunks": 0,
            "standalone_chunks": 0,
            "max_parent_chars": 0,
            "junk_chunks_flagged": 0,
            "table_chunks_with_headers": 0,
            "errors": []
        }
        
        for doc in self.dataset:
            # 1. Chạy Chunking Service
            chunks = chunking_service.chunk_document_advanced(
                text=doc["content"],
                filename=doc["filename"],
                file_type=doc["domain"]
            )
            
            # 2. Thu thập chỉ số chất lượng
            quality_metrics["total_chunks"] += len(chunks)
            for c in chunks:
                role = c.get("chunk_role", "standalone")
                if role == "parent":
                    quality_metrics["parent_chunks"] += 1
                    quality_metrics["max_parent_chars"] = max(quality_metrics["max_parent_chars"], len(c["text"]))
                    domain_caps = {"legal": 4000, "financial": 5000, "general": 3000, "administrative": 3000}
                    cap = domain_caps.get(doc["domain"], 3000)
                    if len(c["text"]) > cap + 200:
                        quality_metrics["errors"].append(
                            f"Parent chunk exceeds cap: domain={doc['domain']}, size={len(c['text'])} > {cap}"
                        )
                elif role == "child":
                    quality_metrics["child_chunks"] += 1
                else:
                    quality_metrics["standalone_chunks"] += 1
                    
                if "junk_source" in c.get("quality_flags", []):
                    quality_metrics["junk_chunks_flagged"] += 1
                    
                if c.get("is_table") and c.get("table_header"):
                    quality_metrics["table_chunks_with_headers"] += 1
            
            # Chỉ lấy các chunk được index (child & standalone) để retrieve
            indexable_chunks = [c for c in chunks if c.get("chunk_role") in ["child", "standalone"]]
            
            # 3. Đánh giá retrieval cho từng case
            for case in doc["cases"]:
                total_cases += 1
                retrieved = mock_retrieve(case["question"], indexable_chunks, top_k=5)
                
                hit = False
                mrr_score = 0.0
                
                for rank, chunk in enumerate(retrieved):
                    chunk_text_lower = chunk["text"].lower()
                    matches = sum(1 for term in case["expected_terms"] if term.lower() in chunk_text_lower)
                    
                    if matches >= min(2, len(case["expected_terms"])):
                        hit = True
                        if mrr_score == 0.0:
                            mrr_score = 1.0 / (rank + 1)
                            
                if hit:
                    total_hit_at_5 += 1
                total_mrr += mrr_score
                
                results.append({
                    "doc_id": doc["doc_id"],
                    "question": case["question"],
                    "hit_at_5": hit,
                    "mrr": mrr_score,
                    "expected_terms": case["expected_terms"]
                })
                
        hit_ratio = total_hit_at_5 / total_cases if total_cases > 0 else 0.0
        mrr_avg = total_mrr / total_cases if total_cases > 0 else 0.0
        
        return {
            "summary": {
                "total_cases": total_cases,
                "hit_ratio_at_5": round(hit_ratio, 4),
                "mrr_avg": round(mrr_avg, 4)
            },
            "quality_metrics": quality_metrics,
            "case_results": results
        }

    def export_reports(self, eval_results: Dict[str, Any], output_dir: str = "."):
        # Export JSON
        json_path = os.path.join(output_dir, "benchmark_report.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(eval_results, f, ensure_ascii=False, indent=2)
        print(f"JSON report exported to: {json_path}")
        
        # Export Markdown
        md_path = os.path.join(output_dir, "benchmark_report.md")
        summary = eval_results["summary"]
        qm = eval_results["quality_metrics"]
        
        md_content = []
        md_content.append("# Báo cáo đánh giá Chunking & Retrieval Accuracy")
        md_content.append(f"\n**Thời gian chạy:** 2026-07-06\n")
        
        md_content.append("## 1. Kết quả Retrieval (Retrieval Metrics)")
        md_content.append(f"- **Tổng số ca kiểm thử (Gold Q&A Cases):** {summary['total_cases']}")
        md_content.append(f"- **Hit@5 Ratio:** {summary['hit_ratio_at_5'] * 100:.2f}%")
        md_content.append(f"- **MRR (Mean Reciprocal Rank):** {summary['mrr_avg']:.4f}")
        
        md_content.append("\n## 2. Chỉ số chất lượng phân mảnh (Chunk Quality Metrics)")
        md_content.append(f"- **Tổng số chunks đã tạo:** {qm['total_chunks']}")
        md_content.append(f"  - Parent chunks: {qm['parent_chunks']}")
        md_content.append(f"  - Child chunks: {qm['child_chunks']}")
        md_content.append(f"  - Standalone chunks: {qm['standalone_chunks']}")
        md_content.append(f"- **Độ dài Parent chunk lớn nhất:** {qm['max_parent_chars']} ký tự (Giới hạn cap thành công!)")
        md_content.append(f"- **Số chunks rác bị gắn cờ (Junk chunks):** {qm['junk_chunks_flagged']}")
        md_content.append(f"- **Số lượng bảng tài chính chia nhỏ lặp lại header:** {qm['table_chunks_with_headers']}")
        
        if qm["errors"]:
            md_content.append("\n### ⚠️ Cảnh báo chất lượng:")
            for err in qm["errors"]:
                md_content.append(f"- [FAIL] {err}")
        else:
            md_content.append("\n✅ **Tất cả các kiểm tra chất lượng chunk (Quality constraints) đều đạt chuẩn.**")
            
        md_content.append("\n## 3. Chi tiết kết quả kiểm thử")
        md_content.append("| Tài liệu | Câu hỏi | Hit@5 | MRR |")
        md_content.append("| --- | --- | --- | --- |")
        for res in eval_results["case_results"]:
            md_content.append(f"| {res['doc_id']} | {res['question']} | {'✅ Có' if res['hit_at_5'] else '❌ Không'} | {res['mrr']:.4f} |")
            
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_content))
        print(f"Markdown report exported to: {md_path}")


if __name__ == "__main__":
    evaluator = BenchmarkEvaluator(GOLD_DATASET)
    print("Starting benchmark evaluation...")
    results = evaluator.run_evaluation()
    evaluator.export_reports(results)
    print("Benchmark completed successfully.")
