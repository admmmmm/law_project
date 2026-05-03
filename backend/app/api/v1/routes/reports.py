from fastapi import APIRouter

from app.core.dependencies import ReportServiceDep
from app.schemas.report import PortraitReport

router = APIRouter()


@router.post("/{case_id}/reports/portrait", response_model=PortraitReport)
def generate_portrait_report(case_id: str, service: ReportServiceDep) -> PortraitReport:
    return service.generate_portrait(case_id)


@router.get("/{case_id}/reports/portrait/latest", response_model=PortraitReport)
def get_latest_portrait_report(case_id: str, service: ReportServiceDep) -> PortraitReport:
    return service.get_latest_portrait(case_id)
