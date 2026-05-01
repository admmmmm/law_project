from pathlib import Path
import contextlib
import io
import logging
import os
import re
import sys
import warnings

PROJECT_ROOT = Path(__file__).resolve().parents[1] / "HippoRAG"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.hipporag.HippoRAG import HippoRAG
from src.hipporag.utils.config_utils import BaseConfig


logging.basicConfig(level=logging.ERROR)
for logger_name in (
    "httpx",
    "huggingface_hub",
    "sentence_transformers",
    "src.hipporag",
):
    logging.getLogger(logger_name).setLevel(logging.ERROR)
warnings.filterwarnings("ignore")

TXT_DIR = Path(__file__).resolve().parent
RUN_INDEX = True
SPLIT_BY_LINE = True
QUIET_MODE = True


def read_text_with_fallback(path: Path) -> tuple[str, str]:
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "gbk"):
        try:
            return path.read_text(encoding=encoding), encoding
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 1, f"Unable to decode {path}")


def normalize_line(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^\d+\s*[、.．]\s*", "", text)
    return text


def run_quietly(func, *args, **kwargs):
    if not QUIET_MODE:
        return func(*args, **kwargs)

    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return func(*args, **kwargs)


def load_docs_from_txt_dir(txt_dir: Path) -> list[str]:
    docs: list[str] = []

    for path in sorted(txt_dir.glob("*.txt")):
        raw_text, encoding = read_text_with_fallback(path)
        print(f"loaded_file= {path.name} encoding= {encoding}")

        if SPLIT_BY_LINE:
            lines = [normalize_line(line) for line in raw_text.splitlines()]
            file_docs = [line for line in lines if line]
        else:
            normalized = raw_text.strip()
            file_docs = [normalized] if normalized else []

        docs.extend(file_docs)

    if not docs:
        raise ValueError(f"No non-empty txt content found in {txt_dir}")

    return docs


def main():
    docs = load_docs_from_txt_dir(TXT_DIR)

    print(f"doc_count= {len(docs)}")
    for i, doc in enumerate(docs, 1):
        print(f"doc_{i}= {doc}")

    config = BaseConfig(
        llm_name="deepseek-chat",
        llm_base_url="https://api.deepseek.com",
        embedding_model_name=os.getenv("HIPPORAG_EMBEDDING_MODEL", "BAAI/bge-m3"),
        save_dir="outputs/local_case",
    )

    hipporag = run_quietly(HippoRAG, global_config=config)

    print("\n=== OPENIE ===")
    for i, doc in enumerate(docs, 1):
        result = run_quietly(hipporag.openie.openie, f"doc-{i}", doc)
        print(f"doc_{i}_entities= {result['ner'].unique_entities}")
        print(f"doc_{i}_triples= {result['triplets'].triples}")

    print("\n=== EMBEDDINGS ===")
    vectors = run_quietly(hipporag.embedding_model.batch_encode, docs)
    print(f"embedding_shape= {vectors.shape}")
    for i, vector in enumerate(vectors, 1):
        head = [round(float(x), 6) for x in vector[:8]]
        print(f"doc_{i}_vector_head= {head}")

    if RUN_INDEX:
        print("\n=== INDEX ===")
        run_quietly(hipporag.index, docs)
        print("index_done= True")


if __name__ == "__main__":
    main()
