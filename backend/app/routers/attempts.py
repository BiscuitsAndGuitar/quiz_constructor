from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import attempt_participant, owned_attempt, require_participant
from app.schemas.attempts import AttemptFinish, AttemptStart, SurveyResult, TestResult, HistoryItem
from app.services.attempts import start_attempt, finish_attempt
from app.services.attempt_results import attempt_history, build_result

router = APIRouter(tags=["Прохождение"])


@router.post("/forms/{id}/attempts", status_code=201, response_model=AttemptStart)
def start(id: int, user=Depends(attempt_participant), db: Session = Depends(get_db)):
    return start_attempt(db, id, user)


@router.post("/attempts/{id}/finish", response_model=SurveyResult | TestResult, response_model_exclude_unset=True)
def finish(data: AttemptFinish, attempt=Depends(owned_attempt), db: Session = Depends(get_db)):
    return finish_attempt(db, attempt, [answer.model_dump(exclude_unset=True) for answer in data.answers])


@router.get("/attempts/{id}/result", response_model=SurveyResult | TestResult, response_model_exclude_unset=True)
def result(attempt=Depends(owned_attempt), db: Session = Depends(get_db)):
    return build_result(db, attempt, include_answers=True)


@router.get("/my/attempts", response_model=list[HistoryItem])
def history(user=Depends(require_participant), db: Session = Depends(get_db)):
    return attempt_history(db, user.id)
