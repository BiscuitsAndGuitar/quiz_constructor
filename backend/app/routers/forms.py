from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_owned_form, require_author
from app.models import Form, User
from app.schemas.forms import FormCreate, FormCreated, FormListItem, FormResponse, FormSave
from app.services import forms as forms_service

router = APIRouter(tags=["Опросы и тесты"])


@router.get("/my/forms", response_model=list[FormListItem])
def list_forms(user: User = Depends(require_author), db: Session = Depends(get_db)):
    return forms_service.list_forms(db, user.id)


@router.post("/forms", status_code=201, response_model=FormCreated)
def create_form(data: FormCreate, user: User = Depends(require_author), db: Session = Depends(get_db)):
    form = forms_service.create_form(db, user.id, data.title, data.is_test)
    return forms_service.build_form_response(db, form)


@router.get("/forms/{id}", response_model=FormResponse)
def get_form(form: Form = Depends(get_owned_form), db: Session = Depends(get_db)):
    return forms_service.build_form_response(db, form)


@router.put("/forms/{id}", response_model=FormResponse)
def save_form(data: FormSave, form: Form = Depends(get_owned_form), db: Session = Depends(get_db)):
    try:
        return forms_service.save_form(db, form, data)
    except forms_service.PublishedFormError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except forms_service.InvalidFormError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


@router.delete("/forms/{id}", status_code=204)
def delete_form(form: Form = Depends(get_owned_form), db: Session = Depends(get_db)):
    forms_service.delete_form(db, form)
    return Response(status_code=204)
