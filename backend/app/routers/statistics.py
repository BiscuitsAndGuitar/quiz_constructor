from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_owned_form, get_author_attempt
from app.schemas.statistics import AttemptListItem, AttemptDetails, FormStatistics
from app.services.statistics_data import list_form_attempts, attempt_details, form_statistics

router = APIRouter(tags=['Статистика'])


@router.get('/forms/{id}/attempts', response_model=list[AttemptListItem])
def attempts(form=Depends(get_owned_form), db: Session = Depends(get_db)):
    return list_form_attempts(db, form)


@router.get('/attempts/{id}/details', response_model=AttemptDetails)
def details(attempt=Depends(get_author_attempt), db: Session = Depends(get_db)):
    return attempt_details(db, attempt)


@router.get('/forms/{id}/stats', response_model=FormStatistics, response_model_exclude_unset=True)
def statistics(form=Depends(get_owned_form), db: Session = Depends(get_db)):
    return form_statistics(db, form)
