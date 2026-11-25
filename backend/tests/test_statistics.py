from datetime import datetime, timedelta

import pytest
from sqlalchemy import event, select

from app.models import Attempt, Form, Question, QuestionType
from app.services import attempts as attempt_service
from test_attempts import published, start, finish, questions
from test_forms import create, draft, headers, users
from test_form_publication import complete_test_draft, save
from test_conditions import condition


def stats(client, form, user):
    response = client.get(f"/forms/{form['id']}/stats", headers=headers(user))
    assert response.status_code == 200, response.text
    return response.json()


def test_test_statistics_attempts_and_details(client, db_session, users, monkeypatch):
    data = complete_test_draft()
    data.update(requires_login=False, max_attempts=None, time_limit_minutes=None)
    form = published(client, users, True, data)
    source = [q for b in form['blocks'] for q in b['questions']]
    completed = []
    for index, (day, duration) in enumerate([(1, 10), (3, 21), (3, 40)]):
        moment = datetime(2026, 1, day, 12)
        monkeypatch.setattr(attempt_service, 'now_utc', lambda: moment)
        attempt = start(client, form, users[2] if index == 0 else None)
        answers = []
        if index < 2:
            for q in source:
                answer = {'question_id': int(q['key'][1:])}
                if q['type'] == 'text':
                    answer['text'] = ' ДА ' if index == 0 else 'да'
                else:
                    selected = [o for o in q['options'] if o['is_correct'] or (index == 1 and q['type'] == 'multiple')]
                    answer['option_ids'] = [int(o['key'][1:]) for o in reversed(selected)]
                answers.append(answer)
        moment += timedelta(seconds=duration)
        response = finish(client, attempt, answers, users[2] if index == 0 else None)
        assert response.status_code == 200, response.text
        completed.append(attempt)
    unfinished = start(client, form)
    # Чужая форма не должна попадать ни в счётчики, ни в распределения.
    other = published(client, users, True, data)
    assert finish(client, start(client, other), []).status_code == 200
    result = stats(client, form, users[0])
    assert result['summary'] == {'started': 4, 'finished': 3, 'completion_percent': 75,
        'finished_early': None, 'median_time_seconds': 21, 'avg_score': 6.3, 'avg_percent': 57.6}
    assert result['grade_distribution'] == [{'grade': '2', 'count': 2}, {'grade': '5', 'count': 1}]
    assert result['early_finish_rules'] is None
    assert result['daily_finished'] == [{'date': '2026-01-01', 'count': 1}, {'date': '2026-01-02', 'count': 0}, {'date': '2026-01-03', 'count': 2}]
    assert [b['avg_percent'] for b in result['blocks']] == [50, 66.7]
    assert [q['correct_percent'] for q in result['questions']] == [66.7, 33.3, 66.7]
    assert [q['avg_score_percent'] for q in result['questions']] == [66.7, 33.3, 66.7]
    assert all(q['shown'] == 3 and q['skipped'] == 1 for q in result['questions'])
    assert result['questions'][2]['top_answers'] == [{'value': 'да', 'count': 2}]
    multiple = result['questions'][1]
    assert multiple['options'][0]['count'] == 2 and multiple['options'][0]['percent'] == 66.7
    assert multiple['options'][1]['count'] == 1 and multiple['options'][1]['percent'] == 33.3
    assert 'top_answers' not in multiple and 'options' not in result['questions'][2]
    listing = client.get(f"/forms/{form['id']}/attempts", headers=headers(users[0])).json()
    assert listing[0]['attempt_id'] == unfinished['attempt']['id']
    assert listing[0]['user'] is None and listing[0]['score'] is None and not listing[0]['is_finished']
    assert listing[-1]['user']['id'] == users[2]
    assert 'attempt_key' not in str(listing)
    detail = client.get(f"/attempts/{completed[1]['attempt']['id']}/details", headers=headers(users[0])).json()
    assert detail['attempt']['id'] == completed[1]['attempt']['id'] and 'attempt_id' not in detail['attempt']
    assert [a['question_id'] for a in detail['answers']] == [int(q['key'][1:]) for q in source]
    assert detail['answers'][1]['selected_options'] == [{'id': int(o['key'][1:]), 'text': o['text']} for o in source[1]['options']]
    assert detail['answers'][1]['score'] == 0 and detail['answers'][1]['max_points'] == 3
    assert client.get(f"/attempts/{unfinished['attempt']['id']}/details", headers=headers(users[0])).json()['answers'] == []
    # Одинаковое время старта: более новый id должен быть первым.
    first = db_session.get(Attempt, completed[0]['attempt']['id'])
    last = db_session.get(Attempt, unfinished['attempt']['id'])
    first.started_at = last.started_at
    db_session.commit()
    listing = client.get(f"/forms/{form['id']}/attempts", headers=headers(users[0])).json()
    assert listing[0]['attempt_id'] == last.id


