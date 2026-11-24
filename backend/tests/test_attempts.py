from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.models import Attempt, AttemptAnswer, AttemptAnswerChoice, Form, User
from app.services import attempts as service
from test_forms import create, draft, headers, users
from test_form_publication import complete_test_draft, save
from test_conditions import condition
from app.database import engine
from app.dependencies import owned_attempt
from app.models import Block, Question, QuestionType
from app.services.attempt_errors import AttemptError


def published(client, users, is_test=False, data=None):
    form = create(client, users[0], is_test)
    saved = save(client, users[0], form, data if data is not None else (complete_test_draft() if is_test else draft()))
    response = client.post(f"/forms/{form['id']}/publish", headers=headers(users[0]))
    assert response.status_code == 200, response.text
    return saved


def start(client, form, user=None):
    response = client.post(f"/forms/{form['id']}/attempts", headers=headers(user) if user else {})
    assert response.status_code == 201, response.text
    return response.json()


def finish(client, started, answers, user=None):
    auth = headers(user) if user else {"X-Attempt-Key": started["attempt"]["attempt_key"]}
    return client.post(f"/attempts/{started['attempt']['id']}/finish", headers=auth, json={"answers": answers})


def questions(started):
    return [q for b in started["form"]["blocks"] for q in b["questions"]]


def test_public_start_limits_and_auth(client, db_session, users):
    form = published(client, users, True)
    url = f"/public/forms/{form['public_code']}"
    assert client.get(url).json()["attempts_used"] is None
    assert client.get(url, headers={"Authorization": "nonsense"}).status_code == 401
    assert client.get(url, headers={"Authorization": "Bearer invalid"}).status_code == 401
    assert client.post(f"/forms/{form['id']}/attempts").status_code == 401
    assert client.post(f"/forms/{form['id']}/attempts", headers=headers(users[0])).json()["detail"] == "Составители не могут проходить формы"
    first = start(client, form, users[2])
    second = start(client, form, users[2])
    assert first["attempt"]["attempt_key"] != second["attempt"]["attempt_key"]
    assert db_session.get(Attempt, first["attempt"]["id"]).user_id == users[2]
    assert client.post(f"/forms/{form['id']}/attempts", headers=headers(users[2])).status_code == 409
    info = client.get(url, headers=headers(users[2])).json()
    assert (info["attempts_used"], info["attempts_left"]) == (2, 0)
    assert datetime.fromisoformat(first["attempt"]["deadline"]) - datetime.fromisoformat(first["attempt"]["started_at"]) == timedelta(minutes=30)
    draft_form = create(client, users[0])
    assert client.get(f"/public/forms/{draft_form['public_code']}").status_code == 404
    assert client.get('/public/forms/missing').status_code == 404
    assert client.post(f"/forms/{draft_form['id']}/attempts").status_code == 404
    assert client.post('/forms/2147483648/attempts').status_code == 404


def test_no_sensitive_fields_at_start(client, users):
    data = complete_test_draft()
    data.update(requires_login=False, max_attempts=None)
    form = published(client, users, True, data)
    started = start(client, form)
    banned = {"points", "is_correct", "correct_text_answers", "grading_scale", "completion_message", "message"}
    def check(value):
        if isinstance(value, dict):
            assert not banned.intersection(value)
            for child in value.values():
                check(child)
        elif isinstance(value, list):
            for child in value:
                check(child)
    check(started["form"])
    assert set(started["form"]["question_order"]) == {q["id"] for q in questions(started)}


