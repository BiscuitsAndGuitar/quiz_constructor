from copy import deepcopy
from datetime import datetime
import re
from uuid import uuid4

import pytest
from sqlalchemy import event, select

from app.models import (
    Attempt, AttemptAnswer, AttemptAnswerChoice, Block, Condition, ConditionGroup,
    ConditionOperator, CorrectTextAnswer, EarlyFinishRule, Form, GradingScale,
    Image, LibraryBlock, LibraryBlockTag, Question, QuestionChoice, QuestionType, Tag, User,
)
from app.services import forms as forms_service
from app.services.security import create_access_token


@pytest.fixture
def users(db_session):
    result = []
    for is_author in [True, True, False]:
        user = User(email=f"stage3-{uuid4().hex}@example.com", password_hash="unused-in-forms-tests",
                    name="Проверка форм", is_author=is_author)
        db_session.add(user)
        db_session.flush()
        result.append(user.id)
    db_session.commit()
    return result


def headers(user_id):
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


def create(client, user_id, is_test=False, title="Новая форма"):
    response = client.post("/forms", headers=headers(user_id), json={"title": title, "is_test": is_test})
    assert response.status_code == 201, response.text
    return response.json()


def draft():
    return {
        "title": "Мой опрос", "description": "Описание", "completion_message": "Спасибо!",
        "blocks": [{"key": "block", "title": None, "questions": [
            {"key": "question-1", "text": "Первый вопрос", "type": "single", "is_answer_required": True,
             "options": [{"key": "choice-1", "text": "Да"}, {"key": "choice-2", "text": "Нет"}]},
            {"key": "question-2", "text": "Второй вопрос", "type": "multiple",
             "options": [{"key": "choice-3", "text": "А"}, {"key": "choice-4", "text": "Б"}]},
        ]}],
    }


@pytest.mark.parametrize("is_test", [False, True])
def test_create_form(client, db_session, users, is_test):
    data = create(client, users[0], is_test, "  Название  ")
    assert set(data) == {"id", "is_test", "title", "is_published", "requires_login", "public_code", "blocks"}
    assert data["title"] == "Название"
    assert data["is_test"] is is_test
    assert data["is_published"] is False
    assert data["requires_login"] is False
    assert re.fullmatch("[a-z0-9]{8}", data["public_code"])
    assert len(data["blocks"]) == 1
    block = data["blocks"][0]
    assert re.fullmatch(r"b\d+", block["key"])
    assert block["title"] is None and block["questions"] == []
    saved_block = db_session.get(Block, int(block["key"][1:]))
    assert saved_block.form_id == data["id"] and saved_block.position == 1
    other = create(client, users[0], is_test)
    assert other["public_code"] != data["public_code"]


def test_public_code_collision(client, users, monkeypatch):
    first = create(client, users[0])
    codes = iter([first["public_code"], "a1b2c3d4"])
    monkeypatch.setattr(forms_service, "generate_public_code", lambda: next(codes))
    second = create(client, users[0])
    assert second["public_code"] == "a1b2c3d4"
    assert len(second["blocks"]) == 1


@pytest.mark.parametrize("title", ["", "  ", "я" * 256])
def test_invalid_title(client, users, title):
    response = client.post("/forms", headers=headers(users[0]), json={"title": title, "is_test": False})
    assert response.status_code == 422
    assert response.json() == {"detail": "Название должно содержать от 1 до 255 символов"}


def test_list_only_own_newest_first(client, db_session, users):
    first = create(client, users[0])
    second = create(client, users[0], True)
    create(client, users[1])
    db_session.add(Attempt(form_id=first["id"], user_id=users[2], attempt_key="test", started_at=datetime(2026, 1, 1)))
    db_session.commit()
    response = client.get("/my/forms", headers=headers(users[0]))
    assert response.status_code == 200
    data = response.json()
    assert [item["id"] for item in data] == [second["id"], first["id"]]
    assert set(data[0]) == {"id", "is_test", "title", "is_published", "requires_login", "public_code",
                            "attempts_count", "created_at", "published_at"}
    assert [item["attempts_count"] for item in data] == [0, 1]
    assert data[0]["created_at"] and data[0]["published_at"] is None


