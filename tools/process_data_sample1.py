from __future__ import annotations

import csv
import json
import math
import re
import struct
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "数据样本1"
OUT_DIR = ROOT / "outputs" / "data_sample1"


def u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def i32(data: bytes, off: int) -> int:
    return struct.unpack_from("<i", data, off)[0]


def read_utf16le_z(data: bytes) -> str:
    try:
        return data.decode("utf-16le", errors="ignore").rstrip("\x00")
    except Exception:
        return data.decode("gb18030", errors="ignore").rstrip("\x00")


class OleReader:
    ENDOFCHAIN = 0xFFFFFFFE
    FREESECT = 0xFFFFFFFF

    def __init__(self, path: Path):
        self.path = path
        self.data = path.read_bytes()
        if self.data[:8] != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
            raise ValueError(f"not an OLE compound file: {path}")
        self.sector_size = 1 << u16(self.data, 30)
        self.mini_sector_size = 1 << u16(self.data, 32)
        self.mini_cutoff = u32(self.data, 56)
        self.first_dir_sector = i32(self.data, 48)
        self.first_mini_fat_sector = i32(self.data, 60)
        self.num_mini_fat_sectors = u32(self.data, 64)
        self.first_difat_sector = i32(self.data, 68)
        self.num_difat_sectors = u32(self.data, 72)
        self.fat = self._load_fat()
        self.dir_entries = self._load_directory()
        self.root_entry = self.dir_entries[0]
        self.mini_fat = self._load_mini_fat()
        self.mini_stream = self._read_regular_stream(self.root_entry["start"], self.root_entry["size"])

    def _sector(self, sid: int) -> bytes:
        off = 512 + sid * self.sector_size
        return self.data[off : off + self.sector_size]

    def _load_fat(self) -> list[int]:
        difat = list(struct.unpack_from("<109I", self.data, 76))
        next_difat = self.first_difat_sector
        for _ in range(self.num_difat_sectors):
            if next_difat < 0:
                break
            sec = self._sector(next_difat)
            difat.extend(struct.unpack_from(f"<{self.sector_size // 4 - 1}I", sec, 0))
            next_difat = i32(sec, self.sector_size - 4)
        fat: list[int] = []
        for sid in difat:
            if sid == self.FREESECT:
                continue
            sec = self._sector(sid)
            fat.extend(struct.unpack(f"<{self.sector_size // 4}I", sec))
        return fat

    def _chain(self, start: int, fat: list[int] | None = None) -> list[int]:
        fat = fat or self.fat
        out: list[int] = []
        sid = start
        seen: set[int] = set()
        while sid not in (self.ENDOFCHAIN, self.FREESECT) and sid >= 0:
            if sid in seen or sid >= len(fat):
                break
            seen.add(sid)
            out.append(sid)
            sid = fat[sid]
        return out

    def _read_regular_stream(self, start: int, size: int) -> bytes:
        if start < 0:
            return b""
        data = b"".join(self._sector(sid) for sid in self._chain(start))
        return data[:size]

    def _load_directory(self) -> list[dict[str, Any]]:
        raw = self._read_regular_stream(self.first_dir_sector, len(self.data))
        entries: list[dict[str, Any]] = []
        for off in range(0, len(raw), 128):
            ent = raw[off : off + 128]
            if len(ent) < 128:
                continue
            name_len = u16(ent, 64)
            if name_len < 2:
                name = ""
            else:
                name = read_utf16le_z(ent[: name_len - 2])
            entries.append(
                {
                    "name": name,
                    "type": ent[66],
                    "start": i32(ent, 116),
                    "size": u32(ent, 120),
                }
            )
        return entries

    def _load_mini_fat(self) -> list[int]:
        if self.first_mini_fat_sector < 0 or self.num_mini_fat_sectors == 0:
            return []
        raw = b"".join(self._sector(sid) for sid in self._chain(self.first_mini_fat_sector))
        count = len(raw) // 4
        return list(struct.unpack(f"<{count}I", raw[: count * 4]))

    def _read_mini_stream(self, start: int, size: int) -> bytes:
        chunks = []
        for sid in self._chain(start, self.mini_fat):
            off = sid * self.mini_sector_size
            chunks.append(self.mini_stream[off : off + self.mini_sector_size])
        return b"".join(chunks)[:size]

    def open_stream(self, *names: str) -> bytes:
        wanted = {n.lower() for n in names}
        for ent in self.dir_entries:
            if ent["name"].lower() in wanted:
                if ent["size"] < self.mini_cutoff:
                    return self._read_mini_stream(ent["start"], ent["size"])
                return self._read_regular_stream(ent["start"], ent["size"])
        raise KeyError(f"stream not found: {names}")


