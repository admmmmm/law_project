# 数据流动方向说明

本文说明当前系统中一份证据从上传、入库、抽取、建图，到前端点击字段查看证据原文和 HippoRAG PPR 溯源的完整流动方向。

## 总览

当前系统的数据流有两条主线：

1. 证据入库与建图线：负责把文件变成系统里的证据、passage、三元组和业务图谱。
2. 字段溯源线：负责用户点击模型生成的某个字段或某句话后，回到证据原文和 PPR 检索路径。

可以粗略理解为：

```text
上传文件/压缩包
  -> IngestionService
  -> EvidenceRecord + raw_contents + ExtractionResult
  -> AnalysisService.run
  -> AlgorithmAdapter.build_graph
  -> InvestigationGraph
  -> 前端图谱/分析/报告页面

用户点击字段/句子
  -> AnalysisService.trace
  -> AlgorithmAdapter.retrieve_trace
  -> HippoRAG retrieve/PPR passages
  -> 证据原文 EvidenceDetail
  -> 前端抽屉展示
```

## 1. 上传入口

前端入口在 `frontend/src/views/Dashboard.vue`。

用户可以选择：

- 文件夹：调用 `POST /api/v1/cases/{case_id}/ingestions/batch`
- 压缩包：调用 `POST /api/v1/cases/{case_id}/ingestions/archive`

后端入口在：

- `backend/app/api/v1/routes/ingestion.py`
- `backend/app/services/ingestion_service.py`

压缩包会被展开，系统会跳过目录、系统文件和不支持的文件类型。目前支持：

```text
txt / md / csv / xlsx / json / pdf / docx
```

## 2. 证据入库

每个被接受的文件都会进入 `IngestionService._save_evidence`。

系统会生成一条 `EvidenceRecord`：

```text
evidence_id: evd_xxx
case_id: 当前案件 ID
title: 文件名
source_type: md / xlsx / csv / docx 等
source_ref: 原文件名
content_preview: 正文前 240 字
created_at: 导入时间
```

同时写入三个内存区：

```text
store.evidence[case_id]        -> 证据列表
store.raw_contents[evidence_id] -> 证据原文
store.extractions[evidence_id]  -> 抽取结果
```

这一步非常关键：后续“查看证据原文”就是从 `store.raw_contents` 里按 `evidence_id` 找回来的。

## 3. 内容解析与抽取

抽取入口在 `backend/app/services/information_extraction.py`：

```text
route_extraction(...)
```

系统会根据文件类型分流。

### 非结构化证据

例如 `.md`、`.txt`、`.docx`、`.pdf`。

当前做法：

```text
文本内容
  -> 按句切分
  -> 生成 PassageRecord
  -> 规则/LLM/OpenIE 生成或辅助生成 ExtractedTriple
```

需要注意：非结构化证据的原文 passage 比图谱三元组更重要。图谱用于路由和提示关联，真正回答和溯源时仍然应该回到原文。

### 结构化证据

例如银行流水、电话流水 `.xlsx`。

当前做法：

```text
xlsx/csv 行数据
  -> parse_structured_content
  -> map_rows_to_triples
  -> 每一行生成若干三元组
  -> 同时生成可读 passage
```

银行流水不会把每一条细流水都无脑画到图上。当前代码里有 `graph_eligible` 逻辑，用来控制哪些流水进入业务图谱，避免图谱被大量正常流水污染。

## 4. 运行分析与建图

前端点击“运行分析并进图谱”后：

```text
POST /api/v1/cases/{case_id}/analysis/run
```

后端进入：

```text
AnalysisService.run
  -> AlgorithmAdapter.build_graph
```

建图时会读取：

```text
store.evidence[case_id]
store.raw_contents
store.extractions
```

然后生成：

```text
InvestigationGraph
  nodes: 图节点
  edges: 图关系
  clues: 风险线索
```

图谱保存到：

```text
store.graphs[case_id]
```

前端图谱页读取：

```text
GET /api/v1/cases/{case_id}/graph
```

## 5. HippoRAG 在哪里介入

当前 `ALGORITHM_PROVIDER=hipporag` 时，`AlgorithmAdapter` 会尝试调用 HippoRAG。

建图阶段：

```text
证据 passage
  -> HippoRAG.index(docs)
  -> HippoRAG OpenIE
  -> OpenIE triples
  -> 合并进业务图谱
```

溯源阶段：

```text
用户点击字段/句子
  -> query
  -> HippoRAG.retrieve([query])
  -> doc_scores + docs
  -> TracePassage[]
```

这里的 `TracePassage` 包含：

```text
rank
score
passage
evidence_id
evidence_title
```

前端再根据 `evidence_id` 调接口取证据原文：

```text
GET /api/v1/cases/{case_id}/evidence/{evidence_id}
```

## 6. 前端字段溯源

当前字段溯源主要在两个页面：

- `frontend/src/views/Intelligence.vue`
- `frontend/src/views/Portrait.vue`

### 智能分析页

页面会把“基础信息卡片”“行为事实还原”“要件拆解”“抗辩预判”等字段渲染成可点击卡片。

点击字段后：

```text
字段 label + 字段内容
  -> 拆成句子
  -> 用户点击某一句
  -> traceAnalysis(caseId, query, evidenceIds, topK)
```

