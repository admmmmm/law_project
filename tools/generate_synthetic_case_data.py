from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from openpyxl import Workbook


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = DATA_DIR / "processed"


BANK_COLUMNS = [
    "来源文件",
    "用户ID",
    "交易单号",
    "账户假名",
    "账户真实姓名",
    "借贷类型",
    "资金方向_按账户",
    "交易业务类型",
    "交易用途类型",
    "原始交易时间",
    "映射案情时间",
    "时间映射规则",
    "时间映射说明",
    "交易金额_元",
    "账户余额_元",
    "对手方ID",
    "对手假名",
    "对手真实姓名",
    "对手侧银行名称",
    "备注",
    "是否案件映射人物",
    "是否案件核心对手方",
    "链条类型",
    "入图策略",
    "映射置信度",
]

TIMELINE_COLUMNS = ["时间", "案件事实", "相关人", "刑罚", "相关证据", "账目往来流水", "电话(拨出)", "电话(接入)"]


def row(
    seq: int,
    account_alias: str,
    account_name: str,
    direction: str,
    biz_type: str,
    use_type: str,
    time: str,
    amount: float,
    cp_alias: str,
    cp_name: str,
    note: str,
    chain: str,
    strategy: str,
    confidence: str = "high",
    core: bool = False,
    bank: str | None = None,
    balance: float = 0,
) -> dict[str, Any]:
    return {
        "来源文件": f"synthetic/wechat/{account_alias}/TenpayTrades.csv",
        "用户ID": account_alias,
        "交易单号": f"SYN{seq:04d}",
        "账户假名": account_alias,
        "账户真实姓名": account_name,
        "借贷类型": "入" if direction == "收入" else "出",
        "资金方向_按账户": direction,
        "交易业务类型": biz_type,
        "交易用途类型": use_type,
        "原始交易时间": time,
        "映射案情时间": time,
        "时间映射规则": "SYN-0",
        "时间映射说明": "本轮合成数据将案情整体后移，微信交易时间即案情时间。",
        "交易金额_元": round(amount, 2),
        "账户余额_元": round(balance, 2),
        "对手方ID": cp_alias,
        "对手假名": cp_alias,
        "对手真实姓名": cp_name,
        "对手侧银行名称": bank,
        "备注": note,
        "是否案件映射人物": True,
        "是否案件核心对手方": core,
        "链条类型": chain,
        "入图策略": strategy,
        "映射置信度": confidence,
    }