def decode_rich_string(data: bytes, off: int) -> tuple[str, int]:
    if off + 3 > len(data):
        return "", len(data) - off
    cch = u16(data, off)
    flags = data[off + 2]
    pos = off + 3
    rich_runs = 0
    ext_size = 0
    if flags & 0x08:
        rich_runs = u16(data, pos)
        pos += 2
    if flags & 0x04:
        ext_size = u32(data, pos)
        pos += 4
    is_16 = bool(flags & 0x01)
    byte_len = cch * (2 if is_16 else 1)
    raw = data[pos : pos + byte_len]
    if is_16:
        text = raw.decode("utf-16le", errors="ignore")
    else:
        for encoding in ("utf-8", "gb18030", "latin1"):
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = raw.decode("latin1", errors="ignore")
    consumed = pos + byte_len + rich_runs * 4 + ext_size - off
    return text, consumed


def rk_value(raw: int) -> float:
    mult100 = raw & 0x01
    is_int = raw & 0x02
    value_bits = raw & 0xFFFFFFFC
    if is_int:
        if value_bits & 0x80000000:
            value_bits -= 0x100000000
        val = value_bits >> 2
    else:
        packed = struct.pack("<Q", value_bits << 32)
        val = struct.unpack("<d", packed)[0]
    if mult100:
        val = val / 100
    return val


def excel_date(serial: float) -> str:
    if serial <= 0 or serial > 60000:
        return str(serial)
    return (datetime(1899, 12, 30) + timedelta(days=float(serial))).strftime("%Y-%m-%d %H:%M:%S").rstrip(" 00:00:00")


BUILTIN_DATE_FORMATS = set(range(14, 23)) | {45, 46, 47}


@dataclass
class SheetData:
    name: str
    rows: list[list[Any]]


