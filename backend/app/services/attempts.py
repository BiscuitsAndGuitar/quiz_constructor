from datetime import datetime, timedelta, timezone
import secrets

from sqlalchemy import func, select

from app.models import Attempt, AttemptAnswer, AttemptAnswerChoice, Form
from app.services.attempt_data import load_attempt_form, participant_form
from app.services.attempt_errors import AttemptError
from app.services.attempt_results import build_result
from app.services.scoring import percent_score, question_score, select_grade
from app.services.shuffling import shuffled_form
from app.services.visibility import has_answer, visible_questions

TIME_GRACE = timedelta(minutes=2)


def now_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def attempts_used(db, form_id, user_id):
    return db.scalar(select(func.count(Attempt.id)).where(Attempt.form_id == form_id, Attempt.user_id == user_id))


def public_form(db, code, user):
    form = db.scalar(select(Form).where(Form.public_code == code, Form.is_published.is_(True)))
    if form is None:
        raise AttemptError(404, "Форма не найдена или не опубликована")
    used = attempts_used(db, form.id, user.id) if user is not None and form.max_attempts is not None else None
    return {"id": form.id, "is_test": form.is_test, "title": form.title, "description": form.description,
            "requires_login": form.requires_login, "time_limit_minutes": form.time_limit_minutes,
            "max_attempts": form.max_attempts, "attempts_used": used,
            "attempts_left": max(0, form.max_attempts - used) if used is not None else None}


def start_attempt(db, form_id, user):
    try:
        # Сериализуем старты одной формы: два запроса не обойдут лимит одновременно.
        form = db.scalar(select(Form).where(Form.id == form_id, Form.is_published.is_(True)).with_for_update()) if 1 <= form_id <= 2147483647 else None
        if form is None:
            raise AttemptError(404, "Форма не найдена или не опубликована")
        if form.requires_login and user is None:
            raise AttemptError(401, "Для прохождения формы войдите в аккаунт")
        if user is not None and form.max_attempts is not None and attempts_used(db, form.id, user.id) >= form.max_attempts:
            raise AttemptError(409, "Лимит попыток исчерпан")
        attempt = Attempt(form_id=form.id, user_id=user.id if user else None,
                          attempt_key=secrets.token_hex(32), started_at=now_utc())
        db.add(attempt)
        db.flush()
        data = participant_form(shuffled_form(load_attempt_form(db, form)))
        deadline = attempt.started_at + timedelta(minutes=form.time_limit_minutes) if form.is_test and form.time_limit_minutes else None
        result = {"attempt": {"id": attempt.id, "attempt_key": attempt.attempt_key, "started_at": attempt.started_at, "deadline": deadline}, "form": data}
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


def index_answers(data, submitted):
    questions = {q["id"] for b in data["blocks"] for q in b["questions"]}
    answers = {}
    for item in submitted:
        question_id = item["question_id"]
        if question_id not in questions:
            raise AttemptError(422, f"Вопрос {question_id} не принадлежит этой форме")
        if question_id in answers:
            raise AttemptError(422, f"Ответ на вопрос {question_id} передан повторно")
        answers[question_id] = item
    return answers


def validate_visible_answers(questions, answers):
    for question in questions:
        if question["type"] == "info":
            continue
        answer = answers.get(question["id"], {})
        options = answer.get("option_ids") or []
        text = answer.get("text")
        prefix = f"Вопрос {question['id']}: "
        if question["type"] == "text":
            if options:
                raise AttemptError(422, prefix + "у текстового вопроса не может быть выбранных вариантов")
            if text is not None and len(text) > 1000:
                raise AttemptError(422, prefix + "ответ должен быть не длиннее 1000 символов")
        else:
            if text is not None:
                raise AttemptError(422, prefix + "вопрос с выбором не принимает текстовый ответ")
            if any(option not in {o["id"] for o in question["options"]} for option in options):
                raise AttemptError(422, prefix + "вариант не принадлежит вопросу")
            if question["type"] == "single" and len(options) > 1:
                raise AttemptError(422, prefix + "можно выбрать только один вариант")


def finish_attempt(db, attempt, submitted):
    try:
        # Строка уже заблокирована зависимостью owned_attempt до проверки владельца.
        if attempt.finished_at is not None:
            raise AttemptError(409, "Попытка уже завершена")
        form = db.get(Form, attempt.form_id)
        finished_at = now_utc()
        if form.is_test and form.time_limit_minutes and finished_at > attempt.started_at + timedelta(minutes=form.time_limit_minutes) + TIME_GRACE:
            raise AttemptError(409, "Время прохождения истекло")
        data = load_attempt_form(db, form)
        answers = index_answers(data, submitted)
        visible, rule = visible_questions(data, answers)
        # Значения скрытых ответов не проверяем и не сохраняем, включая ответы после завершения.
        validate_visible_answers(visible, answers)
        shown = [q for q in visible if q["type"] != "info"]
        if not form.is_test:
            missing = [q["id"] for q in shown if q["is_answer_required"] and not has_answer(answers.get(q["id"]))]
            if missing:
                raise AttemptError(422, "Не заполнены обязательные вопросы", missing_question_ids=missing)
        scores = {}
        for question in shown:
            answer = answers.get(question["id"], {})
            score = question_score(question, answer) if form.is_test else None
            scores[question["id"]] = score
            row = AttemptAnswer(attempt_id=attempt.id, question_id=question["id"], score=score,
                                text_answer=answer.get("text") if question["type"] == "text" else None)
            db.add(row)
            db.flush()
            # Повтор варианта в multiple не увеличивает баллы и не создаёт дубликат строки.
            for choice_id in dict.fromkeys(answer.get("option_ids") or []):
                db.add(AttemptAnswerChoice(attempt_answer_id=row.id, choice_id=choice_id))
        attempt.finished_at = finished_at
        attempt.early_finish_rule_id = rule["id"] if rule else None
        if form.is_test:
            attempt.score = sum(scores.values())
            attempt.max_score = sum(q.get("points") or 0 for b in data["blocks"] for q in b["questions"] if q["type"] != "info")
            attempt.percent = percent_score(attempt.score, attempt.max_score)
            grade = select_grade(attempt.score, attempt.max_score, data["grading_scale"])
            attempt.grading_scale_id = grade["id"] if grade else None
        db.flush()
        result = build_result(db, attempt)
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