def test_survey_required_finish_result_and_ownership(client, db_session, users):
    form = published(client, users)
    started = start(client, form)
    assert started["attempt"]["deadline"] is None
    assert db_session.get(Attempt, started["attempt"]["id"]).user_id is None
    assert client.get(f"/public/forms/{form['public_code']}", headers=headers(users[2])).json()["attempts_left"] is None
    q1, q2 = questions(started)
    url = f"/attempts/{started['attempt']['id']}"
    key = {"X-Attempt-Key": started["attempt"]["attempt_key"]}
    assert client.get(url + '/result', headers=key).status_code == 409
    assert client.get(url + '/result').status_code == 401
    assert client.get(url + '/result', headers={"X-Attempt-Key": "wrong"}).status_code == 403
    response = finish(client, started, [])
    assert response.status_code == 422
    assert response.json()["missing_question_ids"] == [q1["id"]]
    assert not list(db_session.scalars(select(AttemptAnswer).where(AttemptAnswer.attempt_id == started["attempt"]["id"])))
    assert db_session.get(Attempt, started["attempt"]["id"]).finished_at is None
    response = finish(client, started, [{"question_id": q1["id"], "option_ids": [q1["options"][0]["id"]]}])
    assert response.json() == {"attempt_id": started["attempt"]["id"], "is_test": False, "finished_early": False, "message": "Спасибо!"}
    result = client.get(url + '/result', headers=key).json()
    assert len(result["answers"]) == 2
    assert result["answers"][1]["selected_options"] == []
    assert result["answers"][0]["score"] is None
    assert finish(client, started, []).status_code == 409
    assert client.get(url + '/result', headers=key).json() == result
    authenticated = start(client, form, users[2])
    other_url = f"/attempts/{authenticated['attempt']['id']}/finish"
    assert client.post(other_url, headers=headers(users[1]), json={"answers": []}).status_code == 403
    assert client.post(other_url, json={"answers": []}).status_code == 401
    assert client.post(other_url, headers={"X-Attempt-Key": authenticated['attempt']['attempt_key']}, json={"answers": []}).status_code == 403
    assert client.get('/attempts/2147483647/result', headers=key).status_code == 404


@pytest.mark.parametrize("by_blocks,expected", [(False, 1), (True, 2)])
def test_early_finish_and_ignored_invalid_later_answers(client, db_session, users, by_blocks, expected):
    data = draft()
    data['take_by_blocks'] = by_blocks
    data['blocks'][0]['questions'][0]['finish_rules'] = [{"key": "r", "message": "Готово", "condition": condition(operator="chosen", option="choice-1")}]
    data['blocks'].append({"key": "last", "questions": [{"key": "q3", "type": "text", "text": "Позже", "is_answer_required": True}]})
    form = published(client, users, data=data)
    started = start(client, form)
    q1, q2, q3 = questions(started)
    response = finish(client, started, [{"question_id": q1['id'], "option_ids": [q1['options'][0]['id']]},
                                        {"question_id": q3['id'], "text": 'x' * 1001}])
    assert response.status_code == 200, response.text
    assert response.json()['finished_early'] and response.json()['message'] == 'Готово'
    stored = db_session.get(Attempt, started['attempt']['id'])
    assert stored.early_finish_rule_id == q1['finish_rules'][0]['id']
    assert len(list(db_session.scalars(select(AttemptAnswer).where(AttemptAnswer.attempt_id == stored.id)))) == expected
    result = client.get(f"/attempts/{stored.id}/result", headers={"X-Attempt-Key": stored.attempt_key}).json()
    assert result['finished_early'] and len(result['answers']) == expected


def test_hidden_question_not_saved(client, db_session, users):
    data = draft()
    data['blocks'][0]['questions'][1].update(condition=condition(operator='chosen', option='choice-2'), is_answer_required=True)
    form = published(client, users, data=data)
    started = start(client, form)
    q1, q2 = questions(started)
    response = finish(client, started, [{"question_id": q1['id'], "option_ids": [q1['options'][0]['id']]},
                                        {"question_id": q2['id'], "option_ids": [999999]}])
    assert response.status_code == 200
    assert list(db_session.scalars(select(AttemptAnswer.question_id).where(AttemptAnswer.attempt_id == started['attempt']['id']))) == [q1['id']]


@pytest.mark.parametrize("kind", ['foreign', 'duplicate', 'foreign-option', 'single-many', 'text-option', 'choice-text', 'long-text'])
def test_invalid_answers(client, users, kind):
    form = published(client, users, True)
    started = start(client, form, users[2])
    q1 = next(q for q in questions(started) if q['type'] == 'single')
    q2 = next(q for q in questions(started) if q['type'] == 'multiple')
    q3 = next(q for q in questions(started) if q['type'] == 'text')
    answer = {"question_id": q1['id'], "option_ids": [q1['options'][0]['id']]}
    answers = [answer]
    if kind == 'foreign': answer['question_id'] = 2147483647
    elif kind == 'duplicate': answers.append(answer.copy())
    elif kind == 'foreign-option': answer['option_ids'] = [q2['options'][0]['id']]
    elif kind == 'single-many': answer['option_ids'] = [o['id'] for o in q1['options']]
    elif kind == 'text-option': answer['question_id'] = q3['id']
    elif kind == 'choice-text': answer['text'] = 'wrong'
    else: answers = [{"question_id": q3['id'], "text": 'я' * 1001}]
    assert finish(client, started, answers, users[2]).status_code == 422


