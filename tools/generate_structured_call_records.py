from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from openpyxl import Workbook


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "structured"

CALL_COLUMNS = [
    "来源文件",
    "通话ID",
    "主叫号码",
    "主叫假名",
    "主叫真实姓名",
    "被叫号码",
    "被叫假名",
    "被叫真实姓名",
    "通话开始时间",
    "映射案情时间",
    "通话时长_秒",
    "通话类型",
    "事件阶段",
    "链条类型",
    "证据相关性",
    "入图策略",
    "映射置信度",
    "备注",
]

PEOPLE = {
    "张三": ("王静", "13800010001"),
    "李四": ("杨周武", "13800010002"),
    "曾黎": ("何晓初", "13800010003"),
    "老刘": ("刘力飚", "13800010004"),
    "罗宇": ("罗宇", "13800010005"),
    "陈三一": ("陈三一", "13800010006"),
    "张夏天": ("张夏天", "13800010007"),
    "江军": ("江军", "13800010008"),
    "汪春蓉": ("汪春蓉", "13800010009"),
    "赵志高": ("赵志高", "13800010010"),
    "易承桂": ("易承桂", "13800010011"),
    "罗贤涛": ("罗贤涛", "13800010012"),
    "办案民警A": ("办案民警A", "13800010013"),
    "消防联络员": ("消防联络员", "13800010014"),
    "检察联系人": ("检察联系人", "13800010015"),
}


def make_call(
    seq: int,
    caller: str,
    callee: str,
    time: str,
    duration: int,
    stage: str,
    chain: str,
    relevance: str,
    graph: bool,
    confidence: str,
    note: str,
) -> dict[str, Any]:
    caller_name, caller_phone = PEOPLE[caller]
    callee_name, callee_phone = PEOPLE[callee]
    return {
        "来源文件": "synthetic/call_records/cdr.csv",
        "通话ID": f"CALL{seq:04d}",
        "主叫号码": caller_phone,
        "主叫假名": caller,
        "主叫真实姓名": caller_name,
        "被叫号码": callee_phone,
        "被叫假名": callee,
        "被叫真实姓名": callee_name,
        "通话开始时间": time,
        "映射案情时间": time,
        "通话时长_秒": duration,
        "通话类型": "语音通话",
        "事件阶段": stage,
        "链条类型": chain,
        "证据相关性": relevance,
        "入图策略": "graph" if graph else "context",
        "映射置信度": confidence,
        "备注": note,
    }


