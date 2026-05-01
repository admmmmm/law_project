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

## 运行

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

访问：

- API 文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/api/v1/health`

## HippoRAG 接入

当前默认算法提供方已经切到 `hipporag`。运行分析时，后端会把已导入证据的 passage 写入 HippoRAG，执行 LLM/OpenIE、BGE-M3 embedding、HippoRAG 图构建，再把 OpenIE 抽出的事实三元组合并进业务图谱。

建议使用已经验证过的 Python 3.10 环境，不要用 Miniconda base：

```powershell
cd C:\Users\adm14\Desktop\law_project\backend
$env:DEEPSEEK_API_KEY="你的 DeepSeek Key"
$env:TRANSFORMERS_OFFLINE="1"
$env:HF_HUB_OFFLINE="1"
$env:HIPPORAG_EMBEDDING_MODEL="C:\Users\adm14\.cache\huggingface\hub\BAAI\bge-m3"
C:\Users\adm14\AppData\Local\Programs\Python\Python310\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

可调环境变量：

- `ALGORITHM_PROVIDER=hipporag`：启用 HippoRAG；临时调试可设为 `stub`。
- `HIPPORAG_LLM_NAME=deepseek-chat`
- `HIPPORAG_LLM_BASE_URL=https://api.deepseek.com`
- `HIPPORAG_EMBEDDING_MODEL=本地 BGE-M3 路径`
- `HIPPORAG_MAX_DOCS=80`：单次分析最多送入 HippoRAG 的 passage 数，避免联调时过慢。
- `HIPPORAG_SAVE_DIR=../outputs/hipporag_cases`

如果没有 key 或模型环境不可用，系统不会中断分析，会回落到现有规则聚合图，并在图谱中 `HippoRAG` 算法节点的属性里显示错误。

## 与外部模块的接入点

- 算法核心：替换 `app/adapters/algorithm.py` 中的 `AlgorithmAdapter` 实现。
- 人工干预：前端调用 `PATCH /api/v1/cases/{case_id}/graph/interventions`。
- 记忆功能：前端调用 `POST /api/v1/cases/{case_id}/memories`，确认事实后可触发写回图谱。
- 前端：所有接口统一挂在 `/api/v1` 下。




cd C:\Users\adm14\Desktop\law_project\backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
-----
cd C:\Users\adm14\Desktop\law_project\frontend
npm run dev
然后打开 http://127.0.0.1:5173。