def parse_workbook(path: Path) -> list[SheetData]:
    wb = OleReader(path).open_stream("Workbook", "Book")
    sheets: list[tuple[str, int]] = []
    sst: list[str] = []
    formats: dict[int, str] = {}
    xf_formats: list[int] = []

    pos = 0
    while pos + 4 <= len(wb):
        rec_id = u16(wb, pos)
        rec_len = u16(wb, pos + 2)
        rec = wb[pos + 4 : pos + 4 + rec_len]
        pos += 4 + rec_len
        if rec_id == 0x0085 and len(rec) >= 8:
            stream_pos = u32(rec, 0)
            name_len = rec[6]
            flags = rec[7]
            raw = rec[8 : 8 + name_len * (2 if flags & 1 else 1)]
            name = raw.decode("utf-16le" if flags & 1 else "latin1", errors="ignore")
            sheets.append((name, stream_pos))
        elif rec_id == 0x041E and len(rec) >= 3:
            fmt_id = u16(rec, 0)
            text, _ = decode_rich_string(rec, 2)
            formats[fmt_id] = text
        elif rec_id == 0x00E0 and len(rec) >= 4:
            xf_formats.append(u16(rec, 2))
        elif rec_id == 0x00FC and len(rec) >= 8:
            total = u32(rec, 4)
            p = 8
            for _ in range(total):
                if p >= len(rec):
                    break
                text, consumed = decode_rich_string(rec, p)
                sst.append(text)
                p += consumed

    parsed: list[SheetData] = []
    for idx, (name, start) in enumerate(sheets):
        end = sheets[idx + 1][1] if idx + 1 < len(sheets) else len(wb)
        rows: dict[int, dict[int, Any]] = defaultdict(dict)
        p = start
        while p + 4 <= end:
            rec_id = u16(wb, p)
            rec_len = u16(wb, p + 2)
            rec = wb[p + 4 : p + 4 + rec_len]
            p += 4 + rec_len
            if rec_id in (0x000A,):
                break
            if rec_id == 0x00FD and len(rec) >= 10:
                r, c, sst_idx = u16(rec, 0), u16(rec, 2), u32(rec, 6)
                rows[r][c] = sst[sst_idx] if sst_idx < len(sst) else ""
            elif rec_id == 0x0204 and len(rec) >= 8:
                r, c, n = u16(rec, 0), u16(rec, 2), u16(rec, 6)
                raw = rec[8 : 8 + n]
                for encoding in ("utf-8", "gb18030", "latin1"):
                    try:
                        rows[r][c] = raw.decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    rows[r][c] = raw.decode("latin1", errors="ignore")
            elif rec_id == 0x0203 and len(rec) >= 14:
                r, c, xf = u16(rec, 0), u16(rec, 2), u16(rec, 4)
                val = struct.unpack_from("<d", rec, 6)[0]
                fmt = xf_formats[xf] if xf < len(xf_formats) else None
                rows[r][c] = excel_date(val) if fmt in BUILTIN_DATE_FORMATS else val
            elif rec_id == 0x027E and len(rec) >= 10:
                r, c, xf = u16(rec, 0), u16(rec, 2), u16(rec, 4)
                val = rk_value(u32(rec, 6))
                fmt = xf_formats[xf] if xf < len(xf_formats) else None
                rows[r][c] = excel_date(val) if fmt in BUILTIN_DATE_FORMATS else val
            elif rec_id == 0x00BD and len(rec) >= 6:
                r, c_first, c_last = u16(rec, 0), u16(rec, 2), rec[-1]
                offset = 4
                for c in range(c_first, c_last + 1):
                    if offset + 6 > len(rec):
                        break
                    xf = u16(rec, offset)
                    val = rk_value(u32(rec, offset + 2))
                    fmt = xf_formats[xf] if xf < len(xf_formats) else None
                    rows[r][c] = excel_date(val) if fmt in BUILTIN_DATE_FORMATS else val
                    offset += 6

        max_row = max(rows.keys(), default=-1)
        max_col = max((max(cols.keys()) for cols in rows.values() if cols), default=-1)
        table = []
        for r in range(max_row + 1):
            table.append([rows[r].get(c, "") for c in range(max_col + 1)])
        parsed.append(SheetData(name=name, rows=table))
    return parsed