@pytest.mark.parametrize("method,path,body", [
    ("GET", "/my/forms", None), ("POST", "/forms", {"title": "Новая", "is_test": False}),
    ("GET", "/forms/{id}", None), ("PUT", "/forms/{id}", draft()), ("DELETE", "/forms/{id}", None),
])
def test_author_required(client, users, method, path, body):
    form = create(client, users[0])
    path = path.format(id=form["id"])
    assert client.request(method, path, json=body).status_code == 401
    assert client.request(method, path, json=body, headers=headers(users[2])).status_code == 403


@pytest.mark.parametrize("method", ["GET", "PUT", "DELETE"])
def test_other_author_forbidden_and_missing_form(client, users, method):
    form = create(client, users[0])
    body = draft() if method == "PUT" else None
    assert client.request(method, f"/forms/{form['id']}", json=body, headers=headers(users[1])).status_code == 403
    assert client.request(method, "/forms/2147483648", json=body, headers=headers(users[0])).status_code == 404
    assert client.get(f"/forms/{form['id']}", headers=headers(users[0])).status_code == 200


def test_save_read_order_and_replace(client, db_session, users):
    form = create(client, users[0])
    url = f"/forms/{form['id']}"
    data = draft()
    data["blocks"].append({"key": "second-block", "title": "Второй", "questions": [
        {"key": "text-question", "text": "Комментарий", "type": "text"},
    ]})
    response = client.put(url, json=data, headers=headers(users[0]))
    assert response.status_code == 200, response.text
    saved = response.json()
    assert client.get(url, headers=headers(users[0])).json() == saved
    assert saved["public_code"] == form["public_code"]
    assert saved["completion_message"] == "Спасибо!"
    old_block_ids, old_question_ids, old_choice_ids = [], [], []
    for bp, block in enumerate(saved["blocks"], 1):
        assert re.fullmatch(r"b\d+", block["key"])
        block_id = int(block["key"][1:])
        old_block_ids.append(block_id)
        assert db_session.get(Block, block_id).position == bp
        for qp, question in enumerate(block["questions"], 1):
            assert re.fullmatch(r"q\d+", question["key"])
            question_id = int(question["key"][1:])
            old_question_ids.append(question_id)
            assert db_session.get(Question, question_id).position == qp
            assert question["text"] == data["blocks"][bp-1]["questions"][qp-1]["text"]
            for op, choice in enumerate(question["options"], 1):
                assert re.fullmatch(r"o\d+", choice["key"])
                choice_id = int(choice["key"][1:])
                old_choice_ids.append(choice_id)
                assert db_session.get(QuestionChoice, choice_id).position == op
                assert choice["text"] == data["blocks"][bp-1]["questions"][qp-1]["options"][op-1]["text"]
    replacement = {"title": "Другой набор", "blocks": [{"key": "new", "questions": [
        {"key": "new-question", "text": "", "type": "text"},
    ]}]}
    assert client.put(url, json=replacement, headers=headers(users[0])).status_code == 200
    for model, ids in [(Block, old_block_ids), (Question, old_question_ids), (QuestionChoice, old_choice_ids)]:
        assert db_session.scalars(select(model.id).where(model.id.in_(ids))).all() == []
    assert client.get(url, headers=headers(users[0])).json()["blocks"][0]["questions"][0]["text"] == ""


