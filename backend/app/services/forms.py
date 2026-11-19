import secrets
import string

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Attempt, Block, Form, Question, QuestionChoice, QuestionType
from app.schemas.forms import FormSave, FormSettings


class PublishedFormError(Exception):
    pass


class InvalidFormError(Exception):
    pass


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
    questions = db.execute(
        select(Question, QuestionType.type).join(QuestionType)
        .join(Block, Question.block_id == Block.id).where(Block.form_id == form.id)
        .order_by(Question.position, Question.id)
    ).all()
    choices = db.scalars(
        select(QuestionChoice).join(Question).join(Block)
        .where(Block.form_id == form.id).order_by(QuestionChoice.position, QuestionChoice.id)
    ).all()
    choices_by_question = {}
    for choice in choices:
        choices_by_question.setdefault(choice.question_id, []).append(
            {"key": f"o{choice.id}", "text": choice.text}
        )
    questions_by_block = {}
    for question, question_type in questions:
        questions_by_block.setdefault(question.block_id, []).append({
            "key": f"q{question.id}", "text": question.text, "type": question_type,
            "is_answer_required": question.is_answer_required,
            "options": choices_by_question.get(question.id, []),
        })
    result = {field: getattr(form, field) for field in FormSettings.model_fields}
    result.update({
        "id": form.id, "is_test": form.is_test, "is_published": form.is_published,
        "public_code": form.public_code,
        "blocks": [{"key": f"b{block.id}", "title": block.title,
                    "questions": questions_by_block.get(block.id, [])} for block in blocks],
    })
    return result


def save_form(db: Session, form: Form, data: FormSave) -> dict:
    try:
        # Два сохранения одной формы выполняются по очереди и не смешивают блоки.
        db.refresh(form, with_for_update=True)
        if form.is_published:
            raise PublishedFormError("Опубликованную форму нельзя редактировать")
        if not form.is_test and (
            data.shuffle_questions or data.time_limit_minutes is not None
            or data.show_correct_answers or data.show_results_by_block
        ):
            raise InvalidFormError("Настройки теста нельзя задавать у опроса")
        type_ids = dict(db.execute(select(QuestionType.type, QuestionType.id)).all())
        db.execute(delete(Block).where(Block.form_id == form.id))
        for field in FormSettings.model_fields:
            setattr(form, field, getattr(data, field))
        for block_position, block_data in enumerate(data.blocks, start=1):
            block = Block(form_id=form.id, title=block_data.title, position=block_position)
            db.add(block)
            db.flush()
            for question_position, question_data in enumerate(block_data.questions, start=1):
                question = Question(
                    block_id=block.id, type_id=type_ids[question_data.type], text=question_data.text,
                    is_answer_required=question_data.is_answer_required if not form.is_test else False,
                    position=question_position,
                )
                db.add(question)
                db.flush()
                for choice_position, choice_data in enumerate(question_data.options, start=1):
                    db.add(QuestionChoice(question_id=question.id, text=choice_data.text,
                                          position=choice_position))
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
