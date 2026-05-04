# 本次改动说明

本文档用于说明本轮对 `law_project` 的实际改动，便于打包上传、交接和验收。

## 1. 本轮改动目标

本轮主要完成了四类工作：

1. 补齐后端运行依赖，打通 `FastAPI + HippoRAG + DeepSeek` 的基础运行链路。
2. 为后端加入本地持久化能力，使案件数据在服务重启后仍可恢复。
3. 修复若干前后端空态/404/状态丢失问题，提升联调稳定性。
4. 为前端主要长耗时操作补充进度条反馈，减少“点击后无响应感”。

## 2. 关键功能改动

### 2.1 后端加入本地数据库持久化

原先后端仅使用内存字典保存案件、证据、图谱、报告等数据，服务重启后数据会丢失。

现在已改为：

- 继续保留内存缓存，保证当前运行效率。
- 新增 SQLite 持久化落盘。
- 默认数据库文件位置：

```text
outputs/backend_state.sqlite3
```

- 后端启动时会自动从本地数据库恢复：
  - 案件
  - 证据
  - 原始正文
  - 抽取结果
  - 图谱
  - 画像报告
  - 记忆/回写结果

### 2.2 后端配置与依赖修正

已补充或修正：

- `python-dotenv`
- `openai`
- `numpy`
- `pandas`
- `pyarrow`
- `torch`
- `transformers`
- `sentence-transformers`
- `igraph`
- `scikit-learn`
- `scipy`
- `tiktoken`

同时修复了 `.env` 读取逻辑：

- 现在 `.env` 会覆盖旧环境变量，避免“已经换了 key，但进程还在吃旧 key”的问题。

### 2.3 空态与容错修复

已处理以下问题：

1. 未导入证据时访问图谱页，后端不再返回 `404`，而是返回空图谱。
2. 未生成画像报告时访问画像页，后端不再返回 `404`，而是返回“待生成”的空结果。
3. 案件导入过程中切页再返回，前端不再丢失“正在导入/已导入结果”的页面状态。
4. 前端类型声明已补齐，`npm run lint` 可通过。

### 2.4 前端等待进度条

已新增统一进度条组件，并接入以下主要等待操作：

- 白板页
  - 新建默认案件
  - 创建自定义案件
  - 批量导入证据
  - 导入压缩包
  - 运行分析并进入图谱
- 智能分析页
  - 运行分析
  - 证据回溯
- 画像报告页
  - 生成画像报告
  - 报告证据回溯
- 图谱页
  - 刷新图谱
  - 重新分析
- 对话页
  - 检索并生成回答

说明：

- 当前进度条为前端平滑模拟进度，不是直接读取后端 `tqdm` 的真实百分比。
- 优点是无需改后端接口即可显著改善等待体验。

## 3. 主要改动文件

### 3.1 后端

- `backend/app/core/config.py`
- `backend/app/storage/memory_store.py`
- `backend/app/services/case_service.py`
- `backend/app/services/ingestion_service.py`
- `backend/app/services/analysis_service.py`
- `backend/app/services/graph_service.py`
- `backend/app/services/memory_service.py`
- `backend/app/services/report_service.py`
- `backend/requirements.txt`
- `backend/.env.example`
- `backend/test_deepseek_key.py`

### 3.2 前端

- `frontend/src/views/Dashboard.vue`
- `frontend/src/views/Graph.vue`
- `frontend/src/views/Intelligence.vue`
- `frontend/src/views/Portrait.vue`
- `frontend/src/views/Chat.vue`
- `frontend/src/env.d.ts`
- `frontend/src/components/AsyncProgressBar.vue`
- `frontend/src/composables/useSimulatedProgress.ts`

## 4. 当前运行结果

### 4.1 后端

当前后端已具备：

- 可正常启动
- 可读取 `.env`
- 可使用本地 SQLite 持久化案件数据
- 可调用有效的 DeepSeek key
- 可在服务重启后恢复本地案件和图谱数据

### 4.2 前端

当前前端已具备：

- 可正常启动
- 可连接后端接口
- 可展示案件、图谱、画像、分析、对话页面
- 主要长耗时操作具备进度条反馈

## 5. 已完成验证

本轮已完成以下验证：

- 后端可成功 `import app.main`
- 前端 `npm run lint` 通过
- SQLite 数据库文件已实际生成
- DeepSeek key 最小化鉴权测试通过
- 无案件/无图谱/无报告等空态下，关键页面不再因 `404` 直接报错

## 6. 上传前建议

建议一并上传以下内容：

- `backend`
- `frontend`
- `docs`
- `outputs/backend_state.sqlite3`  
  如果希望把当前本地案件一并交付给对方，就需要把这个文件一起带上。

## 7. 当前仍需注意的点

1. 当前数据库是 SQLite，本地单机使用没有问题，但还不是多人并发协作方案。
2. 前端进度条目前不是后端真实进度，只是更友好的等待反馈。
3. 如果更换机器部署，需要重新配置：
   - `backend/.env`
   - DeepSeek API key
   - 本地 embedding 模型路径
4. 如果某些旧案件只存在于“改造前的内存进程”里，并且那个旧进程已经退出，那么那部分数据不会自动恢复。

## 8. 如需后续继续扩展

后续可以继续做的方向：

1. 把进度条升级为真实后端进度同步（SSE / WebSocket）。
2. 将 SQLite 抽象成可切换的数据库层，后续接 MySQL / PostgreSQL。
3. 增加案件导出/导入功能，便于跨机器迁移。
4. 为上传、分析、画像生成补更细粒度的状态字段和失败重试能力。