抽屉展示三类信息：

```text
1. 当前溯源句
2. HippoRAG PPR 检索结果
3. 证据原文
4. 图谱溯源路径候选
```

### 画像报告页

报告里的每条结论/建议也可以点击。

点击后系统用该条结论作为 query，走同样的 PPR 溯源接口。

## 7. 贯穿实例：证据6-1

以 `data/realtest/evidence_docs/证据6-1_深圳市人民检察院立案决定书.md` 为例。

### 7.1 原始文件

文件名：

```text
证据6-1_深圳市人民检察院立案决定书.md
```

这份证据的核心内容是：

```text
杨周武因涉嫌徇私枉法罪，被深圳市人民检察院立案侦查。
文书中载明其在办理舞王俱乐部相关故意伤害案件过程中，
涉嫌接受王静及何晓初请托，安排非本案承办人员介入调解，
并将案件作调解结案处理。
```

### 7.2 导入后生成 EvidenceRecord

导入后会生成类似：

```json
{
  "evidence_id": "evd_xxx",
  "case_id": "case_xxx",
  "title": "evidence_docs/证据6-1_深圳市人民检察院立案决定书.md",
  "source_type": "md",
  "source_ref": "evidence_docs/证据6-1_深圳市人民检察院立案决定书.md",
  "content_preview": "# 证据6-1：深圳市人民检察院立案决定书..."
}
```

同时：

```text
store.raw_contents["evd_xxx"] = 该 md 文件全文
```

### 7.3 抽取结果

因为这是 `.md`，会走非结构化路线。

系统会切出若干 passage，例如：

```text
杨周武因涉嫌徇私枉法罪，被深圳市人民检察院立案侦查。
```

以及：

```text
涉嫌接受王静及何晓初请托，安排非本案承办人员介入调解，并将案件作调解结案处理。
```

这些 passage 会带着同一个 `evidence_id=evd_xxx`。

### 7.4 建图表现

业务图谱里会出现一个证据节点：

```text
node_id: doc:evd_xxx
label: evidence_docs/证据6-1_深圳市人民检察院立案决定书.md
type: evidence
evidence_ids: ["evd_xxx"]
```

前端图谱不会把完整文件名都显示在节点上，而是显示短标签：

```text
证据6-1
检察院立案决定书
```

完整标题、原文和属性放到右侧详情里。

### 7.5 点击字段后的溯源

假设画像报告生成一句：

```text
杨周武涉嫌接受王静及何晓初请托，并通过调解结案方式使相关人员逃避刑事追究。
```

用户点击这句话后，前端会发送：

```json
{
  "query": "行为事实还原\n杨周武涉嫌接受王静及何晓初请托，并通过调解结案方式使相关人员逃避刑事追究。",
  "evidence_ids": [],
  "top_k": 8
}
```

后端 `AnalysisService.trace` 会调用：

```text
AlgorithmAdapter.retrieve_trace
```

HippoRAG 会在 indexed docs 里找最相关的 passage。理想返回应包含证据6-1里的相关片段：

```text
涉嫌接受王静及何晓初请托，安排非本案承办人员介入调解，并将案件作调解结案处理。
```

返回结果中带有：

```text
evidence_id = evd_xxx
evidence_title = evidence_docs/证据6-1_深圳市人民检察院立案决定书.md
score = PPR/检索相关分
```

前端再用 `evidence_id` 取原文，展示在右侧抽屉。

## 8. 当前系统的几个边界

### 8.1 图谱不是最终答案

图谱当前主要承担：

```text
实体/证据路由
关系候选
路径推荐
过滤和可视化
```

它不应该被理解为完整事实真相。真正的结论仍需要回到证据原文和 PPR passage。

### 8.2 字段级溯源本质上是“句子级 query”

当前前端已经把字段拆成句子，点击每一句单独检索。

这比“整个字段一起检索”更接近 citation grounding，但还不是严格的“生成时逐句绑定证据”。严格版本应该在 LLM 生成报告时就要求输出：

```json
{
  "claim": "杨周武涉嫌接受请托。",
  "evidence_ids": ["evd_xxx", "evd_yyy"],
  "supporting_passages": ["..."],
  "confidence": "medium"
}
```

也就是说，现在是“生成后追溯”；更理想的是“生成时带引用”。

### 8.3 结构化数据需要控制入图

银行流水和电话流水如果全部展开，会导致图谱混乱。

合理方向是：

```text
原始流水保留完整
核心流水生成图关系
正常经营流水只作为背景统计或反证材料
```

当前 `realtest/structured` 中只保留：

```text
case_relevant_bank_flows.xlsx
case_relevant_call_records.xlsx
```

用于避免重复导入 `cleaned_*` 和 `case_relevant_*` 两套数据造成图谱重复。

## 9. 推荐的后续优化

为了真正做到“所有字段均可点击 -> 查看证据原文 + 溯源路径 PPR”，建议下一步做三件事：

1. 报告接口返回结构化 claim，而不是纯 Markdown 字符串。
2. 每个 claim 生成时要求模型同时给出候选 `evidence_ids` 和引用 passage。
3. PPR 溯源接口保留当前能力，用于对模型给出的引用做二次校验和补充排序。

这样前端看到的每一句结论，都可以天然带证据锚点，而不是事后再用相似度追回来。