def clean_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isfinite(value) and value.is_integer():
            return str(int(value))
        return str(value)
    text = str(value).replace("\u3000", " ").strip()
    text = re.sub(r"[\u200b-\u200f\u202a-\u202e\ufeff]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def amount_yuan(row: dict[str, str]) -> str:
    value = first_present(row, ["amount", "交易金额", "交易金额(元)"])
    if value:
        return value
    fen = first_present(row, ["amount_fen", "交易金额(分)", "counterparty_receive_amount_fen"])
    number = to_float(fen)
    if number is None:
        return ""
    return f"{number / 100:.2f}"


def is_empty_row(row: list[Any]) -> bool:
    return all(clean_cell(c) == "" for c in row)


def normalize_header(text: str) -> str:
    text = clean_cell(text).strip(":：")
    mapping = {
        "交易单号": "trade_id",
        "商户单号": "merchant_order_id",
        "交易类型": "trade_type",
        "收/支": "direction",
        "交易方式": "payment_method",
        "交易状态": "status",
        "商品名称": "product_name",
        "交易金额(元)": "amount",
        "交易金额（元）": "amount",
        "交易时间": "trade_time",
        "付款方": "payer",
        "收款方": "payee",
        "对方": "counterparty",
        "备注": "remark",
        "姓名": "name",
        "身份证号": "id_card",
        "证件号码": "id_card",
        "微信号": "wechat_id",
        "微信昵称": "wechat_nickname",
        "手机号": "phone",
        "绑定手机": "phone",
        "绑定银行卡": "bank_card",
        "银行账号": "bank_card",
        "开户行信息": "bank_name",
        "注册时间": "register_time",
        "注册姓名": "name",
        "注册身份证号": "id_card",
        "账号": "wechat_id",
        "账户状态": "account_status",
        "绑定状态": "binding_status",
        "用户ID": "wechat_id",
        "用户侧账号名称": "name",
        "借贷类型": "direction",
        "交易业务类型": "trade_type",
        "交易用途类型": "trade_purpose",
        "交易金额(分)": "amount_fen",
        "账户余额(分)": "balance_fen",
        "用户银行卡号": "user_bank_card",
        "第三方账户名称": "third_party_account",
        "对手方ID": "counterparty_id",
        "对手侧账户名称": "counterparty",
        "对手方银行卡号": "counterparty_bank_card",
        "对手侧银行名称": "counterparty_bank_name",
        "对手方接收时间": "counterparty_receive_time",
        "对手方接收金额(分)": "counterparty_receive_amount_fen",
        "备注1": "remark",
        "备注2": "remark2",
    }
    return mapping.get(text, text)


def table_from_rows(rows: list[list[Any]]) -> tuple[list[str], list[dict[str, str]]]:
    cleaned = [[clean_cell(c) for c in row] for row in rows if not is_empty_row(row)]
    if not cleaned:
        return [], []
    header_idx = 0
    best_score = -1
    for i, row in enumerate(cleaned[:20]):
        if row and row[0] in {"账户状态", "用户ID", "交易单号"}:
            header_idx = i
            break
        score = sum(1 for c in row if any(k in c for k in ["交易", "姓名", "身份证", "微信", "金额", "时间", "状态", "账号"]))
        if score > best_score:
            header_idx = i
            best_score = score
    headers = [normalize_header(c) or f"col_{i + 1}" for i, c in enumerate(cleaned[header_idx])]
    rows_out = []
    for row in cleaned[header_idx + 1 :]:
        if row and row[0] in {"注销信息", "账号", "用户ID", "交易单号"}:
            continue
        item = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
        if item.get(headers[0]) in {"注销信息", headers[0]}:
            continue
        if any(item.values()):
            rows_out.append(item)
    return headers, rows_out


def infer_subject(path: Path) -> dict[str, str]:
    parts = path.parts
    out = {"id_card_from_path": "", "account_from_path": ""}
    for i, part in enumerate(parts):
        if re.fullmatch(r"\d{17}[\dXx]", part):
            out["id_card_from_path"] = part.upper()
            if i + 1 < len(parts):
                out["account_from_path"] = parts[i + 1]
            break
    return out


def extract_records() -> tuple[list[dict[str, str]], list[dict[str, str]], list[str]]:
    reg_records: list[dict[str, str]] = []
    trade_records: list[dict[str, str]] = []
    warnings: list[str] = []
    for path in sorted(SAMPLE_DIR.rglob("*.xls")):
        subject = infer_subject(path)
        try:
            sheets = parse_workbook(path)
        except Exception as exc:
            warnings.append(f"failed to parse {path}: {exc}")
            continue
        for sheet in sheets:
            headers, rows = table_from_rows(sheet.rows)
            kind = "trade" if "TenpayTrades" in path.name or "交易" in str(path) else "registration"
            for row_num, row in enumerate(rows, start=1):
                row = {k: clean_cell(v) for k, v in row.items()}
                row.update(subject)
                row["source_file"] = str(path.relative_to(ROOT))
                row["source_sheet"] = sheet.name
                row["source_row"] = str(row_num)
                if kind == "trade":
                    trade_records.append(row)
                else:
                    reg_records.append(row)
    return reg_records, trade_records, warnings


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def node_id(kind: str, value: str) -> str:
    safe = re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]+", "_", value.strip())
    return f"{kind}:{safe}"


def add_node(nodes: dict[str, dict[str, Any]], kind: str, value: str, **props: Any) -> str | None:
    value = clean_cell(value)
    if not value:
        return None
    nid = node_id(kind, value)
    node = nodes.setdefault(nid, {"id": nid, "label": value, "type": kind, "properties": {}})
    node["properties"].update({k: v for k, v in props.items() if v not in ("", None)})
    return nid


