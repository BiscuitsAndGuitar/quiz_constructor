import secrets
import string
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Attempt, Block, Form, GradingScale
from app.schemas.forms import FormSave, FormSettings
from app.services.form_validation import InvalidFormError
from app.services.form_validation import publication_problems
from app.services.block_storage import read_blocks, validate_blocks, write_blocks


class PublishedFormError(Exception):
    pass


class PublicationError(Exception):
    def __init__(self, problems):
        self.problems = problems
        super().__init__("Форма не прошла проверку")


def publish_form(db: Session, form: Form) -> dict:
    try:
        # Сохранение и публикация используют одну блокировку строки формы.
        db.refresh(form, with_for_update=True)
        if form.is_published:
            raise PublishedFormError("Форма уже опубликована")
        problems = publication_problems(build_form_response(db, form))
        if problems:
            raise PublicationError(problems)
        form.is_published = True
        form.published_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.flush()
        result = {"id": form.id, "is_published": True, "published_at": form.published_at,
                  "public_code": form.public_code}
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


def list_forms(db: Session, author_id: int) -> list[dict]:
    attempts_count = (
        select(func.count(Attempt.id)).where(Attempt.form_id == Form.id)
        .correlate(Form).scalar_subquery()
    )
    rows = db.execute(
        select(Form, attempts_count).where(Form.author_id == author_id)
        .order_by(Form.created_at.desc(), Form.id.desc())
    )
    return [
        {"id": form.id, "is_test": form.is_test, "title": form.title,
         "is_published": form.is_published, "requires_login": form.requires_login,
         "public_code": form.public_code, "attempts_count": count,
         "created_at": form.created_at, "published_at": form.published_at}
        for form, count in rows
    ]


def generate_public_code() -> str:
    return "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))


def create_form(db: Session, author_id: int, title: str, is_test: bool) -> Form:
    while True:
        form = Form(author_id=author_id, title=title, is_test=is_test,
                    public_code=generate_public_code())
        try:
            db.add(form)
            db.flush()
            db.add(Block(form_id=form.id, title=None, position=1))
            db.commit()
            db.refresh(form)
            return form
        except IntegrityError as error:
            db.rollback()
            # UNIQUE защищает также от совпадения кодов в параллельных запросах.
            constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if getattr(error.orig, "sqlstate", None) != "23505" or constraint != "forms_public_code_key":
                raise
        except Exception:
            db.rollback()
            raise


def build_form_response(db: Session, form: Form) -> dict:
    blocks = db.scalars(select(Block).where(Block.form_id == form.id).order_by(Block.position, Block.id)).all()
    result = {field: getattr(form, field) for field in FormSettings.model_fields}
    result.update({
        "id": form.id, "is_test": form.is_test, "is_published": form.is_published,
        "public_code": form.public_code,
        "blocks": read_blocks(db, blocks, form.is_test),
    })
    if form.is_test:
        scale = db.scalars(select(GradingScale).where(GradingScale.form_id == form.id)
                           .order_by(GradingScale.min_percent, GradingScale.id))
        result["grading_scale"] = [{"min_percent": row.min_percent, "grade": row.grade,
                                    "message": row.message} for row in scale]
    return result


def save_form(db: Session, form: Form, data: FormSave) -> dict:
    try:
        # Два сохранения одной формы выполняются по очереди и не смешивают блоки.
        db.refresh(form, with_for_update=True)
        if form.is_published:
            raise PublishedFormError("Опубликованную форму нельзя редактировать")
        operator_ids = validate_blocks(db, data, form.is_test)
        db.execute(delete(Block).where(Block.form_id == form.id))
        db.execute(delete(GradingScale).where(GradingScale.form_id == form.id))
        for field in FormSettings.model_fields:
            setattr(form, field, getattr(data, field))
        write_blocks(db, data.blocks, form.is_test, operator_ids, form_id=form.id)
        if form.is_test:
            for row in data.grading_scale or []:
                db.add(GradingScale(form_id=form.id, min_percent=row.min_percent,
                                    grade=row.grade, message=row.message))
        db.flush()
        result = build_form_response(db, form)
        db.commit()
        return result
    except Exception:
        # Включая ошибки после удаления старых блоков: весь черновик восстанавливается.
        db.rollback()
        raise


def delete_form(db: Session, form: Form) -> None:
    try:
        db.delete(form)
        db.commit()
    except Exception:
        db.rollback()
        raise
