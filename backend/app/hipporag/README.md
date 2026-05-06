# need 文件夹说明

这个目录整理的是当前 `DeepSeek + BGE-M3 + HippoRAG` 整条链路运行所需的本地文件，不包含模型缓存和 Hugging Face 下载下来的权重。

## 目录结构

- `HippoRAG/`
  - `src/hipporag/`：当前链路实际使用到的源码包
  - `main.py`、`main_azure.py`：原项目入口脚本
- `test/`
  - `1.txt`：当前样例输入
  - `run_local_test.py`：读取 `txt`、打印三元组和向量、并可选执行 `index()` 的测试脚本
- `requirements_minimal.txt`
  - 当前链路已经验证过的最小依赖集合

## 运行前提

需要提前准备：

1. 已可用的 Python / conda 环境
2. `DEEPSEEK_API_KEY` 环境变量
3. 本地已安装依赖
4. 第一次运行时允许从 Hugging Face 下载 `BAAI/bge-m3`

## 建议运行方式

在 `ai` 环境下执行：

```powershell
conda activate ai
python D:\law\law_project\need\test\run_local_test.py
```

## 运行结果

脚本会输出：

- `doc_x_entities`
- `doc_x_triples`
- `embedding_shape`
- `doc_x_vector_head`
- `index_done= True`

其中图谱、向量库、OpenIE 缓存会被写到运行目录下的 `outputs/`。

## 不包含的内容

为了避免体积过大，下面这些没有放进 `need`：

- Hugging Face 模型权重缓存
- `outputs/` 运行产物
- Python 环境本身
- conda / pip 下载缓存