def test_draft_accepts_incomplete_content_and_ignores_future_fields(client, db_session, users):
    form = create(client, users[0], True)
    data = draft()
    data.update({"is_test": False, "public_code": "changed", "is_published": True,
                 "grading_scale": [{"min_percent": 0, "grade": "5"}]})
    question = data["blocks"][0]["questions"][0]
    data["blocks"][0]["questions"][1]["points"] = 1
    # Условия и правила уже поддерживаются и больше не являются игнорируемыми полями.
    question.update({"text": "", "points": 10, "correct_text_answers": [],
                     "image_id": None, "allow_partial_scoring": True})
    question["options"] = [{"key": "empty", "text": "", "is_correct": True}]
    response = client.put(f"/forms/{form['id']}", json=data, headers=headers(users[0]))
    assert response.status_code == 200
    saved = response.json()
    assert saved["is_test"] is True and saved["is_published"] is False
    assert saved["public_code"] == form["public_code"]
    q = saved["blocks"][0]["questions"][0]
    assert set(q) == {"key", "text", "type", "is_answer_required", "options", "points", "allow_partial_scoring", "image"}
    assert q["image"] is None
    assert q["is_answer_required"] is False
    assert set(q["options"][0]) == {"key", "text", "is_correct"}
    stored = db_session.get(Question, int(q["key"][1:]))
    assert stored.points == 10 and stored.image_id is None and not stored.allow_partial_scoring
    assert db_session.get(QuestionChoice, int(q["options"][0]["key"][1:])).is_correct


def test_preserve_all_settings(client, users):
    form = create(client, users[0], True)
    url = f"/forms/{form['id']}"
    data = draft()
    for question in data["blocks"][0]["questions"]:
        question["points"] = 1
    data.update({"requires_login": True, "max_attempts": 2, "time_limit_minutes": 30,
                 "take_by_blocks": True, "allow_free_navigation": True, "shuffle_questions": True,
                 "shuffle_answer_options": True, "show_correct_answers": True, "show_results_by_block": True})
    saved = client.put(url, json=data, headers=headers(users[0])).json()
    saved["title"] = "Изменённое название"
    again = client.put(url, json=saved, headers=headers(users[0])).json()
    for key in data.keys() - {"blocks", "title"}:
        assert again[key] == data[key]


@pytest.mark.parametrize("changes", [
    {"max_attempts": 2}, {"completion_message": "я" * 1001}, {"blocks": []},
    {"shuffle_questions": True}, {"time_limit_minutes": 1},
    {"show_correct_answers": True}, {"show_results_by_block": True},
])
def test_invalid_save_keeps_form(client, users, changes):
    form = create(client, users[0])
    url = f"/forms/{form['id']}"
    before = client.put(url, json=draft(), headers=headers(users[0])).json()
    invalid = draft()
    invalid.update(changes)
    response = client.put(url, json=invalid, headers=headers(users[0]))
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)
    assert client.get(url, headers=headers(users[0])).json() == before


@pytest.mark.parametrize("kind", ["duplicate", "info", "text-options", "long-option"])
def test_invalid_question(client, users, kind):
    form = create(client, users[0])
    data = draft()
    q = data["blocks"][0]["questions"][0]
    if kind == "duplicate":
        q["options"][0]["key"] = q["key"]
    elif kind == "info":
        q["type"] = "info"
    elif kind == "text-options":
        q["type"] = "text"
    else:
        q["options"][0]["text"] = "а" * 501
    response = client.put(f"/forms/{form['id']}", json=data, headers=headers(users[0]))
    assert response.status_code == 422
    if kind == "info":
        assert 'у «Текста без вопроса» не должно быть' in response.json()["detail"]


def test_published_read_only(client, db_session, users):
    form = create(client, users[0])
    url = f"/forms/{form['id']}"
    stored = db_session.get(Form, form["id"])
    stored.is_published = True
    db_session.commit()
    before = client.get(url, headers=headers(users[0])).json()
    response = client.put(url, json=draft(), headers=headers(users[0]))
    assert response.status_code == 409
    assert response.json() == {"detail": "Опубликованную форму нельзя редактировать"}
    assert client.get(url, headers=headers(users[0])).json() == before


