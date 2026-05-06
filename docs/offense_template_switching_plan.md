# 罪名可选与法律知识 RAG 简化方案

## 1. 这次的原则

我们不要把系统做成复杂的“自动定罪机器”，也不要按某个具体案件写死逻辑。

正确目标是：

```text
检察官创建案件时，可以选择一个罪名，也可以留空。

如果选择罪名：
  DeepSeek 分析时参考对应罪名的法律知识和办案模板。

如果留空：
  DeepSeek 只按证据事实做人物关系、行为还原、疑点分析，不强行套法条。
```

所以这不是“杨周武案模板切换”，也不是“系统自动判断罪名”。它只是给 DeepSeek 更好的上下文。

## 2. 基础信息页改动

案件基础信息页增加一个下拉菜单：

```text
涉嫌罪名： [请选择 / 留空]
```

下拉菜单列出 14 个罪名：

1. 非法拘禁罪
2. 非法搜查罪
3. 刑讯逼供罪
4. 暴力取证罪
5. 虐待被监管人罪
6. 滥用职权罪
7. 玩忽职守罪
8. 徇私枉法罪
9. 民事、行政枉法裁判罪
10. 执行判决、裁定失职罪
11. 执行判决、裁定滥用职权罪
12. 私放在押人员罪
13. 失职致使在押人员脱逃罪
14. 徇私舞弊减刑、假释、暂予监外执行罪

可以留空。留空表示：

```text
本案暂不按特定罪名组织分析，先就证据事实进行关系还原和行为梳理。
```

## 3. 罪名从哪里来

优先由人选。

因为真实办案里，立案材料通常会写：

- “涉嫌徇私枉法罪”
- “因涉嫌……被立案侦查”
- “犯罪嫌疑人……涉嫌……一案”

后续可以做自动识别，但不是第一优先级。

第一版只做：

```text
前端下拉选择 -> 保存到 case.offense_id
```

如果以后要做自动识别，可以作为辅助提示：

```text
系统从立案决定书中识别到“徇私枉法罪”，是否填入？
```

但最终仍由用户确认。

## 4. data/legal_knowledge 也进入 RAG

现在证据材料进入 HippoRAG，但法律知识库也应该能被 DeepSeek 查询。

需要把下面这些文件作为“法律知识语料”建索引：

```text
data/legal_knowledge/sources.json
data/legal_knowledge/evidence_type_mapping.json
data/legal_knowledge/offense_templates/index.json
data/legal_knowledge/offense_templates/*.json
十四种犯罪的构成要件.md
初期进展/十四种犯罪的构成要件.md
```

法律知识 RAG 和案件证据 RAG 分开：

```text
案件证据 RAG：回答“本案材料里有什么事实”
法律知识 RAG：回答“这个罪名通常要查什么、证据怎么归类、缺口是什么”
```

DeepSeek 分析时同时拿两类上下文：

```text
证据 passages
法律知识 passages
图谱 triples
用户选择的罪名（可为空）
```

这样就够了，不需要搞太重的 ontology 决策层。

## 5. DeepSeek 提示词怎么改

### 5.1 如果选择了罪名

提示词核心：

```text
你是检察侦查辅助分析助手。

当前案件选择的罪名是：徇私枉法罪。

你会收到三类材料：
1. 本案证据 passage
2. 本案图谱三元组
3. 法律知识/办案模板 passage

请先还原事实，再参考罪名要件分析。
不要脱离证据直接下结论。
不要写“构成犯罪”的最终判断，只输出侦查参考。

输出结构：
1. 人物关系
2. 行为事实还原
3. 与本罪名要件相关的证据
4. 证据缺口
5. 需要继续调取的材料
6. 可疑点或反侦察迹象
```

重点是：

```text
法律知识是分析框架，不是事实来源。
证据 passage 才能支撑事实判断。
```

### 5.2 如果罪名留空

提示词核心：

```text
当前案件未选择罪名。

请不要强行套用任何罪名构成要件。
只根据证据 passage 和图谱三元组完成：
1. 人物关系还原
2. 行为事实还原
3. 时间线梳理
4. 可疑信息提示
5. 证据缺口

如材料中出现明确罪名表述，可以提示“材料中出现某罪名字样”，但不要直接按该罪名定性。
```

这样换普通案件、小说材料、非标准材料时也不会崩。

## 6. 画像页怎么用

