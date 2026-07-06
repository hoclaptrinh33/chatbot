"""
Chunking Service - Phân đoạn văn bản tối ưu cho tiếng Việt
Service này chịu trách nhiệm chia nhỏ văn bản thành các đoạn (chunks) có ý nghĩa để xử lý vector hóa.
"""
import re
import os
from typing import List, Dict, Optional
import logging

from app.services.document_profiler import document_profiler
from app.services.section_parser import section_parser
from app.services.domain_splitter import domain_splitters

logger = logging.getLogger(__name__)


class ChunkingService:
    """Service xử lý phân đoạn văn bản (Text Chunking) với logic tối ưu cho Tiếng Việt và cấu trúc Markdown"""
    
    def __init__(self):
        # Các ký tự ngắt câu tiếng Việt theo độ ưu tiên giảm dần
        self.vietnamese_separators = [
            "\n\n",  # Ngắt đoạn
            "\n",    # Xuống dòng
            ". ",    # Dấu chấm câu
            "! ",    # Dấu chấm than
            "? ",    # Dấu hỏi
            "; ",    # Dấu chấm phẩy
            ": ",    # Dấu hai chấm
            ", ",    # Dấu phẩy
            " ",     # Khoảng trắng (ưu tiên thấp nhất)
        ]
    
    def normalize_vietnamese_text(self, text: str) -> str:
        """
        Chuẩn hóa văn bản tiếng Việt
        
        Logic:
        - Loại bỏ khoảng trắng thừa
        - Chuẩn hóa các dấu xuống dòng lặp lại
        """
        # Gộp nhiều khoảng trắng thành 1
        text = re.sub(r' +', ' ', text)
        
        # Chuẩn hóa xuống dòng: \n\n là ngắt đoạn
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Cắt khoảng trắng đầu/cuối
        text = text.strip()
        
        return text
    
    def _split_into_blocks(self, text: str) -> List[str]:
        """Tách văn bản thành các khối văn bản thường và các khối bảng biểu Markdown"""
        lines = text.split("\n")
        blocks = []
        current_table = []
        current_text = []

        for line in lines:
            # Kiểm tra dòng bảng biểu Markdown (chứa ít nhất 2 ký tự '|')
            is_table_line = line.count("|") >= 2
            
            if is_table_line:
                # Nếu đang có văn bản thường, đóng nó lại và thêm vào blocks
                if current_text:
                    blocks.append("\n".join(current_text))
                    current_text = []
                current_table.append(line)
            else:
                # Nếu đang có bảng biểu, đóng nó lại và thêm vào blocks
                if current_table:
                    blocks.append("\n".join(current_table))
                    current_table = []
                current_text.append(line)

        # Đóng các khối còn sót
        if current_text:
            blocks.append("\n".join(current_text))
        if current_table:
            blocks.append("\n".join(current_table))

        return [b for b in blocks if b.strip()]

    def _split_large_table(self, table_text: str, chunk_size: int) -> List[str]:
        """Chia nhỏ bảng biểu lớn và lặp lại header ở đầu mỗi phần để giữ ngữ cảnh cột"""
        # Loại bỏ các dòng rỗng để tính toán dòng chính xác
        lines = [line for line in table_text.split("\n") if line.strip()]
        if len(lines) < 3:
            return [table_text]
            
        header = lines[0] + "\n" + lines[1]
        header_len = len(header)
        
        # Sử dụng kích thước chunk lớn hơn cho bảng biểu để tránh chia cắt vụn vặt
        table_chunk_size = max(chunk_size, 1800)
        
        # Nếu header quá dài, ta tăng kích thước chunk tương ứng để chứa được header + ít nhất 1 dòng dữ liệu
        if header_len >= table_chunk_size - 150:
            table_chunk_size = header_len + 600
            
        table_chunks = []
        current_chunk_lines = [lines[0], lines[1]]
        current_size = header_len
        
        for line in lines[2:]:
            line_len = len(line) + 1  # tính cả \n
            
            # Nếu thêm dòng này vào vượt quá kích thước chunk, ta đóng chunk cũ
            if current_size + line_len > table_chunk_size:
                # Đảm bảo chunk hiện tại có ít nhất 1 dòng dữ liệu (ngoài header)
                if len(current_chunk_lines) > 2:
                    table_chunks.append("\n".join(current_chunk_lines))
                    current_chunk_lines = [lines[0], lines[1], line]
                    current_size = header_len + line_len
                else:
                    # Nếu chưa có dòng dữ liệu nào, buộc phải đưa dòng này vào chunk hiện tại
                    # để tránh tạo ra chunk chỉ chứa mỗi header rỗng
                    current_chunk_lines.append(line)
                    table_chunks.append("\n".join(current_chunk_lines))
                    current_chunk_lines = [lines[0], lines[1]]
                    current_size = header_len
            else:
                current_chunk_lines.append(line)
                current_size += line_len
                
        if len(current_chunk_lines) > 2:
            table_chunks.append("\n".join(current_chunk_lines))
            
        return table_chunks

    def chunk_text(
        self,
        text: str,
        chunk_size: int = 1024,
        chunk_overlap: int = 20,
        preserve_sentences: bool = True
    ) -> List[Dict]:
        """
        Phân đoạn văn bản thành các chunks có chồng lấp (overlap)
        
        Args:
            text: Văn bản đầu vào
            chunk_size: Kích thước tối đa của mỗi chunk (tính theo ký tự)
            chunk_overlap: Số ký tự lặp lại giữa chunk trước và chunk sau (giữ ngữ cảnh)
            preserve_sentences: Cố gắng giữ nguyên câu trọn vẹn (True)
        
        Returns:
            List[Dict]: Danh sách các chunks kèm metadata
        """
        if not text or not text.strip():
            return []
        
        # Bước 1: Chuẩn hóa văn bản
        text = self.normalize_vietnamese_text(text)
        
        chunks = []
        current_chunk = ""
        current_size = 0
        chunk_index = 0
        
        # Bước 2: Tách văn bản thành các khối văn bản thường và các khối bảng biểu Markdown
        blocks = self._split_into_blocks(text)
        
        segments = []
        for block in blocks:
            # Nếu là bảng biểu Markdown (nhận diện bằng ký tự '|')
            if "|" in block:
                if len(block) <= chunk_size:
                    # Giữ nguyên cả bảng làm 1 segment
                    segments.append(block)
                else:
                    # Bảng quá dài -> chia nhỏ bảng biểu và lặp lại header
                    table_parts = self._split_large_table(block, chunk_size)
                    segments.extend(table_parts)
            else:
                # Khối văn bản thường: dùng chia đệ quy tiếng Việt
                segments.extend(self._split_recursive(block, self.vietnamese_separators, chunk_size))
        
        # Bước 3: Ghép các segments thành chunk hoàn chỉnh
        for segment in segments:
            segment_len = len(segment)
            
            # Segment là bảng biểu hoặc một phần bảng biểu (chứa '|')
            is_table_seg = "|" in segment
            
            # Trường hợp 1: Segment bảng biểu -> Ta ưu tiên xuất bản thành chunk độc lập để bảo vệ cấu trúc
            if is_table_seg:
                # Lưu chunk hiện tại trước
                if current_chunk:
                    chunks.append(self._create_chunk_dict(current_chunk.strip(), chunk_index))
                    chunk_index += 1
                    current_chunk = ""
                    current_size = 0
                
                # Thêm bảng biểu trực tiếp thành chunk độc lập
                chunks.append(self._create_chunk_dict(segment.strip(), chunk_index))
                chunk_index += 1
                continue
            
            # Trường hợp 2: Segment đơn lẻ đã lớn hơn chunk_size -> Buộc phải cắt đôi
            if segment_len > chunk_size:
                if current_chunk:
                    chunks.append(self._create_chunk_dict(current_chunk.strip(), chunk_index))
                    chunk_index += 1
                    current_chunk = ""
                    current_size = 0
                
                # Cắt segment dài thành nhiều chunks nhỏ
                forced_chunks = self._force_split(segment, chunk_size, chunk_overlap)
                for fc in forced_chunks:
                    chunks.append(self._create_chunk_dict(fc, chunk_index))
                    chunk_index += 1
                continue
            
            # Trường hợp 3: Nếu cộng thêm segment vào sẽ vượt quá chunk_size -> Ngắt chunk mới
            if current_size + segment_len > chunk_size:
                # Lưu chunk hiện tại
                if current_chunk:
                    chunks.append(self._create_chunk_dict(current_chunk.strip(), chunk_index))
                    chunk_index += 1
                
                # Tạo chunk mới, kèm phần overlap từ chunk cũ
                if chunk_overlap > 0 and current_chunk:
                    overlap_text = self._get_smart_overlap(current_chunk, chunk_overlap)
                    if overlap_text:
                        current_chunk = overlap_text + "\n" + segment if not segment.startswith(("\n", " ")) else overlap_text + segment
                    else:
                        current_chunk = segment
                    current_size = len(current_chunk)
                else:
                    current_chunk = segment
                    current_size = segment_len
            else:
                # Trường hợp 4: Vẫn chứa đủ -> Cộng dồn vào chunk hiện tại
                current_chunk += segment
                current_size += segment_len
        
        # Lưu chunk cuối cùng nếu còn sót
        if current_chunk.strip():
            chunks.append(self._create_chunk_dict(current_chunk.strip(), chunk_index))
        
        logger.info(f"[CHUNKING] Đã tạo {len(chunks)} chunks từ {len(text)} ký tự")
        return chunks
    
    def _split_recursive(
        self,
        text: str,
        separators: List[str],
        chunk_size: int
    ) -> List[str]:
        """
        Hàm đệ quy chia nhỏ văn bản dựa trên danh sách separator ưu tiên
        """
        # Điều kiện dừng: Hết separator hoặc text đã đủ nhỏ
        if not separators or len(text) <= chunk_size:
            return [text]
        
        separator = separators[0]
        remaining_separators = separators[1:]
        
        # Tách theo separator hiện tại
        splits = text.split(separator)
        
        # Tái tạo lại các phần string kèm separator (để không mất dấu câu)
        segments = []
        for i, split in enumerate(splits):
            if i < len(splits) - 1:
                segments.append(split + separator)
            else:
                segments.append(split)
        
        # Tiếp tục đệ quy cho từng phần nếu nó vẫn quá dài
        final_segments = []
        for seg in segments:
            if len(seg) > chunk_size and remaining_separators:
                final_segments.extend(
                    self._split_recursive(seg, remaining_separators, chunk_size)
                )
            else:
                final_segments.append(seg)
        
        return final_segments
    
    def _force_split(
        self,
        text: str,
        chunk_size: int,
        overlap: int
    ) -> List[str]:
        """
        Cắt văn bản thông minh khi vượt quá chunk_size và không có dấu ngắt câu lớn.
        Đảm bảo không bị cắt đôi từ (Word Mutilation) ở cả điểm kết thúc và điểm bắt đầu (overlap).
        """
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            if start + chunk_size >= text_len:
                chunks.append(text[start:])
                break
                
            # Dự kiến điểm kết thúc
            end = start + chunk_size
            
            # Quét ngược từ end để tìm khoảng trắng hoặc xuống dòng gần nhất
            # Giới hạn quét ngược tối đa 30 ký tự để tránh chunk quá ngắn
            scan_limit = max(start, end - 30)
            break_point = end
            for i in range(end - 1, scan_limit - 1, -1):
                if text[i] in (' ', '\n'):
                    break_point = i
                    break
            
            # Cắt chunk hiện tại
            chunk_content = text[start:break_point].strip()
            if chunk_content:
                chunks.append(chunk_content)
                
            # Tính điểm bắt đầu cho chunk sau (lùi lại overlap từ break_point)
            next_start = max(start, break_point - overlap)
            
            # Ưu tiên tìm ranh giới câu hoặc ranh giới dòng trong vùng overlap [next_start, break_point]
            found_sentence_boundary = False
            for i in range(next_start, break_point):
                if i + 1 < break_point and text[i] in ('.', '?', '!', '\n') and text[i+1] in (' ', '\n'):
                    next_start = i + 1
                    found_sentence_boundary = True
                    break
                    
            if not found_sentence_boundary:
                # Đảm bảo điểm bắt đầu tiếp theo cũng không cắt đôi từ
                while next_start > start and text[next_start] not in (' ', '\n'):
                    next_start -= 1
                if text[next_start] in (' ', '\n'):
                    next_start += 1
                
            start = next_start
            
        return chunks
    
    def _create_chunk_dict(self, text: str, index: int) -> Dict:
        """
        Helper: Tạo cấu trúc dữ liệu chuẩn cho một Chunk
        """
        return {
            "text": text,
            "chunk_index": index,
            "char_count": len(text),
            "word_count": len(text.split())
        }

    def _get_smart_overlap(self, text: str, overlap_limit: int) -> str:
        """
        Lấy phần overlap thông minh từ cuối đoạn văn bản text:
        - Quét ngược tìm dấu ngắt câu hoặc ngắt dòng gần nhất trong phạm vi overlap_limit.
        - Nếu tìm thấy, lấy phần văn bản từ sau dấu ngắt câu đó.
        - Nếu không tìm thấy ngắt câu sạch, ta quét ngược từ điểm bắt đầu (len(text) - overlap_limit)
          về phía đầu văn bản để tìm khoảng trắng hoặc xuống dòng gần nhất, giúp lấy trọn vẹn từ đầu tiên.
        """
        if not text or overlap_limit <= 0:
            return ""
            
        text_len = len(text)
        if text_len <= overlap_limit:
            return text
            
        start_idx = text_len - overlap_limit
        candidate_text = text[start_idx:]
        
        # 1. Tìm dấu ngắt câu lớn từ cuối candidate_text ngược lên đầu
        best_break = -1
        for i in range(len(candidate_text) - 1, -1, -1):
            char = candidate_text[i]
            if char == '\n':
                best_break = i
                break
            if i < len(candidate_text) - 1 and char in ('.', ';', ':', '!', '?') and candidate_text[i+1] == ' ':
                best_break = i + 1
                break
                
        if best_break != -1:
            overlap_part = candidate_text[best_break:].strip()
            if len(overlap_part) > 10 and any(c.isalnum() for c in overlap_part):
                return overlap_part
                
        # 2. Fallback: Lấy trọn vẹn cụm từ chuyển tiếp bằng cách lùi start_idx về khoảng trắng/xuống dòng gần nhất
        curr_idx = start_idx
        while curr_idx > 0 and text[curr_idx] not in (' ', '\n'):
            curr_idx -= 1
            
        if curr_idx < text_len and text[curr_idx] in (' ', '\n'):
            curr_idx += 1
            
        overlap_part = text[curr_idx:].strip()
        if len(overlap_part) > 5 and any(c.isalnum() for c in overlap_part):
            return overlap_part
            
        return ""

    def _split_by_sentences(self, text: str) -> List[str]:
        """
        Chia nhỏ văn bản thành các câu dựa trên các dấu ngắt câu tiếng Việt
        """
        # Tránh split ở các ký hiệu viết tắt như "QĐ-ĐH", "QĐ-ĐHSPHN", "tp.", "P.", "TS."
        sentence_end = re.compile(r'(?<=[\.\?\!;])\s+')
        parts = sentence_end.split(text)
        return [p.strip() for p in parts if p.strip()]

    def _is_lead_line(self, line: str) -> bool:
        """Kiểm tra xem dòng văn bản có phải dòng dẫn nhập (kết thúc bằng : hoặc chứa từ khóa dẫn) hay không"""
        line_str = line.strip()
        if not line_str:
            return False
        if line_str.endswith(":"):
            return True
        if re.search(r'(như sau|sau đây|dưới đây)[:\.]\s*$', line_str, re.IGNORECASE):
            return True
        return False

    def _split_legal_hierarchy(
        self, 
        content: str, 
        context_prefix: str, 
        child_size: int
    ) -> List[str]:
        """
        Chia nhỏ nội dung của một Điều (hoặc mục pháp lý) theo phân cấp cấu trúc:
        Khoản -> Điểm -> Câu -> Ký tự.
        Đồng thời bảo vệ bảng biểu Markdown nếu có.
        Gom các block con lại sao cho mỗi child chunk gần với child_size và luôn đính kèm context_prefix.
        """
        # Tiền xử lý gộp các dòng đánh số bị ngắt dòng vật lý do parser
        raw_lines = content.split('\n')
        processed_lines = []
        skip_next = False
        
        # Regex nhận diện ký tự đánh số/khoản/điểm đơn độc bị ngắt dòng
        isolated_num_pattern = re.compile(r'^\s*(?:\d+|[a-zđ]|Khoản\s+\d+)[\.\):\-\*•]\s*$', re.IGNORECASE)
        
        for idx in range(len(raw_lines)):
            if skip_next:
                skip_next = False
                continue
                
            line = raw_lines[idx]
            line_strip = line.strip()
            
            if isolated_num_pattern.match(line_strip) and idx + 1 < len(raw_lines):
                next_line = raw_lines[idx + 1]
                # Gộp dòng hiện tại với dòng tiếp theo
                combined_line = line.rstrip('\r\n') + " " + next_line.lstrip()
                processed_lines.append(combined_line)
                skip_next = True
            else:
                processed_lines.append(line)
                
        content = '\n'.join(processed_lines)

        # Chia thành các block lớn (văn bản thường hoặc bảng biểu)
        initial_blocks = self._split_into_blocks(content)
        
        # Regex nhận diện các cấu trúc pháp lý (nới lỏng khoảng trắng)
        clause_pattern = re.compile(r'^\s*(?:\d+|Khoản\s+\d+)[:\.]\s*')
        point_header_pattern = re.compile(r'^\s*[a-zđ]\)\s*', re.IGNORECASE)  # Ví dụ: a), b), đ)
        bullet_pattern = re.compile(r'^\s*[-+•\*]\s*')
        
        items = []
        active_clause_hdr = ""
        active_point_hdr = ""
        
        # Kích thước tối đa cho phần content của chunk (không tính độ dài prefix)
        max_chunk_content_size = max(100, child_size - len(context_prefix) - 5)
        
        # Ngưỡng an toàn để gộp danh sách tránh bị bẻ vụn
        SAFE_LIST_LIMIT = max(800, child_size * 2)
        
        # Danh sách các dòng dẫn nhập chưa được liên kết với con nào
        # Mỗi phần tử dạng: (level, text, context_headers)
        pending_leads = []
        
        def flush_pending_leads(target_level=None):
            """Đưa các dòng dẫn nhập đang chờ vào items dưới dạng item độc lập nếu chúng không có con ở cấp thấp hơn"""
            nonlocal pending_leads
            remaining_leads = []
            for lvl, text_val, hdrs in pending_leads:
                if target_level is None or lvl >= target_level:
                    add_refined_item(text_val, hdrs, lvl, is_lead_only=True)
                else:
                    remaining_leads.append((lvl, text_val, hdrs))
            pending_leads = remaining_leads

        def add_refined_item(text_val, context_hdrs, lvl, is_lead_only=False):
            """Chia nhỏ câu nếu vượt quá max_chunk_content_size và đưa vào items"""
            if len(text_val) <= max_chunk_content_size:
                items.append({
                    "text": text_val,
                    "context_headers": context_hdrs,
                    "level": lvl,
                    "is_lead_only": is_lead_only
                })
            else:
                sentences = self._split_by_sentences(text_val)
                for sent in sentences:
                    sent = sent.strip()
                    if not sent:
                        continue
                    if len(sent) <= max_chunk_content_size:
                        items.append({
                            "text": sent,
                            "context_headers": context_hdrs,
                            "level": lvl,
                            "is_lead_only": is_lead_only
                        })
                    else:
                        forced = self._force_split(sent, max_chunk_content_size, overlap=0)
                        for fc in forced:
                            fc = fc.strip()
                            if fc:
                                items.append({
                                    "text": fc,
                                    "context_headers": context_hdrs,
                                    "level": lvl,
                                    "is_lead_only": is_lead_only
                                })

        i = 0
        while i < len(initial_blocks):
            block = initial_blocks[i].strip()
            if not block:
                i += 1
                continue
                
            # Nếu là bảng biểu
            if "|" in block:
                lead_line = ""
                # Lấy dòng dẫn nhập gần nhất đang chờ trong pending_leads
                if pending_leads:
                    lead_line = pending_leads[-1][1]
                    pending_leads.pop()
                elif items:
                    # Fallback kiểm tra item cuối cùng có phải là câu dẫn nhập cấp cao không
                    last_item = items[-1]
                    if last_item.get("is_lead_only") or (not last_item["context_headers"] and self._is_lead_line(last_item["text"])):
                        lead_line = last_item["text"]
                        items.pop()
                        
                # Chia nhỏ bảng nếu kích thước vượt giới hạn
                if len(block) <= max_chunk_content_size:
                    items.append({
                        "text": block,
                        "context_headers": [lead_line] if lead_line else [],
                        "level": 2,
                        "is_lead_only": False
                    })
                else:
                    table_parts = self._split_large_table(block, max_chunk_content_size)
                    for part in table_parts:
                        items.append({
                            "text": part,
                            "context_headers": [lead_line] if lead_line else [],
                            "level": 2,
                            "is_lead_only": False
                        })
            else:
                # Xử lý khối văn bản thường: tách thành các dòng và phân loại phân cấp
                lines = block.split('\n')
                for line in lines:
                    line_strip = line.strip()
                    if not line_strip:
                        continue
                        
                    # 1. Xác định level của dòng
                    if clause_pattern.match(line_strip):
                        lvl = 1
                        # Chuẩn bị đổi sang Khoản mới -> flush các lead đang chờ của Khoản cũ
                        flush_pending_leads(1)
                        active_clause_hdr = line_strip
                        active_point_hdr = ""
                    elif point_header_pattern.match(line_strip):
                        lvl = 2
                        flush_pending_leads(2)
                        active_point_hdr = line_strip
                    elif bullet_pattern.match(line_strip):
                        lvl = 3
                    else:
                        # Dòng thường
                        if active_point_hdr:
                            lvl = 3
                        elif active_clause_hdr:
                            lvl = 2
                        else:
                            lvl = 1

                    # 2. Xác định context_headers kế thừa từ cấp trên
                    hdrs = []
                    if lvl == 2:
                        if active_clause_hdr:
                            hdrs.append(active_clause_hdr)
                    elif lvl == 3:
                        if active_clause_hdr:
                            hdrs.append(active_clause_hdr)
                        if active_point_hdr:
                            hdrs.append(active_point_hdr)

                    # 3. Kiểm tra xem dòng có phải là dòng dẫn nhập (lead)
                    is_lead = self._is_lead_line(line_strip)
                    
                    if is_lead:
                        # Lưu vào hàng đợi pending để làm ngữ cảnh cho con, tránh tạo chunk mồ côi
                        pending_leads.append((lvl, line_strip, hdrs))
                    else:
                        # Giải phóng các lead cấp cao hơn đang chờ vì đã tìm thấy dòng con kế thừa
                        pending_leads = [lead for lead in pending_leads if lead[0] >= lvl]
                        add_refined_item(line_strip, hdrs, lvl, is_lead_only=False)
            i += 1

        # Dọn dẹp nốt các dòng dẫn nhập còn tồn đọng ở cuối tài liệu
        flush_pending_leads()

        # Hàm dựng text cho một nhóm items kèm theo các header ngữ cảnh cha
        def get_chunk_text(items_list):
            if not items_list:
                return ""
            first_item = items_list[0]
            prefix_parts = []
            for hdr in first_item["context_headers"]:
                prefix_parts.append(hdr)
            prefix = "\n".join(prefix_parts) + "\n" if prefix_parts else ""
            content_text = "\n\n".join([item["text"] for item in items_list])
            return prefix + content_text

        # Gom cụm các item thành các child chunks
        child_chunks = []
        current_chunk_items = []
        
        for item in items:
            test_items = current_chunk_items + [item]
            test_text = get_chunk_text(test_items)
            
            # Kiểm tra xem item mới và item cuối cùng trong chunk hiện tại có chung ngữ cảnh trực tiếp hay không
            is_same_list_group = False
            if current_chunk_items:
                last_item = current_chunk_items[-1]
                # Cùng chung cha trực tiếp gần nhất
                if last_item["context_headers"] and item["context_headers"]:
                    if last_item["context_headers"][-1] == item["context_headers"][-1]:
                        is_same_list_group = True
                # Hoặc item mới là con trực tiếp của item liền trước
                elif last_item["text"] in item["context_headers"]:
                    is_same_list_group = True
            
            if len(test_text) <= max_chunk_content_size or not current_chunk_items:
                current_chunk_items.append(item)
            elif is_same_list_group and len(test_text) <= SAFE_LIST_LIMIT:
                # Gộp vượt ngưỡng thông thường vì cùng nhóm danh sách và dưới giới hạn an toàn
                current_chunk_items.append(item)
            else:
                # Xuất bản chunk hiện tại
                chunk_content = get_chunk_text(current_chunk_items)
                child_chunks.append(context_prefix + "\n" + chunk_content)
                # Bắt đầu chunk mới
                current_chunk_items = [item]
                
        if current_chunk_items:
            chunk_content = get_chunk_text(current_chunk_items)
            child_chunks.append(context_prefix + "\n" + chunk_content)
            
        return child_chunks

    def _split_general_hierarchy(
        self, 
        content: str, 
        context_prefix: str, 
        child_size: int,
        separators: List[str],
        overlap: int,
        min_chunk_size: int = 150
    ) -> List[str]:
        """
        Chia nhỏ nội dung của general/financial section.
        Đồng thời bảo vệ bảng biểu Markdown.
        Tự động đính kèm context_prefix và hậu xử lý gộp các chunk quá ngắn.
        """
        initial_blocks = self._split_into_blocks(content)
        
        refined_blocks = []
        max_chunk_content_size = max(100, child_size - len(context_prefix) - 5)
        
        for block in initial_blocks:
            block = block.strip()
            if not block:
                continue
                
            if "|" in block:
                # Bảng biểu
                if len(block) <= max_chunk_content_size:
                    refined_blocks.append(block)
                else:
                    table_parts = self._split_large_table(block, max_chunk_content_size)
                    refined_blocks.extend(table_parts)
                continue
                
            # Văn bản thường -> chia đệ quy
            if len(block) <= max_chunk_content_size:
                refined_blocks.append(block)
            else:
                sub_segs = self._split_recursive(block, separators, max_chunk_content_size)
                
                # Gom sub_segs của block này thành các đoạn văn có kích thước phù hợp
                temp_block_chunks = []
                curr_seg_parts = []
                curr_seg_len = 0
                
                for seg in sub_segs:
                    seg_len = len(seg)
                    if seg_len > max_chunk_content_size:
                        # Buộc phải cắt cứng
                        if curr_seg_parts:
                            temp_block_chunks.append("".join(curr_seg_parts))
                            curr_seg_parts = []
                            curr_seg_len = 0
                        forced = self._force_split(seg, max_chunk_content_size, overlap)
                        temp_block_chunks.extend([fc.strip() for fc in forced if fc.strip()])
                    elif curr_seg_len + seg_len <= max_chunk_content_size:
                        curr_seg_parts.append(seg)
                        curr_seg_len += seg_len
                    else:
                        if curr_seg_parts:
                            temp_block_chunks.append("".join(curr_seg_parts))
                        
                        # Tạo overlap thông minh giữa các segment của cùng một khối văn bản
                        if overlap > 0 and curr_seg_parts:
                            last_part = curr_seg_parts[-1]
                            overlap_text = self._get_smart_overlap(last_part, overlap)
                            if overlap_text:
                                curr_seg_parts = [overlap_text, seg]
                                curr_seg_len = len(overlap_text) + seg_len
                            else:
                                curr_seg_parts = [seg]
                                curr_seg_len = seg_len
                        else:
                            curr_seg_parts = [seg]
                            curr_seg_len = seg_len
                            
                if curr_seg_parts:
                    temp_block_chunks.append("".join(curr_seg_parts))
                    
                refined_blocks.extend(temp_block_chunks)
                        
        # Gom refined_blocks thành các child chunks tạm thời
        temp_chunks = []
        current_chunk_parts = []
        current_len = 0
        
        for block in refined_blocks:
            block = block.strip()
            if not block:
                continue
            block_len = len(block)
            is_table = "|" in block
            
            # Nếu gặp bảng biểu, ưu tiên xuất bản chunk hiện tại trước
            if is_table:
                if current_chunk_parts:
                    temp_chunks.append("\n\n".join(current_chunk_parts))
                    current_chunk_parts = []
                    current_len = 0
                temp_chunks.append(block)
                continue
                
            if current_len + block_len + (2 if current_chunk_parts else 0) <= max_chunk_content_size:
                current_chunk_parts.append(block)
                current_len += block_len + (2 if len(current_chunk_parts) > 1 else 0)
            else:
                if current_chunk_parts:
                    temp_chunks.append("\n\n".join(current_chunk_parts))
                
                # Vì các đoạn văn trong refined_blocks đã tự tạo overlap khi split đệ quy rồi,
                # ở đây khi gom các đoạn lớn lại với nhau, ta không cần tạo thêm overlap chồng chéo nữa.
                current_chunk_parts = [block]
                current_len = block_len
                    
        if current_chunk_parts:
            temp_chunks.append("\n\n".join(current_chunk_parts))
            
        # Hậu xử lý gộp các chunk ngắn (< min_chunk_size)
        final_chunks_content = []
        for tc in temp_chunks:
            tc = tc.strip()
            if not tc:
                continue
            # Bảng biểu luôn được giữ nguyên, không gộp
            if "|" in tc:
                final_chunks_content.append(tc)
                continue
                
            if not final_chunks_content:
                final_chunks_content.append(tc)
            else:
                last_idx = len(final_chunks_content) - 1
                # Nếu chunk cuối cùng là bảng biểu, không gộp vào bảng
                if "|" in final_chunks_content[last_idx]:
                    final_chunks_content.append(tc)
                elif len(final_chunks_content[last_idx]) < min_chunk_size or len(tc) < min_chunk_size:
                    # Gộp chunk ngắn
                    final_chunks_content[last_idx] = final_chunks_content[last_idx] + "\n\n" + tc
                else:
                    final_chunks_content.append(tc)
                    
        # Nếu sau khi gộp, vẫn còn chunk cuối cùng bị ngắn (và có nhiều hơn 1 chunk)
        if len(final_chunks_content) > 1:
            last_idx = len(final_chunks_content) - 1
            if len(final_chunks_content[last_idx]) < min_chunk_size and "|" not in final_chunks_content[last_idx] and "|" not in final_chunks_content[last_idx - 1]:
                final_chunks_content[last_idx - 1] = final_chunks_content[last_idx - 1] + "\n\n" + final_chunks_content[last_idx]
                final_chunks_content.pop(last_idx)
                
        # Thêm context_prefix vào đầu từng chunk
        child_chunks = []
        for fcc in final_chunks_content:
            if context_prefix:
                child_chunks.append(context_prefix + "\n" + fcc)
            else:
                child_chunks.append(fcc)
                
        return child_chunks

    def _parse_markdown_sections(self, text: str) -> List[Dict]:
        """
        Bộ phân tích section đa luồng:
        1. Nếu có Markdown heading (#, ##) -> Dùng Markdown parser
        2. Nếu có pattern Chương/Điều -> Dùng Legal parser
        3. Nếu có numbering 1., 1.1, 1.1.1 -> Dùng Numbered parser
        4. Fallback -> Trả về 1 section duy nhất
        """
        if not text or not text.strip():
            return []
            
        lines = text.split("\n")
        
        # 1. Kiểm tra Markdown heading
        has_markdown = False
        markdown_re = re.compile(r'^(#{1,6})\s+(.+)$')
        for line in lines:
            if markdown_re.match(line):
                has_markdown = True
                break
                
        if has_markdown:
            logger.info("[CHUNKING] Tài liệu được phân tích bằng Markdown parser")
            return self._parse_markdown_sections_classic(text)
            
        # 2. Kiểm tra Legal pattern (Chương / Điều)
        has_legal = False
        chuong_re = re.compile(r'^(\*\*Chương\s+[IVXLCDM\d]+\*\*|^Chương\s+[IVXLCDM\d]+)', re.IGNORECASE)
        dieu_re = re.compile(r'^(\*\*Điều\s+\d+\.?[^\*]*\*\*|^Điều\s+\d+)', re.IGNORECASE)
        for line in lines:
            stripped = line.strip()
            if chuong_re.match(stripped) or dieu_re.match(stripped):
                has_legal = True
                break
                
        if has_legal:
            logger.info("[CHUNKING] Tài liệu được phân tích bằng Legal parser")
            return self._parse_legal_sections(text)
            
        # 3. Kiểm tra Numbered structure (Đánh số 1., 1.1, 1.1.1)
        has_numbered = False
        numbered_re = re.compile(r'^(\*\*|\s)*(\d+\.\d+(?:\.\d+)?)\s+(.+)$')
        numbered_matches_count = 0
        for line in lines:
            if numbered_re.match(line.strip()):
                numbered_matches_count += 1
                if numbered_matches_count >= 2: # ít nhất 2 dòng đánh số phân cấp
                    has_numbered = True
                    break
                    
        if has_numbered:
            logger.info("[CHUNKING] Tài liệu được phân tích bằng Numbered parser")
            return self._parse_numbered_sections(text)
            
        # 4. Fallback
        logger.info("[CHUNKING] Tài liệu được phân tích bằng Fallback parser")
        return self._parse_fallback_sections(text)

    def _parse_markdown_sections_classic(self, text: str) -> List[Dict]:
        """
        Phân tích văn bản Markdown thành các Section dựa trên tiêu đề (#, ##, ###, ...)
        Mỗi Section chứa:
        - heading_path: List[str] (Đường dẫn tiêu đề)
        - text: str (Nội dung của Section)
        """
        lines = text.split("\n")
        sections = []
        current_headers = []
        current_section_text = []
        
        # Regex nhận diện tiêu đề Markdown
        header_pattern = re.compile(r'^(#{1,6})\s+(.+)$')
        
        def save_current_section():
            if current_section_text:
                full_text = "\n".join(current_section_text).strip()
                if full_text:
                    sections.append({
                        "heading_path": list(current_headers),
                        "text": full_text
                    })
                current_section_text.clear()

        for line in lines:
            match = header_pattern.match(line)
            if match:
                # Lưu section trước đó
                save_current_section()
                
                # Cập nhật danh sách tiêu đề hiện tại
                level = len(match.group(1)) # số dấu #
                title = match.group(2).strip()
                
                # Cắt bớt headers cấp thấp hơn hoặc bằng level hiện tại
                current_headers = current_headers[:level - 1]
                # Điền đầy nếu bị nhảy cấp
                while len(current_headers) < level - 1:
                    current_headers.append("")
                current_headers.append(title)
            else:
                current_section_text.append(line)
                
        # Lưu section cuối cùng
        save_current_section()
        
        # Nếu tài liệu không có tiêu đề nào, trả về 1 section duy nhất
        if not sections and text.strip():
            sections.append({
                "heading_path": [],
                "text": text.strip()
            })
            
        return sections

    def _parse_legal_sections(self, text: str) -> List[Dict]:
        """
        Phân tích văn bản pháp quy theo Chương, Mục, Điều
        """
        lines = text.split("\n")
        sections = []
        
        chuong_re = re.compile(r'^(\*\*Chương\s+[IVXLCDM\d]+\*\*|^Chương\s+[IVXLCDM\d]+:?)(.*)$', re.IGNORECASE)
        muc_re = re.compile(r'^(\*\*Mục\s+\d+\*\*|^Mục\s+\d+:?)(.*)$', re.IGNORECASE)
        dieu_re = re.compile(r'^(\*\*Điều\s+\d+\.?[^\*]*\*\*|^Điều\s+\d+\.?)(.*)$', re.IGNORECASE)
        
        current_chuong = ""
        current_muc = ""
        current_dieu = ""
        
        current_section_text = []
        pending_lines = []
        
        def save_current_section():
            if current_section_text:
                full_text = "\n".join(current_section_text).strip()
                if full_text:
                    path = []
                    if current_chuong:
                        path.append(current_chuong)
                    if current_muc:
                        path.append(current_muc)
                    if current_dieu:
                        path.append(current_dieu)
                    sections.append({
                        "heading_path": path,
                        "text": full_text
                    })
                current_section_text.clear()

        for line in lines:
            stripped = line.strip()
            
            match_chuong = chuong_re.match(stripped)
            match_muc = muc_re.match(stripped)
            match_dieu = dieu_re.match(stripped)
            
            if match_chuong:
                save_current_section()
                title = (match_chuong.group(1) + match_chuong.group(2)).replace("**", "").strip()
                current_chuong = title
                current_muc = ""
                current_dieu = ""
                pending_lines.append(line)
            elif match_muc:
                save_current_section()
                title = (match_muc.group(1) + match_muc.group(2)).replace("**", "").strip()
                current_muc = title
                current_dieu = ""
                pending_lines.append(line)
            elif match_dieu:
                save_current_section()
                title = (match_dieu.group(1) + match_dieu.group(2)).replace("**", "").strip()
                current_dieu = title
                # Khi bắt đầu Điều mới, đưa các tiêu đề Chương/Mục đang chờ vào đầu
                if pending_lines:
                    current_section_text.extend(pending_lines)
                    pending_lines = []
                current_section_text.append(line)
            else:
                if not current_section_text and pending_lines:
                    # Nếu có dòng thường nằm ngoài Điều nhưng nằm trong Chương/Mục mới,
                    # ta đưa pending_lines vào và bắt đầu một section
                    current_section_text.extend(pending_lines)
                    pending_lines = []
                current_section_text.append(line)
                
        save_current_section()
        return sections

    def _parse_numbered_sections(self, text: str) -> List[Dict]:
        """
        Phân tích văn bản đánh số phân cấp (1., 1.1, 1.1.1)
        """
        lines = text.split("\n")
        sections = []
        
        # Regex đánh số 1. hoặc 1.1 hoặc 1.1.1
        numbered_re = re.compile(r'^(\*\*|\s)*(\d+\.\d+(?:\.\d+)?|\d+)\.?\s+(.+)$')
        
        current_headers = ["", "", ""]
        current_section_text = []
        
        def save_current_section():
            if current_section_text:
                full_text = "\n".join(current_section_text).strip()
                if full_text:
                    path = [h for h in current_headers if h]
                    sections.append({
                        "heading_path": path,
                        "text": full_text
                    })
                current_section_text.clear()

        for line in lines:
            stripped = line.strip()
            match = numbered_re.match(stripped)
            if match:
                save_current_section()
                num_part = match.group(2)
                title_part = match.group(3).replace("**", "").strip()
                full_title = f"{num_part}. {title_part}"
                
                dots_count = num_part.count(".")
                if dots_count == 0:
                    current_headers = [full_title, "", ""]
                elif dots_count == 1:
                    current_headers = [current_headers[0], full_title, ""]
                else:
                    current_headers = [current_headers[0], current_headers[1], full_title]
                
                current_section_text.append(line)
            else:
                current_section_text.append(line)
                
        save_current_section()
        return sections

    def _parse_fallback_sections(self, text: str) -> List[Dict]:
        """
        Fallback parser: coi cả văn bản là 1 section duy nhất
        """
        return [{
            "heading_path": [],
            "text": text.strip()
        }]

    def _is_junk_chunk(self, text: str) -> bool:
        """Kiểm tra xem đoạn văn bản có phải là rác vô nghĩa hoặc quá ngắn hay không"""
        clean = text.strip()
        if not clean:
            return True
            
        # Loại bỏ nếu không chứa bất kỳ chữ cái hay chữ số nào
        if not any(c.isalnum() for c in clean):
            return True
            
        # Lấy danh sách các từ có chứa chữ/số
        words = [w for w in clean.split() if any(c.isalnum() for c in w)]
        if not words:
            return True
            
        # Nếu tổng số ký tự quá ngắn (< 5)
        if len(clean) < 5:
            if len(clean) == 1:
                return True
            if clean.lower() in ["è", "=", "d", "n", "-", "_", "*", "+", "è\n="]:
                return True
                
        # Nếu chuỗi ngắn (< 25 ký tự) nhưng tất cả các từ trong đó đều chỉ dài 1 ký tự (rác rời rạc như: = D N hoặc è\n=)
        if len(clean) < 25 and all(len(w) <= 1 for w in words):
            return True
            
        return False

    def chunk_document_advanced(
        self,
        text: str,
        filename: str = "",
        document_summary: str = "",
        file_type: str = "general"
    ) -> List[Dict]:
        """
        Chiến lược chunking nâng cấp:
        1. Sử dụng DocumentProfiler cục bộ/rule-based để phát hiện domain, language, structure_type
        2. Sử dụng SectionParser tách thành các logical sections
        3. Sử dụng Domain-Specific Splitter chia nhỏ từng section và bảo vệ bảng biểu/cấu trúc
        4. Áp dụng Parent-Child Policy & giới hạn parent size cap theo domain
        5. Sinh embedding_text và metadata đầy đủ cho các chunks
        """
        if not text or not text.strip():
            return []

        # 1. Profile document
        profile = document_profiler.profile_document(filename, text)
        domain = profile["domain"]
        language = profile["language"]
        structure_type = profile["structure_type"]
        
        # Nếu user truyền file_type cụ thể và không phải general, ưu tiên file_type đó
        if file_type and file_type != "general":
            domain = file_type
            if domain == "legal":
                structure_type = "legal"
            elif domain == "faq":
                structure_type = "faq"

        # Kích thước parent cap và child target theo domain
        parent_caps = {
            "legal": 4000,
            "financial": 5000,
            "academic_technical": 4000,
            "faq": 999999, # standalone
            "administrative": 3000,
            "general": 3000
        }
        parent_cap = parent_caps.get(domain, 3000)

        # 2. Parse sections
        sections = section_parser.parse_sections(text, structure_type)
        
        processed_chunks = []
        chunk_index = 0
        
        # Lấy splitter tương ứng
        splitter = domain_splitters.get(domain, domain_splitters["general"])
        
        for sec in sections:
            sec_text = sec["text"].strip()
            if not sec_text:
                continue
                
            heading_path = sec["heading_path"]
            section_type = sec["section_type"]
            
            # Xây dựng prefix cho context
            meta_prefix_parts = []
            if filename:
                base_name = os.path.basename(filename)
                clean_name, _ = os.path.splitext(base_name)
                meta_prefix_parts.append(clean_name)
            if heading_path:
                meta_prefix_parts.extend(heading_path)
            meta_prefix = f"**{' - '.join(meta_prefix_parts)}**" if meta_prefix_parts else ""

            # Thẻ cờ chất lượng
            quality_flags = []
            if splitter._is_junk_chunk(sec_text):
                quality_flags.append("junk_source")
                
            # Chia nhỏ section này
            child_candidates = splitter.split_section(sec_text, heading_path)
            
            # Parent-Child Policy:
            if domain == "faq" or (len(sec_text) <= parent_cap and len(child_candidates) <= 1):
                # Lưu làm STANDALONE CHUNK
                for cc in child_candidates:
                    chunk_text = cc["text"]
                    is_table = cc.get("is_table", False)
                    
                    emb_text = self._build_embedding_text(
                        text=chunk_text,
                        filename=filename,
                        domain=domain,
                        language=language,
                        heading_path=heading_path,
                        is_table=is_table,
                        table_caption=cc.get("table_caption"),
                        row_range=cc.get("row_range")
                    )
                    
                    processed_chunks.append({
                        "chunk_index": chunk_index,
                        "text": chunk_text,
                        "embedding_text": emb_text,
                        "context_enriched_text": emb_text,  # Tương thích ngược
                        "heading_path": heading_path,
                        "domain": domain,
                        "language": language,
                        "section_type": section_type,
                        "chunk_role": "standalone",
                        "is_parent": False,
                        "parent_chunk_id": None,
                        "is_table": is_table,
                        "table_caption": cc.get("table_caption"),
                        "table_header": cc.get("table_header", []),
                        "row_range": cc.get("row_range"),
                        "quality_flags": quality_flags
                    })
                    chunk_index += 1
            else:
                # Dùng cấu trúc PARENT-CHILD
                # Chia nhỏ sec_text thành các parent groups để không vượt quá parent_cap
                parent_groups = []
                current_parent_parts = []
                current_parent_len = 0
                
                # Gom các child chunks vào các parent groups một cách cân bằng
                child_to_parent_map = {} # map index child candidate -> index parent group
                
                for idx, cc in enumerate(child_candidates):
                    cc_len = len(cc["text"])
                    if current_parent_len + cc_len > parent_cap and current_parent_parts:
                        # Đóng parent group hiện tại
                        parent_groups.append("\n\n".join(current_parent_parts))
                        current_parent_parts = [cc["text"]]
                        current_parent_len = cc_len
                    else:
                        current_parent_parts.append(cc["text"])
                        current_parent_len += cc_len + 2
                    child_to_parent_map[idx] = len(parent_groups)
                    
                if current_parent_parts:
                    parent_groups.append("\n\n".join(current_parent_parts))
                    
                # Thêm parent groups vào processed_chunks trước
                parent_temp_ids = []
                for p_idx, p_text in enumerate(parent_groups):
                    p_prefix = meta_prefix + f" (Part {p_idx+1})" if len(parent_groups) > 1 and meta_prefix else meta_prefix
                    p_full_text = p_prefix + "\n" + p_text if p_prefix else p_text
                    
                    # Capped parent
                    p_full_text = p_full_text[:parent_cap + 200]
                    
                    p_emb_text = self._build_embedding_text(
                        text=p_full_text,
                        filename=filename,
                        domain=domain,
                        language=language,
                        heading_path=heading_path,
                        is_table=False
                    )
                    
                    parent_chunk = {
                        "chunk_index": chunk_index,
                        "text": p_full_text,
                        "embedding_text": p_emb_text,
                        "context_enriched_text": p_emb_text,
                        "heading_path": heading_path,
                        "domain": domain,
                        "language": language,
                        "section_type": section_type,
                        "chunk_role": "parent",
                        "is_parent": True,
                        "parent_chunk_id": None,
                        "is_table": False,
                        "table_caption": None,
                        "table_header": [],
                        "row_range": None,
                        "quality_flags": quality_flags
                    }
                    processed_chunks.append(parent_chunk)
                    parent_temp_ids.append(chunk_index)
                    chunk_index += 1
                    
                # Thêm các child chunks
                for idx, cc in enumerate(child_candidates):
                    chunk_text = cc["text"]
                    is_table = cc.get("is_table", False)
                    parent_group_idx = child_to_parent_map[idx]
                    parent_temp_idx = parent_temp_ids[parent_group_idx]
                    
                    emb_text = self._build_embedding_text(
                        text=chunk_text,
                        filename=filename,
                        domain=domain,
                        language=language,
                        heading_path=heading_path,
                        is_table=is_table,
                        table_caption=cc.get("table_caption"),
                        row_range=cc.get("row_range")
                    )
                    
                    processed_chunks.append({
                        "chunk_index": chunk_index,
                        "text": chunk_text,
                        "embedding_text": emb_text,
                        "context_enriched_text": emb_text,
                        "heading_path": heading_path,
                        "domain": domain,
                        "language": language,
                        "section_type": section_type,
                        "chunk_role": "child",
                        "is_parent": False,
                        "parent_chunk_temp_idx": parent_temp_idx, # temporary link
                        "is_table": is_table,
                        "table_caption": cc.get("table_caption"),
                        "table_header": cc.get("table_header", []),
                        "row_range": cc.get("row_range"),
                        "quality_flags": quality_flags
                    })
                    chunk_index += 1
                    
        return processed_chunks

    def _build_embedding_text(
        self,
        text: str,
        filename: str,
        domain: str,
        language: str,
        heading_path: List[str],
        is_table: bool,
        table_caption: Optional[str] = None,
        row_range: Optional[List[int]] = None
    ) -> str:
        """Sinh embedding_text dựa trên metadata cục bộ mà không gọi LLM"""
        meta_parts = []
        if filename:
            meta_parts.append(f"Document: {os.path.basename(filename)}")
        meta_parts.append(f"Domain: {domain}")
        meta_parts.append(f"Language: {language}")
        if heading_path:
            meta_parts.append(f"Section: {' > '.join(heading_path)}")
        if is_table:
            if table_caption:
                meta_parts.append(f"Table: {table_caption}")
            if row_range:
                meta_parts.append(f"Rows: {row_range[0]}-{row_range[1]}")
                
        prefix = "\n".join(meta_parts) + "\n\n" if meta_parts else ""
        return prefix + text

    def _build_enriched_text(self, text: str, filename: str, summary: str, heading_path: List[str]) -> str:
        """Helper để build text có chứa Rich Context"""
        enrich_parts = []
        if filename:
            base_name = os.path.basename(filename)
            enrich_parts.append(f"Tài liệu: {base_name}")
        if summary:
            enrich_parts.append(f"Tóm tắt: {summary}")
        if heading_path:
            enrich_parts.append(f"Mục: {' > '.join(heading_path)}")
            
        if enrich_parts:
            prefix = "[" + " | ".join(enrich_parts) + "]\n"
            return f"{prefix}Nội dung: {text}"
        return text


# Singleton instance toàn cục
chunking_service = ChunkingService()


