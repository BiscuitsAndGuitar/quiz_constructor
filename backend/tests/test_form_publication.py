from datetime import datetime, timezone

import pytest
from sqlalchemy import event, select

from app.models import (Attempt, Block, Condition, ConditionGroup, EarlyFinishRule, Form,
                        Image, Question, QuestionChoice)
from app.services import forms as forms_service
from app.services.form_validation import publication_problems
from test_forms import create, draft, headers, users
from test_conditions import condition, survey


def complete_test_draft():
    data = draft()
    for question in data["blocks"][0]["questions"]:
        question["points"] = 3
        question["options"][0]["is_correct"] = True
    data["blocks"][0]["questions"][1]["allow_partial_scoring"] = True
    data["blocks"].append({"key": "b2", "title": "Текст", "questions": [
        {"key": "text", "text": "Ответ?", "type": "text", "points": 5, "correct_text_answers": ["Да", "Верно"]}]})
    data["grading_scale"] = [{"min_percent": 0, "grade": "2", "message": "Повторите"},
                             {"min_percent": 80, "grade": "5", "message": "Отлично"}]
    data.update(requires_login=True, max_attempts=2, time_limit_minutes=30, take_by_blocks=True,
                allow_free_navigation=True, shuffle_questions=True, shuffle_answer_options=True,
                show_correct_answers=True, show_results_by_block=True)
    return data


def save(client, user, form, data):
    response = client.put(f"/forms/{form['id']}", headers=headers(user), json=data)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("is_test", [False, True])
def test_publish_and_lock_editing(client, db_session, users, is_test):
    form = create(client, users[0], is_test)
    saved = save(client, users[0], form, complete_test_draft() if is_test else draft())
    before = datetime.now(timezone.utc).replace(tzinfo=None)
    url = f"/forms/{form['id']}"
    response = client.post(url + "/publish", headers=headers(users[0]))
    assert response.status_code == 200, response.text
    assert set(response.json()) == {"id", "is_published", "published_at", "public_code"}
    assert response.json()["is_published"] is True
    assert before <= datetime.fromisoformat(response.json()["published_at"]) <= datetime.now(timezone.utc).replace(tzinfo=None)
    assert response.json()["public_code"] == form["public_code"]
    assert client.post(url + "/publish", headers=headers(users[0])).status_code == 409
    assert client.put(url, headers=headers(users[0]), json=saved).status_code == 409
    row = next(item for item in client.get('/my/forms', headers=headers(users[0])).json() if item['id'] == form['id'])
    assert row['is_published'] and row['public_code'] == form['public_code']
    assert client.delete(url, headers=headers(users[0])).status_code == 204
    assert db_session.get(Form, form["id"]) is None


@pytest.mark.parametrize("problem", ["empty", "options", "single", "multiple", "text", "points"])
def test_each_publication_problem(client, db_session, users, problem):
    form = create(client, users[0], True)
    data = complete_test_draft()
    questions = data["blocks"][0]["questions"]
    if problem == "empty":
        data["blocks"] = [{"key": "b", "questions": []}]
    elif problem == "options":
        questions[0]["options"] = questions[0]["options"][:1]
    elif problem in {"single", "multiple"}:
        questions[0 if problem == "single" else 1]["options"][0]["is_correct"] = False
    elif problem == "text":
        data["blocks"][1]["questions"][0]["correct_text_answers"] = []
    saved = save(client, users[0], form, data)
    if problem == "points":
        question = db_session.get(Question, int(saved["blocks"][0]["questions"][0]["key"][1:]))
        question.points = None  # Старая форма, созданная до поддержки баллов.
        db_session.commit()
    response = client.post(f"/forms/{form['id']}/publish", headers=headers(users[0]))
    assert response.status_code == 422
    assert response.json()["detail"] == "Форма не прошла проверку"
    assert len(response.json()["problems"]) == 1
    stored = db_session.get(Form, form["id"])
    assert not stored.is_published and stored.published_at is None


