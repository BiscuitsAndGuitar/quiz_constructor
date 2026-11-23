from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from app.models import (Block, Condition, ConditionGroup, CorrectTextAnswer, EarlyFinishRule,
                        Form, GradingScale, Question, QuestionChoice)
from app.schemas.forms import FormSettings
from app.services import forms as forms_service


def create_copy_header(db, source):
    settings = {field: getattr(source, field) for field in FormSettings.model_fields}
    settings["title"] = source.title[:255 - len(" (копия)")] + " (копия)"
    while True:
        try:
            # При редком совпадении кода откатываем только попытку вставки заголовка.
            with db.begin_nested():
                copied = Form(author_id=source.author_id, is_test=source.is_test,
                              public_code=forms_service.generate_public_code(),
                              is_published=False, published_at=None, **settings)
                db.add(copied)
                db.flush()
            return copied
        except IntegrityError as error:
            constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if getattr(error.orig, "sqlstate", None) != "23505" or constraint != "forms_public_code_key":
                raise


def copy_questions(db, source_id, copied_id):
    block_ids, question_ids, choice_ids = {}, {}, {}
    for block in db.scalars(select(Block).where(Block.form_id == source_id).order_by(Block.position, Block.id)).all():
        copied = Block(form_id=copied_id, title=block.title, position=block.position)
        db.add(copied)
        db.flush()
        block_ids[block.id] = copied.id
    for question in db.scalars(select(Question).where(Question.block_id.in_(block_ids))
                              .order_by(Question.id)).all():
        copied = Question(block_id=block_ids[question.block_id], type_id=question.type_id,
                          text=question.text, image_id=question.image_id,
                          is_answer_required=question.is_answer_required, position=question.position,
                          points=question.points, allow_partial_scoring=question.allow_partial_scoring)
        db.add(copied)
        db.flush()
        question_ids[question.id] = copied.id
    for choice in db.scalars(select(QuestionChoice).where(QuestionChoice.question_id.in_(question_ids))
                            .order_by(QuestionChoice.id)).all():
        copied = QuestionChoice(question_id=question_ids[choice.question_id], text=choice.text,
                                is_correct=choice.is_correct, position=choice.position)
        db.add(copied)
        db.flush()
        choice_ids[choice.id] = copied.id
    for answer in db.scalars(select(CorrectTextAnswer).where(CorrectTextAnswer.question_id.in_(question_ids))
                            .order_by(CorrectTextAnswer.id)).all():
        db.add(CorrectTextAnswer(question_id=question_ids[answer.question_id], answer_text=answer.answer_text))
    return block_ids, question_ids, choice_ids


def copy_conditions(db, block_ids, question_ids, choice_ids):
    rule_ids = {}
    for rule in db.scalars(select(EarlyFinishRule).where(EarlyFinishRule.question_id.in_(question_ids))
                          .order_by(EarlyFinishRule.id)).all():
        copied = EarlyFinishRule(question_id=question_ids[rule.question_id], message=rule.message, position=rule.position)
        db.add(copied)
        db.flush()
        rule_ids[rule.id] = copied.id
    pending = db.scalars(select(ConditionGroup).where(or_(
        ConditionGroup.block_id.in_(block_ids), ConditionGroup.question_id.in_(question_ids),
        ConditionGroup.early_finish_rule_id.in_(rule_ids))).order_by(ConditionGroup.id)).all()
    group_ids = {}
    # Копируем дерево по уровням: родитель получает новый id до дочерних групп.
    while pending:
        level_ids = []
        for group in pending:
            copied = ConditionGroup(match_all=group.match_all,
                parent_group_id=group_ids.get(group.parent_group_id), block_id=block_ids.get(group.block_id),
                question_id=question_ids.get(group.question_id), early_finish_rule_id=rule_ids.get(group.early_finish_rule_id))
            db.add(copied)
            db.flush()
            group_ids[group.id] = copied.id
            level_ids.append(group.id)
        pending = db.scalars(select(ConditionGroup).where(ConditionGroup.parent_group_id.in_(level_ids))
                            .order_by(ConditionGroup.id)).all()
    for condition in db.scalars(select(Condition).where(Condition.group_id.in_(group_ids)).order_by(Condition.id)).all():
        db.add(Condition(group_id=group_ids[condition.group_id], question_id=question_ids[condition.question_id],
                         operator_id=condition.operator_id, text_answer=condition.text_answer,
                         choice_id=choice_ids[condition.choice_id] if condition.choice_id is not None else None))


def copy_form(db, source):
    try:
        db.refresh(source, with_for_update=True)
        copied = create_copy_header(db, source)
        block_ids, question_ids, choice_ids = copy_questions(db, source.id, copied.id)
        copy_conditions(db, block_ids, question_ids, choice_ids)
        for grade in db.scalars(select(GradingScale).where(GradingScale.form_id == source.id)
                               .order_by(GradingScale.id)).all():
            db.add(GradingScale(form_id=copied.id, min_percent=grade.min_percent, grade=grade.grade, message=grade.message))
        db.flush()
        result = {"id": copied.id, "title": copied.title, "is_published": False, "public_code": copied.public_code}
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
