from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status


class LegalKnowledgeService:
    def __init__(self, knowledge_dir: Path | None = None) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        self.knowledge_dir = knowledge_dir or repo_root / "data" / "legal_knowledge"

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
