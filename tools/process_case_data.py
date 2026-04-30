from __future__ import annotations

import csv
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = DATA_DIR / "processed"
EVIDENCE_DIR = DATA_DIR / "evidence_docs"

IN_TEXT = "\u5165"
OUT_TEXT = "\u51fa"


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    for marker in ("\u200c", "\u200e", "\u202a", "\u202c"):
        text = text.replace(marker, "")
    return text.replace("\xa0", " ").strip()


def excel_serial_to_datetime(value: float) -> datetime:
    return datetime(1899, 12, 30) + timedelta(days=float(value))


def normalize_case_time(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, (int, float)):
        return excel_serial_to_datetime(value).strftime("%Y-%m-%d")
    return clean_text(value)


def safe_filename(text: str, fallback: str) -> str:
    text = clean_text(text)
    text = re.sub(r"[\\/:*?\"<>|]", "_", text)
    text = re.sub(r"\s+", "_", text)
    return text[:80] or fallback


def read_case_workbook() -> tuple[list[dict[str, str]], dict[str, str]]:
    workbook_path = next(DATA_DIR.rglob("*.xlsx"))
    wb = load_workbook(workbook_path, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    header = [clean_text(v) for v in rows[0]]
    records: list[dict[str, str]] = []
    alias_map: dict[str, str] = {}
    in_alias_section = False

    for raw in rows[1:]:
        values = [clean_text(v) for v in raw]
        if values and values[0].startswith("注姓名对应关系"):
            in_alias_section = True

        if in_alias_section:
            alias = values[1] if len(values) > 1 else ""
            real = values[2] if len(values) > 2 else ""
            if alias and real and not real.startswith("("):
                alias_map[alias] = real
            continue

        if not any(values):
            continue
        record = {header[i] if i < len(header) else f"列{i+1}": values[i] for i in range(len(values))}
        if record.get("时间"):
            record["时间"] = normalize_case_time(raw[0])
        records.append(record)

    return records, alias_map


def split_proof_md() -> list[dict[str, str]]:
    proof_path = DATA_DIR / "proof.md"
    text = proof_path.read_text(encoding="utf-8")
    text = text.replace("\xa0", " ")

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    date_pattern = re.compile(r"^\d{4}年.*$", re.MULTILINE)
    evidence_pattern = re.compile(r"^证据(?P<id>\d+-\d+)：(?P<title>.+)$", re.MULTILINE)

    date_matches = list(date_pattern.finditer(text))
    evidence_matches = list(evidence_pattern.finditer(text))
    outputs: list[dict[str, str]] = []

    for idx, match in enumerate(evidence_matches):
        start = match.start()
        end = evidence_matches[idx + 1].start() if idx + 1 < len(evidence_matches) else len(text)
        block = text[start:end].strip()

        current_date = ""
        current_matter = ""
        for date_match in date_matches:
            if date_match.start() <= start:
                current_date = date_match.group(0).strip()
            else:
                break

        context_start = 0
        for date_match in date_matches:
            if date_match.start() <= start:
                context_start = date_match.start()
            else:
                break
        context = text[context_start:start]
        matter_match = re.search(r"证明事项：\s*(.+)", context)
        if matter_match:
            current_matter = matter_match.group(1).strip()

        evidence_id = match.group("id")
        title = match.group("title").strip()
        filename = safe_filename(f"证据{evidence_id}_{title}.md", f"evidence_{idx+1}.md")
        out_path = EVIDENCE_DIR / filename
        content = (
            f"# 证据{evidence_id}：{title}\n\n"
            f"- 案情日期：{current_date}\n"
            f"- 证明事项：{current_matter}\n"
            f"- 来源文件：data/proof.md\n\n"
            f"## 原文\n\n{block}\n"
        )
        out_path.write_text(content, encoding="utf-8")
        outputs.append({"证据编号": evidence_id, "标题": title, "案情日期": current_date, "文件": str(out_path.relative_to(ROOT))})

    index_path = EVIDENCE_DIR / "index.md"
    lines = ["# 证据文档索引", ""]
    for item in outputs:
        lines.append(f"- 证据{item['证据编号']}：{item['标题']} -> `{item['文件']}`")
    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return outputs


def read_xls_with_excel() -> list[dict[str, Any]]:
    import win32com.client as win32

    excel = win32.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False

    records: list[dict[str, Any]] = []
    try:
        for path in DATA_DIR.rglob("TenpayTrades.xls"):
            wb = excel.Workbooks.Open(str(path.resolve()), ReadOnly=True)
            try:
                ws = wb.Worksheets(1)
                data = ws.UsedRange.Value
                if not isinstance(data, tuple):
                    continue
                header = [clean_text(v) for v in data[0]]
                for raw_row in data[1:]:
                    if not any(v is not None and clean_text(v) for v in raw_row):
                        continue
                    row = {header[i]: raw_row[i] if i < len(raw_row) else "" for i in range(len(header))}
                    row["来源文件"] = str(path.relative_to(ROOT))
                    records.append(row)
            finally:
                wb.Close(False)
    finally:
        excel.Quit()
    return records


def parse_transaction_time(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    text = clean_text(value)
    if not text:
        return None
    for fmt in ("%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M:%S%z", "%Y-%m-%d %H:%M:%S"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.replace(tzinfo=None)
        except ValueError:
            pass
    return None


def linear_map_time(value: datetime, raw_start: datetime, raw_end: datetime, case_start: datetime, case_end: datetime) -> datetime:
    if raw_end <= raw_start:
        return case_start
    ratio = (value - raw_start).total_seconds() / (raw_end - raw_start).total_seconds()
    ratio = max(0.0, min(1.0, ratio))
    return case_start + (case_end - case_start) * ratio


def build_time_rules(cleaned: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rules = [
        {
            "规则ID": "R1",
            "适用条件": "王静账户中与罗宇、陈三一等经营方/筹款方的往来",
            "raw_filter": lambda r: r["账户真实姓名"] == "王静" and r["对手真实姓名"] == "王静",
            "案情起点": datetime(2008, 8, 15, 0, 0),
            "案情终点": datetime(2008, 9, 5, 23, 59),
            "说明": "映射为王静等人筹集赔偿、请托调解并推动免予刑责的期间。",
        },
        {
            "规则ID": "R2",
            "适用条件": "王静账户中与何晓初相关假名的往来",
            "raw_filter": lambda r: r["账户真实姓名"] == "王静" and r["对手真实姓名"] == "杨周武之妻何晓初",
            "案情起点": datetime(2008, 8, 15, 0, 0),
            "案情终点": datetime(2008, 9, 5, 23, 59),
            "说明": "映射为通过何晓初收受、转移或关联处理好处费的期间。",
        },
        {
            "规则ID": "R3",
            "适用条件": "王静账户中与张夏天等舞王俱乐部人员的往来",
            "raw_filter": lambda r: r["账户真实姓名"] == "王静" and r["对手假名"] == "张夏天",
            "案情起点": datetime(2008, 9, 6, 10, 0),
            "案情终点": datetime(2008, 9, 6, 18, 30),
            "说明": "映射为调解结案、释放涉案人员当天的资金/人员关联。",
        },
        {
            "规则ID": "R4",
            "适用条件": "杨周武账户流水背景数据",
            "raw_filter": lambda r: r["账户真实姓名"] == "杨周武",
            "案情起点": datetime(2007, 9, 1, 0, 0),
            "案情终点": datetime(2008, 9, 20, 23, 59),
            "说明": "映射为任所期间监管失职、异常资金背景和后续火灾事故前的长周期背景。",
        },
    ]

    for rule in rules:
        matched = [r for r in cleaned if rule["raw_filter"](r) and r["原始交易时间_dt"]]
        if matched:
            times = [r["原始交易时间_dt"] for r in matched]
            rule["原始起点"] = min(times)
            rule["原始终点"] = max(times)
        else:
            rule["原始起点"] = None
            rule["原始终点"] = None
    return rules


def clean_bank_flows(alias_map: dict[str, str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    raw_records = read_xls_with_excel()
    cleaned: list[dict[str, Any]] = []

    for row in raw_records:
        owner_alias = clean_text(row.get("用户侧账号名称"))
        counterparty_alias = clean_text(row.get("对手侧账户名称"))
        direction = clean_text(row.get("借贷类型"))
        amount_fen = row.get("交易金额(分)") or 0
        balance_fen = row.get("账户余额(分)") or 0
        try:
            amount_yuan = round(float(amount_fen) / 100, 2)
        except (TypeError, ValueError):
            amount_yuan = 0.0
        try:
            balance_yuan = round(float(balance_fen) / 100, 2)
        except (TypeError, ValueError):
            balance_yuan = 0.0

        tx_time = parse_transaction_time(row.get("交易时间"))
        record = {
            "来源文件": clean_text(row.get("来源文件")),
            "用户ID": clean_text(row.get("用户ID")),
            "交易单号": clean_text(row.get("交易单号")),
            "账户假名": owner_alias,
            "账户真实姓名": alias_map.get(owner_alias, owner_alias),
            "借贷类型": direction,
            "交易业务类型": clean_text(row.get("交易业务类型")),
            "交易用途类型": clean_text(row.get("交易用途类型")),
            "原始交易时间": tx_time.strftime("%Y-%m-%d %H:%M:%S") if tx_time else clean_text(row.get("交易时间")),
            "原始交易时间_dt": tx_time,
            "交易金额_元": amount_yuan,
            "账户余额_元": balance_yuan,
            "对手方ID": clean_text(row.get("对手方ID")),
            "对手假名": counterparty_alias,
            "对手真实姓名": alias_map.get(counterparty_alias, counterparty_alias),
            "对手侧银行名称": clean_text(row.get("对手侧银行名称")),
            "备注": "；".join(x for x in [clean_text(row.get("备注1")), clean_text(row.get("备注2"))] if x),
            "是否案件映射人物": owner_alias in alias_map or counterparty_alias in alias_map,
            "是否案件核心对手方": counterparty_alias in alias_map,
            "资金方向_按账户": "收入" if direction == IN_TEXT else "支出" if direction == OUT_TEXT else direction,
        }
        cleaned.append(record)

    rules = build_time_rules(cleaned)
    for record in cleaned:
        mapped_time = ""
        rule_id = ""
        note = ""
        tx_time = record["原始交易时间_dt"]
        if tx_time:
            for rule in rules:
                if rule["raw_filter"](record) and rule["原始起点"] and rule["原始终点"]:
                    mapped = linear_map_time(tx_time, rule["原始起点"], rule["原始终点"], rule["案情起点"], rule["案情终点"])
                    mapped_time = mapped.strftime("%Y-%m-%d %H:%M:%S")
                    rule_id = rule["规则ID"]
                    note = rule["说明"]
                    break
        record["映射案情时间"] = mapped_time
        record["时间映射规则"] = rule_id
        record["时间映射说明"] = note

    return cleaned, rules


def write_table_xlsx(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.append(columns)
    for row in rows:
        ws.append([row.get(col, "") for col in columns])
    wb.save(path)


def write_outputs(case_records: list[dict[str, str]], alias_map: dict[str, str], cleaned: list[dict[str, Any]], rules: list[dict[str, Any]], evidence_index: list[dict[str, str]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    alias_rows = [{"假名": k, "案件真实姓名": v} for k, v in sorted(alias_map.items())]
    write_table_xlsx(OUTPUT_DIR / "name_mapping.xlsx", alias_rows, ["假名", "案件真实姓名"])

    bank_columns = [
        "来源文件", "用户ID", "交易单号", "账户假名", "账户真实姓名", "借贷类型", "资金方向_按账户",
        "交易业务类型", "交易用途类型", "原始交易时间", "映射案情时间", "时间映射规则", "时间映射说明",
        "交易金额_元", "账户余额_元", "对手方ID", "对手假名", "对手真实姓名", "对手侧银行名称",
        "备注", "是否案件映射人物", "是否案件核心对手方",
    ]
    public_cleaned = [{k: v for k, v in row.items() if not k.endswith("_dt")} for row in cleaned]
    write_table_xlsx(OUTPUT_DIR / "cleaned_bank_flows.xlsx", public_cleaned, bank_columns)

    relevant = [row for row in public_cleaned if row["是否案件核心对手方"]]
    write_table_xlsx(OUTPUT_DIR / "case_relevant_bank_flows.xlsx", relevant, bank_columns)

    time_rows = []
    for rule in rules:
        time_rows.append(
            {
                "规则ID": rule["规则ID"],
                "适用条件": rule["适用条件"],
                "原始起点": rule["原始起点"].strftime("%Y-%m-%d %H:%M:%S") if rule["原始起点"] else "",
                "原始终点": rule["原始终点"].strftime("%Y-%m-%d %H:%M:%S") if rule["原始终点"] else "",
                "案情起点": rule["案情起点"].strftime("%Y-%m-%d %H:%M:%S"),
                "案情终点": rule["案情终点"].strftime("%Y-%m-%d %H:%M:%S"),
                "说明": rule["说明"],
            }
        )
    write_table_xlsx(OUTPUT_DIR / "time_mapping.xlsx", time_rows, ["规则ID", "适用条件", "原始起点", "原始终点", "案情起点", "案情终点", "说明"])

    case_columns = ["时间", "案件事实", "相关人", "刑罚", "相关证据", "账目往来流水", "电话(拨出)", "电话(接入)"]
    write_table_xlsx(OUTPUT_DIR / "case_timeline.xlsx", case_records, case_columns)

    with (OUTPUT_DIR / "summary.md").open("w", encoding="utf-8") as f:
        f.write("# 数据处理结果摘要\n\n")
        f.write(f"- 拆分证据文档：{len(evidence_index)} 份，目录：`data/evidence_docs/`\n")
        f.write(f"- 假名映射：{len(alias_map)} 条，输出：`data/processed/name_mapping.xlsx`\n")
        f.write(f"- 清洗流水：{len(public_cleaned)} 条，输出：`data/processed/cleaned_bank_flows.xlsx`\n")
        f.write(f"- 案件核心对手方流水：{len(relevant)} 条，输出：`data/processed/case_relevant_bank_flows.xlsx`\n")
        f.write("- 时间映射表：`data/processed/time_mapping.xlsx`\n\n")
        f.write("## 假名映射\n\n")
        for item in alias_rows:
            f.write(f"- {item['假名']} -> {item['案件真实姓名']}\n")
        f.write("\n## 时间映射原则\n\n")
        f.write("原始交易时间不被覆盖；系统新增“映射案情时间”用于图谱时间线和案情展示。\n")


def main() -> None:
    case_records, alias_map = read_case_workbook()
    evidence_index = split_proof_md()
    cleaned, rules = clean_bank_flows(alias_map)
    write_outputs(case_records, alias_map, cleaned, rules, evidence_index)
    print(f"evidence_docs={len(evidence_index)}")
    print(f"alias_mapping={len(alias_map)}")
    print(f"bank_flows={len(cleaned)}")
    print(f"processed_dir={OUTPUT_DIR}")


if __name__ == "__main__":
    main()