def test_all_problems_and_global_numbers(client, db_session, users):
    form = create(client, users[0], True)
    data = complete_test_draft()
    for question in data["blocks"][0]["questions"]:
        question["options"] = []
    data["blocks"][1]["questions"][0]["correct_text_answers"] = []
    saved = save(client, users[0], form, data)
    for block in saved["blocks"]:
        for item in block["questions"]:
            db_session.get(Question, int(item["key"][1:])).points = None
    db_session.commit()
    response = client.post(f"/forms/{form['id']}/publish", headers=headers(users[0]))
    assert response.status_code == 422
    problems = response.json()["problems"]
    assert len(problems) == 8
    assert "В вопросе 3 нет правильного ответа" in problems
    assert "В вопросе 2 меньше двух вариантов" in problems


@pytest.mark.parametrize("points", [None, 0, -1, 1.5, True])
def test_points_validation_is_plain_function(points):
    data = {"is_test": True, "blocks": [{"questions": [
        {"type": "text", "points": points, "correct_text_answers": ["yes"]}]}]}
    assert len(publication_problems(data)) == 1


@pytest.mark.parametrize("action", ["publish", "copy"])
def test_action_permissions(client, users, action):
    form = create(client, users[0])
    url = f"/forms/{form['id']}/{action}"
    assert client.post(url, headers=headers(users[1])).status_code == 403
    assert client.post(url, headers=headers(users[2])).status_code == 403
    assert client.post(url).status_code == 401
    assert client.post(f"/forms/2147483647/{action}", headers=headers(users[0])).status_code == 404


@pytest.mark.parametrize("published", [False, True])
def test_copy_test_complete_and_independent(client, db_session, users, published):
    form = create(client, users[0], True)
    original = save(client, users[0], form, complete_test_draft())
    if published:
        assert client.post(f"/forms/{form['id']}/publish", headers=headers(users[0])).status_code == 200
        original = client.get(f"/forms/{form['id']}", headers=headers(users[0])).json()
    db_session.add(Attempt(form_id=form["id"], user_id=users[2], attempt_key="copy-test", started_at=datetime.now(timezone.utc).replace(tzinfo=None)))
    db_session.commit()
    response = client.post(f"/forms/{form['id']}/copy", headers=headers(users[0]))
    assert response.status_code == 201, response.text
    copied = response.json()
    assert set(copied) == {"id", "title", "is_published", "public_code"}
    assert copied["title"] == original["title"] + " (копия)"
    assert copied["public_code"] != original["public_code"]
    assert not copied["is_published"]
    stored = db_session.get(Form, copied["id"])
    assert stored.published_at is None and stored.author_id == users[0]
    assert not list(db_session.scalars(select(Attempt).where(Attempt.form_id == copied["id"])))
    result = client.get(f"/forms/{copied['id']}", headers=headers(users[0])).json()
    for field in complete_test_draft().keys() - {"title", "blocks"}:
        assert result[field] == original[field]
    for old_block, new_block in zip(original["blocks"], result["blocks"]):
        assert old_block["key"] != new_block["key"]
        assert old_block["title"] == new_block["title"]
        for old, new in zip(old_block["questions"], new_block["questions"]):
            assert old["key"] != new["key"]
            assert {k: v for k, v in old.items() if k not in {"key", "options"}} == {k: v for k, v in new.items() if k not in {"key", "options"}}
            assert [(x["text"], x["is_correct"]) for x in old["options"]] == [(x["text"], x["is_correct"]) for x in new["options"]]
    result["blocks"][0]["questions"][0]["text"] = "Изменена только копия"
    save(client, users[0], copied, result)
    assert client.get(f"/forms/{form['id']}", headers=headers(users[0])).json() == original


