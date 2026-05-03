from functools import lru_cache
from os import getenv

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="Procuratorial Investigation Portrait Backend", alias="APP_NAME")
    app_env: str = Field(default="dev", alias="APP_ENV")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")
    algorithm_provider: str = Field(default="hipporag", alias="ALGORITHM_PROVIDER")
    hipporag_llm_name: str = Field(default="deepseek-chat", alias="HIPPORAG_LLM_NAME")
    hipporag_llm_base_url: str = Field(default="https://api.deepseek.com", alias="HIPPORAG_LLM_BASE_URL")
    deepseek_analysis_model: str = Field(default="deepseek-reasoner", alias="DEEPSEEK_ANALYSIS_MODEL")
    deepseek_analysis_timeout: int = Field(default=90, alias="DEEPSEEK_ANALYSIS_TIMEOUT")
    deepseek_analysis_enabled: bool = Field(default=True, alias="DEEPSEEK_ANALYSIS_ENABLED")
    hipporag_embedding_model: str = Field(default="BAAI/bge-m3", alias="HIPPORAG_EMBEDDING_MODEL")
    hipporag_save_dir: str = Field(default="../outputs/hipporag_cases", alias="HIPPORAG_SAVE_DIR")
    hipporag_max_docs: int = Field(default=240, alias="HIPPORAG_MAX_DOCS")
    hipporag_passage_max_chars: int = Field(default=180, alias="HIPPORAG_PASSAGE_MAX_CHARS")
    hipporag_trace_window_chars: int = Field(default=220, alias="HIPPORAG_TRACE_WINDOW_CHARS")
    hipporag_retrieval_top_k: int = Field(default=8, alias="HIPPORAG_RETRIEVAL_TOP_K")
    hipporag_fail_fast: bool = Field(default=True, alias="HIPPORAG_FAIL_FAST")
    hipporag_enable_qa: bool = Field(default=True, alias="HIPPORAG_ENABLE_QA")
    hipporag_qa_top_k: int = Field(default=5, alias="HIPPORAG_QA_TOP_K")
    memory_auto_writeback: bool = Field(default=False, alias="MEMORY_AUTO_WRITEBACK")
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"]


@lru_cache
def get_settings() -> Settings:
    env_file = getenv("ENV_FILE")
    if env_file:
        return Settings(_env_file=env_file)
    return Settings()


settings = get_settings()
