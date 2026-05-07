from fastapi import APIRouter

from app.core.dependencies import AnalysisSkillServiceDep
from app.schemas.analysis_skill import RuleBundleRunRequest, RuleBundleRunResult, RulePackRunResult, RulePackSummary

router = APIRouter()


@router.get("/rule-packs", response_model=list[RulePackSummary])
def list_rule_packs(service: AnalysisSkillServiceDep) -> list[RulePackSummary]:
    return service.list_rule_packs()


@router.post("/cases/{case_id}/analysis/rule-packs/{pack_name}/run", response_model=RulePackRunResult)
def run_rule_pack(case_id: str, pack_name: str, service: AnalysisSkillServiceDep) -> RulePackRunResult:
    return service.run_rule_pack(case_id, pack_name)


@router.post("/cases/{case_id}/analysis/rule-packs/run-bundle", response_model=RuleBundleRunResult)
def run_rule_bundle(case_id: str, payload: RuleBundleRunRequest, service: AnalysisSkillServiceDep) -> RuleBundleRunResult:
    return service.run_bundle(case_id, payload)