def build_bank_flows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    seq = 1

    def add(*args: Any, **kwargs: Any) -> None:
        nonlocal seq
        rows.append(row(seq, *args, **kwargs))
        seq += 1

    # 1. 核心行贿链：27万元转账 + 3万元现金。
    add("张三", "王静", "收入", "商户结算", "舞厅营收", "2024-08-13 21:40:00", 86000, "舞王歌舞厅", "舞王歌舞厅", "周末营业款结算", "正常经营与消费", "context", bank="中国建设银行")
    add("张三", "王静", "收入", "商户结算", "舞厅营收", "2024-08-14 22:10:00", 124000, "舞王歌舞厅", "舞王歌舞厅", "包厢酒水收入", "正常经营与消费", "context", bank="中国建设银行")
    add("张三", "王静", "收入", "现金存入", "舞厅营收", "2024-08-15 11:20:00", 96000, "现金柜台", "现金柜台", "营业现金缴存", "正常经营与消费", "context", bank="中国建设银行")
    add("张三", "王静", "支出", "微信转账", "往来款", "2024-08-16 10:12:00", 90000, "罗宇", "罗宇", "借款", "核心行贿链", "graph", core=True)
    add("张三", "王静", "支出", "微信转账", "货款", "2024-08-16 10:18:00", 80000, "陈三一", "陈三一", "货款", "核心行贿链", "graph", core=True)
    add("张三", "王静", "支出", "微信转账", "往来款", "2024-08-16 10:27:00", 100000, "张夏天", "张夏天", "往来款", "核心行贿链", "graph", core=True)
    add("罗宇", "罗宇", "支出", "微信转账", "还款", "2024-08-17 15:30:00", 90000, "曾黎", "何晓初", "还款", "核心行贿链", "graph", core=True)
    add("陈三一", "陈三一", "支出", "微信转账", "劳务费", "2024-08-18 09:48:00", 80000, "饶蝶", "何晓初控制账户", "劳务费", "核心行贿链", "graph", core=True)
    add("张夏天", "张夏天", "支出", "微信转账", "投资款", "2024-08-18 14:05:00", 100000, "周芷", "何晓初控制账户", "投资款", "核心行贿链", "graph", core=True)
    add("张三", "王静", "支出", "ATM取现", "现金", "2024-08-19 16:42:00", 30000, "ATM", "ATM", "现金备用", "核心行贿链", "graph", core=True)
    add("曾黎", "何晓初", "收入", "柜台存款", "现金存入", "2024-08-21 10:08:00", 30000, "现金柜台", "现金柜台", "现金存入", "核心行贿链", "graph", core=True)

    # 2. 徇私枉法链：11万元案发后赔偿款。
    add("李四", "杨周武", "支出", "微信转账", "赔偿款", "2024-09-06 09:20:00", 50000, "江军", "江军", "调解赔偿款", "徇私枉法链", "graph", core=True)
    add("老刘", "刘力飚", "支出", "微信转账", "赔偿款", "2024-09-06 09:31:00", 30000, "汪春蓉", "汪春蓉", "调解赔偿款", "徇私枉法链", "graph", core=True)
    add("老刘", "刘力飚", "支出", "微信转账", "赔偿款", "2024-09-06 09:35:00", 20000, "赵志高", "赵志高", "调解赔偿款", "徇私枉法链", "graph", core=True)
    add("老刘", "刘力飚", "支出", "微信转账", "赔偿款", "2024-09-06 09:39:00", 10000, "易承桂", "易承桂", "调解赔偿款", "徇私枉法链", "graph", core=True)

    # 3. 正常经营与消费，用于混淆视听但不作为核心链条。
    normal_items = [
        ("张三", "王静", "支出", "微信转账", "工资", "2024-08-10 18:00:00", 6800, "罗贤涛", "罗贤涛", "8月工资"),
        ("张三", "王静", "支出", "微信转账", "工资", "2024-08-10 18:03:00", 6200, "李春梅", "李春梅", "8月工资"),
        ("张三", "王静", "支出", "微信转账", "房租", "2024-08-12 12:00:00", 42000, "城东物业", "深圳市城东物业有限公司", "场地租金"),
        ("张三", "王静", "支出", "扫码消费", "餐饮", "2024-08-20 20:11:00", 328, "粤味轩", "粤味轩餐饮", "商务餐"),
        ("李四", "杨周武", "收入", "工资收入", "工资", "2024-08-25 09:00:00", 12800, "同乐派出所", "同乐派出所", "工资"),
        ("李四", "杨周武", "支出", "代扣还款", "房贷", "2024-08-26 08:30:00", 5200, "住房按揭", "中国建设银行深圳分行", "房贷"),
        ("李四", "杨周武", "支出", "快捷支付", "车贷", "2024-08-27 08:30:00", 3100, "汽车金融", "平安汽车金融", "车贷"),
        ("李四", "杨周武", "支出", "扫码消费", "家庭消费", "2024-08-30 19:25:00", 456, "百佳超市", "百佳超市", "日用品"),
    ]
    for item in normal_items:
        add(*item, chain="正常经营与消费", strategy="context", confidence="medium")

    relevant = [item for item in rows if item["入图策略"] == "graph"]
    return rows, relevant


