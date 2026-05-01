from fastapi import APIRouter

from app.core.dependencies import CaseServiceDep
from app.schemas.case import CaseCreate, CaseDetail, CaseSummary

router = APIRouter()


@router.post("", response_model=CaseDetail)
def create_case(payload: CaseCreate, service: CaseServiceDep) -> CaseDetail:
    return service.create_case(payload)


@router.get("", response_model=list[CaseSummary])
def list_cases(service: CaseServiceDep) -> list[CaseSummary]:
    return service.list_cases()


@router.get("/{case_id}", response_model=CaseDetail)
def get_case(case_id: str, service: CaseServiceDep) -> CaseDetail:
    return service.get_case(case_id)