def test_survey_early_finish_and_details(client, db_session, users):
    data = draft()
    data['take_by_blocks'] = False
    data['blocks'][0]['questions'][0]['finish_rules'] = [
        {'key': 'rule', 'message': None, 'condition': condition(operator='chosen', option='choice-1')}]
    form = published(client, users, data=data)
    early = start(client, form)
    q1, q2 = questions(early)
    assert finish(client, early, [{'question_id': q1['id'], 'option_ids': [q1['options'][0]['id']]}]).status_code == 200
    normal = start(client, form)
    assert finish(client, normal, [{'question_id': q1['id'], 'option_ids': [q1['options'][1]['id']]}]).status_code == 200
    result = stats(client, form, users[0])
    assert result['summary']['finished_early'] == 1
    assert result['summary']['avg_score'] is None and result['summary']['avg_percent'] is None
    assert result['grade_distribution'] is None and result['blocks'] is None
    assert result['early_finish_rules'] == [{'rule_id': q1['finish_rules'][0]['id'], 'question_id': q1['id'],
        'question_text': q1['text'], 'message': None, 'count': 1}]
    assert [(q['shown'], q['skipped']) for q in result['questions']] == [(2, 0), (1, 1)]
    assert 'correct_percent' not in result['questions'][0] and 'avg_score_percent' not in result['questions'][0]
    assert 'is_correct' not in result['questions'][0]['options'][0]
    detail = client.get(f"/attempts/{early['attempt']['id']}/details", headers=headers(users[0])).json()
    assert detail['attempt']['finished_early']
    assert len(detail['answers']) == 1
    assert detail['answers'][0]['max_points'] is None and detail['answers'][0]['score'] is None
    assert detail['answers'][0]['block_title'] is None


@pytest.mark.parametrize('is_test', [False, True])
def test_empty_draft_statistics(client, users, is_test):
    form = create(client, users[0], is_test)
    saved = save(client, users[0], form, complete_test_draft() if is_test else draft())
    result = stats(client, saved, users[0])
    assert result['summary']['started'] == result['summary']['finished'] == result['summary']['completion_percent'] == 0
    assert all(result['summary'][key] is None for key in ['median_time_seconds', 'avg_score', 'avg_percent'])
    assert result['daily_finished'] == []
    assert len(result['questions']) == (3 if is_test else 2)
    for question in result['questions']:
        assert question['shown'] == question['skipped'] == 0
        for option in question.get('options', []):
            assert option['count'] == option['percent'] == 0
        if is_test:
            assert question['correct_percent'] == question['avg_score_percent'] == 0
    if is_test:
        assert result['grade_distribution'] == [{'grade': '2', 'count': 0}, {'grade': '5', 'count': 0}]
        assert result['questions'][-1]['top_answers'] == []
        assert all(block['avg_percent'] == 0 for block in result['blocks'])
    else:
        assert result['early_finish_rules'] == [] and result['blocks'] is None


def test_access_rules(client, users):
    form = published(client, users)
    attempt = start(client, form)
    urls = [f"/forms/{form['id']}/attempts", f"/forms/{form['id']}/stats", f"/attempts/{attempt['attempt']['id']}/details"]
    for url in urls:
        assert client.get(url).status_code == 401
        assert client.get(url, headers=headers(users[2])).status_code == 403
        assert client.get(url, headers=headers(users[1])).status_code == 403
    for url in ['/forms/2147483648/attempts', '/forms/2147483648/stats', '/attempts/2147483648/details']:
        assert client.get(url, headers=headers(users[0])).status_code == 404


def test_query_count_does_not_grow_and_unfinished_not_in_metrics(client, db_session, users):
    form = published(client, users, True)
    def count_queries():
        queries = []
        def record(conn, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith('SELECT'):
                queries.append(statement)
        connection = db_session.connection()
        event.listen(connection, 'before_cursor_execute', record)
        try:
            result = stats(client, form, users[0])
        finally:
            event.remove(connection, 'before_cursor_execute', record)
        return len(queries), result
    initial, _ = count_queries()
    for i in range(10):
        db_session.add(Attempt(form_id=form['id'], started_at=datetime(2020, 1, 1), attempt_key=f'stats-{i}'))
    # info проверяется напрямую: его создание в API отложено до этапа 8.
    block_id = int(form['blocks'][0]['key'][1:])
    db_session.add(Question(block_id=block_id, position=99, text='Пояснение',
        type_id=db_session.scalar(select(QuestionType.id).where(QuestionType.type == 'info'))))
    db_session.commit()
    later, result = count_queries()
    assert later == initial and later <= 16
    assert result['summary']['started'] == 10 and result['summary']['finished'] == 0
    assert result['summary']['avg_score'] is None
    assert len(result['questions']) == 3
