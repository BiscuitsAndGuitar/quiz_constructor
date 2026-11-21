import secrets
import string

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Attempt, Block, CorrectTextAnswer, Form, GradingScale, Question, QuestionChoice, QuestionType
from app.schemas.forms import FormSave, FormSettings
from app.services.form_validation import InvalidFormError, validate_form
from app.models import ConditionOperator
from app.services.conditions import validate_conditions
from app.services.condition_storage import add_conditions_to_response, save_conditions


class PublishedFormError(Exception):
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
        item = {"key": f"o{choice.id}", "text": choice.text}
        if form.is_test:
            item["is_correct"] = choice.is_correct
        choices_by_question.setdefault(choice.question_id, []).append(item)
    answers_by_question = {}
    if form.is_test:
        # У допустимых ответов нет position: id сохраняет порядок вставки списка.
        answers = db.scalars(select(CorrectTextAnswer).join(Question).join(Block)
                             .where(Block.form_id == form.id).order_by(CorrectTextAnswer.id))
        for answer in answers:
            answers_by_question.setdefault(answer.question_id, []).append(answer.answer_text)
    questions_by_block = {}
    for question, question_type in questions:
        item = {
            "key": f"q{question.id}", "text": question.text, "type": question_type,
            "is_answer_required": question.is_answer_required,
            "options": choices_by_question.get(question.id, []),
        }
        if form.is_test:
            item["points"] = question.points
            item["allow_partial_scoring"] = question.allow_partial_scoring if question_type == "multiple" else False
            if question_type == "text":
                item["correct_text_answers"] = answers_by_question.get(question.id, [])
        questions_by_block.setdefault(question.block_id, []).append(item)
    result = {field: getattr(form, field) for field in FormSettings.model_fields}
    result.update({
        "id": form.id, "is_test": form.is_test, "is_published": form.is_published,
        "public_code": form.public_code,
        "blocks": [{"key": f"b{block.id}", "title": block.title,
                    "questions": questions_by_block.get(block.id, [])} for block in blocks],
    })
    if form.is_test:
        scale = db.scalars(select(GradingScale).where(GradingScale.form_id == form.id)
                           .order_by(GradingScale.min_percent, GradingScale.id))
        result["grading_scale"] = [{"min_percent": row.min_percent, "grade": row.grade,
                                    "message": row.message} for row in scale]
    if not form.is_test:
        add_conditions_to_response(db, result)
    return result


def save_form(db: Session, form: Form, data: FormSave) -> dict:
    try:
        # Два сохранения одной формы выполняются по очереди и не смешивают блоки.
        db.refresh(form, with_for_update=True)
        if form.is_published:
            raise PublishedFormError("Опубликованную форму нельзя редактировать")
        validate_form(data, form.is_test)
        operator_ids = dict(db.execute(select(ConditionOperator.operator, ConditionOperator.id)).all())
        validate_conditions([block.model_dump(exclude_unset=True) for block in data.blocks], form.is_test, set(operator_ids))
        type_ids = dict(db.execute(select(QuestionType.type, QuestionType.id)).all())
        db.execute(delete(Block).where(Block.form_id == form.id))
        db.execute(delete(GradingScale).where(GradingScale.form_id == form.id))
        for field in FormSettings.model_fields:
            setattr(form, field, getattr(data, field))
        block_ids, question_ids, choice_ids = {}, {}, {}
        for block_position, block_data in enumerate(data.blocks, start=1):
            block = Block(form_id=form.id, title=block_data.title, position=block_position)
            db.add(block)
            db.flush()
            block_ids[block_data.key] = block.id
            for question_position, question_data in enumerate(block_data.questions, start=1):
                question = Question(
                    block_id=block.id, type_id=type_ids[question_data.type], text=question_data.text,
                    is_answer_required=question_data.is_answer_required if not form.is_test else False,
                    position=question_position,
                    points=question_data.points if form.is_test else None,
                    allow_partial_scoring=bool(question_data.allow_partial_scoring) if form.is_test else False,
                )
                db.add(question)
                db.flush()
                question_ids[question_data.key] = question.id
                for choice_position, choice_data in enumerate(question_data.options, start=1):
                    choice = QuestionChoice(question_id=question.id, text=choice_data.text,
                                          position=choice_position,
                                          is_correct=bool(choice_data.is_correct) if form.is_test else False)
                    db.add(choice)
                    db.flush()
                    choice_ids[choice_data.key] = choice.id
                if form.is_test:
                    for answer in question_data.correct_text_answers:
                        db.add(CorrectTextAnswer(question_id=question.id, answer_text=answer))
        if not form.is_test:
            save_conditions(db, data.blocks, block_ids, question_ids, choice_ids, operator_ids)
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
