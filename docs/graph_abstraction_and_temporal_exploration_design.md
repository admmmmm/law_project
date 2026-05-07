# 图谱时间化、母图抽象与节点合并建议设计

## 1. 背景判断

当前画像页的一个问题是：为了让报告更完整，我们在 RAG 查询里显式加入了“时间线、火灾、后果、事故调查”等方向。这能改善单案结果，但本质上还是 **人工指定召回问题**，不是真正让系统理解案情结构。

更稳的方向应当是：

1. 普通非结构化边也带时间信息。
2. 从全量细碎图中抽象出可读的“母图”。
3. DeepSeek 在母图和证据 passage 上做受控多跳探索。
4. 别名、假名、同人不同名由 DeepSeek 提出合并建议，但不自动合并。

画像报告页应当基于这些结构生成，而不是靠固定 prompt 把某些关键词塞进去。

## 2. 问题一：普通边缺少 timestamp

### 2.1 现状

结构化数据的时间比较明确：

- 银行流水有交易时间。
- 通话记录有通话时间。
- 这些时间可以进入 edge properties。

但非结构化证据里的 OpenIE 三元组通常只有：

```text
杨周武 -- 指派 --> 刘力飚
王静 -- 请托 --> 杨周武
同乐派出所 -- 释放 --> 罗贤涛
```

它们缺少：

```json
{
  "time_point": "2024-08-16",
  "time_range": ["2024-08-16", "2024-09-05"],
  "time_text": "2008年8月14日至2008年9月5日期间",
  "time_confidence": 0.84,
  "time_source": "same_sentence | paragraph | document_title | inferred"
}
```

导致图谱无法按时间生长，也无法让 DeepSeek 沿时间顺序探索。

### 2.2 需要新增的时间抽取层

OpenIE 抽取非结构化文本时，不应只输出三元组，而应输出“事件化三元组”：

```json
{
  "subject": "杨周武",
  "relation": "指派",
  "object": "刘力飚",
  "subject_type": "person",
  "object_type": "person",
  "time": {
    "type": "point",
    "value": "2024-08-16",
    "raw": "2008年8月16日以后至2008年9月5日期间",
    "confidence": 0.72
  },
  "event": {
    "event_type": "case_handling",
    "action": "指派非办案人员介入调解",
    "stage": "处置/调解"
  },
  "evidence_id": "evd_xxx",
  "passage_id": "psg_xxx"
}
```

### 2.3 时间继承规则

非结构化文本经常不是每句话都有时间，因此需要分层继承：

1. 句内时间：最高可信。
2. 同段落最近上文时间：中等可信。
3. 文书标题/证据标题时间：中等偏低。
4. 案情表或结构化时间映射：较高，但需要标记为外部映射。
5. 无时间：保留为空，不强行编。

时间分两类：

- `time_point`: 具体日期或时刻。
- `time_range`: 起止范围。

不要把时间一律做成节点。时间主要是 **边/事件的属性**。只有在时间轴视图里，才临时把时间渲染成轴上的刻度。

## 3. 问题二：全量图太复杂，需要“母图”

### 3.1 为什么全量图不可直接用于画像

全量图包含：

- 证据文档节点
- passage 节点
- 人名、机构、账户
- 金额、时间、文书名
- OpenIE 产生的中间抽象节点
- 银行流水和通话流水的明细边

它适合检索和溯源，不适合直接给检察官阅读，也不适合作为 DeepSeek 的主要上下文。

### 3.2 母图的定义

母图不是删除全量图，而是在全量图之上生成一个 **案件骨架图**。

母图节点可以代表：

```text
人物节点：杨周武、王静、何晓初、刘力飚、罗贤涛、江军
组织节点：同乐派出所、舞王俱乐部、深圳市人民检察院
事件节点：故意伤害案、调解结案、释放、火灾事故、检察院立案侦查
资金链节点：27万元好处费链、3万元现金链、11万元赔偿链
通联链节点：请托通话链、调解协调通话链
文书链节点：接警登记、拘留文书、调解处理报告、释放通知、立案决定
```

