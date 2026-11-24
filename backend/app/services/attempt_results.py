from sqlalchemy import func, select

from app.models import Attempt, AttemptAnswer, AttemptAnswerChoice, Form, GradingScale
from app.services.attempt_data import load_attempt_form
from app.services.attempt_errors import AttemptError
from app.services.scoring import completion_message, percent_score


def stored_answers(db, attempt_id):
    rows = db.scalars(select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt_id)).all()
    choices = {}
    for answer_id, choice_id in db.execute(select(AttemptAnswerChoice.attempt_answer_id, AttemptAnswerChoice.choice_id)
        .where(AttemptAnswerChoice.attempt_answer_id.in_([row.id for row in rows])).order_by(AttemptAnswerChoice.id)):
        choices.setdefault(answer_id, []).append(choice_id)
    return {row.question_id: {"text": row.text_answer, "score": row.score, "option_ids": choices.get(row.id, [])} for row in rows}


def survey_answers(data, answers):
    result = []
    for block in data["blocks"]:
        for question in block["questions"]:
            answer = answers.get(question["id"])
            if answer is None or question["type"] == "info":
                continue
            result.append({"question_id": question["id"], "block_title": block["title"], "text": question["text"],
                "type": question["type"], "selected_options": [
                    {"id": option["id"], "text": option["text"]} for option in question["options"] if option["id"] in answer["option_ids"]],
                "text_answer": answer["text"], "max_points": None, "score": None})
    return result


def better_than_percent(db, attempt):
    others = select(Attempt).where(Attempt.form_id == attempt.form_id, Attempt.id != attempt.id,
                                   Attempt.finished_at.is_not(None))
    total = db.scalar(select(func.count()).select_from(others.subquery()))
    if total < 5:
        return None
    lower = db.scalar(select(func.count()).select_from(others.where(Attempt.percent < attempt.percent).subquery()))
    return lower * 100 // total


def build_result(db, attempt, include_answers=False):
    if attempt.finished_at is None:
        raise AttemptError(409, "Попытка ещё не завершена")
    form = db.get(Form, attempt.form_id)
    data = load_attempt_form(db, form)
    answers = stored_answers(db, attempt.id)
    grade = next((row for row in data["grading_scale"] if row["id"] == attempt.grading_scale_id), None)
    rule = next((rule for block in data["blocks"] for q in block["questions"] for rule in q.get("finish_rules", [])
                 if rule["id"] == attempt.early_finish_rule_id), None)
    result = {"attempt_id": attempt.id, "is_test": form.is_test, "finished_early": bool(attempt.early_finish_rule_id),
              "message": completion_message(rule.get("message") if rule else None, grade.get("message") if grade else None, form.completion_message)}
    if not form.is_test:
        if include_answers:
            result["answers"] = survey_answers(data, answers)
        return result
    result.update(score=attempt.score, max_score=attempt.max_score, percent=float(attempt.percent),
                  grade=grade["grade"] if grade else None, better_than_percent=better_than_percent(db, attempt),
                  block_results=None, review=None)
    if form.show_results_by_block and len(data["blocks"]) >= 2:
        result["block_results"] = []
        for block in data["blocks"]:
            questions = [q for q in block["questions"] if q["type"] != "info"]
            maximum = sum(q.get("points") or 0 for q in questions)
            score = sum(answers.get(q["id"], {}).get("score") or 0 for q in questions)
            if maximum > 0:
                result["block_results"].append({"block_id": block["id"], "title": block["title"], "score": score,
                    "max_score": maximum, "percent": float(percent_score(score, maximum))})
    if form.show_correct_answers:
        result["review"] = []
        for block in data["blocks"]:
            for question in block["questions"]:
                if question["type"] == "info":
                    continue
                answer = answers.get(question["id"], {})
                item = {"question_id": question["id"], "text": question["text"], "max_points": question.get("points") or 0,
                        "score": answer.get("score") or 0}
                if question["type"] == "text":
                    item.update(your_text=answer.get("text"), correct_text_answers=question.get("correct_text_answers", []))
                else:
                    item.update(your_option_ids=answer.get("option_ids", []),
                                correct_option_ids=[o["id"] for o in question["options"] if o["is_correct"]],
                                your_options=[{"id": o["id"], "text": o["text"]} for o in question["options"]
                                              if o["id"] in answer.get("option_ids", [])],
                                correct_options=[{"id": o["id"], "text": o["text"]} for o in question["options"] if o["is_correct"]])
                result["review"].append(item)
    return result


def attempt_history(db, user_id):
    rows = db.execute(select(Attempt, Form, GradingScale.grade).select_from(Attempt)
                      .join(Form, Attempt.form_id == Form.id).outerjoin(GradingScale, Attempt.grading_scale_id == GradingScale.id)
                      .where(Attempt.user_id == user_id).order_by(Attempt.started_at.desc(), Attempt.id.desc()))
    return [{"attempt_id": attempt.id, "form": {"id": form.id, "title": form.title, "is_test": form.is_test},
             "is_finished": attempt.finished_at is not None, "finished_at": attempt.finished_at,
             "score": attempt.score if attempt.finished_at else None, "max_score": attempt.max_score if attempt.finished_at else None,
             "percent": float(attempt.percent) if attempt.finished_at and attempt.percent is not None else None,
             "grade": grade if attempt.finished_at else None} for attempt, form, grade in rows]
