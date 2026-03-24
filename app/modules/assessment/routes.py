import uuid

from fastapi import APIRouter

from app.schemas.assessment import AnswersResponse, AssessmentCreateResponse, RulesResponse

router = APIRouter(
    prefix="/assessments",
    tags=["Assessment Engine"],
)


@router.post("/", response_model=AssessmentCreateResponse)
def create_assessment():
    return {"id": str(uuid.uuid4()), "status": "draft"}


@router.post("/{assessment_id}/answers", response_model=AnswersResponse)
def submit_answers(assessment_id: str):
    return {"message": "Answers saved"}


@router.post("/{assessment_id}/run-rules", response_model=RulesResponse)
def run_rules(assessment_id: str):
    return {
        "flags": [
            {"type": "risk", "message": "No structured IT governance"},
        ]
    }