母图边代表高层关系：

```text
王静 -- 请托/利益输送 --> 杨周武
杨周武 -- 指派/安排 --> 刘力飚
刘力飚 -- 促成 --> 调解结案
调解结案 -- 导致 --> 嫌疑人释放
舞王俱乐部 -- 后续发生 --> 火灾事故
深圳市人民检察院 -- 立案侦查 --> 杨周武
```

每条母图边都保存其子图来源：

```json
{
  "parent_edge_id": "meta_edge_001",
  "label": "请托/利益输送",
  "source": "王静",
  "target": "杨周武",
  "supporting_subgraph": {
    "node_ids": ["person:王静", "person:何晓初", "person:杨周武", "account:曾黎"],
    "edge_ids": ["edge_call_001", "edge_bank_003", "edge_openie_008"],
    "passage_ids": ["psg_12", "psg_19"]
  },
  "time_range": ["2024-08-16", "2024-08-21"],
  "confidence": 0.81
}
```

### 3.3 母图生成策略

第一版可以不用 GNN，也不需要复杂图学习。先做规则 + LLM 归纳：

1. 从全量图中取关键节点：
   - 案件标题中的嫌疑人
   - 立案书中的犯罪嫌疑人、罪名、案由
   - 高度数人物
   - 有资金/通话/文书关联的人物
   - 出现在法律要件相关 passage 中的人物

2. 以关键节点为中心取 k-hop 子图：
   - 默认 2 跳。
   - 对资金/通话可扩到 3 跳。
   - 排除证据文档、passage 明细节点，只保留其引用。

3. 对相同语义边聚合：
   - 多条转账边聚成“资金链”。
   - 多条通话边聚成“通联链”。
   - 多条文书动作聚成“文书处置链”。

4. 让 DeepSeek 对候选链条命名：
   - “请托链”
   - “现金贿赂链”
   - “调解释放链”
   - “后果/事故链”

5. 母图不替代全量图，只是画像和分析页默认使用的阅读图。

## 4. 问题三：DeepSeek 多跳探索不能硬塞全文

### 4.1 当前误区

如果直接把所有 passage、三元组、法律知识塞给 DeepSeek，上下文会很长，而且接近“全文阅读”，HippoRAG 的价值会被削弱。

真正应该做的是把 DeepSeek 当成一个规划者：

```text
DeepSeek 提出下一步要查什么
      ↓
后端执行图查询 / PPR 检索 / 时间范围查询
      ↓
返回少量证据 passage + 子图
      ↓
DeepSeek 再决定是否继续查
```

### 4.2 建议工具接口

第一版可提供 5 个工具：

```text
1. search_passages(query, top_k)
   用 HippoRAG PPR 检索证据片段。

2. expand_node(node_label, depth, relation_filter)
   从某个节点出发扩展子图。

3. search_time_range(start, end, keywords)
   按时间范围查事件、边和 passage。

4. get_meta_graph(focus)
   获取母图局部。

5. get_legal_context(offense_id, query)
   查法律知识库和办案模板。
```

DeepSeek 每轮最多调用 3 到 5 次工具。每次只返回 top 5 到 top 10 的结果，避免上下文膨胀。

### 4.3 多跳探索流程

以画像报告为例：

1. 读取立案书和案件基础信息。
2. 确定核心嫌疑人和罪名。
3. 从嫌疑人节点出发扩展 2 跳母图。
4. 对每个高价值邻居做定向检索：
   - 关系：谁请托谁、谁指派谁。
   - 时间：行为发生前后顺序。
   - 资金：是否与处置节点前后呼应。
   - 结果：是否出现释放、调解、撤案、后续严重后果。
5. 生成画像段落。
6. 每句话绑定生成时实际使用的 passage 和子图边。

