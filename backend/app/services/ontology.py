from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EntityProfile:
    label: str
    canonical_label: str
    entity_type: str
    node_id: str
    timestamp: str | None = None


@dataclass(frozen=True)
class RelationProfile:
    label: str
    category: str
    source_types: tuple[str, ...]
    target_types: tuple[str, ...]
    confidence: float
    constrained: bool = True


@dataclass(frozen=True)
class NormalizedTriple:
    subject: EntityProfile
    relation: RelationProfile
    object: EntityProfile
    raw_relation: str
    properties: dict[str, Any]
    timestamp: str | None


class CaseOntology:
    """A lightweight domain ontology for procuratorial investigation graphs.

    It is intentionally conservative: unknown entities and relations are still
    accepted, but they are marked as low-confidence "关联" instead of flowing
    into the graph as unconstrained OpenIE output.
    """

    entity_types = {
        "person",
        "organization",
        "account",
        "amount",
        "time",
        "location",
        "case",
        "evidence",
        "legal_charge",
        "duty_action",
        "communication",
        "fund_flow",
        "event",
        "entity",
    }

    relation_specs: tuple[tuple[tuple[str, ...], RelationProfile], ...] = (
        (("转账", "付款", "收款", "支付", "汇款", "入账", "支出", "收入"), RelationProfile("转账", "fund_flow", ("person", "account", "organization", "entity"), ("person", "account", "organization", "entity"), 0.86)),
        (("金额", "交易金额", "收受金额"), RelationProfile("金额为", "fund_flow", ("person", "account", "organization", "fund_flow", "entity"), ("amount", "entity"), 0.82)),
        (("现金", "取现", "存入", "柜台存款", "ATM"), RelationProfile("现金流转", "fund_flow", ("person", "account", "entity"), ("person", "account", "amount", "entity"), 0.8)),
        (("通话", "短信", "联系", "微信", "拨打"), RelationProfile("联系", "communication", ("person", "account", "organization", "entity"), ("person", "account", "organization", "entity"), 0.8)),
        (("任职", "所长", "副所长", "民警", "工作单位"), RelationProfile("任职于", "duty_identity", ("person", "entity"), ("organization", "entity"), 0.84)),
        (("指派", "安排", "授意", "交办"), RelationProfile("指派/安排", "duty_behavior", ("person", "organization", "entity"), ("person", "duty_action", "event", "entity"), 0.86)),
        (("批准", "审批", "签批", "决定"), RelationProfile("批准/决定", "duty_behavior", ("person", "organization", "entity"), ("case", "event", "duty_action", "evidence", "entity"), 0.84)),
        (("立案",), RelationProfile("立案", "procedure", ("person", "organization", "case", "entity"), ("case", "event", "evidence", "entity"), 0.8)),
        (("拘留",), RelationProfile("拘留", "procedure", ("person", "organization", "case", "entity"), ("person", "case", "event", "entity"), 0.8)),
        (("释放", "解除"), RelationProfile("释放", "procedure", ("person", "organization", "case", "entity"), ("person", "case", "event", "entity"), 0.8)),
        (("调解", "结案", "撤案", "撤销"), RelationProfile("调解/结案", "procedure", ("person", "organization", "case", "entity"), ("case", "event", "duty_action", "entity"), 0.8)),
        (("请托", "宴请", "好处", "徇私"), RelationProfile("请托/利益", "subjective_state", ("person", "organization", "entity"), ("person", "organization", "amount", "event", "entity"), 0.82)),
        (("明知", "故意", "隐瞒", "规避", "反侦察"), RelationProfile("主观认知", "subjective_state", ("person", "organization", "entity"), ("case", "event", "duty_action", "entity"), 0.78)),
        (("发生时间", "时间", "日期"), RelationProfile("发生时间", "temporal", ("person", "organization", "case", "event", "fund_flow", "entity"), ("time", "entity"), 0.72)),
        (("对应证据", "证据", "来源"), RelationProfile("对应证据", "evidence_link", ("person", "organization", "case", "event", "entity"), ("evidence", "entity"), 0.76)),
        (("案件事实", "事实", "涉及", "参与"), RelationProfile("涉及", "case_fact", ("person", "organization", "case", "entity"), ("person", "organization", "case", "event", "entity"), 0.72)),
    )

    def normalize_triple(self, subject: str, relation: str, obj: str, properties: dict[str, Any] | None = None) -> NormalizedTriple:
        props = dict(properties or {})
        timestamp = extract_timestamp(props.get("time") or props.get("mapped_case_time") or props.get("original_time") or subject or obj)
        relation_profile = self.classify_relation(relation)
        subject_profile = self.classify_entity(subject, relation=relation_profile, properties=props, role="subject")
        object_profile = self.classify_entity(obj, relation=relation_profile, properties=props, role="object")
        allowed = self.is_allowed(relation_profile, subject_profile.entity_type, object_profile.entity_type)
        if not allowed:
            relation_profile = RelationProfile("关联", "related", ("entity",), ("entity",), 0.42, constrained=False)
        props.update(
            {
                "raw_relation": relation,
                "relation_category": relation_profile.category,
                "ontology_constrained": allowed,
                "subject_type": subject_profile.entity_type,
                "object_type": object_profile.entity_type,
            }
        )
        return NormalizedTriple(
            subject=subject_profile,
            relation=relation_profile,
            object=object_profile,
            raw_relation=relation,
            properties=props,
            timestamp=timestamp,
        )

    def classify_relation(self, relation: str) -> RelationProfile:
        text = normalize_text(relation)
        for patterns, spec in self.relation_specs:
            if any(pattern in text for pattern in patterns):
                return spec
        return RelationProfile("关联", "related", ("entity",), ("entity",), 0.42, constrained=False)

    def classify_entity(self, label: str, relation: RelationProfile | None = None, properties: dict[str, Any] | None = None, role: str = "") -> EntityProfile:
        clean = normalize_label(label)
        context = f"{clean} {relation.label if relation else ''} {relation.category if relation else ''} {properties or {}}"
        entity_type = self.infer_entity_type(clean, context, role)
        canonical = canonical_label(clean, entity_type, properties or {})
        return EntityProfile(
            label=clean,
            canonical_label=canonical,
            entity_type=entity_type,
            node_id=f"{entity_type}:{stable_key(canonical)}",
            timestamp=extract_timestamp(clean),
        )

    def infer_entity_type(self, label: str, context: str, role: str = "") -> str:
        if not label:
            return "entity"
        if "证据" in label or label.endswith((".md", ".docx", ".pdf", ".xlsx", ".csv")):
            return "evidence"
        if extract_timestamp(label):
            return "time"
        if re.search(r"\d+(?:\.\d+)?\s*(元|万元|人民币)", label) or re.fullmatch(r"\d+(?:\.\d+)?", label):
            return "amount"
        if re.search(r"(账户|银行卡|微信|支付宝|手机号|电话|138\d{8}|账号)", context):
            return "account"
        if re.search(r"(公司|银行|派出所|公安|检察院|法院|政府|委员会|医院|看守所|分局|支行|俱乐部|舞厅)", label):
            return "organization"
        if re.search(r"(罪|案|案件|警情|事故|火灾|调解|结案|释放|拘留|立案)", label) and len(label) > 4:
            return "case" if "案" in label else "event"
        if re.search(r"(徇私枉法|玩忽职守|受贿|故意伤害)", label):
            return "legal_charge"
        if re.search(r"(批准|指派|调解|释放|拘留|立案|撤销|结案|处置)", context):
            return "duty_action" if role == "object" and len(label) > 5 else "person"
        if re.fullmatch(r"[\u4e00-\u9fa5]{2,4}", label) and not re.search(r"(区|市|省|局|所|院|会|部|队)$", label):
            return "person"
        if re.search(r"(路|街|区|市|村|停车场|办公室|舞厅|酒楼)", label):
            return "location"
        if len(label) > 18:
            return "event"
        return "entity"

    def is_allowed(self, relation: RelationProfile, source_type: str, target_type: str) -> bool:
        if not relation.constrained:
            return False
        return _type_allowed(source_type, relation.source_types) and _type_allowed(target_type, relation.target_types)