def build_timeline() -> list[dict[str, Any]]:
    return [
        {"时间": "2024-07-01", "案件事实": "杨周武任同乐派出所所长，负责辖区治安和刑事案件办理。", "相关人": "杨周武", "刑罚": None, "相关证据": "证据5-2", "账目往来流水": None, "电话(拨出)": None, "电话(接入)": None},
        {"时间": "2024-08-12", "案件事实": "舞王歌舞厅发生伤害事件，江军等人受伤并报警。", "相关人": "王静、江军、汪春蓉、赵志高、易承桂", "刑罚": None, "相关证据": "证据1-1、证据1-2", "账目往来流水": None, "电话(拨出)": None, "电话(接入)": None},
        {"时间": "2024-08-15", "案件事实": "王静为推动调解和免予刑责，开始筹集资金并联系中间人。", "相关人": "王静、罗宇、陈三一、张夏天", "刑罚": None, "相关证据": "证据3-2、证据3-3", "账目往来流水": "核心行贿链", "电话(拨出)": None, "电话(接入)": None},
        {"时间": "2024-08-17", "案件事实": "罗宇、陈三一、张夏天将资金转入何晓初及其控制账户。", "相关人": "何晓初、曾黎、饶蝶、周芷", "刑罚": None, "相关证据": "证据3-1", "账目往来流水": "27万元转账", "电话(拨出)": None, "电话(接入)": None},
        {"时间": "2024-08-21", "案件事实": "王静账户取现3万元后，何晓初主账户出现现金存入。", "相关人": "王静、何晓初", "刑罚": None, "相关证据": "证据3-1", "账目往来流水": "3万元现金链", "电话(拨出)": None, "电话(接入)": None},
        {"时间": "2024-09-06", "案件事实": "杨周武安排刘力飚调解，向江军等人支付11万元赔偿款。", "相关人": "杨周武、刘力飚、江军、汪春蓉、赵志高、易承桂", "刑罚": None, "相关证据": "证据4-1", "账目往来流水": "11万元赔偿款", "电话(拨出)": None, "电话(接入)": None},
        {"时间": "2024-09-10", "案件事实": "案件被撤销或作调解处理，相关人员被释放。", "相关人": "杨周武、刘力飚", "刑罚": None, "相关证据": "证据4-2、证据2-1", "账目往来流水": None, "电话(拨出)": None, "电话(接入)": None},
    ]


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_xlsx(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet"
    ws.append(columns)
    for item in rows:
        ws.append([item.get(column) for column in columns])
    wb.save(path)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_flows, relevant_flows = build_bank_flows()
    timeline = build_timeline()
    mappings = [
        {"假名": "张三", "案件真实姓名": "王静"},
        {"假名": "李四", "案件真实姓名": "杨周武"},
        {"假名": "老刘", "案件真实姓名": "刘力飚"},
        {"假名": "曾黎", "案件真实姓名": "何晓初"},
        {"假名": "饶蝶", "案件真实姓名": "何晓初控制账户"},
        {"假名": "周芷", "案件真实姓名": "何晓初控制账户"},
    ]
    time_rules = [
        {
            "规则ID": "SYN-0",
            "适用条件": "合成微信流水",
            "原始起点": "2024-08-10 00:00:00",
            "原始终点": "2024-09-10 23:59:59",
            "案情起点": "2024-08-10 00:00:00",
            "案情终点": "2024-09-10 23:59:59",
            "说明": "案情整体后移，微信交易时间即案情时间。",
        }
    ]

    write_csv(OUT_DIR / "cleaned_bank_flows.csv", all_flows, BANK_COLUMNS)
    write_csv(OUT_DIR / "case_relevant_bank_flows.csv", relevant_flows, BANK_COLUMNS)
    write_xlsx(OUT_DIR / "cleaned_bank_flows.xlsx", all_flows, BANK_COLUMNS)
    write_xlsx(OUT_DIR / "case_relevant_bank_flows.xlsx", relevant_flows, BANK_COLUMNS)
    write_xlsx(OUT_DIR / "case_timeline.xlsx", timeline, TIMELINE_COLUMNS)
    try:
        write_xlsx(DATA_DIR / "案情梳理.xlsx", timeline, TIMELINE_COLUMNS)
    except PermissionError:
        write_xlsx(DATA_DIR / "案情梳理_合成后移版.xlsx", timeline, TIMELINE_COLUMNS)
    write_xlsx(OUT_DIR / "name_mapping.xlsx", mappings, ["假名", "案件真实姓名"])
    write_xlsx(OUT_DIR / "time_mapping.xlsx", time_rules, ["规则ID", "适用条件", "原始起点", "原始终点", "案情起点", "案情终点", "说明"])
    (DATA_DIR / "案情梳理.md").write_text(build_case_markdown(), encoding="utf-8")
    (OUT_DIR / "summary.md").write_text(
        "\n".join(
            [
                "# Synthetic processed data",
                "",
                "- 案情已整体后移到 2024-08 至 2024-09，直接覆盖微信交易时间段。",
                f"- 全量合成流水：{len(all_flows)} 条。",
                f"- 核心入图流水：{len(relevant_flows)} 条。",
                "- 三类流水：核心行贿链、徇私枉法赔偿链、正常经营与消费。",
                "- 旧 cleaned 数据不再作为默认导入数据使用。",
            ]
        ),
        encoding="utf-8",
    )
    print(f"all_flows={len(all_flows)}")
    print(f"relevant_flows={len(relevant_flows)}")
    print(f"timeline={len(timeline)}")


def build_case_markdown() -> str:
    return """# 案情梳理

本版案情时间已整体后移至 2024 年 8 月至 9 月，使案件时间线与合成微信交易流水处于同一时间段。账目往来流水在本表中只做概括，精确流水见 `data/processed/case_relevant_bank_flows.csv` 与 `data/processed/cleaned_bank_flows.csv`。

| 时间 | 事件 | 相关人 | 账目往来流水 | 电话拨打情况 |
| --- | --- | --- | --- | --- |
| 2024-07-01 | 杨周武任同乐派出所所长，负责辖区治安、刑事案件办理以及派出所日常执法管理。 | 杨周武 | 暂无直接异常流水。杨周武账户保留工资、房贷、车贷、家庭消费等正常背景流水。 | 暂无异常通话；作为职务身份背景节点。 |
| 2024-08-12 | 舞王歌舞厅发生伤害事件，江军等人受伤并报警，同乐派出所接警并启动处置。 | 王静、江军、汪春蓉、赵志高、易承桂、同乐派出所 | 暂无行贿链流水；王静账户存在舞厅营收、员工工资、房租等正常经营流水，用于形成资金来源背景。 | 报警及接处警相关通话集中出现，王静一方开始联系熟人寻求处理。 |
| 2024-08-15 | 王静为推动调解、压低刑事风险并争取免予刑责，开始筹集资金并联系罗宇、陈三一、张夏天等中间人。 | 王静、罗宇、陈三一、张夏天 | 王静账户出现舞厅营收及现金缴存，随后准备向中间人分拆转款。 | 王静与罗宇、陈三一、张夏天之间通话频率上升，沟通“借款”“往来款”“货款”等转账名义。 |
| 2024-08-16 | 王静通过张三账户将 27 万元拆分转给罗宇、陈三一、张夏天。 | 王静、罗宇、陈三一、张夏天 | 核心行贿链第一段：王静分别向罗宇、陈三一、张夏天转出 9 万、8 万、10 万，备注为借款、货款、往来款。 | 转账前后，中间人与王静有连续短时通话，疑似确认收款账户和备注口径。 |
| 2024-08-17 至 2024-08-18 | 罗宇、陈三一、张夏天陆续将资金转入何晓初及其控制账户。 | 何晓初、曾黎、饶蝶、周芷、罗宇、陈三一、张夏天 | 核心行贿链第二段：罗宇转 9 万至曾黎账户；陈三一转 8 万至饶蝶账户；张夏天转 10 万至周芷账户。曾黎为何晓初主账户，饶蝶、周芷为何晓初控制账户或马甲账户。 | 何晓初与中间人之间出现转账前后联系，通话时间与入账时间相近。 |
| 2024-08-19 至 2024-08-21 | 现金 3 万元链条形成：王静账户取现后，何晓初主账户出现现金存入。 | 王静、何晓初、曾黎 | 核心行贿链现金部分：王静张三账户 ATM 取现 3 万；间隔两日后，何晓初曾黎账户出现 3 万元柜台现金存入。 | 取现前后王静与何晓初或中间人有联系，现金存入当日存在确认性通话。 |
| 2024-09-06 | 杨周武安排刘力飚进行调解，向江军等被害方支付 11 万元赔偿款，以推动案件作调解处理。 | 杨周武、刘力飚、江军、汪春蓉、赵志高、易承桂 | 徇私枉法链：杨周武或刘力飚账户向江军、汪春蓉、赵志高、易承桂转出赔偿款，共计 11 万元。该链条不是行贿受贿本身，而是案发后处置和压案调解的资金表现。 | 杨周武与刘力飚通话集中，随后刘力飚与被害方人员联系，通话与赔偿转账时间接近。 |
| 2024-09-10 | 案件被撤销或作调解处理，相关人员被释放，刑事追责链条被削弱。 | 杨周武、刘力飚、王静、相关办案人员 | 赔偿款已完成支付，行贿链和赔偿链在时间上形成先后呼应。 | 调解完成后，杨周武、刘力飚、王静一方通话频次下降，形成事后收尾特征。 |

## 流水文件说明

- `data/processed/case_relevant_bank_flows.csv`：只包含核心入图流水，包括 27 万元转账、3 万元现金链、11 万元赔偿链。
- `data/processed/cleaned_bank_flows.csv`：包含核心流水与正常经营/消费流水。正常流水用于混淆视听和 RAG 解释，不默认进入证据图谱。
- `data/processed/name_mapping.xlsx`：假名到案件人物的映射，例如张三对应王静、李四对应杨周武、曾黎对应何晓初。
- `data/processed/time_mapping.xlsx`：本版采用 `SYN-0` 规则，即案情整体后移，微信交易时间即案情时间。
"""


if __name__ == "__main__":
    main()
