from fastapi import APIRouter

from app.core.dependencies import MemoryServiceDep
from app.schemas.memory import MemoryCreate, MemoryRecord

router = APIRouter()


@router.post("/{case_id}/memories", response_model=MemoryRecord)
def create_memory(case_id: str, payload: MemoryCreate, service: MemoryServiceDep) -> MemoryRecord:
    return service.create(case_id, payload)


@router.get("/{case_id}/memories", response_model=list[MemoryRecord])
def list_memories(case_id: str, service: MemoryServiceDep) -> list[MemoryRecord]:
    return service.list_by_case(case_id)


@router.post("/{case_id}/memories/{memory_id}/writeback", response_model=MemoryRecord)
def writeback_memory(case_id: str, memory_id: str, service: MemoryServiceDep) -> MemoryRecord:
    return service.writeback_to_graph(case_id, memory_id)
