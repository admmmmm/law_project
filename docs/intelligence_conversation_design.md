# 智能分析页对话式工作区设计

## 1. 目标

智能分析页不再只是“点击按钮 -> 生成一段分析 -> 前端临时展示”。

它应变成一个可持久化的分析工作区：

```text
假设验证
  -> 多个分析会话卡片
  -> 点击卡片查看会话
  -> 可以继续追问
  -> 可以新建会话
  -> 可以删除会话
  -> 每条答案句子可溯源

可疑资金流
  -> 同样是一组分析会话卡片
  -> 支持多轮对话、删除、溯源
```

前端只负责展示和交互；生成结果必须保存在后端，切换页面、刷新页面后仍然存在。

## 2. 页面结构

智能分析页分成三块：

```text
┌──────────────────────────────────────────────┐
│ 当前案件 / 当前罪名 / 分析模式说明             │
├──────────────────────────────────────────────┤
│ 左侧：分析类型                                │
│   1. 跨案件碰撞                               │
│   2. 假设验证                                 │
│   3. 可疑资金流                               │
├──────────────────────────────────────────────┤
│ 中间：当前类型下的会话卡片列表                 │
│   [假设：杨周武可能篡改文书...]                │
│   [假设：刘力飚介入是否异常...]                │
│   [资金：王静 -> 何晓初 -> 杨周武...]          │
├──────────────────────────────────────────────┤
│ 右侧/主区：选中会话的消息流                    │
│   用户问题                                    │
│   DeepSeek 答案                               │
│   继续追问输入框                              │
└──────────────────────────────────────────────┘
```

第一版可以不做复杂三栏，最小可用布局为：

```text
顶部：模式 tabs
中部：会话卡片列表
下部：选中会话详情
```

## 3. 会话卡片

### 3.1 卡片是什么

每一张卡片对应一个后端持久化的分析会话。

卡片字段：

```json
{
  "thread_id": "ath_xxx",
  "case_id": "case_xxx",
  "mode": "hypothesis",
  "title": "杨周武可能对执法文书做了倒签或补录",
  "summary": "目前材料显示存在文书时间线核查必要，但直接篡改证据不足。",
  "created_at": "2026-05-06T...",
  "updated_at": "2026-05-06T...",
  "message_count": 4,
  "status": "active"
}
```

### 3.2 卡片显示

卡片只显示缩略信息：

```text
假设验证
杨周武可能对执法文书做了倒签或补录
4轮对话 / 更新于 21:34

摘要：存在时间线核查必要，直接篡改证据不足。
```

卡片上有：

- 点击：选中并打开详情
- 删除按钮：删除这个会话
- 状态标记：假设验证 / 可疑资金流

### 3.3 选中状态

点击卡片后：

```text
selected_thread_id = thread_id
```

页面加载该 thread 的完整消息流。

再次点击其他卡片，切换会话，不重新生成。

## 4. 多轮对话

### 4.1 新建会话

假设验证：

```text
用户输入一个假设：
“杨周武可能对某些文件做了篡改或倒签。”

点击：新建假设验证
```

后端创建 thread：

```text
POST /api/v1/cases/{case_id}/intelligence/threads
```

请求：

```json
{
  "mode": "hypothesis",
  "title": "杨周武可能对某些文件做了篡改或倒签",
  "initial_question": "杨周武可能对某些文件做了篡改或倒签，请检索证据验证。"
}
```

返回 thread + 第一轮答案。

可疑资金流：

可以允许用户输入，也可以有默认问题：

```text
“请分析本案是否存在可疑资金流、现金化、过桥账户或资金与处置节点呼应的问题。”
```

### 4.2 继续追问

选中一个会话后，下方有输入框：

```text
继续追问： [输入问题]
```

请求：

```text
POST /api/v1/cases/{case_id}/intelligence/threads/{thread_id}/messages
```

请求体：

```json
{
  "question": "把证据6-1和通话记录放在同一时间线上看，是否支持这个假设？"
}
```

