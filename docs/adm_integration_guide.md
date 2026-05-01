# adm 分支整合说明

## 当前结构

- `backend/` 是唯一后端入口，PR 里的 `prosecution-ai-platform/` 已经折进主后端后移除，避免两套 FastAPI 服务并存。
- `frontend/` 是唯一前端入口，默认运行在 `http://127.0.0.1:5173`。
- `need/HippoRAG/` 作为 RAG 算法代码依赖保留，由 `backend/app/adapters/algorithm.py` 延迟加载。默认仍可用 stub 图谱，设置 `ALGORITHM_PROVIDER=hipporag` 后会检查 HippoRAG 是否可导入。

## 后端链路

1. 创建案件：`POST /api/v1/cases`
2. 导入文本：`POST /api/v1/cases/{case_id}/ingestions/text`
3. 导入文件：`POST /api/v1/cases/{case_id}/ingestions/files`
4. 运行分析：`POST /api/v1/cases/{case_id}/analysis/run`
5. 获取图谱：`GET /api/v1/cases/{case_id}/graph`

导入层现在会保存：

- 原始证据摘要：`store.evidence`
- 原文内容：`store.raw_contents`
- 抽取结果：`store.extractions`

抽取结果包含：

- `route`：`structured` 或 `unstructured`
- `triples`：三元组
- `passages`：给 RAG/LLM 阅读的文本片段
- `metadata`：数据行数、来源类型等

## 文件导入

当前优先支持：

- `.csv`
- `.xlsx`
- `.json`
- `.txt`
- `.docx`
- `.pdf`

银行流水联调建议先用：

- `data/processed/cleaned_bank_flows.csv`
- `data/processed/case_relevant_bank_flows.csv`
- `data/processed/cleaned_bank_flows.xlsx`

旧 `.xls` 建议先走现有清洗脚本转换到 `data/processed/` 下的 CSV/XLSX，再导入前端。

## 启动方式

后端：

```powershell
cd C:\Users\adm14\Desktop\law_project\backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
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

## 前端使用流程

1. 进入“案件导入”
2. 新建案件
3. 导入文本证据或 CSV/XLSX 流水
4. 点击“运行分析”
5. 自动跳转到“证据图谱”

现在前端不会再预置假案件数据；没有后端数据时会显示空状态。

## 验证记录

已验证：

- 后端 Python 编译通过
- 前端 `npm run build` 通过
- TestClient 最小链路通过：创建案件、导入文本、导入 CSV、运行分析、获取图谱

最小链路结果：

```text
create 200
text 200 unstructured
file 200 3
analysis 200 已完成 full 分析，生成 8 个节点、8 条关系、2 条线索。
graph 200 8 8 2
```
