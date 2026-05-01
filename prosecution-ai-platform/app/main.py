from fastapi import FastAPI

from app.api.v1.api import api_router


app = FastAPI(
    title="检察办案智能分析辅助平台",
    version="0.1.0",
    description="面向结构化与非结构化证据的知识抽取与分析服务。",
)

app.include_router(api_router, prefix="/api/v1")