后端加载该 thread 历史消息，把历史摘要 + 当前问题 + RAG 结果发给 DeepSeek。

## 5. 后端存储

新增两个后端结构。

### 5.1 AnalysisThread

```python
class AnalysisThread(BaseModel):
    thread_id: str
    case_id: str
    mode: Literal["hypothesis", "financial_flow", "cross_case"]
    title: str
    summary: str = ""
    status: Literal["active", "archived"] = "active"
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
```

### 5.2 AnalysisMessage

```python
class AnalysisMessage(BaseModel):
    message_id: str
    thread_id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    claims: list[GroundedSentence] = []
    retrievals: list[TracePassage] = []
    graph_context: list[str] = []
    legal_context: list[TracePassage] = []
```

### 5.3 GroundedSentence

用于句子级溯源。

```python
class GroundedSentence(BaseModel):
    sentence_id: str
    text: str
    start: int
    end: int
    status: Literal["supported", "weak", "unsupported"]
    supporting_passages: list[TracePassage]
    supporting_graph_paths: list[TracePath]
    confidence: float
```

这里的 `start/end` 是在 assistant `content` 中的位置，方便前端高亮句子。

## 6. 数据库表

`MemoryStore` 目前已有 SQLite 持久化。新增两张表：

```sql
CREATE TABLE IF NOT EXISTS analysis_threads (
  case_id TEXT NOT NULL,
  thread_id TEXT PRIMARY KEY,
  payload TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analysis_messages (
  case_id TEXT NOT NULL,
  thread_id TEXT NOT NULL,
  message_id TEXT PRIMARY KEY,
  payload TEXT NOT NULL
);
```

后端内存结构：

```python
analysis_threads: dict[str, list[AnalysisThread]]
analysis_messages: dict[str, list[AnalysisMessage]]
```

按 `case_id` 分组。

## 7. 后端接口

### 7.1 列出会话

```text
GET /api/v1/cases/{case_id}/intelligence/threads?mode=hypothesis
```

返回：

```json
[
  {
    "thread_id": "ath_xxx",
    "mode": "hypothesis",
    "title": "...",
    "summary": "...",
    "message_count": 4,
    "updated_at": "..."
  }
]
```

### 7.2 创建会话

```text
POST /api/v1/cases/{case_id}/intelligence/threads
```

请求：

```json
{
  "mode": "hypothesis",
  "title": "文书是否存在倒签或补录",
  "initial_question": "请验证这个假设。"
}
```

后端动作：

1. 创建 thread。
2. 保存 user message。
3. 执行多轮 RAG。
4. 调 DeepSeek。
5. 对答案做句子切分和溯源绑定。
6. 保存 assistant message。
7. 返回 thread detail。

### 7.3 获取会话详情

```text
GET /api/v1/cases/{case_id}/intelligence/threads/{thread_id}
```

返回：

```json
{
  "thread": {...},
  "messages": [...]
}
```

### 7.4 继续对话

```text
POST /api/v1/cases/{case_id}/intelligence/threads/{thread_id}/messages
```

请求：

```json
{
  "question": "结合证据6-1再看一次。"
}
```

返回更新后的 thread detail。

### 7.5 删除会话

```text
DELETE /api/v1/cases/{case_id}/intelligence/threads/{thread_id}
```

删除 thread 和 messages。

第一版可以真删，不做 archive。

## 8. DeepSeek 多轮 RAG 流程

每次生成答案时，后端组织上下文：

```text
1. 当前案件信息
2. 当前选择罪名，可为空
3. 当前 thread 历史摘要
4. 用户当前问题
5. 案件证据 HippoRAG passages
6. 法律知识 HippoRAG passages
7. 图谱 triples / edges
8. 上一轮 assistant 的结论和未解问题
```

然后 DeepSeek 输出：