def test_copy_survey_remaps_links_positions_and_image(client, db_session, users):
    form = create(client, users[0])
    data = survey()
    data["blocks"][1]["condition"] = condition(operator="chosen", option="choice-1")
    data["blocks"][0]["questions"][1]["condition"] = condition(operator="not_chosen", option="choice-2")
    data["blocks"][0]["questions"][0]["finish_rules"] = [
        {"key": "r1", "message": "До свидания", "condition": condition(operator="chosen", option="choice-2")},
        {"key": "r2", "condition": condition()},
    ]
    original = save(client, users[0], form, data)
    image = Image(owner_id=users[0], file_name=f"copy-{form['id']}.png", content_type="image/png", size=1)
    db_session.add(image)
    db_session.flush()
    source_question = db_session.get(Question, int(original["blocks"][0]["questions"][0]["key"][1:]))
    source_question.image_id = image.id
    source_question.position = 7
    db_session.commit()
    response = client.post(f"/forms/{form['id']}/copy", headers=headers(users[0]))
    assert response.status_code == 201, response.text
    copied_id = response.json()["id"]
    new_blocks = db_session.scalars(select(Block).where(Block.form_id == copied_id)).all()
    new_questions = db_session.scalars(select(Question).where(Question.block_id.in_([b.id for b in new_blocks]))).all()
    qids = {q.id for q in new_questions}
    new_choices = db_session.scalars(select(QuestionChoice).where(QuestionChoice.question_id.in_(qids))).all()
    oids = {o.id for o in new_choices}
    rules = db_session.scalars(select(EarlyFinishRule).where(EarlyFinishRule.question_id.in_(qids)).order_by(EarlyFinishRule.position)).all()
    assert [r.position for r in rules] == [1, 2]
    assert [r.message for r in rules] == ["До свидания", None]
    groups = db_session.scalars(select(ConditionGroup).where(
        (ConditionGroup.block_id.in_([b.id for b in new_blocks])) |
        (ConditionGroup.question_id.in_(qids)) | (ConditionGroup.early_finish_rule_id.in_([r.id for r in rules])))).all()
    assert len(groups) == 4
    conditions = db_session.scalars(select(Condition).where(Condition.group_id.in_([g.id for g in groups]))).all()
    assert len(conditions) == 4
    assert all(c.question_id in qids and (c.choice_id is None or c.choice_id in oids) for c in conditions)
    assert len([g for g in groups if g.early_finish_rule_id in {r.id for r in rules}]) == 2
    copied_question = next(q for q in new_questions if q.text == source_question.text)
    assert copied_question.image_id == image.id and copied_question.position == 7
    assert copied_question.is_answer_required == source_question.is_answer_required
    assert db_session.get(Question, source_question.id).image_id == image.id


def test_copy_long_title_and_collision(client, users, monkeypatch):
    form = create(client, users[0], title="я" * 255)
    codes = iter([form["public_code"], "copycode"])
    monkeypatch.setattr(forms_service, "generate_public_code", lambda: next(codes))
    response = client.post(f"/forms/{form['id']}/copy", headers=headers(users[0]))
    assert response.status_code == 201, response.text
    assert len(response.json()["title"]) == 255
    assert response.json()["title"].endswith(" (копия)")
    assert response.json()["public_code"] == "copycode"


def test_copy_failure_rolls_back_new_form(client, db_session, users):
    form = create(client, users[0])
    original = save(client, users[0], form, draft())
    before = list(db_session.scalars(select(Form.id).where(Form.author_id == users[0])))
    connection = db_session.connection()
    def fail(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO question_choices "):
            raise RuntimeError("Проверка отката копии")
    event.listen(connection, "before_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="Проверка отката"):
            client.post(f"/forms/{form['id']}/copy", headers=headers(users[0]))
    finally:
        event.remove(connection, "before_cursor_execute", fail)
    assert list(db_session.scalars(select(Form.id).where(Form.author_id == users[0]))) == before
    assert client.get(f"/forms/{form['id']}", headers=headers(users[0])).json() == original
