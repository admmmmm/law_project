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

## 与外部模块的接入点

- 算法核心：替换 `app/adapters/algorithm.py` 中的 `AlgorithmAdapter` 实现。
- 人工干预：前端调用 `PATCH /api/v1/cases/{case_id}/graph/interventions`。
- 记忆功能：前端调用 `POST /api/v1/cases/{case_id}/memories`，确认事实后可触发写回图谱。
- 前端：所有接口统一挂在 `/api/v1` 下。
