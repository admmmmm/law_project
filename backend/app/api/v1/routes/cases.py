from fastapi import APIRouter

from app.core.dependencies import CaseServiceDep
from app.schemas.case import CaseCreate, CaseDetail, CaseSummary, CaseUpdate

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


@router.patch("/{case_id}", response_model=CaseDetail)
def update_case(case_id: str, payload: CaseUpdate, service: CaseServiceDep) -> CaseDetail:
    return service.update_case(case_id, payload)


@router.delete("/{case_id}", status_code=204)
def delete_case(case_id: str, service: CaseServiceDep) -> None:
    service.delete_case(case_id)
