# 检察侦查画像模型后端骨架

这个后端骨架服务于“数据处理、分析、碰撞、画像与侦查参考建议”这条主流程。当前重点不是把算法一次性写满，而是先把后端龙骨搭出来，让算法核心、人工干预、记忆功能和前端都能并行接入。

## 模块边界

- `api/`：面向前端的 HTTP 接口。
- `core/`：配置、异常、通用依赖。
- `schemas/`：前后端契约数据结构。
- `services/`：业务编排层，负责把导入、分析、图谱、记忆、报告串起来。
- `adapters/`：外部能力适配层，后续接 HippoRAG、BGE-M3、LLM、图数据库、对象存储等。
- `storage/`：当前原型阶段的内存存储，后续可替换为数据库实现。

## 核心流程

1. 创建案件。
2. 导入依法调取的数据文件或文本。
3. 解析为证据材料、实体、关系和段落引用。
4. 调用算法核心进行图谱构建、碰撞分析和风险线索生成。
5. 支持人工修正节点、关系和错误三元组。
6. 将侦查员与系统交互中确认的新事实加入记忆，并可写回图谱。
7. 输出画像报告和参考建议。

## 启动方式

先确认 [backend/.env](./.env) 已经存在，并把里面的 `DEEPSEEK_API_KEY` 改成真实 key。不要提交 `.env`，只提交 `.env.example`。

后端必须用已经验证过的 Python 3.10，不要用 Miniconda base：

```powershell
cd C:\Users\adm14\Desktop\law_project\backend
C:\Users\adm14\AppData\Local\Programs\Python\Python310\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

前端：

```powershell
cd C:\Users\adm14\Desktop\law_project\frontend
npm run dev
```

浏览器打开：

```text
http://127.0.0.1:5173
```

后端检查地址：

- API 文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/api/v1/health`
- HippoRAG 状态：`http://127.0.0.1:8000/api/v1/health/hipporag`

## HippoRAG 接入

当前默认算法提供方已经切到 `hipporag`。运行分析时，后端会把已导入证据的 passage 写入 HippoRAG，执行 LLM/OpenIE、BGE-M3 embedding、HippoRAG 图构建，再把 OpenIE 抽出的事实三元组合并进业务图谱。

后端启动时会读取 [backend/.env](./.env)，并把变量加载进进程环境，供 HippoRAG / DeepSeek / Transformers 使用。

可调环境变量：

- `ALGORITHM_PROVIDER=hipporag`：启用 HippoRAG；临时调试可设为 `stub`。
- `HIPPORAG_LLM_NAME=deepseek-chat`
- `HIPPORAG_LLM_BASE_URL=https://api.deepseek.com`
- `HIPPORAG_EMBEDDING_MODEL=本地 BGE-M3 路径`
- `HIPPORAG_MAX_DOCS=80`：单次分析最多送入 HippoRAG 的 passage 数，避免联调时过慢。
- `HIPPORAG_SAVE_DIR=../outputs/hipporag_cases`
- `HIPPORAG_FAIL_FAST=true`：默认开启。HippoRAG 缺 key、模型或环境不可用时直接让分析失败，避免把规则 stub 图误当成 LLM/OpenIE 结果。
- `HIPPORAG_ENABLE_QA=true`：默认开启。分析阶段会调用 HippoRAG `rag_qa()`，围绕基础信息、行为事实和主观方面生成问答式研判。
- `HIPPORAG_QA_TOP_K=5`：每个问题喂给 LLM 阅读的召回片段数量。

注意：非结构化文本的旧规则抽取只保留为 passage 切分兜底，不再默认入图。图谱里的开放域事实关系应来自 HippoRAG 的 LLM/OpenIE；智能分析和画像报告里的自然语言研判应来自 HippoRAG `rag_qa()`。如果看到大量“提及/职务行为/关联”，说明运行的不是当前 HippoRAG 主链路，或服务没有重启到最新代码。

## 与外部模块的接入点

- 算法核心：替换 `app/adapters/algorithm.py` 中的 `AlgorithmAdapter` 实现。
- 人工干预：前端调用 `PATCH /api/v1/cases/{case_id}/graph/interventions`。
- 记忆功能：前端调用 `POST /api/v1/cases/{case_id}/memories`，确认事实后可触发写回图谱。
- 前端：所有接口统一挂在 `/api/v1` 下。
