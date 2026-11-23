from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_owned_form, require_author
from app.models import Form, User
from app.schemas.forms import FormCreate, FormCreated, FormListItem, FormResponse, FormSave
from app.services import forms as forms_service
from app.schemas.forms import FormCopied, FormPublished
from app.services.form_copy import copy_form
from fastapi.responses import JSONResponse

router = APIRouter(tags=["Опросы и тесты"])


@router.post("/forms/{id}/publish", response_model=FormPublished)
def publish_form(form: Form = Depends(get_owned_form), db: Session = Depends(get_db)):
    try:
        return forms_service.publish_form(db, form)
    except forms_service.PublishedFormError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except forms_service.PublicationError as error:
        return JSONResponse(status_code=422, content={"detail": str(error), "problems": error.problems})


@router.post("/forms/{id}/copy", status_code=201, response_model=FormCopied)
def create_copy(form: Form = Depends(get_owned_form), db: Session = Depends(get_db)):
    return copy_form(db, form)


@router.get("/my/forms", response_model=list[FormListItem])
def list_forms(user: User = Depends(require_author), db: Session = Depends(get_db)):
    return forms_service.list_forms(db, user.id)


@router.post("/forms", status_code=201, response_model=FormCreated)
def create_form(data: FormCreate, user: User = Depends(require_author), db: Session = Depends(get_db)):
    form = forms_service.create_form(db, user.id, data.title, data.is_test)
    return forms_service.build_form_response(db, form)


@router.get("/forms/{id}", response_model=FormResponse, response_model_exclude_unset=True)
def get_form(form: Form = Depends(get_owned_form), db: Session = Depends(get_db)):
    return forms_service.build_form_response(db, form)


@router.put("/forms/{id}", response_model=FormResponse, response_model_exclude_unset=True)
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