@pytest.mark.parametrize('length,padding,status', [(1000, '', 200), (1001, '', 422),
                                                (1000, ' \n\t', 200), (1001, ' \n\t', 422)])
def test_text_answer_length_after_trim(client, db_session, users, length, padding, status):
    form = published(client, users, True)
    started = start(client, form, users[2])
    text_question = next(q for q in questions(started) if q['type'] == 'text')
    single = next(q for q in questions(started) if q['type'] == 'single')
    response = finish(client, started, [
        {'question_id': single['id'], 'option_ids': [single['options'][0]['id']]},
        {'question_id': text_question['id'], 'text': padding + 'я' * length + padding},
    ], users[2])
    assert response.status_code == status, response.text
    attempt_id = started['attempt']['id']
    attempt = db_session.get(Attempt, attempt_id)
    rows = list(db_session.scalars(select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt_id)))
    if status == 422:
        assert str(text_question['id']) in response.json()['detail']
        assert 'длиннее 1000 символов' in response.json()['detail']
        assert attempt.finished_at is None and attempt.score is None
        assert rows == []
        assert not list(db_session.scalars(select(AttemptAnswerChoice).join(AttemptAnswer)
            .where(AttemptAnswer.attempt_id == attempt_id)))
    else:
        assert attempt.finished_at is not None
        assert next(row for row in rows if row.question_id == text_question['id']).text_answer == padding + 'я' * length + padding


def test_test_scores_result_and_history(client, db_session, users):
    form = published(client, users, True)
    started = start(client, form, users[2])
    # Ответы берём из сохранённой авторской формы, а не из случайного порядка старта.
    answers = []
    for block in form['blocks']:
        for question in block['questions']:
            answer = {'question_id': int(question['key'][1:])}
            if question['type'] == 'text':
                answer['text'] = ' ДА '
            else:
                answer['option_ids'] = [int(o['key'][1:]) for o in question['options'] if o['is_correct']]
            answers.append(answer)
    response = finish(client, started, answers, users[2])
    assert response.status_code == 200, response.text
    result = response.json()
    assert (result['score'], result['max_score'], result['percent'], result['grade'], result['message']) == (11, 11, 100, '5', 'Отлично')
    assert len(result['review']) == 3 and len(result['block_results']) == 2
    assert result['better_than_percent'] is None and 'answers' not in result
    assert client.get(f"/attempts/{started['attempt']['id']}/result", headers=headers(users[2])).json() == result
    later = start(client, form, users[2])
    history = client.get('/my/attempts', headers=headers(users[2])).json()
    assert history[0]['attempt_id'] == later['attempt']['id']
    assert history[0]['is_finished'] is False
    assert all(history[0][key] is None for key in ['finished_at', 'score', 'max_score', 'percent', 'grade'])
    assert history[1]['grade'] == '5'
    assert client.get('/my/attempts').status_code == 401
    assert client.get('/my/attempts', headers=headers(users[0])).status_code == 403
    stored_form = db_session.get(Form, form['id'])
    stored_form.show_correct_answers = False
    stored_form.show_results_by_block = False
    db_session.commit()
    result = client.get(f"/attempts/{started['attempt']['id']}/result", headers=headers(users[2])).json()
    assert result['review'] is None and result['block_results'] is None


