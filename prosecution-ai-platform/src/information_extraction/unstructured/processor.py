from app.schemas.ingestion import PassageItem, Triple


async def extract_unstructured_triples(content: str) -> tuple[list[Triple], list[PassageItem]]:
    """
    非结构化抽取占位实现：
    - 真实场景应调用 LLM 做关系抽取
    - 当前先按句号切分并生成可演进的三元组结构
    """
    triples: list[Triple] = []
    passages: list[PassageItem] = []

    sentences = [x.strip() for x in content.replace("\n", " ").split("。") if x.strip()]
    for idx, sent in enumerate(sentences, start=1):
        triple = Triple(
            subject=f"文本片段{idx}",
            relation="描述",
            object=sent,
        )
        triples.append(triple)
        passages.append(PassageItem(text=sent + "。", triple_index=idx - 1))

    if not triples and content.strip():
        triples.append(Triple(subject="文本片段1", relation="描述", object=content.strip()))
        passages.append(PassageItem(text=content.strip(), triple_index=0))

    return triples, passages
