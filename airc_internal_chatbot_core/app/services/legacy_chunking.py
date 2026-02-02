import re
from typing import List, Tuple

_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+|\n+')
_CLAUSE_SPLIT_RE = re.compile(r'(?<=[,;:])\s+')

import logging
logger = logging.getLogger(__name__)

def _normalize_text(text: str) -> str:
    text = text.replace("\t", " ")
    text = re.sub(r'[ ]{2,}', ' ', text)
    text = re.sub(r'\n{2,}', '\n', text)
    return text.strip()

def _word_count(text: str) -> int:
    return len(text.split())

def _split_long_text(text: str, max_words: int) -> List[str]:
    parts = _CLAUSE_SPLIT_RE.split(text)
    results = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        words = part.split()
        for i in range(0, len(words), max_words):
            sub = " ".join(words[i:i + max_words]).strip()
            if sub:
                results.append(sub)

    return results


def chunk_text_legacy(
    text: str,
    chunk_size: int = 200, # Default based on word count usually
    chunk_overlap: int = 20,
) -> List[str]:
    """
    Legacy chunking logic ported from airc-internal-chatbot.
    Returns: List[str] (just text chunks, overlap is handled inside but we flattened the output to list of strings)
    Original returns List[(text, overlap_text)], but for vector db we just need the text pieces usually.
    Actually, let's keep the return as list of strings for embedding.
    """
    # Note: Legacy code used logic based on 'words' (split()), not characters.
    # We should respect that if we want exact parity.
    
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("invalid chunk_overlap")

    if not text or not text.strip():
        return []

    text = _normalize_text(text)
    if not text:
        return []

    sentences = _SENTENCE_SPLIT_RE.split(text)

    results: List[str] = []

    current = []
    current_words = 0
    prev_chunk_words: List[str] = []

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue

        sent_words = _word_count(sent)

        # Sentence too long
        if sent_words > chunk_size:
            if current:
                chunk_text_ = " ".join(current).strip()
                # overlap = " ".join(prev_chunk_words[-chunk_overlap:])
                results.append(chunk_text_)
                prev_chunk_words = chunk_text_.split()
                current = []
                current_words = 0

            for part in _split_long_text(sent, chunk_size):
                # overlap = " ".join(prev_chunk_words[-chunk_overlap:]) # Overlap logic was complex in legacy return
                results.append(part)
                prev_chunk_words = part.split()
            continue

        if current_words + sent_words > chunk_size:
            chunk_text_ = " ".join(current).strip()
            # overlap = " ".join(prev_chunk_words[-chunk_overlap:])
            results.append(chunk_text_)
            prev_chunk_words = chunk_text_.split()

            current = []
            current_words = 0

        current.append(sent)
        current_words += sent_words

    if current:
        chunk_text_ = " ".join(current).strip()
        results.append(chunk_text_)

    return results