这比“固定查询火灾”更泛化。换一个罪名或案件，也能从立案书和母图结构中决定该查什么。

## 5. 节点合并建议功能

### 5.1 目标

系统不能贸然合并节点。它只能提出建议：

```text
“曾黎”可能是“何晓初”的控制账户或马甲账户。
“李四”可能对应“杨周武”的银行流水化名。
“同乐所所长”可能指向“杨周武”。
```

用户确认后，才建立 `same_as` 或 `controlled_by` 等人工确认关系。

### 5.2 DeepSeek 输入

合并建议需要给 DeepSeek 的不是全图，而是候选对：

候选对来源：

1. 名称相似：
   - 杨周武 / 杨所长 / 同乐所所长
2. 身份线索：
   - “曾黎，何晓初控制账户”
3. 同手机号、同身份证、同账号、同地址：
   - 强候选
4. 银行流水映射表：
   - 张三 -> 王静
   - 李四 -> 杨周武
5. 同一 passage 内明确说明：
   - “何晓初收到钱后发短信告诉杨周武”
6. 图结构相似：
   - 两个节点连接同一批人、同一批账户、同一时间段。

### 5.3 输出结构

```json
{
  "suggestions": [
    {
      "suggestion_id": "merge_sug_001",
      "left_node": "account:曾黎",
      "right_node": "person:何晓初",
      "suggested_relation": "controlled_by",
      "confidence": 0.82,
      "reason": "银行流水中曾黎账户在何晓初相关请托节点后接收现金，证据中又出现何晓初向杨周武转述收钱情况。",
      "supporting_evidence_ids": ["evd_xxx", "evd_yyy"],
      "supporting_passages": ["..."],
      "risk": "不能直接合并为同一自然人，只能建议为控制/代持关系。"
    }
  ]
}
```

### 5.4 前端交互

图谱页或画像页增加“合并建议”区域：

```text
候选：曾黎 -> 何晓初
建议关系：controlled_by
置信度：82%
证据：2份
[查看证据] [采纳为控制关系] [忽略]
```

采纳后：

- 不删除原节点。
- 新增人工确认边：

```text
何晓初 -- 控制账户 --> 曾黎
```

如果确实是同一人，再由用户选择更强操作：

```text
合并为同一实体 same_as
```

默认不做强合并。

## 6. 和画像报告页的关系

画像报告页未来不应直接从全量图生成，而应使用：

```text
立案书/案件基础信息
      +
法律知识 RAG
      +
母图
      +
必要的全量图局部展开
      +
句子级 passage 溯源
      +
人工确认的合并/控制关系
```

报告生成流程：

1. 读取案件罪名和立案书。
2. 构建或读取母图。
3. DeepSeek 从嫌疑人节点开始做受控多跳。
4. 遇到别名/马甲账户时查询合并建议。
5. 生成：
   - 人物关系画像
   - 行为事实还原
   - 资金/通联/文书链条
   - 主观方面推理
   - 缺口与补强方向
6. 每个段落记录：
   - 使用了哪些工具
   - 哪些母图边
   - 哪些 passage
   - 哪些法律知识片段

页面上只展示简短的工具说明，详细调用记录折叠起来。

## 7. 推荐实施顺序

### 第一阶段：时间化边

1. 修改 OpenIE 输出 schema，要求返回 time。
2. 对非结构化 passage 做句内/段落时间继承。
3. 图谱 edge 增加：
   - `time_point`
   - `time_range`
   - `time_text`
   - `time_confidence`
   - `time_source`
4. 时间轴生长改为真实依据 edge 时间。

### 第二阶段：母图

1. 新增 `meta_graph_service.py`。
2. 从全量图抽取核心节点和高价值链条。
3. 聚合资金、通话、文书、处置、后果链。
4. 图谱页增加“全量图 / 母图”切换。
5. 画像页默认读取母图。

