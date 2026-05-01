# FastAPI 接口交付说明（需求对齐版）

本文档按“Ingestion + Analysis”需求重新对齐，聚焦联调契约。

## 1) Ingestion：证据接入分流

### 接口 1：`POST /api/v1/cases/{case_id}/ingestion/text`

- 用途：接收结构化/半结构化字符串并分流抽取。
- 入参：`title`、`content`、`source_type`（示例：`笔录`、`流水`）。
- 分流规则：
  - `source_type=流水`：按结构化流程解析并构造三元组/Passage
  - `source_type=笔录` 或文本型：走非结构化抽取

请求示例：

```json
{
  "title": "询问笔录-张某",
  "content": "张某承认在2024年3月12日完成一笔转账。",
  "source_type": "笔录"
}
```

成功响应（200）：

```json
{
  "case_id": "case_01",
  "accepted": true,
  "evidences": [
    {
      "evidence_id": "evd_8f5f5a1d",
      "title": "询问笔录-张某",
      "source_type": "笔录",
      "source_ref": "ingestion:text",
      "content_preview": "张某承认在2024年3月12日完成一笔转账。",
      "created_at": "2026-04-30T01:59:08.928Z"
    }
  ],
  "next_step": "run_analysis"
}
```

字段说明：

- 顶层：`case_id`、`accepted`、`evidences`（本次写入的证据列表）、`next_step`（固定建议值 `run_analysis`，供前端串联分析接口）。
- `evidences[]`：`evidence_id`、`title`、`source_type`、`source_ref`（文本接入为 `ingestion:text`；文件接入为原始文件名或 `ingestion:file`）、`content_preview`（入库正文截断预览）、`created_at`（UTC，毫秒精度，以 `Z` 结尾）。

请求体验证失败（422，FastAPI / Pydantic 标准 `detail` 数组）：

```json
{
  "detail": [
    {
      "type": "enum",
      "loc": ["body", "source_type"],
      "msg": "Input should be 'text', '笔录', '流水', 'doc', 'docx', 'pdf', 'txt', 'csv', 'xlsx', 'json' or 'unknown'",
      "input": "bad",
      "ctx": {
        "expected": "'text', '笔录', '流水', 'doc', 'docx', 'pdf', 'txt', 'csv', 'xlsx', 'json' or 'unknown'"
      }
    }
  ]
}
```

说明：`loc` 为错误位置路径（`body` / `query` / `path` 等与字段名）；`type` 为错误类别；`input` 为被拒绝的入参值（部分错误项可能省略）；`ctx` 为附加上下文对象，无额外信息时可为 `{}`。

### 接口 2：`POST /api/v1/cases/{case_id}/ingestion/file`

- 用途：接收文件流并触发对应解析逻辑。
- 表单字段：`file`（必填）、`source_type`（可选）、`title`（可选）。
- 支持后缀：`txt/text/csv/xlsx/json/pdf/docx/doc`。
- 约束：
  - 超 10MB 返回 `413`
  - 后缀不支持返回 `422`
  - 空文件/无有效文本返回 `422`

成功响应结构与 `/ingestion/text` 一致。

## 2) Analysis：分析启动

### 接口 3：`POST /api/v1/cases/{case_id}/analysis/run`

- 兼容接口：`POST /api/v1/cases/{case_id}/analysis/run-graph`
- 用途：对该案件已接入证据进行全量汇聚分析（统一三元组缓冲区）。
- 行为：消费 Ingestion 已保存的抽取结果并统计。

成功响应（200）：

```json
{
  "case_id": "case_01",
  "accepted": true,
  "analyzed_evidence_count": 3,
  "triples_count": 18,
  "message": "分析任务已触发，已汇聚证据三元组缓冲区。"
}
```

失败语义：

- `422`：该案件还没有任何已接入证据
- `500`：内部异常

## 3) 校验与异常约束

- `source_type` 使用枚举强校验（非法值由 FastAPI/Pydantic 直接拦截为 `422`，响应体为上一节的 `detail` 数组结构）。
- 业务规则类错误（如文本为空、文件后缀不支持）当前仍返回 `422`，但 `detail` 可能为字符串而非数组；联调时请以 HTTP 状态码 + 实际 `detail` 类型为准。
- 文件后缀和大小有显式校验。

## 4) 当前测试状态

- 自动化测试：`7 passed`

