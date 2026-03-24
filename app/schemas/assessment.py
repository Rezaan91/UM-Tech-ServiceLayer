from pydantic import BaseModel


class AssessmentCreateResponse(BaseModel):
    id: str
    status: str


class AnswersResponse(BaseModel):
    message: str


class RuleFlag(BaseModel):
    type: str
    message: str


class RulesResponse(BaseModel):
    flags: list[RuleFlag]
