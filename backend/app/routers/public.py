from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import optional_user
from app.schemas.attempts import PublicForm
from app.services.attempts import public_form

router = APIRouter(tags=["Публичные формы"])


@router.get("/public/forms/{code}", response_model=PublicForm)
def get_public_form(code: str, user=Depends(optional_user), db: Session = Depends(get_db)):
    return public_form(db, code, user)
