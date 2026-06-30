"""
Chunking Service - Phân đoạn văn bản tối ưu cho tiếng Việt
Service này chịu trách nhiệm chia nhỏ văn bản thành các đoạn (chunks) có ý nghĩa để xử lý vector hóa.
"""
import re
from typing import List, Dict, Optional
import logging

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
        lines = table_text.split("\n")
        if len(lines) < 3:
            return [table_text]
            
        header = lines[0] + "\n" + lines[1]
        header_len = len(header)
        
        # Nếu header quá dài (gần bằng chunk_size), ta buộc phải split bình thường
        if header_len >= chunk_size - 100:
            return self._force_split(table_text, chunk_size, 50)
            
        table_chunks = []
        current_chunk_lines = [lines[0], lines[1]]
        current_size = header_len
        
        for line in lines[2:]:
            line_len = len(line) + 1  # tính cả \n
            if current_size + line_len > chunk_size:
                # Đóng chunk hiện tại
                table_chunks.append("\n".join(current_chunk_lines))
                # Khởi tạo chunk mới bắt đầu bằng header
                current_chunk_lines = [lines[0], lines[1], line]
                current_size = header_len + line_len
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
                    # Lùi điểm bắt đầu overlap về khoảng trắng gần nhất để tránh cắt ngang từ (Word Mutilation)
                    overlap_start = max(0, len(current_chunk) - chunk_overlap)
                    while overlap_start > 0 and current_chunk[overlap_start] != ' ':
                        overlap_start -= 1
                    # Bỏ qua khoảng trắng nếu có
                    if current_chunk[overlap_start] == ' ':
                        overlap_start += 1
                        
                    overlap_text = current_chunk[overlap_start:]
                    current_chunk = overlap_text + segment
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
        Cắt cứng văn bản (theo ký tự) khi không thể tách theo dấu câu
        """
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunks.append(text[start:end])
            # Tính điểm bắt đầu cho chunk sau (lùi lại overlap)
            start = end - overlap if end < text_len else end
        
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


# Singleton instance toàn cục
chunking_service = ChunkingService()

