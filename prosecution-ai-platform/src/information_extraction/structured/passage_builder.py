from app.schemas.ingestion import PassageItem, Triple


def build_passages_from_triples(triples: list[Triple]) -> list[PassageItem]:
    """
    将三元组转换为自然语言段落，供 LLM 深度阅读。
    """
    passages: list[PassageItem] = []
    for idx, triple in enumerate(triples):
        sentence = f"{triple.subject} 发生了 {triple.relation} 行为，对象是 {triple.object}。"
        passages.append(PassageItem(text=sentence, triple_index=idx))
    return passages
