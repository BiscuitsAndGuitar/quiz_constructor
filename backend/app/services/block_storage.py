from sqlalchemy import select
from app.models import Block, Question, QuestionType, QuestionChoice, CorrectTextAnswer, Image, ConditionOperator
from app.services.condition_storage import add_conditions_to_response, save_conditions
from app.services.conditions import validate_conditions
from app.services.form_validation import InvalidFormError, validate_form


def read_blocks(db, blocks, is_test):
    block_ids = [block.id for block in blocks]
    questions = db.execute(
        select(Question, QuestionType.type).join(QuestionType)
        .join(Block, Question.block_id == Block.id).where(Block.id.in_(block_ids))
        .order_by(Question.position, Question.id)
    ).all()
    choices = db.scalars(
        select(QuestionChoice).join(Question).join(Block)
        .where(Block.id.in_(block_ids)).order_by(QuestionChoice.position, QuestionChoice.id)
    ).all()
    choices_by_question = {}
    for choice in choices:
        item = {"key": f"o{choice.id}", "text": choice.text}
        if is_test:
            item["is_correct"] = choice.is_correct
        choices_by_question.setdefault(choice.question_id, []).append(item)
    answers_by_question = {}
    if is_test:
        # У допустимых ответов нет position: id сохраняет порядок вставки списка.
        answers = db.scalars(select(CorrectTextAnswer).join(Question).join(Block)
                             .where(Block.id.in_(block_ids)).order_by(CorrectTextAnswer.id))
        for answer in answers:
            answers_by_question.setdefault(answer.question_id, []).append(answer.answer_text)
    questions_by_block = {}
    images = {image.id: image for image in db.scalars(select(Image).where(Image.id.in_(
        {question.image_id for question, _ in questions if question.image_id is not None}
    )))}
    for question, question_type in questions:
        item = {
            "key": f"q{question.id}", "text": question.text, "type": question_type,
            "is_answer_required": question.is_answer_required,
            "options": choices_by_question.get(question.id, []),
            "image": ({"id": question.image_id, "url": f"/uploads/{images[question.image_id].file_name}"}
                      if question.image_id in images else None),
        }
        if is_test and question_type != "info":
            item["points"] = question.points
            item["allow_partial_scoring"] = question.allow_partial_scoring if question_type == "multiple" else False
            if question_type == "text":
                item["correct_text_answers"] = answers_by_question.get(question.id, [])
        questions_by_block.setdefault(question.block_id, []).append(item)
    result = {"blocks": [{"key": f"b{block.id}", "title": block.title,
                          "questions": questions_by_block.get(block.id, [])} for block in blocks]}
    if not is_test:
        add_conditions_to_response(db, result)
    return result["blocks"]


def validate_blocks(db, data, is_test):
    validate_form(data, is_test)
    image_ids = {question.image_id for block in data.blocks for question in block.questions if question.image_id is not None}
    existing_images = set(db.scalars(select(Image.id).where(Image.id.in_(image_ids))))
    if image_ids != existing_images:
        raise InvalidFormError("Картинка не найдена")
    operator_ids = dict(db.execute(select(ConditionOperator.operator, ConditionOperator.id)).all())
    validate_conditions([block.model_dump(exclude_unset=True) for block in data.blocks], is_test, set(operator_ids))
    return operator_ids


def write_blocks(db, blocks, is_test, operator_ids, *, form_id=None, library_block_id=None):
    type_ids = dict(db.execute(select(QuestionType.type, QuestionType.id)).all())
    block_ids, question_ids, choice_ids = {}, {}, {}
    for block_position, block_data in enumerate(blocks, start=1):
        block = Block(form_id=form_id, library_block_id=library_block_id, title=block_data.title, position=block_position)
        db.add(block)
        db.flush()
        block_ids[block_data.key] = block.id
        for question_position, question_data in enumerate(block_data.questions, start=1):
            question = Question(
                block_id=block.id, type_id=type_ids[question_data.type], text=question_data.text,
                is_answer_required=question_data.is_answer_required if not is_test else False,
                position=question_position,
                image_id=question_data.image_id,
                points=question_data.points if is_test else None,
                allow_partial_scoring=bool(question_data.allow_partial_scoring) if is_test else False,
            )
            db.add(question)
            db.flush()
            question_ids[question_data.key] = question.id
            for choice_position, choice_data in enumerate(question_data.options, start=1):
                choice = QuestionChoice(question_id=question.id, text=choice_data.text,
                                      position=choice_position,
                                      is_correct=bool(choice_data.is_correct) if is_test else False)
                db.add(choice)
                db.flush()
                choice_ids[choice_data.key] = choice.id
            if is_test:
                for answer in question_data.correct_text_answers:
                    db.add(CorrectTextAnswer(question_id=question.id, answer_text=answer))
    if not is_test:
        save_conditions(db, blocks, block_ids, question_ids, choice_ids, operator_ids)


