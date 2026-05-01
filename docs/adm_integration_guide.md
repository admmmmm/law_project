# adm 分支整合说明与白板约定

## 一句话结论

当前系统已经具备“批量导入入口 + 抽取三元组 + 生成图谱”的联调骨架，但还不能算完整满足项目需求。

它现在适合作为后端龙骨和接口白板，不适合作为最终前端，也不适合作为最终算法效果验收版本。

## 白板界面约定

前端暂时只保留最小功能，不做精细 UI：

1. 案件
   - 新建默认案件
   - 选择当前案件
   - 显示证据数量

2. 导入
   - 选择文件夹批量上传
   - 选择 zip 压缩包上传
   - 显示导入数量、跳过数量、三元组数量

3. 分析
   - 运行分析
   - 跳转到图谱页面

4. 图谱
   - 展示后端返回的节点、边、线索
   - 不写死演示数据

前端专人后续只需要围绕这些固定动作做精细设计，不需要重新猜业务流程。

## 当前结构

- `backend/` 是唯一后端入口，PR 里的 `prosecution-ai-platform/` 已经折进主后端后移除，避免两套 FastAPI 服务并存。
- `frontend/` 是唯一前端入口，默认运行在 `http://127.0.0.1:5173`。
- `need/HippoRAG/` 作为 RAG 算法代码依赖保留，由 `backend/app/adapters/algorithm.py` 延迟加载。默认仍可用 stub 图谱，设置 `ALGORITHM_PROVIDER=hipporag` 后会检查 HippoRAG 是否可导入。

## 后端链路

1. 创建案件：`POST /api/v1/cases`
2. 导入文本：`POST /api/v1/cases/{case_id}/ingestions/text`
3. 导入文件：`POST /api/v1/cases/{case_id}/ingestions/files`
4. 批量导入文件夹：`POST /api/v1/cases/{case_id}/ingestions/batch`
5. 导入压缩包：`POST /api/v1/cases/{case_id}/ingestions/archive`
6. 运行分析：`POST /api/v1/cases/{case_id}/analysis/run`
7. 获取图谱：`GET /api/v1/cases/{case_id}/graph`

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
- `.md`
- `.docx`
- `.pdf`
- `.zip`

银行流水联调建议先用：

- `data/processed/cleaned_bank_flows.csv`
- `data/processed/case_relevant_bank_flows.csv`
- `data/processed/cleaned_bank_flows.xlsx`

旧 `.xls` 建议先走现有清洗脚本转换到 `data/processed/` 下的 CSV/XLSX，再导入前端。

## 当前能力边界

已经做到：

- 可以单文件导入
- 可以选择文件夹批量导入
- 可以上传 zip，后端自动展开并导入内部文件
- 可以把 CSV/XLSX/JSON 解析成结构化行
- 可以把银行流水清洗结果中的姓名、金额、时间、交易类型映射成三元组
- 可以把文本证据切成 passage，并生成粗粒度三元组
- 可以把导入结果保存到同一个案件 store
- 可以运行分析并生成图谱节点、边、线索

还没做到：

- 不能直接稳定处理原始 `.xls`，应先转为 CSV/XLSX
- 不能处理图片 OCR
- 不能自动识别所有复杂目录语义，比如“这个文件夹就是证据组 5”
- 非结构化文本抽取现在是规则/stub，不是最终 LLM 抽取
- HippoRAG 目前是可选加载桥，尚未真正把 passage 写入 HippoRAG 索引并跑 PPR 检索
- 没有持久化数据库，当前 store 仍是内存态，服务重启数据会丢
- 没有任务队列，大 zip/大批量文件仍是同步处理

所以目前答案是：入口形态接近项目需求，但处理能力还只是 MVP。它可以支撑联调和接口固定，不能直接当最终数据导入模块交付。

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
- TestClient zip 链路通过：创建案件、导入 zip、运行分析、获取图谱

最小链路结果：

```text
create 200
text 200 unstructured
file 200 3
analysis 200 已完成 full 分析，生成 8 个节点、8 条关系、2 条线索。
graph 200 8 8 2
```

zip 链路结果：

```text
archive 200 2 0
analysis 200 已完成 full 分析，生成 8 个节点、8 条关系、2 条线索。
graph 8 8 2
```