def add_edge(edges: dict[tuple[str, str, str], dict[str, Any]], source: str | None, target: str | None, rel: str, **props: Any) -> None:
    if not source or not target or source == target:
        return
    key = (source, target, rel)
    edge = edges.setdefault(key, {"source": source, "target": target, "relation": rel, "properties": {}, "count": 0})
    edge["count"] += 1
    for k, v in props.items():
        if v not in ("", None):
            edge["properties"][k] = v


def first_present(row: dict[str, str], keys: list[str]) -> str:
    for key in keys:
        if row.get(key):
            return row[key]
    return ""


def build_graph(reg_records: list[dict[str, str]], trade_records: list[dict[str, str]]) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[tuple[str, str, str], dict[str, Any]] = {}

    for row in reg_records:
        account = first_present(row, ["wechat_id", "微信号", "account_from_path"])
        person_name = first_present(row, ["name", "姓名", "真实姓名"])
        id_card = first_present(row, ["id_card", "身份证号", "证件号码", "id_card_from_path"])
        phone = first_present(row, ["phone", "手机号", "手机号码"])
        nickname = first_present(row, ["wechat_nickname", "微信昵称", "昵称"])
        account_id = add_node(nodes, "wechat_account", account, nickname=nickname)
        person_id = add_node(nodes, "person", person_name or id_card, name=person_name)
        id_id = add_node(nodes, "id_card", id_card)
        phone_id = add_node(nodes, "phone", phone)
        add_edge(edges, person_id, id_id, "USES_ID_CARD")
        add_edge(edges, person_id, phone_id, "USES_PHONE")
        add_edge(edges, person_id, account_id, "OWNS_WECHAT_ACCOUNT")
        add_edge(edges, account_id, id_id, "BOUND_TO_ID_CARD")
        bank_card = first_present(row, ["bank_card", "user_bank_card"])
        bank_id = add_node(nodes, "bank_card", bank_card, bank_name=row.get("bank_name", ""))
        add_edge(edges, account_id, bank_id, "BINDS_BANK_CARD", status=row.get("binding_status", ""))

    for row in trade_records:
        account = first_present(row, ["wechat_id", "account_from_path"])
        account_id = add_node(nodes, "wechat_account", account)
        trade_id = first_present(row, ["trade_id", "交易单号", "商户单号", "merchant_order_id"])
        amount = amount_yuan(row)
        trade_time = first_present(row, ["trade_time", "交易时间"])
        direction = first_present(row, ["direction", "收/支"])
        status = first_present(row, ["status", "交易状态"])
        product = first_present(row, ["product_name", "商品名称", "交易商品"])
        counterparty = first_present(row, ["counterparty", "counterparty_id", "对方", "付款方", "收款方", "交易对方"])
        trade_node_id = add_node(
            nodes,
            "transaction",
            trade_id or f"{row.get('source_file', '')}#{row.get('source_row', '')}",
            amount=amount,
            trade_time=trade_time,
            direction=direction,
            status=status,
            product=product,
        )
        cp_id = add_node(nodes, "counterparty", counterparty)
        add_edge(edges, account_id, trade_node_id, "HAS_TRANSACTION", amount=amount, trade_time=trade_time)
        add_edge(edges, trade_node_id, cp_id, "TRANSACTS_WITH", amount=amount, direction=direction)
        if direction in {"支出", "支", "付款", "出"}:
            add_edge(edges, account_id, cp_id, "PAYS_TO", amount=amount, trade_time=trade_time)
        elif direction in {"收入", "收", "收款", "入"}:
            add_edge(edges, cp_id, account_id, "PAYS_TO", amount=amount, trade_time=trade_time)

    return {
        "metadata": {
            "source": "数据样本1",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "node_count": len(nodes),
            "edge_count": len(edges),
        },
        "nodes": list(nodes.values()),
        "edges": list(edges.values()),
    }


def to_float(value: str) -> float | None:
    if not value:
        return None
    text = re.sub(r"[^0-9.\-]", "", value)
    try:
        return float(text)
    except ValueError:
        return None