```json
{
  "answer": "连续中文分析文本...",
  "claims": [
    {
      "sentence": "材料显示某文书形成时间与通话节点接近，存在核查必要。",
      "source_passage_ranks": [2, 5],
      "source_graph_path_ids": ["p1"],
      "status": "weak",
      "confidence": 0.62
    }
  ],
  "summary": "本轮认为存在核查必要，但直接证据不足。",
  "next_questions": [
    "调取原始文书元数据",
    "核对审批流和打印时间"
  ]
}
```

重要规则：

```text
法律知识只能作为分析框架。
本案事实必须来自证据 passage 或图谱上下文。
没有证据支撑的句子标为 unsupported，不应作为结论。
```

## 9. 句子级溯源

### 9.1 前端交互

答案文本渲染为句子片段：

```html
<span class="grounded-sentence supported">材料显示……</span>
<span class="grounded-sentence weak">存在核查必要……</span>
```

交互：

- 鼠标 hover：句子高亮
- 点击句子：右侧/下方打开来源面板
- 来源面板显示：
  - 支撑 passage
  - 证据标题
  - 分数
  - 图谱路径
  - 状态：证据支撑 / 支撑较弱 / 暂无支撑

### 9.2 如果 DeepSeek 没绑定来源

后端兜底：

```text
对每个句子调用 retrieve_trace(sentence)
取 top passages
如果分数过低，标为 unsupported
```

第一版可以这样做，后续再要求 DeepSeek 严格输出 source ranks。

## 10. 前端状态

智能分析页状态：

```ts
activeMode: 'hypothesis' | 'financial_flow' | 'cross_case'
threads: AnalysisThread[]
selectedThreadId: string | null
selectedThreadDetail: AnalysisThreadDetail | null
newQuestion: string
loading: boolean
selectedSentence: GroundedSentence | null
```

切换页面再回来：

```text
重新 GET threads
如果 localStorage 有 selectedThreadId，就尝试恢复选中。
```

不再依赖前端缓存保存结果。

## 11. 页面简化原则

不要再展示一堆“自动生成的小卡片”。

应只展示：

```text
会话卡片列表
选中会话的消息流
继续追问输入框
句子溯源面板
```

分析内容以文段为主，不要强行拆成很多空洞卡片。

## 12. 与画像页的关系

智能分析页的会话不是事实结论。

如果用户认可某段分析，可以后续加“采纳到疑点画像”按钮。

第一版可以先不做采纳，只做持久化会话。

后续：

```text
智能分析会话
  -> 用户选中某条 assistant answer 或 sentence
  -> 采纳为疑点
  -> 画像页显示“疑点画像”
```

## 13. 实施顺序

建议分五步做：

1. 后端新增 `AnalysisThread` / `AnalysisMessage` schema 和 SQLite 持久化。
2. 新增 threads CRUD 接口。
3. 复用现有 `_deepseek_tool_loop_answer`，包装成“创建会话/继续对话”。
4. 前端智能分析页改成会话卡片 + 消息流。
5. 加句子级渲染和点击溯源面板。

其中第 1-4 步先完成，就能解决“结果丢失、不能多轮、不能删除”的问题。

第 5 步解决“答案每句话可溯源”。

## 14. 我的问题

1. “跨案件碰撞”也要做成同样的会话卡片吗？还是第一版只改“假设验证”和“可疑资金流”？
跨案件碰撞不用
2. 删除会话是真删除，还是放入“已删除/归档”可恢复？我建议第一版真删除。
真删除
3. 继续追问时，是否允许用户手动指定只查某几份证据？第一版可以先不做。
继续追问可以针对某份证据吧。用户可以说，你查看一下@ 什么什么证据。这时候我们传给deepseek要自动把证据的passage传进去。这里@要有标准，要有自动补全。如果输入了不存在的证据要给出提醒。
4. 句子级溯源面板是放右侧抽屉，还是直接在答案下方展开？我建议右侧抽屉，但移动端自动变成下方展开。
溯源面板听你的
