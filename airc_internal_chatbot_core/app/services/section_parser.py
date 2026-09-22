import re
from typing import List, Dict, Any

class SectionParser:
    """
    Phân tích văn bản thành các logical sections trước khi thực hiện chunking.
    Mỗi section bao gồm:
    - section_index: int
    - heading_path: list[str]
    - section_type: "markdown" | "legal_article" | "legal_header" | "numbered" | "faq_pair" | "plain"
    - text: str
    - page_hint: str | None
    - structure_markers: dict
    """
    def __init__(self):
        self.markdown_re = re.compile(r'^(#{1,6})\s+(.+)$')
        self.chuong_re = re.compile(r'^(\*\*Chương\s+[IVXLCDM\d]+\*\*|^Chương\s+[IVXLCDM\d]+:?)(.*)$', re.IGNORECASE)
        self.muc_re = re.compile(r'^(\*\*Mục\s+\d+\*\*|^Mục\s+\d+:?)(.*)$', re.IGNORECASE)
        self.dieu_re = re.compile(r'^(\*\*Điều\s+\d+\.?[^\*]*\*\*|^Điều\s+\d+\.?)(.*)$', re.IGNORECASE)
        self.numbered_re = re.compile(r'^(\*\*|\s)*(\d+\.\d+(?:\.\d+)?|\d+)\.?\s+(.+)$')

    def parse_sections(self, text: str, structure_type: str = "plain") -> List[Dict[str, Any]]:
        if not text or not text.strip():
            return []

        if structure_type == "markdown":
            return self._parse_markdown(text)
        elif structure_type == "legal":
            return self._parse_legal(text)
        elif structure_type == "numbered":
            return self._parse_numbered(text)
        elif structure_type == "faq":
            return self._parse_faq(text)
        else:
            return self._parse_plain(text)

    def _parse_markdown(self, text: str) -> List[Dict[str, Any]]:
        lines = text.split("\n")
        sections = []
        headers_by_level = {}
        current_section_text = []
        section_idx = 0
        
        def current_headers():
            return [headers_by_level[k] for k in sorted(headers_by_level)]

        def save_section():
            nonlocal section_idx
            if current_section_text:
                full_text = "\n".join(current_section_text).strip()
                if full_text:
                    sections.append({
                        "section_index": section_idx,
                        "heading_path": current_headers(),
                        "section_type": "markdown",
                        "text": full_text,
                        "page_hint": None,
                        "structure_markers": {}
                    })
                    section_idx += 1
                current_section_text.clear()

        for line in lines:
            match = self.markdown_re.match(line)
            if match:
                save_section()
                level = len(match.group(1))
                title = match.group(2).strip()
                headers_by_level = {k: v for k, v in headers_by_level.items() if k < level}
                headers_by_level[level] = title
                current_section_text.append(line)
            else:
                current_section_text.append(line)
                
        save_section()
        if not sections and text.strip():
            sections.append({
                "section_index": 0,
                "heading_path": [],
                "section_type": "plain",
                "text": text.strip(),
                "page_hint": None,
                "structure_markers": {}
            })
        return self._merge_heading_only_sections(sections)

    def _merge_heading_only_sections(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Gộp mục chỉ có heading vào section kế tiếp để tránh chunk rỗng/siêu ngắn."""
        if not sections:
            return sections
        merged: List[Dict[str, Any]] = []
        i = 0
        while i < len(sections):
            sec = dict(sections[i])
            sec["heading_path"] = [h for h in sec.get("heading_path", []) if h]
            body = "\n".join(
                ln for ln in sec["text"].split("\n")
                if ln.strip() and not self.markdown_re.match(ln.strip())
            ).strip()
            if not body and i + 1 < len(sections):
                nxt = dict(sections[i + 1])
                nxt["text"] = sec["text"].rstrip() + "\n\n" + nxt["text"]
                nxt_path = [h for h in nxt.get("heading_path", []) if h]
                path = sec["heading_path"]
                nxt["heading_path"] = path + [h for h in nxt_path if h not in path]
                merged.append(nxt)
                i += 2
                continue
            merged.append(sec)
            i += 1
        for idx, sec in enumerate(merged):
            sec["section_index"] = idx
        return merged

    def _parse_legal(self, text: str) -> List[Dict[str, Any]]:
        lines = text.split("\n")
        sections = []
        section_idx = 0
        
        current_chuong = ""
        current_muc = ""
        current_dieu = ""
        
        current_section_text = []
        pending_lines = []
        
        def save_section():
            nonlocal section_idx
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
                        "section_index": section_idx,
                        "heading_path": path,
                        "section_type": "legal_article" if current_dieu else "legal_header",
                        "text": full_text,
                        "page_hint": None,
                        "structure_markers": {
                            "chuong": current_chuong,
                            "muc": current_muc,
                            "dieu": current_dieu
                        }
                    })
                    section_idx += 1
                current_section_text.clear()

        for line in lines:
            stripped = line.strip()
            
            match_chuong = self.chuong_re.match(stripped)
            match_muc = self.muc_re.match(stripped)
            match_dieu = self.dieu_re.match(stripped)
            
            if match_chuong:
                save_section()
                title = (match_chuong.group(1) + match_chuong.group(2)).replace("**", "").strip()
                current_chuong = title
                current_muc = ""
                current_dieu = ""
                pending_lines.append(line)
            elif match_muc:
                save_section()
                title = (match_muc.group(1) + match_muc.group(2)).replace("**", "").strip()
                current_muc = title
                current_dieu = ""
                pending_lines.append(line)
            elif match_dieu:
                save_section()
                title = (match_dieu.group(1) + match_dieu.group(2)).replace("**", "").strip()
                current_dieu = title
                if pending_lines:
                    current_section_text.extend(pending_lines)
                    pending_lines = []
                current_section_text.append(line)
            else:
                if not current_section_text and pending_lines:
                    current_section_text.extend(pending_lines)
                    pending_lines = []
                current_section_text.append(line)
                
        save_section()
        return sections

    def _parse_numbered(self, text: str) -> List[Dict[str, Any]]:
        lines = text.split("\n")
        sections = []
        section_idx = 0
        current_headers = ["", "", ""]
        current_section_text = []
        
        def save_section():
            nonlocal section_idx
            if current_section_text:
                full_text = "\n".join(current_section_text).strip()
                if full_text:
                    path = [h for h in current_headers if h]
                    sections.append({
                        "section_index": section_idx,
                        "heading_path": path,
                        "section_type": "numbered",
                        "text": full_text,
                        "page_hint": None,
                        "structure_markers": {}
                    })
                    section_idx += 1
                current_section_text.clear()

        for line in lines:
            stripped = line.strip()
            match = self.numbered_re.match(stripped)
            if match:
                save_section()
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
                
        save_section()
        return sections

    def _parse_faq(self, text: str) -> List[Dict[str, Any]]:
        lines = text.split("\n")
        sections = []
        section_idx = 0
        current_section_text = []
        
        # Nhận diện Q: hoặc Question:
        faq_q_pattern = re.compile(r'^\s*(Q:|Question:|Hỏi:|Hỏi\s+\d+:)', re.IGNORECASE)
        
        def save_section():
            nonlocal section_idx
            if current_section_text:
                full_text = "\n".join(current_section_text).strip()
                if full_text:
                    heading = ""
                    for line in current_section_text:
                        if line.strip():
                            heading = line.strip()
                            break
                    sections.append({
                        "section_index": section_idx,
                        "heading_path": [heading] if heading else [],
                        "section_type": "faq_pair",
                        "text": full_text,
                        "page_hint": None,
                        "structure_markers": {}
                    })
                    section_idx += 1
                current_section_text.clear()

        for line in lines:
            if faq_q_pattern.match(line.strip()):
                save_section()
                current_section_text.append(line)
            else:
                current_section_text.append(line)
                
        save_section()
        if not sections and text.strip():
            sections.append({
                "section_index": 0,
                "heading_path": [],
                "section_type": "faq_pair",
                "text": text.strip(),
                "page_hint": None,
                "structure_markers": {}
            })
        return sections

    def _parse_plain(self, text: str) -> List[Dict[str, Any]]:
        return [{
            "section_index": 0,
            "heading_path": [],
            "section_type": "plain",
            "text": text.strip(),
            "page_hint": None,
            "structure_markers": {}
        }]

section_parser = SectionParser()