### 第三阶段：节点合并建议

1. 新增候选生成器：
   - 名称相似
   - alias 映射
   - 同账号/手机号
   - 图结构相似
2. 让 DeepSeek 审查候选对。
3. 前端展示建议，不自动合并。
4. 用户采纳后写入人工确认边。

### 第四阶段：DeepSeek 工具化多跳画像

1. 提供 `search_passages / expand_node / search_time_range / get_meta_graph / get_legal_context`。
2. DeepSeek 分轮调用。
3. 每轮限制上下文大小。
4. 每句话绑定实际使用的 passage 和母图边。

## 8. 关键原则

1. 不靠 prompt 硬塞特定案情关键词。
2. 时间是边/事件属性，不是普通实体节点。
3. 母图是阅读图，不替代全量图。
4. DeepSeek 负责归纳和规划，不负责无约束漫游。
5. 节点合并只做建议，最终必须人工确认。
6. 画像报告的每句话都必须能回到 passage 或图谱边。


------
# Agentic RAG 检索计划器改造方案

## Summary
把当前“后端固定 query → 检索 → DeepSeek 一次生成”改成“模型规划检索 → 后端执行工具 → 模型评估缺口 → 循环检索 → Pro 模型生成报告”的 agentic RAG。第一版用于智能分析页和画像报告页，重点解决：故事不全、固定 prompt 治标不治本、上下文一次性过长、检索过程不可解释。

## Key Changes

### 1. 新增检索计划器
- 新增 `RetrievalPlannerService`，负责一次分析任务的循环：
  1. 构造初始 brief：案件标题、罪名、立案书摘要、当前问题、已有图谱摘要。
  2. 调用规划模型生成下一轮工具调用计划。
  3. 执行工具并记录结果。
  4. 让模型评估“信息缺口是否已足够覆盖”。
  5. 达到终止条件后，调用 Pro 模型生成最终画像/分析文本。
- 模型分工：
  - 规划模型：新增 `DEEPSEEK_PLANNER_MODEL`，默认 `deepseek-chat`，负责便宜快速地产生工具调用。
  - 生成模型：沿用 `DEEPSEEK_ANALYSIS_MODEL`，默认 `deepseek-reasoner`，负责最终报告、假设验证、资金分析。
- 终止条件：
  - 默认最多 4 轮。
  - 每轮最多 5 个工具调用。
  - 连续一轮没有新增 passage/graph fact 时停止。
  - 模型输出 `ready_to_answer=true` 时停止。
  - 超时或工具错误时降级为已有上下文生成，但标明检索不完整。

### 2. 封装可调用工具
- 后端提供内部工具，不直接暴露给前端：
  - `search_documents(query, top_k=8)`：调用现有 HippoRAG `retrieve_trace`，返回 passage。
  - `search_graph(query, k=20)`：从当前图谱中按关键词、节点名、关系名召回边和节点。
  - `expand_node(node_label, depth=2, relation_filter=null)`：从某节点出发取局部子图。
  - `search_time_range(start, end, keywords=[])`：按 edge timestamp / time_range / passage 时间文本召回事件；第一版若普通边无 timestamp，则用已有 `time` properties 和文本时间兜底。
  - `search_legal(query, top_k=6)`：调用 `LegalKnowledgeService.retrieve`。
- 工具结果统一压缩为：
  - `tool_call_id`
  - `tool_name`
  - `arguments`
  - `summary`
  - `passages`
  - `graph_facts`
  - `legal_passages`
  - `new_entities`
  - `errors`
- 每条最终生成句子只能绑定实际出现过的 `tool_call_id + passage/edge`。

### 3. 新增会话状态和持久化
- 新增 schema：
  - `RetrievalSession`
  - `RetrievalStep`
  - `RetrievalToolCall`
  - `RetrievalArtifact`
- 存储到现有 SQLite：
  - `retrieval_sessions`
  - `retrieval_steps`