@pytest.mark.parametrize("seconds,status", [(31 * 60, 200), (32 * 60, 200), (32 * 60 + 1, 409)])
def test_deadline_grace(client, db_session, users, monkeypatch, seconds, status):
    now = datetime(2026, 1, 1)
    monkeypatch.setattr(service, 'now_utc', lambda: now)
    form = published(client, users, True)
    started = start(client, form, users[2])
    monkeypatch.setattr(service, 'now_utc', lambda: now + timedelta(seconds=seconds))
    assert finish(client, started, [], users[2]).status_code == status
    attempt = db_session.get(Attempt, started['attempt']['id'])
    assert (attempt.finished_at is None) == (status == 409)
    assert client.get(f"/public/forms/{form['public_code']}", headers=headers(users[2])).json()['attempts_used'] == 1


def test_better_than_and_zero_maximum(client, db_session, users):
    form = published(client, users, True)
    started = start(client, form, users[2])
    assert finish(client, started, [], users[2]).status_code == 200
    current = db_session.get(Attempt, started['attempt']['id'])
    current.score, current.max_score, current.percent, current.grading_scale_id = 0, 0, 0, None
    for i in range(5):
        db_session.add(Attempt(form_id=form['id'], attempt_key=f'compare-{i}', started_at=datetime(2026, 1, 1),
                              finished_at=datetime(2026, 1, 1), score=i, max_score=5, percent=i * 20))
    db_session.commit()
    url = f"/attempts/{current.id}/result"
    result = client.get(url, headers=headers(users[2])).json()
    assert result['better_than_percent'] == 0 and result['grade'] is None and result['message'] == 'Спасибо!'
    current.percent = 50
    db_session.commit()
    assert client.get(url, headers=headers(users[2])).json()['better_than_percent'] == 60


def test_finish_rollback_after_insert_failure(client, db_session, users):
    form = published(client, users)
    started = start(client, form)
    q1 = questions(started)[0]
    connection = db_session.connection()
    def fail(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith('INSERT INTO attempt_answer_choices '):
            raise RuntimeError('Проверка отката')
    event.listen(connection, 'before_cursor_execute', fail)
    try:
        with pytest.raises(RuntimeError, match='Проверка отката'):
            finish(client, started, [{"question_id": q1['id'], "option_ids": [q1['options'][0]['id']]}])
    finally:
        event.remove(connection, 'before_cursor_execute', fail)
    assert db_session.get(Attempt, started['attempt']['id']).finished_at is None
    assert not list(db_session.scalars(select(AttemptAnswer).where(AttemptAnswer.attempt_id == started['attempt']['id'])))


def test_concurrent_finish_only_writes_once():
    # Две реальные транзакции должны видеть одну временную опубликованную форму.
    # Удаляем только записи этого теста в finally, вместе с каскадными ответами.
    marker = uuid4().hex
    user_id = form_id = None
    try:
        with Session(engine) as db:
            user = User(email=f'concurrent-{marker}@example.com', name='Проверка гонки', password_hash='test', is_author=True)
            db.add(user)
            db.flush()
            form = Form(author_id=user.id, title='Проверка гонки', public_code=marker[:20], is_published=True)
            db.add(form)
            db.flush()
            block = Block(form_id=form.id, position=1)
            db.add(block)
            db.flush()
            db.add(Question(block_id=block.id, type_id=db.scalar(select(QuestionType.id).where(QuestionType.type == 'text')), text='Ответ', position=1))
            attempt = Attempt(form_id=form.id, started_at=datetime(2026, 1, 1), attempt_key=marker)
            db.add(attempt)
            db.flush()
            user_id, form_id, attempt_id = user.id, form.id, attempt.id
            db.commit()
        barrier = Barrier(2)
        def worker():
            with Session(engine) as db:
                barrier.wait(timeout=10)
                attempt = owned_attempt(attempt_id, SimpleNamespace(method='POST'), None, marker, db)
                try:
                    service.finish_attempt(db, attempt, [])
                    return 200
                except AttemptError as error:
                    return error.status
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker) for _ in range(2)]
            assert sorted(f.result(timeout=15) for f in futures) == [200, 409]
        with Session(engine) as db:
            assert len(list(db.scalars(select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt_id)))) == 1
    finally:
        with Session(engine) as db:
            if form_id is not None and (form := db.get(Form, form_id)) is not None:
                db.delete(form)
                db.flush()
            if user_id is not None and (user := db.get(User, user_id)) is not None:
                db.delete(user)
            db.commit()
