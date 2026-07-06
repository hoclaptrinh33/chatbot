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

if __name__ == "__main__":
    unittest.main()
