"""
Prompt Service - Xây dựng prompts cho RAG
Service này chịu trách nhiệm ghép nối câu hỏi, lịch sử chat và context thành một prompt hoàn chỉnh cho LLM.
"""
from typing import List, Dict, Any, Optional


class PromptService:
    """Service xây dựng và format prompts"""
    
    def build_prompt(
        self,
        question: str,
        grouped_results: List[Dict[str, Any]],
        history: Optional[List[Dict]] = None,
        max_chunk_chars: int = 1200,
        system_prompt: Optional[str] = None # New argument
    ) -> str:
        """
        Xây dựng RAG prompt từ context đã retrieve được
        
        Args:
            question: Câu hỏi của người dùng
            grouped_results: Kết quả tìm kiếm (đã gom nhóm theo dataset)
            history: Lịch sử chat (nếu có)
            max_chunk_chars: Số ký tự tối đa cho mỗi chunk (để tránh context quá dài)
            system_prompt: Prompt hệ thống tùy chỉnh (override default)
        
        Returns:
            str: Prompt hoàn chỉnh để gửi cho LLM
        """
        # Lấy danh sách tên các dataset có trong kết quả
        dataset_names = [
            g.get("dataset_name")
            for g in grouped_results
            if g.get("dataset_name")
        ]
        
        lines: List[str] = []
        
        # Phần 1: System Instruction
        lines.append("Prompt Instruction:")
        lines.append("[Instruction]")
        
        if system_prompt:
             # Use custom system prompt
             lines.append(system_prompt)
        else:
            # Default System Prompt - STRICT RAG MODE
            lines.append(
                "Bạn là Chatbot RAG (Retrieval-Augmented Generation) nội bộ của AIRC. "
                "NHIỆM VỤ: Trả lời câu hỏi DỰA TRÊN TÀI LIỆU được cung cấp trong phần [Knowledge]."
            )
            lines.append(
                "\n🔒 QUY TẮC BẮT BUỘC:\n"
                "1. CHỈ sử dụng thông tin từ phần [Knowledge] bên dưới\n"
                "2. LUÔN cite nguồn: 'Theo tài liệu [TÊN_FILE]: ...'\n"
                "3. NẾU [Knowledge] = '(Không tìm thấy...)' → Trả lời: 'Xin lỗi, tôi không tìm thấy thông tin về [chủ đề] trong tài liệu. Vui lòng kiểm tra lại dataset hoặc upload tài liệu liên quan.'\n"
                "4. KHÔNG được bịa đặt thông tin hoặc dùng kiến thức chung nếu không có trong [Knowledge]"
            )
            lines.append(
                f"\nDatasets hiện có: {', '.join(dataset_names) if dataset_names else '(Chưa có)'}"
            )
        
        # Phần 2: Chat History (Context ngữ cảnh hội thoại)
        if history:
            lines.append("\n[History]")
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                # Format: User: ... / Model: ...
                lines.append(f"{role.capitalize()}: {content}")
            lines.append("")
        
        # Phần 3: Knowledge Context (Thông tin tìm được từ Vector DB)
        lines.append("[Knowledge]")
        
        has_any = False
        
        for group in grouped_results:
            dataset_name = group.get("dataset_name")
            results = group.get("results") or []
            files = group.get("files", [])
            
            # Render if we have results OR files (metadata only query)
            if not dataset_name or (not results and not files):
                continue
            
            has_any = True
            lines.append(f"Dataset: {dataset_name}")
            
            # List available files in this dataset
            files = group.get("files", [])
            if files:
                lines.append(f"Files: {', '.join(files)}")
            
            lines.append(f"Relevant Content:")
            
            # Group chunks by file_name for better organization
            from collections import defaultdict
            chunks_by_file = defaultdict(list)
            
            for r in results:
                text = (r.get("text") or "").strip()
                if not text:
                    continue
                    
                # Cắt ngắn chunk nếu quá dài
                if len(text) > max_chunk_chars:
                    text = text[: max_chunk_chars - 1] + "…"
                
                # CRITICAL: Add file_name to each chunk
                file_name = r.get("file_name", "Unknown File")
                chunks_by_file[file_name].append(text)
            
            # Render chunks grouped by file
            for file_name, texts in chunks_by_file.items():
                lines.append(f"\n  [File: {file_name}]")
                for text in texts:
                    lines.append(f"  - {text}")
        
        if not has_any:
            lines.append("\n⚠️ CẢNH BÁO: Không tìm thấy thông tin liên quan trong tài liệu.")
            lines.append("Nguyên nhân có thể: Dataset trống, file chưa được xử lý, hoặc câu hỏi không liên quan.")
            lines.append("Hãy thông báo người dùng kiểm tra lại dataset/tài liệu.\n")
        
        # Phần 4: Câu hỏi hiện tại
        lines.append("[Question]")
        lines.append(question.strip())
        
        return "\n".join(lines)


# Singleton instance toàn cục
prompt_service = PromptService()
