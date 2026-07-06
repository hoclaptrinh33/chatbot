import re
from typing import List, Dict, Any, Optional

class BaseSplitter:
    """Lớp cơ sở cho các bộ splitters theo domain"""
    def _is_junk_chunk(self, text: str) -> bool:
        clean = text.strip()
        if not clean:
            return True
        if not any(c.isalnum() for c in clean):
            return True
        words = [w for w in clean.split() if any(c.isalnum() for c in w)]
        if not words:
            return True
        if len(clean) < 5:
            if len(clean) == 1:
                return True
            if clean.lower() in ["è", "=", "d", "n", "-", "_", "*", "+", "è\n="]:
                return True
        if len(clean) < 25 and all(len(w) <= 1 for w in words):
            return True
        # Lọc các dòng bảng biểu chỉ chứa dấu phân cách như |---|---|
        if "|" in clean:
            lines = [l.strip() for l in clean.split("\n") if l.strip()]
            if all(re.match(r'^[\s|:\-*_+=#]*$', l) for l in lines):
                return True
        return False

    def _split_recursive(self, text: str, separators: List[str], max_size: int) -> List[str]:
        if not separators or len(text) <= max_size:
            return [text]
        separator = separators[0]
        remaining = separators[1:]
        splits = text.split(separator)
        segments = []
        for i, s in enumerate(splits):
            if i < len(splits) - 1:
                segments.append(s + separator)
            else:
                segments.append(s)
        final_segments = []
        for seg in segments:
            if len(seg) > max_size and remaining:
                final_segments.extend(self._split_recursive(seg, remaining, max_size))
            else:
                final_segments.append(seg)
        return final_segments

    def _force_split(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        chunks = []
        start = 0
        text_len = len(text)
        while start < text_len:
            if start + chunk_size >= text_len:
                chunks.append(text[start:])
                break
            end = start + chunk_size
            scan_limit = max(start, end - 30)
            break_point = end
            for i in range(end - 1, scan_limit - 1, -1):
                if text[i] in (' ', '\n'):
                    break_point = i
                    break
            chunk_content = text[start:break_point].strip()
            if chunk_content:
                chunks.append(chunk_content)
            next_start = max(start, break_point - overlap)
            found_sentence_boundary = False
            for i in range(next_start, break_point):
                if i + 1 < break_point and text[i] in ('.', '?', '!', '\n') and text[i+1] in (' ', '\n'):
                    next_start = i + 1
                    found_sentence_boundary = True
                    break
            if not found_sentence_boundary:
                while next_start > start and text[next_start] not in (' ', '\n'):
                    next_start -= 1
                if text[next_start] in (' ', '\n'):
                    next_start += 1
            start = next_start
        return chunks


class LegalSplitter(BaseSplitter):
    """
    Splitter cho tài liệu pháp quy.
    Giữ Dieu/Article làm parent boundary chính.
    Target child: 500-900 ký tự.
    """
    def __init__(self):
        self.clause_pattern = re.compile(r'^\s*(?:\d+|Khoản\s+\d+)[:\.]\s*')
        self.point_header_pattern = re.compile(r'^\s*[a-zđ]\)\s*', re.IGNORECASE)
        self.bullet_pattern = re.compile(r'^\s*[-+•\*]\s*')

    def split_section(self, text: str, heading_path: List[str], child_size: int = 700) -> List[Dict[str, Any]]:
        # Phân tích theo Điều -> Khoản -> Điểm -> Câu
        lines = text.split("\n")
        items = []
        
        current_clause = ""
        current_point = ""
        
        # Tiền xử lý gộp các dòng bị ngắt dòng do parser
        processed_lines = []
        skip_next = False
        isolated_num_pattern = re.compile(r'^\s*(?:\d+|[a-zđ]|Khoản\s+\d+)[\.\):\-\*•]\s*$', re.IGNORECASE)
        
        for idx in range(len(lines)):
            if skip_next:
                skip_next = False
                continue
            line = lines[idx]
            line_strip = line.strip()
            if isolated_num_pattern.match(line_strip) and idx + 1 < len(lines):
                combined = line.rstrip('\r\n') + " " + lines[idx + 1].lstrip()
                processed_lines.append(combined)
                skip_next = True
            else:
                processed_lines.append(line)
                
        # Phân tích từng dòng để trích xuất cấu trúc pháp lý
        for line in processed_lines:
            line_strip = line.strip()
            if not line_strip:
                continue
                
            if self.clause_pattern.match(line_strip):
                current_clause = line_strip
                current_point = ""
                items.append({"text": line_strip, "headers": [], "type": "clause"})
            elif self.point_header_pattern.match(line_strip):
                current_point = line_strip
                hdrs = [current_clause] if current_clause else []
                items.append({"text": line_strip, "headers": hdrs, "type": "point"})
            elif self.bullet_pattern.match(line_strip):
                hdrs = []
                if current_clause:
                    hdrs.append(current_clause)
                if current_point:
                    hdrs.append(current_point)
                items.append({"text": line_strip, "headers": hdrs, "type": "bullet"})
            else:
                # Dòng thường
                hdrs = []
                if current_point:
                    if current_clause:
                        hdrs.append(current_clause)
                    hdrs.append(current_point)
                    items.append({"text": line_strip, "headers": hdrs, "type": "point_content"})
                elif current_clause:
                    hdrs.append(current_clause)
                    items.append({"text": line_strip, "headers": hdrs, "type": "clause_content"})
                else:
                    items.append({"text": line_strip, "headers": [], "type": "paragraph"})
                    
        # Gom các item thành child chunks
        chunks = []
        current_chunk_items = []
        current_len = 0
        
        def build_chunk_text(item_list):
            if not item_list:
                return ""
            first = item_list[0]
            prefix = "\n".join(first["headers"]) + "\n" if first["headers"] else ""
            content = "\n\n".join([it["text"] for it in item_list])
            return prefix + content

        for item in items:
            if self._is_junk_chunk(item["text"]):
                continue
            test_items = current_chunk_items + [item]
            test_text = build_chunk_text(test_items)
            
            # Kiểm tra xem có nên gộp hay ngắt chunk
            if len(test_text) <= child_size or not current_chunk_items:
                current_chunk_items.append(item)
                current_len = len(test_text)
            else:
                # Xuất bản chunk hiện tại
                chunks.append({
                    "text": build_chunk_text(current_chunk_items),
                    "is_table": False,
                    "section_type": "legal_article"
                })
                current_chunk_items = [item]
                current_len = len(item["text"])
                
        if current_chunk_items:
            chunks.append({
                "text": build_chunk_text(current_chunk_items),
                "is_table": False,
                "section_type": "legal_article"
            })
            
        return chunks


class FinancialSplitter(BaseSplitter):
    """
    Splitter cho tài liệu tài chính.
    Đặc biệt xử lý bảng biểu bằng row window, lặp lại header và caption.
    """
    def split_section(self, text: str, heading_path: List[str]) -> List[Dict[str, Any]]:
        # Tách văn bản thành văn bản thường và bảng biểu
        lines = text.split("\n")
        blocks = []
        current_table = []
        current_text = []
        
        # Tìm caption của bảng (thông thường là dòng trước bảng bắt đầu bằng "Bảng", "Table" hoặc dòng in đậm kết thúc bằng ":")
        last_normal_line = ""

        for line in lines:
            is_table_line = line.count("|") >= 2
            if is_table_line:
                if current_text:
                    blocks.append({"type": "text", "content": "\n".join(current_text), "caption": ""})
                    current_text = []
                current_table.append(line)
            else:
                if current_table:
                    # Caption có thể là dòng ngay trước bảng
                    caption = last_normal_line if last_normal_line and any(k in last_normal_line.lower() for k in ["bảng", "table", "biểu", "doanh thu", "chi phí", "thuế", "lợi nhuận", "báo cáo"]) else ""
                    blocks.append({"type": "table", "content": "\n".join(current_table), "caption": caption})
                    current_table = []
                current_text.append(line)
                if line.strip():
                    last_normal_line = line.strip()

        if current_text:
            blocks.append({"type": "text", "content": "\n".join(current_text), "caption": ""})
        if current_table:
            caption = last_normal_line if last_normal_line and any(k in last_normal_line.lower() for k in ["bảng", "table", "biểu", "doanh thu", "chi phí", "thuế", "lợi nhuận", "báo cáo"]) else ""
            blocks.append({"type": "table", "content": "\n".join(current_table), "caption": caption})

        chunks = []
        for block in blocks:
            if block["type"] == "table":
                # Tách bảng lớn thành các row window
                table_text = block["content"]
                caption = block["caption"]
                table_chunks = self._split_table_by_rows(table_text, caption)
                for tc in table_chunks:
                    chunks.append(tc)
            else:
                # Text thường
                sub_segs = self._split_recursive(block["content"], ["\n\n", "\n", ". ", "; ", "? ", "! ", ", "], 600)
                for seg in sub_segs:
                    if not self._is_junk_chunk(seg):
                        chunks.append({
                            "text": seg.strip(),
                            "is_table": False,
                            "section_type": "paragraph"
                        })
        return chunks

    def _split_table_by_rows(self, table_text: str, caption: str) -> List[Dict[str, Any]]:
        # Chia nhỏ bảng biểu và lặp lại header
        lines = [line.strip() for line in table_text.split("\n") if line.strip()]
        if len(lines) < 3:
            return [{"text": table_text, "is_table": True, "table_caption": caption or None, "table_header": [], "row_range": None}]
            
        header_rows = []
        # Nhận diện header: dòng 1 và dòng phân cách 2
        header_rows.append(lines[0])
        if len(lines) > 1 and all(c in " |:-=*" for c in lines[1]):
            header_rows.append(lines[1])
            data_start_idx = 2
        else:
            data_start_idx = 1
            
        header_text = "\n".join(header_rows)
        data_rows = lines[data_start_idx:]
        
        # Cắt dòng dữ liệu theo window 5 dòng
        window_size = 5
        table_chunks = []
        
        for idx in range(0, len(data_rows), window_size):
            chunk_data = data_rows[idx : idx + window_size]
            row_range = [data_start_idx + idx, data_start_idx + idx + len(chunk_data) - 1]
            
            # Tạo văn bản bảng biểu cho chunk này
            chunk_table_text = header_text + "\n" + "\n".join(chunk_data)
            
            # Thêm caption vào đầu bảng
            display_text = f"Table: {caption}\n{chunk_table_text}" if caption else chunk_table_text
            
            table_chunks.append({
                "text": display_text,
                "is_table": True,
                "table_caption": caption or None,
                "table_header": header_rows,
                "row_range": row_range,
                "has_repeated_header": idx > 0
            })
            
        return table_chunks


class FAQSplitter(BaseSplitter):
    """
    Splitter cho FAQ.
    Đảm bảo 1 chunk chứa đúng 1 cặp Q&A.
    """
    def split_section(self, text: str, heading_path: List[str]) -> List[Dict[str, Any]]:
        if not text.strip():
            return []
        # FAQ pair thường đã được SectionParser chia nhỏ thành 1 section duy nhất.
        # Ở đây ta chỉ cần trả về luôn section đó hoặc bóc tách câu hỏi & câu trả lời.
        return [{
            "text": text.strip(),
            "is_table": False,
            "section_type": "faq_pair"
        }]


class AcademicTechnicalSplitter(BaseSplitter):
    """
    Splitter cho Academic & Technical.
    Giữ công thức toán học và code block.
    """
    def split_section(self, text: str, heading_path: List[str], child_size: int = 800) -> List[Dict[str, Any]]:
        # Academic và Technical: ưu tiên ngắt theo markdown sections, giữ code block nguyên vẹn.
        # Đầu tiên, trích xuất và bảo vệ các code blocks
        code_blocks = re.findall(r'```[\s\S]*?```', text)
        # Thay thế code block bằng placeholder
        placeholder_text = text
        placeholders = []
        for idx, cb in enumerate(code_blocks):
            placeholder = f"__CODE_BLOCK_PLACEHOLDER_{idx}__"
            placeholders.append((placeholder, cb))
            placeholder_text = placeholder_text.replace(cb, placeholder)
            
        # Chia nhỏ placeholder_text đệ quy
        sub_segs = self._split_recursive(placeholder_text, ["\n\n", "\n", ". ", "; ", "? ", "! "], child_size)
        
        chunks = []
        for seg in sub_segs:
            # Khôi phục code blocks
            restored_seg = seg
            for placeholder, cb in placeholders:
                restored_seg = restored_seg.replace(placeholder, cb)
                
            if not self._is_junk_chunk(restored_seg):
                chunks.append({
                    "text": restored_seg.strip(),
                    "is_table": False,
                    "section_type": "academic_technical"
                })
        return chunks


class AdministrativeGeneralSplitter(BaseSplitter):
    """
    Splitter cho văn bản hành chính & chung.
    """
    def split_section(self, text: str, heading_path: List[str], child_size: int = 600) -> List[Dict[str, Any]]:
        # Tách văn bản thường đệ quy
        sub_segs = self._split_recursive(text, ["\n\n", "\n", ". ", "; ", "? ", "! ", " "], child_size)
        chunks = []
        for seg in sub_segs:
            if not self._is_junk_chunk(seg):
                chunks.append({
                    "text": seg.strip(),
                    "is_table": False,
                    "section_type": "paragraph"
                })
        return chunks


# Mappings splitters theo domain
domain_splitters = {
    "legal": LegalSplitter(),
    "financial": FinancialSplitter(),
    "academic_technical": AcademicTechnicalSplitter(),
    "faq": FAQSplitter(),
    "administrative": AdministrativeGeneralSplitter(),
    "general": AdministrativeGeneralSplitter()
}
