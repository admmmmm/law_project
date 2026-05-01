from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_ingestion_text_success() -> None:
    response = client.post(
        "/api/v1/cases/case_001/ingestion/text",
        json={
            "title": "证据文本",
            "content": "张三于2024年签署合同。",
            "source_type": "笔录",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == "case_001"
    assert data["accepted"] is True
    assert data["next_step"] == "run_analysis"
    assert len(data["evidences"]) == 1
    ev0 = data["evidences"][0]
    assert ev0["source_type"] == "笔录"
    assert ev0["source_ref"] == "ingestion:text"
    assert "张三" in ev0["content_preview"]


def test_ingestion_text_empty_content_returns_422() -> None:
    response = client.post(
        "/api/v1/cases/case_001/ingestion/text",
        json={
            "title": "空文本",
            "content": "   ",
            "source_type": "笔录",
        },
    )
    assert response.status_code == 422
    assert "不能为空" in response.json()["detail"]


def test_ingestion_file_empty_upload_returns_422() -> None:
    response = client.post(
        "/api/v1/cases/case_001/ingestion/file",
        files={"file": ("empty.txt", b"", "text/plain")},
        data={"title": "空文件"},
    )
    assert response.status_code == 422
    assert "文件为空" in response.json()["detail"]


def test_analysis_run_graph_without_body_success() -> None:
    client.post(
        "/api/v1/cases/case_002/ingestion/text",
        json={
            "title": "待分析笔录",
            "content": "李某承认参与转账操作。",
            "source_type": "笔录",
        },
    )
    response = client.post("/api/v1/cases/case_002/analysis/run-graph")
    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == "case_002"
    assert data["accepted"] is True
    assert data["analyzed_evidence_count"] >= 1
    assert data["triples_count"] >= 1


def test_ingestion_file_unsupported_suffix_returns_422() -> None:
    response = client.post(
        "/api/v1/cases/case_001/ingestion/file",
        files={"file": ("malware.exe", b"abc", "application/octet-stream")},
        data={"title": "非法后缀"},
    )
    assert response.status_code == 422
    assert "不支持的文件后缀" in response.json()["detail"]


def test_ingestion_file_too_large_returns_413() -> None:
    response = client.post(
        "/api/v1/cases/case_001/ingestion/file",
        files={"file": ("large.txt", b"a" * (10 * 1024 * 1024 + 1), "text/plain")},
        data={"title": "超限文件"},
    )
    assert response.status_code == 413


def test_analysis_run_without_evidence_returns_422() -> None:
    response = client.post("/api/v1/cases/empty_case/analysis/run")
    assert response.status_code == 422