def _type_allowed(entity_type: str, allowed: tuple[str, ...]) -> bool:
    if "entity" in allowed:
        return True
    if entity_type == "person_or_action":
        return "person" in allowed or "duty_action" in allowed
    return entity_type in allowed


def normalize_label(value: Any) -> str:
    text = normalize_text(value)
    text = re.sub(r"^[：:，,。；;\s]+|[：:，,。；;\s]+$", "", text)
    return text[:120]


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def canonical_label(label: str, entity_type: str, properties: dict[str, Any]) -> str:
    aliases = [
        properties.get("real_name"),
        properties.get("case_name"),
        properties.get("account_alias"),
        properties.get("counterparty_alias"),
    ]
    for alias in aliases:
        alias_text = normalize_label(alias)
        if alias_text and alias_text != label and entity_type in {"person", "account"}:
            return alias_text
    text = re.sub(r"[《》（）()【】\[\]\"'“”]", "", label)
    text = re.sub(r"(先生|女士|所长|民警|警官|证人|被告人|嫌疑人)$", "", text)
    return text or label


def stable_key(value: str) -> str:
    text = normalize_label(value).lower()
    text = re.sub(r"[^\w\u4e00-\u9fa5.-]+", "_", text)
    return text.strip("_")[:96] or "unknown"


def extract_timestamp(value: Any) -> str | None:
    text = normalize_text(value)
    match = re.search(r"((?:19|20)\d{2})[年/-]?(\d{1,2})?(?:[月/-]?(\d{1,2}))?", text)
    if not match:
        return None
    year = match.group(1)
    month = (match.group(2) or "01").zfill(2)
    day = (match.group(3) or "01").zfill(2)
    return f"{year}-{month}-{day}"


CASE_ONTOLOGY = CaseOntology()
