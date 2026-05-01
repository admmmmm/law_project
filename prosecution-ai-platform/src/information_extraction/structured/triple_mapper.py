from app.schemas.ingestion import Triple


def map_rows_to_triples(rows: list[dict[str, str]]) -> list[Triple]:
    """
    将结构化表格的每一行转换为 (S, R, O) 三元组列表。

    规则说明：
    - 优先读取标准字段：subject/relation/object（大小写不敏感）
    - 若缺失则尝试常见中文字段：主体/关系/对象
    - 若仍缺失，使用兜底关系 "关联"，并按行序号生成主体
    """
    triples: list[Triple] = []
    for idx, row in enumerate(rows, start=1):
        normalized = {str(k).strip().lower(): str(v).strip() for k, v in row.items()}

        subject = (
            normalized.get("subject")
            or normalized.get("主体")
            or f"记录{idx}"
        )
        relation = (
            normalized.get("relation")
            or normalized.get("关系")
            or "关联"
        )
        obj = (
            normalized.get("object")
            or normalized.get("对象")
            or normalized.get("value")
            or normalized.get("值")
            or "未知对象"
        )
        triples.append(Triple(subject=subject, relation=relation, object=obj))
    return triples
