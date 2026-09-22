import os
import re
from typing import Dict, List, Any

class DocumentProfiler:
    """
    Bộ phân loại và phân tích tài liệu cục bộ, theo quy tắc.
    Không sử dụng LLM calls để phân loại domain hay ngôn ngữ.
    """
    def __init__(self):
        # Các từ chức năng tiếng Việt phổ biến để nhận diện ngôn ngữ
        self.vi_keywords = {"và", "của", "là", "để", "cho", "trong", "có", "với", "thì", "mà", "nhưng", "được", "bởi", "tại", "này", "những", "việc", "như"}
        # Các từ chức năng tiếng Anh phổ biến (loại bỏ "i", "a" để tránh nhận diện nhầm số La Mã/từ đơn)
        self.en_keywords = {"the", "of", "and", "to", "in", "that", "is", "was", "he", "for", "on", "are", "as", "with", "his", "they"}

    def profile_document(self, filename: str, text: str) -> Dict[str, Any]:
        if not text or not text.strip():
            return {
                "domain": "general",
                "language": "unknown",
                "structure_type": "plain",
                "has_tables": False,
                "has_numbered_sections": False,
                "heading_density": 0.0,
                "table_density": 0.0,
                "confidence": 1.0,
                "signals": ["empty_text"]
            }

        signals = []
        
        # 1. Phát hiện Ngôn ngữ (Language Detection)
        # Loại bỏ các ký tự đặc biệt, chuyển thành chữ thường và chia từ
        words = re.findall(r'\b\w+\b', text.lower())
        word_count = len(words)
        
        vi_count = 0
        en_count = 0
        
        # Đếm nguyên âm tiếng Việt đặc trưng có dấu
        vi_diacritics_pattern = re.compile(r'[áàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ]')
        vi_diacritic_chars = len(vi_diacritics_pattern.findall(text.lower()))
        
        # Đếm các từ chức năng
        for w in words:
            if w in self.vi_keywords:
                vi_count += 1
            elif w in self.en_keywords:
                en_count += 1
                
        # Tính tỷ lệ từ và ký tự tiếng Việt / tiếng Anh
        char_count = len(text)
        vi_char_ratio = vi_diacritic_chars / char_count if char_count > 0 else 0
        
        vi_ratio = (vi_count / word_count) if word_count > 0 else 0
        en_ratio = (en_count / word_count) if word_count > 0 else 0
        
        if vi_char_ratio > 0.003 or vi_ratio > 0.02:
            if en_ratio > 0.05:  # Ngưỡng en_ratio cho mixed là 5% trở lên
                language = "mixed"
                signals.append(f"language_signals: vi_diacritics={vi_diacritic_chars}, vi_ratio={vi_ratio:.3f}, en_ratio={en_ratio:.3f}")
            else:
                language = "vi"
                signals.append(f"language_signals: vi_diacritics={vi_diacritic_chars}, vi_ratio={vi_ratio:.3f}")
        elif en_ratio > 0.02:
            language = "en"
            signals.append(f"language_signals: en_ratio={en_ratio:.3f}")
        else:
            language = "unknown"
            signals.append("language_signals: low_confidence")
            
        # 2. Phát hiện cấu trúc và domain (Domain & Structure Detection)
        # Tính toán density của bảng biểu
        lines = text.split("\n")
        total_lines = len(lines)
        table_lines_count = sum(1 for line in lines if line.count("|") >= 2)
        table_density = table_lines_count / total_lines if total_lines > 0 else 0
        has_tables = table_lines_count >= 1
        
        # Đếm số lượng Markdown headings
        markdown_header_re = re.compile(r'^(#{1,6})\s+(.+)$')
        header_count = sum(1 for line in lines if markdown_header_re.match(line.strip()))
        heading_density = header_count / total_lines if total_lines > 0 else 0
        
        # Đếm các pattern pháp lý
        legal_vi_re = re.compile(r'^\s*(Chương|Mục|Điều|Khoản|Điểm)\s+(\d+|[a-zđIVXLCDM]+)', re.IGNORECASE)
        legal_en_re = re.compile(r'^\s*(Chapter|Section|Article|Clause|Point)\s+(\d+|[a-zIVXLCDM]+)', re.IGNORECASE)
        legal_matches = sum(1 for line in lines if legal_vi_re.match(line.strip()) or legal_en_re.match(line.strip()))
        
        # Đếm các pattern numbered headings (1.1, 1.1.1)
        numbered_re = re.compile(r'^\s*(\d+\.\d+(?:\.\d+)?)\s+', re.IGNORECASE)
        numbered_matches = sum(1 for line in lines if numbered_re.match(line.strip()))
        has_numbered_sections = numbered_matches >= 2
        
        # Đếm FAQ patterns (Q:, A:, Question, Answer, Hỏi, Đáp)
        faq_re = re.compile(r'^\s*(Q:|A:|Question:|Answer:|Hỏi:|Đáp:|Hỏi\s+\d+:|Đáp\s+\d+:)', re.IGNORECASE)
        faq_matches = sum(1 for line in lines if faq_re.match(line.strip()))
        
        # Phân loại dựa trên filename và content signals
        filename_lower = filename.lower() if filename else ""
        
        # Khởi tạo điểm số cho các domain
        domain_scores = {
            "legal": 0.0,
            "financial": 0.0,
            "academic_technical": 0.0,
            "faq": 0.0,
            "administrative": 0.0,
            "general": 0.1 # base score
        }
        
        # Tín hiệu từ tên file
        if filename_lower:
            if any(k in filename_lower for k in ["quy che", "quy chế", "dieu khoan", "điều khoản", "luat", "luật", "nghi dinh", "nghị định", "thong tu", "thông tư", "quy dinh", "quy định", "chinh sach", "chính sách"]):
                domain_scores["legal"] += 2.0
                signals.append("filename: legal_keyword")
            if any(k in filename_lower for k in ["bao cao", "báo cáo", "tai chinh", "tài chính", "doanh thu", "ket qua", "kết quả", "balance sheet", "income statement", "financial"]):
                domain_scores["financial"] += 2.0
                signals.append("filename: financial_keyword")
            if any(k in filename_lower for k in ["faq", "hoi dap", "hỏi đáp", "q&a", "qa", "question"]):
                domain_scores["faq"] += 2.0
                signals.append("filename: faq_keyword")
            if any(k in filename_lower for k in ["paper", "thesis", "technical", "spec", "academic", "research", "hướng dẫn kỹ thuật"]):
                domain_scores["academic_technical"] += 1.5
                signals.append("filename: academic_technical_keyword")
            if any(k in filename_lower for k in ["notice", "thông báo", "quyet dinh", "quyết định", "cong van", "công văn", "recipients"]):
                domain_scores["administrative"] += 1.5
                signals.append("filename: administrative_keyword")
                
        # Tín hiệu từ nội dung (content signals)
        # 1. Legal
        if legal_matches > 0:
            legal_score = min(legal_matches * 0.5, 3.0)
            domain_scores["legal"] += legal_score
            signals.append(f"content: legal_patterns_count={legal_matches}")
            
        # 2. Financial
        if table_density > 0.05:
            domain_scores["financial"] += min(table_density * 10, 2.0)
            signals.append(f"content: high_table_density={table_density:.3f}")
        financial_keywords = ["balance sheet", "income statement", "cash flow", "doanh thu", "lợi nhuận", "nợ", "tài sản", "vốn chủ sở hữu", "chi phí", "thuế", "payable", "receivable"]
        fin_keyword_matches = sum(1 for w in financial_keywords if w in text.lower())
        if fin_keyword_matches > 0:
            domain_scores["financial"] += min(fin_keyword_matches * 0.3, 1.5)
            signals.append(f"content: financial_keywords_count={fin_keyword_matches}")
            
        # 3. FAQ
        if faq_matches > 0:
            faq_score = min(faq_matches * 0.5, 3.0)
            domain_scores["faq"] += faq_score
            signals.append(f"content: faq_patterns_count={faq_matches}")
            
        # 4. Academic/Technical
        academic_keywords = ["abstract", "references", "tóm tắt", "tài liệu tham khảo", "conclusion", "kết luận", "chương", "phương pháp", "thực nghiệm", "bảng", "hình", "figure", "equation", "công thức"]
        acad_keyword_matches = sum(1 for w in academic_keywords if w in text.lower())
        if acad_keyword_matches > 0:
            domain_scores["academic_technical"] += min(acad_keyword_matches * 0.2, 1.5)
        if "```" in text:
            domain_scores["academic_technical"] += 1.0
            signals.append("content: code_blocks_found")
        if has_numbered_sections:
            domain_scores["academic_technical"] += 0.8
            signals.append("content: numbered_sections_found")
            
        # 5. Administrative
        admin_keywords = ["cộng hòa xã hội", "độc lập - tự do", "kính gửi", "v/v:", "nơi nhận", "ký tên", "ban hành", "quyết định", "thông báo"]
        admin_keyword_matches = sum(1 for w in admin_keywords if w in text.lower())
        if admin_keyword_matches > 0:
            domain_scores["administrative"] += min(admin_keyword_matches * 0.4, 2.0)
            signals.append(f"content: admin_keywords_count={admin_keyword_matches}")

        # Chọn domain có điểm số cao nhất
        sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
        domain = sorted_domains[0][0]
        max_score = sorted_domains[0][1]
        
        # Xác định structure_type
        if heading_density > 0.02:
            structure_type = "markdown"
        elif domain == "legal" and legal_matches > 0:
            structure_type = "legal"
        elif has_numbered_sections:
            structure_type = "numbered"
        elif domain == "faq" and faq_matches > 0:
            structure_type = "faq"
        elif table_density > 0.15:
            structure_type = "table_heavy"
        else:
            structure_type = "plain"
            
        # Tính confidence
        confidence = min(max_score / 3.0, 1.0) if max_score > 0 else 0.5
        
        return {
            "domain": domain,
            "language": language,
            "structure_type": structure_type,
            "has_tables": has_tables,
            "has_numbered_sections": has_numbered_sections,
            "heading_density": heading_density,
            "table_density": table_density,
            "confidence": confidence,
            "signals": signals
        }

document_profiler = DocumentProfiler()