画像页先保持简单。

### 6.1 罪名为空

显示：

```text
人物关系
行为事实
时间线
可疑信息
证据缺口
```

不显示“主体要件、客观要件、主观方面”这类法律章节。

### 6.2 罪名不为空

显示：

```text
人物关系
行为事实
时间线
要件参考
证据缺口
补查建议
```

“要件参考”来自法律知识 RAG 和对应模板，不再是后端硬编码。

## 7. 智能分析页怎么用

智能分析页仍然做三类：

1. 假设验证
2. 可疑资金流
3. 跨案件临时分析

区别只是 DeepSeek 的上下文增加了法律知识 RAG。

如果选择了罪名，DeepSeek 会参考该罪名模板。

如果罪名留空，DeepSeek 就只根据事实材料分析。

## 8. 后端最小改动

### 8.1 Case 增加一个字段

```text
offense_id: string | null
```

可选扩展：

```text
offense_name
```

不需要一开始就做 confidence、source_evidence_ids、review_status。

### 8.2 新增法律知识 RAG

可以做一个简单服务：

```text
LegalRAGService
  - build_index()
  - retrieve(query, offense_id=None, top_k=8)
```

第一版甚至可以不用 HippoRAG，先用 embedding 或关键词召回也行。

但理想上，法律知识也走和证据相同的 RAG 接口，DeepSeek 不需要知道底层差异。

### 8.3 画像/分析服务改提示词

当前重点不是重构全部流程，而是把 DeepSeek 调用改成：

```text
evidence_context = evidence_rag.retrieve(...)
legal_context = legal_rag.retrieve(..., offense_id=case.offense_id)
graph_context = graph triples

DeepSeek(evidence_context + legal_context + graph_context + prompt)
```

### 8.4 禁止专案硬编码

后端分析服务中不应出现：

```text
王静、何晓初、刘力飚、罗贤涛、易承桂
```

这类名字作为默认检索问题。

如果这些名字来自当前证据，可以使用。

如果当前案子没有这些名字，就不能问这些问题。

## 9. 前端最小改动

### 9.1 案件基础信息页

增加罪名下拉。

保存后写入案件。

### 9.2 画像页

根据 `offense_id` 是否为空，切换标题和章节。

不要让页面假装已经做了法律要件核查。

### 9.3 智能分析页

显示当前使用模式：

```text
当前模式：事实分析
```

或：

```text
当前模式：徇私枉法罪参考分析
```

## 10. 数据文件建议

继续使用现有目录：

```text
data/legal_knowledge/
  sources.json
  template_schema.json
  evidence_type_mapping.json
  offense_templates/
    index.json
    xunsi_wangfa.json
```

短期只需要补：

```text
offense_templates/*.json
```

每个罪名模板不要太复杂，先包含：

```json
{
  "offense_id": "wanhu_zhishou",
  "name": "玩忽职守罪",
  "focus_questions": [
    "行为人负有什么职责？",
    "有哪些应履行而未履行或未认真履行的事实？",
    "造成了什么损失或严重后果？",
    "未履职与后果之间是否存在因果关系？"
  ],
  "evidence_focus": [
    "岗位职责",
    "工作记录",
    "制度规定",
    "后果鉴定",
    "督办或整改记录"
  ],
  "report_sections": [
    "职责权限",
    "未履职事实",
    "后果与因果关系",
    "证据缺口",
    "补查建议"
  ]
}
```

这比一开始写复杂 schema 更实用。

## 11. 实施顺序

1. 基础信息页增加 14 罪名下拉，可留空。
2. 后端 Case 增加 `offense_id`。
3. `data/legal_knowledge` 建 RAG 索引。
4. 画像/智能分析提示词接入：
   - evidence passage
   - graph triples
   - legal knowledge passage
   - offense_id 可为空
5. 删除分析服务里的具体案件人物硬编码。
6. 先补 14 个轻量模板，不追求复杂。

## 12. 我还有的问题

1. 罪名下拉放在“案件管理/基础信息页”即可，还是导入首页也要出现？
2. 如果用户选择多个罪名，第一版是否允许？还是先只允许单选？
3. 法律知识 RAG 第一版可以用关键词/embedding 简化召回，还是你希望直接接 HippoRAG？
4. “十四种犯罪的构成要件.md”目前根目录和 `初期进展/` 下各有一份，后续以哪一份作为正式知识源？