def build_call_records() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    specs = [
        ("张三", "李四", "2023-08-31 19:18:00", 96, "请托宴请前后", "请托接触链", "支持王静与杨周武形成请托关系", False, "medium", "宴请前确认到场和地点"),
        ("李四", "曾黎", "2023-08-31 19:43:00", 52, "请托宴请前后", "请托接触链", "支持何晓初作为中间联络人", False, "medium", "宴请前短时联络"),
        ("办案民警A", "李四", "2023-10-11 10:02:00", 181, "日常监管汇报", "监管失职背景", "支持民警向所长报告娱乐场所隐患", False, "medium", "娱乐场所无证经营问题汇报"),
        ("办案民警A", "李四", "2024-03-12 15:26:00", 206, "专项行动通报后", "监管失职背景", "支持扫雷行动后仍未督促整改", False, "medium", "专项行动通报后的工作沟通"),
        ("消防联络员", "李四", "2024-06-18 09:35:00", 134, "百日信息会战期间", "监管失职背景", "支持消防隐患和上报链条", False, "medium", "隐患排查沟通"),
        ("江军", "办案民警A", "2024-08-12 02:16:00", 72, "伤害事件报警", "接处警链", "对应接警处登记表", True, "high", "伤者报警"),
        ("办案民警A", "李四", "2024-08-12 02:31:00", 188, "伤害事件报警", "接处警链", "支持所长介入案件处置", True, "high", "民警向所长报告伤害事件"),
        ("张三", "李四", "2024-08-12 08:42:00", 231, "案发后请托", "请托接触链", "支持王静案发后联系杨周武", True, "high", "案发后第一次较长通话"),
        ("张三", "曾黎", "2024-08-12 09:05:00", 164, "案发后请托", "请托接触链", "支持王静通过何晓初转达诉求", True, "high", "请托何晓初帮忙协调"),
        ("曾黎", "李四", "2024-08-12 09:18:00", 93, "案发后请托", "请托接触链", "支持何晓初向杨周武转达", True, "high", "何晓初与杨周武短时通话"),
        ("张三", "罗宇", "2024-08-16 09:56:00", 66, "27万元转账前", "核心行贿链", "与9万元转账前后对应", True, "high", "确认收款账户和备注"),
        ("张三", "陈三一", "2024-08-16 10:04:00", 58, "27万元转账前", "核心行贿链", "与8万元转账前后对应", True, "high", "确认收款账户和备注"),
        ("张三", "张夏天", "2024-08-16 10:09:00", 74, "27万元转账前", "核心行贿链", "与10万元转账前后对应", True, "high", "确认收款账户和备注"),
        ("罗宇", "曾黎", "2024-08-17 15:18:00", 81, "过桥转账前", "核心行贿链", "与罗宇转曾黎9万元对应", True, "high", "转账前确认"),
        ("陈三一", "曾黎", "2024-08-18 09:36:00", 49, "过桥转账前", "核心行贿链", "与陈三一转饶蝶8万元对应", True, "high", "转账前确认"),
        ("张夏天", "曾黎", "2024-08-18 13:52:00", 55, "过桥转账前", "核心行贿链", "与张夏天转周芷10万元对应", True, "high", "转账前确认"),
        ("张三", "曾黎", "2024-08-19 16:12:00", 112, "3万元现金链", "核心行贿链", "与ATM取现前后对应", True, "high", "现金交付前沟通"),
        ("曾黎", "李四", "2024-08-21 10:19:00", 37, "3万元现金链", "核心行贿链", "与现金存入后短信/通话对应", True, "high", "存入后告知"),
        ("李四", "老刘", "2024-08-16 14:24:00", 143, "安排调解", "徇私枉法链", "支持杨周武安排非承办民警调解", True, "high", "安排刘力飚介入调解"),
        ("老刘", "江军", "2024-08-17 11:08:00", 219, "调解接触", "徇私枉法链", "支持刘力飚联系被害方", True, "high", "沟通调解意向"),
        ("老刘", "汪春蓉", "2024-08-17 11:33:00", 132, "调解接触", "徇私枉法链", "支持刘力飚联系被害方", True, "high", "沟通调解意向"),
        ("老刘", "赵志高", "2024-09-05 17:21:00", 177, "赔偿前确认", "徇私枉法链", "与9月6日赔偿款转账前对应", True, "high", "确认赔偿金额和收款"),
        ("李四", "老刘", "2024-09-06 08:57:00", 64, "赔偿当天", "徇私枉法链", "与11万元赔偿款支付对应", True, "high", "赔偿款支付前确认"),
        ("老刘", "江军", "2024-09-06 09:12:00", 71, "赔偿当天", "徇私枉法链", "与江军收款对应", True, "high", "通知收款"),
        ("老刘", "易承桂", "2024-09-06 09:43:00", 59, "赔偿当天", "徇私枉法链", "与易承桂收款对应", True, "high", "通知收款"),
        ("李四", "办案民警A", "2024-09-07 16:20:00", 118, "释放前后", "徇私枉法链", "支持调解结案和释放程序", True, "high", "释放和结案处理沟通"),
        ("张三", "罗贤涛", "2024-09-20 02:44:00", 46, "火灾事故", "事故处置链", "支持火灾事故后经营方内部联系", False, "medium", "事故后内部通知"),
        ("消防联络员", "李四", "2024-09-20 03:18:00", 155, "火灾事故", "事故处置链", "支持事故应急处置通话", False, "medium", "消防事故处置沟通"),
        ("检察联系人", "办案民警A", "2024-09-28 09:40:00", 126, "检察机关立案", "侦查取证链", "支持立案后调取前期材料", False, "medium", "立案后材料调取沟通"),
    ]
    rows = [make_call(index, *spec) for index, spec in enumerate(specs, start=1)]
    return rows, [row for row in rows if row["入图策略"] == "graph"]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CALL_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_xlsx(path: Path, rows: list[dict[str, Any]]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "call_records"
    ws.append(CALL_COLUMNS)
    for row in rows:
        ws.append([row.get(column) for column in CALL_COLUMNS])
    wb.save(path)


def update_summary(all_count: int, core_count: int) -> None:
    path = OUT_DIR / "summary.md"
    text = path.read_text(encoding="utf-8") if path.exists() else "# Structured data bundle\n"
    block = "\n".join(
        [
            "## 电话流水",
            "",
            f"- 全量合成通话记录：{all_count} 条，输出：`cleaned_call_records.csv/xlsx`。",
            f"- 核心案件相关通话记录：{core_count} 条，输出：`case_relevant_call_records.csv/xlsx`。",
            "- 核心通话围绕接处警、请托、27万元转账、3万元现金链、11万元赔偿调解和释放结案；背景通话保留为 RAG 解释材料，不默认入图。",
        ]
    )
    before = text.split("## 电话流水", 1)[0].rstrip()
    path.write_text(f"{before}\n\n{block}\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows, core_rows = build_call_records()
    write_csv(OUT_DIR / "cleaned_call_records.csv", rows)
    write_csv(OUT_DIR / "case_relevant_call_records.csv", core_rows)
    write_xlsx(OUT_DIR / "cleaned_call_records.xlsx", rows)
    write_xlsx(OUT_DIR / "case_relevant_call_records.xlsx", core_rows)
    update_summary(len(rows), len(core_rows))
    print(f"all_call_records={len(rows)}")
    print(f"case_relevant_call_records={len(core_rows)}")


if __name__ == "__main__":
    main()
