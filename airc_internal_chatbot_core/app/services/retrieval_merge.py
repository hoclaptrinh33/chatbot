"""Pure retrieval merge helpers (no Qdrant / model imports)."""
from typing import Dict, List, Tuple


def rrf_merge(
    vector_items: List[tuple],
    keyword_items: List[tuple],
    k: int = 60,
) -> List[tuple]:
    scores: Dict[str, float] = {}
    payloads: Dict[str, tuple] = {}

    def consume(items):
        for rank, (chunk, raw_score, origin) in enumerate(items):
            cid = str(chunk.get("_id") or chunk.get("id"))
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
            if cid not in payloads:
                payloads[cid] = (chunk, raw_score, origin)

    consume(vector_items)
    consume(keyword_items)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return [
        (payloads[cid][0], fused, payloads[cid][2], payloads[cid][1])
        for cid, fused in ranked
    ]


def apply_score_threshold(grouped_results: List[Dict], threshold: float) -> None:
    if threshold is None or threshold <= 0:
        return
    for group in grouped_results:
        kept = []
        dropped = []
        for item in group.get("results", []):
            origin = item.get("origin")
            comparable = item.get("vector_score")
            if comparable is None and origin != "keyword":
                raw = float(item.get("score") or 0)
                comparable = raw if raw >= 0.1 else None
            if origin == "keyword" or comparable is None:
                kept.append(item)
            elif comparable >= float(threshold):
                kept.append(item)
            else:
                dropped.append(item)
        # vietnamese-sbert cosine for đúng chủ đề thường ~0.25–0.40; đừng reject hết
        if not kept and dropped:
            dropped.sort(
                key=lambda x: float(x.get("vector_score") or x.get("score") or 0),
                reverse=True,
            )
            kept = dropped[: min(3, len(dropped))]
        group["results"] = kept
