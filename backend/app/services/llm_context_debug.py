from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def log_llm_context(call_name: str, *, question: str = "", passages: list[Any] | None = None, extra: dict[str, Any] | None = None) -> None:
    rows = [_normalize_passage(item) for item in (passages or [])]
    payload = {
        "call_name": call_name,
        "question": question,
        "passage_count": len(rows),
        "passages": rows,
        "extra": extra or {},
    }
    log_dir = Path(__file__).resolve().parents[3] / "outputs" / "llm_context_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{_safe_name(call_name)}.json"
    path = log_dir / filename
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[LLM_CONTEXT] {call_name}: {len(rows)} passages -> {path}")
    for row in rows[:12]:
        title = row.get("evidence_title") or row.get("evidence_id") or row.get("doc_id") or "unknown"
        preview = str(row.get("passage") or row.get("text") or "")[:180].replace("\n", " ")
        print(f"[LLM_CONTEXT] - {title}: {preview}")


def _normalize_passage(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return {
            "evidence_id": item.get("evidence_id"),
            "evidence_title": item.get("evidence_title"),
            "doc_id": item.get("doc_id"),
            "score": item.get("score"),
            "passage": item.get("passage") or item.get("text") or item.get("content"),
        }
    return {"passage": str(item)}


def _safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in value)[:80] or "llm"