def analyze(reg_records: list[dict[str, str]], trade_records: list[dict[str, str]], graph: dict[str, Any], warnings: list[str]) -> str:
    accounts = sorted({r.get("account_from_path", "") for r in reg_records + trade_records if r.get("account_from_path")})
    id_cards = sorted({r.get("id_card_from_path", "") for r in reg_records + trade_records if r.get("id_card_from_path")})
    amounts = [a for a in (to_float(amount_yuan(r)) for r in trade_records) if a is not None]
    by_account = Counter(r.get("account_from_path", "") for r in trade_records)
    status = Counter(first_present(r, ["status", "交易状态"]) or "未知" for r in trade_records)
    directions = Counter(first_present(r, ["direction", "收/支"]) or "未知" for r in trade_records)

    lines = [
        "# 数据样本1分析与清洗入图说明",
        "",
        "## 数据概况",
        f"- 源文件：{len(list(SAMPLE_DIR.rglob('*.xls')))} 个 .xls 文件",
        f"- 注册信息记录：{len(reg_records)} 条",
        f"- 交易明细记录：{len(trade_records)} 条",
        f"- 识别账号：{', '.join(accounts) if accounts else '未识别'}",
        f"- 识别身份证号：{', '.join(id_cards) if id_cards else '未识别'}",
        "",
        "## 交易统计",
        f"- 交易笔数按账号：{dict(by_account)}",
        f"- 收支方向：{dict(directions)}",
        f"- 交易状态：{dict(status)}",
        f"- 金额合计：{round(sum(amounts), 2) if amounts else '未识别'}",
        f"- 最大单笔金额：{round(max(amounts), 2) if amounts else '未识别'}",
        "",
        "## 清洗策略",
        "- 删除空行，压缩多余空白，统一字段别名为英文键名。",
        "- 从文件路径补充身份证号与微信账号，解决表内字段缺失时的主体归属问题。",
        "- 保留原始来源文件和 sheet，便于证据追溯。",
        "- 交易金额转为可统计数值；无法识别的字段保留原字段名。",
        "",
        "## 图谱录入结构",
        f"- 节点数：{graph['metadata']['node_count']}",
        f"- 边数：{graph['metadata']['edge_count']}",
        "- 核心节点类型：person、id_card、phone、wechat_account、transaction、counterparty。",
        "- 核心关系类型：OWNS_WECHAT_ACCOUNT、BOUND_TO_ID_CARD、HAS_TRANSACTION、TRANSACTS_WITH、PAYS_TO。",
        "",
        "## 输出文件",
        "- cleaned_registration.csv：清洗后的注册信息。",
        "- cleaned_trades.csv：清洗后的交易明细。",
        "- graph_import.json：可直接用于图谱录入的 nodes/edges JSON。",
        "- graph_documents.jsonl：可供 HippoRAG 等文本索引工具录入的事实句。",
    ]
    if warnings:
        lines.extend(["", "## 解析警告", *[f"- {w}" for w in warnings]])
    return "\n".join(lines) + "\n"


def write_graph_documents(graph: dict[str, Any], path: Path) -> None:
    node_labels = {n["id"]: n["label"] for n in graph["nodes"]}
    with path.open("w", encoding="utf-8") as f:
        for edge in graph["edges"]:
            s = node_labels.get(edge["source"], edge["source"])
            t = node_labels.get(edge["target"], edge["target"])
            rel = edge["relation"]
            props = edge.get("properties", {})
            extra = "，".join(f"{k}={v}" for k, v in props.items())
            text = f"{s} 与 {t} 存在关系 {rel}" + (f"，属性：{extra}。" if extra else "。")
            f.write(json.dumps({"title": rel, "text": text, "source": "数据样本1"}, ensure_ascii=False) + "\n")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reg_records, trade_records, warnings = extract_records()
    write_csv(OUT_DIR / "cleaned_registration.csv", reg_records)
    write_csv(OUT_DIR / "cleaned_trades.csv", trade_records)
    graph = build_graph(reg_records, trade_records)
    (OUT_DIR / "graph_import.json").write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    write_graph_documents(graph, OUT_DIR / "graph_documents.jsonl")
    (OUT_DIR / "analysis_report.md").write_text(analyze(reg_records, trade_records, graph, warnings), encoding="utf-8")
    print(json.dumps(graph["metadata"], ensure_ascii=False))
    print(f"registration={len(reg_records)} trades={len(trade_records)} out={OUT_DIR}")


if __name__ == "__main__":
    main()
