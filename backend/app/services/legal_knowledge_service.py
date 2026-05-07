from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

from app.adapters.algorithm import HippoRagBridge, _safe_sequence
from app.core.config import settings
from app.schemas.analysis import TracePassage, TraceResult


class LegalKnowledgeService:
    def __init__(self, knowledge_dir: Path | None = None) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        self.repo_root = repo_root
        self.knowledge_dir = knowledge_dir or repo_root / "data" / "legal_knowledge"
        self.hipporag = HippoRagBridge()

    def list_sources(self) -> list[dict[str, Any]]:
        return self._read_json("sources.json")

    def get_template_schema(self) -> dict[str, Any]:
        return self._read_json("template_schema.json")

    def get_evidence_type_mapping(self) -> dict[str, Any]:
        return self._read_json("evidence_type_mapping.json")

    def get_alias_resolution_rules(self) -> dict[str, Any]:
        return self._read_json("alias_resolution_rules.json")

    def list_offense_templates(self) -> list[dict[str, Any]]:
        return self._read_json("offense_templates/index.json")

    def list_procedure_flows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for folder_name in ["procedure_flows", "user_knowledge"]:
            folder = self.knowledge_dir / folder_name
            if not folder.exists():
                continue
            for path in sorted(folder.glob("*.md")):
                text = path.read_text(encoding="utf-8")
                title = _title_from_markdown(text) or path.stem
                rows.append({
                    "id": path.stem,
                    "title": title,
                    "kind": folder_name,
                    "relative_path": str(path.relative_to(self.knowledge_dir)).replace("\\", "/"),
                    "size": path.stat().st_size,
                })
        return rows

    def get_procedure_flow(self, knowledge_id: str) -> dict[str, Any]:
        for folder_name in ["procedure_flows", "user_knowledge"]:
            path = self.knowledge_dir / folder_name / f"{_safe_filename(knowledge_id)}.md"
            if path.exists():
                text = path.read_text(encoding="utf-8")
                return {
                    "id": path.stem,
                    "title": _title_from_markdown(text) or path.stem,
                    "kind": folder_name,
                    "content": text,
                    "relative_path": str(path.relative_to(self.knowledge_dir)).replace("\\", "/"),
                }
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Knowledge '{knowledge_id}' not found.")

    def create_procedure_flow(self, title: str, content: str, kind: str = "user_knowledge") -> dict[str, Any]:
        clean_title = title.strip() or _title_from_markdown(content) or "未命名办案知识"
        clean_content = content.strip()
        if not clean_content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="content must not be empty.")
        folder_name = "procedure_flows" if kind == "procedure_flows" else "user_knowledge"
        folder = self.knowledge_dir / folder_name
        folder.mkdir(parents=True, exist_ok=True)
        base = _safe_filename(clean_title)
        path = folder / f"{base}.md"
        index = 2
        while path.exists():
            path = folder / f"{base}_{index}.md"
            index += 1
        text = clean_content if clean_content.lstrip().startswith("#") else f"# {clean_title}\n\n{clean_content}\n"
        path.write_text(text, encoding="utf-8")
        return {
            "id": path.stem,
            "title": clean_title,
            "kind": folder_name,
            "relative_path": str(path.relative_to(self.knowledge_dir)).replace("\\", "/"),
            "size": path.stat().st_size,
        }

    def get_offense_template(self, offense_id: str) -> dict[str, Any]:
        index = self.list_offense_templates()
        item = next((entry for entry in index if entry.get("offense_id") == offense_id), None)
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Offense template '{offense_id}' not found.",
            )

        template_file = item.get("template_file")
        if not template_file:
            return self._build_skeleton_template(item)
        return self._read_json(f"offense_templates/{template_file}")

    def retrieve(self, query: str, offense_id: str | None = None, top_k: int = 8) -> TraceResult:
        docs, doc_titles = self._build_legal_docs(offense_id)
        if not docs:
            return TraceResult(case_id="legal_knowledge", query=query, provider="hipporag_legal", error="法律知识库为空。")

        klass = self.hipporag.load_class()
        config_class = self.hipporag.load_config_class()
        if not klass or not config_class:
            return TraceResult(
                case_id="legal_knowledge",
                query=query,
                provider="hipporag_legal",
                error=self.hipporag.error or "HippoRAG class is unavailable",
            )

        try:
            config = config_class(
                save_dir=str((Path(settings.hipporag_save_dir).parent / "hipporag_legal_knowledge").resolve()),
                llm_name=settings.hipporag_llm_name,
                llm_base_url=settings.hipporag_llm_base_url,
                embedding_model_name=settings.hipporag_embedding_model,
                retrieval_top_k=max(top_k, settings.hipporag_retrieval_top_k),
                qa_top_k=settings.hipporag_qa_top_k,
            )
            hipporag = klass(global_config=config)
            hipporag.index(docs)
            raw_results = _safe_sequence(hipporag.retrieve([query], num_to_retrieve=top_k))
            first = _safe_sequence(raw_results[0] if raw_results else [])
            passages: list[TracePassage] = []
            for rank, item in enumerate(first[:top_k], start=1):
                doc = item[0] if isinstance(item, (tuple, list)) and item else item
                score = item[1] if isinstance(item, (tuple, list)) and len(item) > 1 else 1.0
                text = str(doc)
                title = doc_titles.get(text)
                passages.append(
                    TracePassage(
                        rank=rank,
                        score=float(score) if isinstance(score, (int, float)) else 1.0,
                        passage=text,
                        evidence_id=None,
                        evidence_title=title or "法律知识库",
                    )
                )
            return TraceResult(case_id="legal_knowledge", query=query, provider="hipporag_legal", passages=passages)
        except Exception as exc:  # noqa: BLE001
            return TraceResult(case_id="legal_knowledge", query=query, provider="hipporag_legal", error=str(exc))

    def _read_json(self, relative_path: str) -> Any:
        path = self.knowledge_dir / relative_path
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Legal knowledge file '{relative_path}' not found.",
            )
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Legal knowledge file '{relative_path}' is invalid JSON: {exc}",
            ) from exc

    def _build_legal_docs(self, offense_id: str | None = None) -> tuple[list[str], dict[str, str]]:
        docs: list[str] = []
        titles: dict[str, str] = {}

        def add_doc(title: str, text: str) -> None:
            text = text.strip()
            if not text:
                return
            doc = f"【{title}】\n{text}"
            docs.append(doc)
            titles[doc] = title

        for relative in ["README.md", "sources.json", "evidence_type_mapping.json", "offense_templates/index.json"]:
            path = self.knowledge_dir / relative
            if path.exists():
                add_doc(f"法律知识/{relative}", path.read_text(encoding="utf-8"))

        for folder_name in ["procedure_flows", "user_knowledge"]:
            folder = self.knowledge_dir / folder_name
            if folder.exists():
                for path in sorted(folder.glob("*.md")):
                    add_doc(f"系统先验/{path.stem}", path.read_text(encoding="utf-8"))

        template_ids: list[str] = []
        if offense_id:
            template_ids.append(offense_id)
        else:
            template_ids = [str(item.get("offense_id")) for item in self.list_offense_templates() if item.get("offense_id")]
        for template_id in template_ids:
            try:
                template = self.get_offense_template(template_id)
            except HTTPException:
                continue
            add_doc(
                f"罪名模板/{template.get('name') or template_id}",
                json.dumps(template, ensure_ascii=False, indent=2),
            )

        for path in [self.repo_root / "十四种犯罪的构成要件.md", self.repo_root / "初期进展" / "十四种犯罪的构成要件.md"]:
            if path.exists():
                add_doc(path.name, path.read_text(encoding="utf-8"))

        return docs[: max(settings.hipporag_max_docs, 1)], titles

    @staticmethod
    def _build_skeleton_template(index_item: dict[str, Any]) -> dict[str, Any]:
        priority_elements = index_item.get("priority_elements", [])
        return {
            "schema_version": "0.1.0",
            "offense_id": index_item["offense_id"],
            "name": index_item["name"],
            "category": index_item.get("category"),
            "status": "skeleton",
            "article_hint": index_item.get("article_hint"),
            "legal_sources": [
                "spp_2006_malfeasance_filing_standard",
                "spp_2013_malfeasance_interpretation_1",
                "spp_2016_public_prosecution_evidence_standard",
            ],
            "case_creation_checklist": [
                {
                    "id": f"element.{idx + 1}",
                    "title": element,
                    "required_evidence_types": [],
                }
                for idx, element in enumerate(priority_elements)
            ],
            "evidence_mapping_rules": [],
            "path_recommendation_rules": [],
            "report_outline": [
                {"section": "基础信息聚合", "must_include": ["主体身份", "职权职责"]},
                {"section": "行为事实还原", "must_include": ["客观行为", "关键节点"]},
                {"section": "主观方面推理", "must_include": ["故意/过失", "动机或明知依据"]},
                {"section": "要件核查结论", "must_include": ["证据支撑", "证据缺口", "法律来源"]},
            ],
        }


def _title_from_markdown(text: str) -> str | None:
    for line in str(text or "").splitlines():
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip() or None
    return None


def _safe_filename(value: str) -> str:
    text = re.sub(r"[^\w\u4e00-\u9fa5-]+", "_", str(value or "").strip(), flags=re.UNICODE).strip("_")
    return text[:80] or "knowledge"
