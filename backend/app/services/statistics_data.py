from sqlalchemy import select

from app.models import Attempt, AttemptAnswer, AttemptAnswerChoice, Form, GradingScale, User
from app.services.attempt_data import load_attempt_form
from app.services.attempt_results import stored_answers, survey_answers
from app.services.statistics import build_statistics


def attempt_row(attempt, user, grade, is_test):
    scored = is_test and attempt.finished_at is not None
    return {'attempt_id': attempt.id, 'user': {'id': user.id, 'name': user.name} if user else None,
            'is_finished': attempt.finished_at is not None, 'finished_early': attempt.early_finish_rule_id is not None,
            'started_at': attempt.started_at, 'finished_at': attempt.finished_at,
            'score': attempt.score if scored else None, 'max_score': attempt.max_score if scored else None,
            'percent': attempt.percent if scored else None, 'grade': grade if scored else None}


def list_form_attempts(db, form):
    rows = db.execute(select(Attempt, User, GradingScale.grade).select_from(Attempt)
                      .outerjoin(User, Attempt.user_id == User.id)
                      .outerjoin(GradingScale, Attempt.grading_scale_id == GradingScale.id)
                      .where(Attempt.form_id == form.id).order_by(Attempt.started_at.desc(), Attempt.id.desc()))
    return [attempt_row(attempt, user, grade, form.is_test) for attempt, user, grade in rows]


def attempt_details(db, attempt):
    form = db.get(Form, attempt.form_id)
    user = db.get(User, attempt.user_id) if attempt.user_id is not None else None
    grade = db.get(GradingScale, attempt.grading_scale_id) if attempt.grading_scale_id is not None else None
    item = attempt_row(attempt, user, grade.grade if grade else None, form.is_test)
    item['id'] = item.pop('attempt_id')
    if attempt.finished_at is None:
        return {'attempt': item, 'answers': []}
    data = load_attempt_form(db, form)
    answers = stored_answers(db, attempt.id)
    # Тексты и порядок вариантов собираются так же, как в результате опроса.
    result = survey_answers(data, answers)
    if form.is_test:
        questions = {q['id']: q for b in data['blocks'] for q in b['questions']}
        for row in result:
            row['max_points'] = questions[row['question_id']].get('points') or 0
            row['score'] = answers[row['question_id']]['score']
    return {'attempt': item, 'answers': result}


def form_statistics(db, form):
    data = load_attempt_form(db, form)
    attempts = [dict(row) for row in db.execute(select(
        Attempt.id, Attempt.started_at, Attempt.finished_at, Attempt.score, Attempt.percent,
        Attempt.grading_scale_id, Attempt.early_finish_rule_id).where(Attempt.form_id == form.id)).mappings()]
    # Две общие выборки для всех ответов; число запросов не растёт с числом вопросов и попыток.
    statement = select(AttemptAnswer).join(Attempt).where(Attempt.form_id == form.id, Attempt.finished_at.is_not(None))
    rows = db.scalars(statement).all()
    selected = {}
    choices = db.execute(select(AttemptAnswerChoice.attempt_answer_id, AttemptAnswerChoice.choice_id)
                         .join(AttemptAnswer, AttemptAnswerChoice.attempt_answer_id == AttemptAnswer.id)
                         .join(Attempt, AttemptAnswer.attempt_id == Attempt.id)
                         .where(Attempt.form_id == form.id, Attempt.finished_at.is_not(None)))
    for answer_id, choice_id in choices:
        selected.setdefault(answer_id, []).append(choice_id)
    answers = [{'attempt_id': row.attempt_id, 'question_id': row.question_id, 'text': row.text_answer,
                'score': row.score, 'option_ids': selected.get(row.id, [])} for row in rows]
    return build_statistics(data, attempts, answers)