- 每次智能分析会话和画像报告都保存：
  - 模型提出的检索目标
  - 每轮工具调用
  - 返回的 passage / graph facts / legal facts
  - 模型对缺口的评估
  - 最终使用的证据集合
- 前端不展示完整思维链，只展示简短说明：
  - “本报告经过 3 轮检索，调用文档检索 7 次、图谱扩展 3 次、法律知识 2 次。”
  - 详细调用记录折叠展示。

### 4. 接入智能分析页和画像报告页
- 智能分析页：
  - 新建/追问时调用 agentic RAG，而不是 `_analysis_queries()` 固定问题列表。
  - 保留现有会话卡片、删除、@证据机制。
  - `@证据` 会成为 planner 的强约束：首轮必须检索指定证据。
- 事实画像页：
  - 替换 `_portrait_queries()` 固定列表。
  - 初始 brief 必须包含立案书/案件基础信息。
  - 目标固定为：人物关系、行为事实、时间线、结果后果、关键缺口。
- 详细画像报告：
  - 替换 `_select_report_passages_with_hipporag()` 的固定 query。
  - 报告段落生成前先跑 agentic retrieval session。
  - 每个段落附简短工具调用摘要，每句话仍走现有句子级溯源。

### 5. 上下文控制策略
- 每轮只把上一轮摘要、未解决缺口、top artifacts 传回模型，不 dump 全量历史。
- Artifact 去重规则：
  - 同 `evidence_id + passage` 只保留最高分。
  - 同一工具连续召回高度重复内容时，保留摘要不再传全文。
- 最终生成输入限制：
  - passages 最多 40 条。
  - graph facts 最多 80 条。
  - legal passages 最多 10 条。
  - tool call summaries 全量保留，但正文压缩到每条 120 字以内。

## Public Interfaces / Types
- 新增后端内部配置：
  - `DEEPSEEK_PLANNER_MODEL=deepseek-chat`
  - `AGENTIC_RAG_MAX_ROUNDS=4`
  - `AGENTIC_RAG_MAX_TOOL_CALLS_PER_ROUND=5`
- 扩展前端 API 返回字段：
  - `tool_call_summary`
  - `retrieval_session_id`
  - `retrieval_steps_count`
- 新增只读调试接口：
  - `GET /api/v1/cases/{case_id}/analysis/retrieval-sessions/{session_id}`
  - 返回工具调用记录、召回摘要、错误，不返回模型隐藏推理。

## Test Plan
- 单元测试：
  - planner JSON 解析失败时能重试/降级。
  - 工具调用参数非法时被拒绝并记录错误。
  - passage 去重、top-k 限制、时间范围过滤正确。
- 集成测试：
  - 假设验证：模型至少产生 `search_documents` 和 `search_graph` 调用。
  - 可疑资金流：模型至少产生资金相关 `search_documents` 和 `expand_node` 调用。
  - 事实画像：包含立案书、人物关系、行为事实、结果后果四类检索目标。
  - 画像报告切页后不重新生成，读取已保存 `retrieval_session_id`。
- 前端验收：
  - 智能分析答案仍可按句点击溯源。
  - 报告显示简短“检索轮次/工具调用”说明。
  - 调试抽屉可查看每轮工具调用，但默认折叠。

## Assumptions
- “Flash”在本项目中落地为 `deepseek-chat` 规划模型；“Pro”落地为 `deepseek-reasoner` 分析模型。
- 第一版不使用 DeepSeek 官方函数调用协议，而采用 JSON tool-plan 协议，由后端解析执行，更容易和现有 `urllib` 调用兼容。
- 第一版 `search_time_range` 先使用现有结构化时间和文本时间兜底；普通 OpenIE 边全面 timestamp 化放到下一步图谱时间化改造。
- 不暴露模型内部推理，只保存和展示检索计划、工具调用、召回结果、缺口评估摘要。
