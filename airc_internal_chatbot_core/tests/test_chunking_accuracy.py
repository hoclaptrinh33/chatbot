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

import unittest
import os

# Thêm đường dẫn app vào PYTHONPATH để import
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.document_profiler import document_profiler
from app.services.section_parser import section_parser
from app.services.chunking_service import chunking_service

class TestChunkingAccuracy(unittest.TestCase):
    def test_document_profiler_vietnamese_legal(self):
        text = "Chương I: Quy định chung\nĐiều 1. Phạm vi điều chỉnh\nQuyết định này quy định về việc quản lý và sử dụng..."
        profile = document_profiler.profile_document("quy_che_lam_viec.txt", text)
        self.assertEqual(profile["domain"], "legal")
        self.assertEqual(profile["language"], "vi")
        self.assertEqual(profile["structure_type"], "legal")

    def test_document_profiler_english_financial(self):
        text = "Balance Sheet as of December 31, 2025\n| Assets | Current Year | Previous Year |\n| --- | --- | --- |\n| Cash | 150,000 | 120,000 |"
        profile = document_profiler.profile_document("Financial_Statement.md", text)
        self.assertEqual(profile["domain"], "financial")
        self.assertEqual(profile["language"], "en")
        self.assertTrue(profile["has_tables"])

    def test_section_parser_markdown(self):
        text = "# Section 1\nThis is content 1.\n## Subsection 1.1\nThis is content 1.1."
        sections = section_parser.parse_sections(text, "markdown")
        self.assertEqual(len(sections), 2)
        self.assertEqual(sections[0]["heading_path"], ["Section 1"])
        self.assertEqual(sections[1]["heading_path"], ["Section 1", "Subsection 1.1"])

    def test_section_parser_sibling_h2_not_nested(self):
        text = "## TỔNG QUAN\n\n## 1. THÔNG TIN CHUNG\nNội dung mục 1.\n\n## 2. BỐI CẢNH\nNội dung mục 2."
        sections = section_parser.parse_sections(text, "markdown")
        self.assertGreaterEqual(len(sections), 2)
        sec2 = next(s for s in sections if any("BỐI CẢNH" in h for h in s["heading_path"]))
        self.assertIn("2. BỐI CẢNH", sec2["heading_path"])
        self.assertFalse(any("TỔNG QUAN" in h for h in sec2["heading_path"]))

    def test_financial_table_splitting(self):
        table_text = (
            "| Item | Q1 | Q2 | Q3 | Q4 |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| Rev | 10 | 12 | 14 | 16 |\n"
            "| Exp | 8 | 9 | 10 | 11 |\n"
            "| Net | 2 | 3 | 4 | 5 |\n"
            "| Tax | 0.4 | 0.6 | 0.8 | 1.0 |\n"
            "| Dep | 1.1 | 1.2 | 1.3 | 1.4 |\n"
            "| Div | 0.5 | 0.5 | 0.5 | 0.5 |\n"
        )
        from app.services.domain_splitter import FinancialSplitter
        splitter = FinancialSplitter()
        chunks = splitter.split_section(table_text, [])
        self.assertEqual(len(chunks), 2)
        self.assertTrue(chunks[0]["is_table"])
        self.assertTrue(chunks[1]["is_table"])
        self.assertTrue(chunks[1]["has_repeated_header"])

    def test_parent_chunk_size_capping(self):
        # Tạo một section văn bản rất dài để kích hoạt Parent-Child Policy & Capping
        long_section = "Đây là một câu rất dài. " * 300 # ~ 7200 ký tự
        chunks = chunking_service.chunk_document_advanced(
            text=long_section,
            filename="general_policy.txt",
            file_type="general"
        )
        
        # Kiểm tra kích thước parent chunk
        parent_chunks = [c for c in chunks if c["is_parent"]]
        for p in parent_chunks:
            self.assertTrue(len(p["text"]) <= 3200) # general cap = 3000 + 200 prefix budget

        # Kiểm tra mối liên kết parent-child
        child_chunks = [c for c in chunks if not c["is_parent"]]
        self.assertTrue(len(child_chunks) > 1)
        for c in child_chunks:
            self.assertEqual(c["chunk_role"], "child")
            self.assertIsNotNone(c["parent_chunk_temp_idx"])

    def test_institutional_markdown_keeps_lists_together(self):
        text = """## TỔNG QUAN VỀ TRUNG TÂM NGHIÊN CỨU TIÊN TIẾN QUỐC TẾ VỀ TRÍ TUỆ NHÂN TẠO ỨNG DỤNG (AIRC)

## 1. THÔNG TIN CHUNG VỀ ĐƠN VỊ

- Tên đầy đủ bằng tiếng Việt: Trung tâm Nghiên cứu tiên tiến quốc tế về Trí tuệ nhân tạo ứng dụng
- Tên tiếng Anh: Artificial Intelligence Research Center
- Tên viết tắt: AIRC
- Cơ quan chủ quản: Viện Công nghệ Thông tin (VNU-ITI)

## 2. BỐI CẢNH HÌNH THÀNH VÀ CƠ QUAN CHỦ QUẢN

- Viện Công nghệ Thông tin (VNU-ITI) được thành lập năm 2001, là đơn vị thành viên của Đại học Quốc gia Hà Nội.
- Sứ mệnh của Viện: Đào tạo nguồn nhân lực chất lượng cao; nghiên cứu khoa học, triển khai ứng dụng.
- Các hướng nghiên cứu chủ đạo của Viện và Trung tâm AIRC:
- Khoa học dữ liệu (Data Science)
- Trí tuệ nhân tạo (Artificial Intelligence - AI), Mô hình ngôn ngữ lớn (LLM)
- Thực tại ảo và thực tại tăng cường (VR/AR)
- Xử lý ảnh và video, thị giác máy tính (Computer Vision)
- An toàn và an ninh thông tin (Cybersecurity)
- Công nghệ chuỗi khối (Blockchain)
- Internet vạn vật (IoT) và hệ thống nhúng

## 5. NĂM GIÁ TRỊ CỐT LÕI CỦA TRUNG TÂM AIRC

Trung tâm theo đuổi năm giá trị cốt lõi: khoa học, sáng tạo, hợp tác, trách nhiệm và phụng sự cộng đồng.
"""
        chunks = chunking_service.chunk_document_advanced(
            text=text,
            filename="Thong_tin_Trung_tam_AIRC_Plain.pdf",
            file_type="general",
        )
        embeddable = [c for c in chunks if not c.get("is_parent")]
        texts = [c["text"] for c in embeddable]

        self.assertLessEqual(len(embeddable), 6)
        self.assertTrue(all(len(t.strip()) >= 80 for t in texts))
        self.assertFalse(any(t.strip() == "- Khoa học dữ liệu (Data Science)" for t in texts))
        self.assertTrue(any("Khoa học dữ liệu (Data Science)" in t and "Blockchain" in t for t in texts))
        self.assertTrue(all(c["heading_path"] and all(h for h in c["heading_path"]) for c in embeddable))
        boi_canh = [c for c in embeddable if any("BỐI CẢNH" in h for h in c["heading_path"])]
        self.assertTrue(boi_canh)
        self.assertFalse(any("TỔNG QUAN" in h for c in boi_canh for h in c["heading_path"]))

    def test_general_splitter_packs_short_bullets(self):
        from app.services.domain_splitter import AdministrativeGeneralSplitter
        splitter = AdministrativeGeneralSplitter()
        text = "## Hướng nghiên cứu\n" + "\n".join(
            f"- Hướng nghiên cứu số {i} của trung tâm AIRC"
            for i in range(1, 9)
        )
        chunks = splitter.split_section(text, ["Hướng nghiên cứu"])
        self.assertEqual(len(chunks), 1)
        self.assertIn("Hướng nghiên cứu số 1", chunks[0]["text"])
        self.assertIn("Hướng nghiên cứu số 8", chunks[0]["text"])

if __name__ == "__main__":
    unittest.main()