def test_rollback_after_old_content_was_deleted(client, db_session, users):
    form = create(client, users[0])
    url = f"/forms/{form['id']}"
    before = client.put(url, json=draft(), headers=headers(users[0])).json()
    changed = deepcopy(before)
    changed["title"] = "Не должно сохраниться"
    connection = db_session.connection()

    def fail_insert(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO questions"):
            raise RuntimeError("Проверка отката после удаления")

    event.listen(connection, "before_cursor_execute", fail_insert)
    try:
        with pytest.raises(RuntimeError, match="Проверка отката"):
            client.put(url, json=changed, headers=headers(users[0]))
    finally:
        event.remove(connection, "before_cursor_execute", fail_insert)
    assert client.get(url, headers=headers(users[0])).json() == before


def test_delete_cascades_and_preserves_library(client, db_session, users):
    form = create(client, users[0])
    url = f"/forms/{form['id']}"
    saved = client.put(url, json=draft(), headers=headers(users[0])).json()
    block_id = int(saved["blocks"][0]["key"][1:])
    question_id = int(saved["blocks"][0]["questions"][0]["key"][1:])
    choice_id = int(saved["blocks"][0]["questions"][0]["options"][0]["key"][1:])

    def add(row):
        db_session.add(row)
        db_session.flush()
        return row

    image = add(Image(owner_id=users[0], file_name=f"{uuid4().hex}.png", content_type="image/png", size=1))
    db_session.get(Question, question_id).image_id = image.id
    correct = add(CorrectTextAnswer(question_id=question_id, answer_text="Да"))
    grade = add(GradingScale(form_id=form["id"], min_percent=0, grade="5"))
    rule = add(EarlyFinishRule(question_id=question_id, position=1))
    groups = [add(ConditionGroup(block_id=block_id)), add(ConditionGroup(question_id=question_id)),
              add(ConditionGroup(early_finish_rule_id=rule.id))]
    groups.append(add(ConditionGroup(parent_group_id=groups[-1].id)))
    operator_id = db_session.scalar(select(ConditionOperator.id).where(ConditionOperator.operator == "chosen"))
    conditions = [add(Condition(group_id=g.id, question_id=question_id, operator_id=operator_id,
                                choice_id=choice_id)) for g in groups]
    attempt = add(Attempt(form_id=form["id"], user_id=users[2], attempt_key="test-cascade",
                          started_at=datetime(2026, 1, 1), grading_scale_id=grade.id, early_finish_rule_id=rule.id))
    answer = add(AttemptAnswer(attempt_id=attempt.id, question_id=question_id))
    answer_choice = add(AttemptAnswerChoice(attempt_answer_id=answer.id, choice_id=choice_id))
    library = add(LibraryBlock(owner_id=users[0], is_test=False))
    sample = add(Block(library_block_id=library.id, title="Образец", position=1))
    type_id = db_session.scalar(select(QuestionType.id).where(QuestionType.type == "single"))
    sample_question = add(Question(block_id=sample.id, type_id=type_id, text="Копия", position=1, image_id=image.id))
    sample_choice = add(QuestionChoice(question_id=sample_question.id, text="Да", position=1))
    tag = add(Tag(name=uuid4().hex[:30]))
    add(LibraryBlockTag(library_block_id=library.id, tag_id=tag.id))
    deleted = [(Form, form["id"]), (Block, block_id), (Question, question_id), (QuestionChoice, choice_id),
               (CorrectTextAnswer, correct.id), (GradingScale, grade.id), (EarlyFinishRule, rule.id),
               (Attempt, attempt.id), (AttemptAnswer, answer.id), (AttemptAnswerChoice, answer_choice.id)]
    deleted += [(ConditionGroup, group.id) for group in groups] + [(Condition, condition.id) for condition in conditions]
    preserved = [(LibraryBlock, library.id), (Block, sample.id), (Question, sample_question.id),
                 (QuestionChoice, sample_choice.id), (Image, image.id), (Tag, tag.id)]
    library_id, tag_id = library.id, tag.id
    db_session.commit()
    response = client.delete(url, headers=headers(users[0]))
    assert response.status_code == 204 and response.content == b""
    # Проверяем SELECT, а не кэш ORM: дочерние строки удалял PostgreSQL.
    for model, row_id in deleted:
        assert db_session.scalar(select(model.id).where(model.id == row_id)) is None
    for model, row_id in preserved:
        assert db_session.scalar(select(model.id).where(model.id == row_id)) == row_id
    assert db_session.scalar(select(LibraryBlockTag.tag_id).where(
        LibraryBlockTag.library_block_id == library_id, LibraryBlockTag.tag_id == tag_id)) == tag_id
    assert client.get(url, headers=headers(users[0])).status_code == 404
