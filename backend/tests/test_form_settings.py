import pytest
from sqlalchemy import event, select

from app.models import CorrectTextAnswer, GradingScale, Question, QuestionType
from app.services.form_validation import normalize_text_answers
from test_forms import create, draft, headers, users


def quiz_draft():
    data = draft()
    questions = data["blocks"][0]["questions"]
    questions[0].update(points=2, allow_partial_scoring=True)
    questions[0]["options"][0]["is_correct"] = True
    questions[1].update(points=3, allow_partial_scoring=True)
    for option in questions[1]["options"]:
        option["is_correct"] = True
    questions.append({"key": "text", "text": "Столица?", "type": "text", "points": 1,
                      "correct_text_answers": [" Москва ", "москва", "  ", "Нижний   Новгород", "нижний новгород"]})
    data["grading_scale"] = [{"min_percent": 70, "grade": " 5 ", "message": "Отлично"},
                             {"min_percent": 0, "grade": "2", "message": None}]
    data.update(requires_login=True, max_attempts=1000, time_limit_minutes=1440,
                take_by_blocks=True, allow_free_navigation=True, shuffle_questions=True,
                shuffle_answer_options=True, show_correct_answers=True, show_results_by_block=True)
    return data



def save(client, users, data=None):
    form = create(client, users[0], True)
    url = f"/forms/{form['id']}"
    response = client.put(url, json=data if data is not None else quiz_draft(), headers=headers(users[0]))
    assert response.status_code == 200, response.text
    return form, url, response.json()


def test_test_round_trip(client, db_session, users):
    form, url, saved = save(client, users)
    assert client.get(url, headers=headers(users[0])).json() == saved
    q1, q2, q3 = saved["blocks"][0]["questions"]
    assert [q["points"] for q in [q1, q2, q3]] == [2, 3, 1]
    assert not q1["allow_partial_scoring"] and q2["allow_partial_scoring"]
    assert [o["is_correct"] for o in q1["options"]] == [True, False]
    assert q3["correct_text_answers"] == ["Москва", "Нижний   Новгород"]
    assert saved["grading_scale"] == [{"min_percent": 0, "grade": "2", "message": None},
                                      {"min_percent": 70, "grade": "5", "message": "Отлично"}]
    stored = db_session.get(Question, int(q2["key"][1:]))
    assert stored.points == 3 and stored.allow_partial_scoring
    for key in ["requires_login", "max_attempts", "time_limit_minutes", "take_by_blocks",
                "allow_free_navigation", "shuffle_questions", "shuffle_answer_options",
                "show_correct_answers", "show_results_by_block", "completion_message"]:
        assert saved[key] == quiz_draft()[key]


@pytest.mark.parametrize("points", [0, 1001, None, 1.5, True, "2", "missing"])
def test_invalid_points(client, users, points):
    form = create(client, users[0], True)
    data = quiz_draft()
    question = data["blocks"][0]["questions"][0]
    if points == "missing":
        question.pop("points")
    else:
        question["points"] = points
    response = client.put(f"/forms/{form['id']}", json=data, headers=headers(users[0]))
    assert response.status_code == 422
    assert "Вопрос 1" in response.json()["detail"]
    assert "1 до 1000" in response.json()["detail"]


def test_single_two_correct(client, users):
    form = create(client, users[0], True)
    data = quiz_draft()
    data["blocks"][0]["questions"][0]["options"][1]["is_correct"] = True
    response = client.put(f"/forms/{form['id']}", json=data, headers=headers(users[0]))
    assert response.status_code == 422
    assert "Вопрос 1" in response.json()["detail"]


@pytest.mark.parametrize("scale", [
    [{"min_percent": 50, "grade": "3"}],
    [{"min_percent": 0, "grade": "2"}, {"min_percent": 0, "grade": "3"}],
    [{"min_percent": -1, "grade": "2"}], [{"min_percent": 101, "grade": "2"}],
    [{"min_percent": 0.5, "grade": "2"}], [{"min_percent": True, "grade": "2"}],
    [{"min_percent": 0, "grade": "  "}], [{"min_percent": 0, "grade": "я" * 21}],
    [{"min_percent": 0, "grade": "2", "message": "я" * 1001}],
])
def test_invalid_scale_preserves_form(client, users, scale):
    _, url, before = save(client, users)
    data = quiz_draft()
    data["grading_scale"] = scale
    response = client.put(url, json=data, headers=headers(users[0]))
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)
    assert client.get(url, headers=headers(users[0])).json() == before


def test_empty_scale_and_incomplete_correct_answers(client, users):
    data = quiz_draft()
    data["grading_scale"] = []
    for q in data["blocks"][0]["questions"]:
        q["correct_text_answers"] = []
        for option in q.get("options", []):
            option.pop("is_correct", None)
    _, _, saved = save(client, users, data)
    assert saved["grading_scale"] == []
    assert saved["blocks"][0]["questions"][2]["correct_text_answers"] == []


@pytest.mark.parametrize("field,value", [("points", 1), ("points", 0), ("allow_partial_scoring", True),
                                         ("correct_text_answers", ["Да"]), ("is_correct", True),
                                         ("grading_scale", [{"min_percent": 0, "grade": "2"}])])
def test_survey_rejects_test_fields(client, users, field, value):
    form = create(client, users[0])
    data = draft()
    question = data["blocks"][0]["questions"][0]
    target = data if field == "grading_scale" else question["options"][0] if field == "is_correct" else question
    target[field] = value
    response = client.put(f"/forms/{form['id']}", json=data, headers=headers(users[0]))
    assert response.status_code == 422
    assert response.json()["detail"] == "Это поле есть только у тестов"


def test_survey_empty_test_fields_not_in_response(client, users):
    form = create(client, users[0])
    data = draft()
    data["grading_scale"] = None
    for q in data["blocks"][0]["questions"]:
        q.update(points=None, allow_partial_scoring=False, correct_text_answers=[])
        for option in q["options"]:
            option["is_correct"] = None
    response = client.put(f"/forms/{form['id']}", json=data, headers=headers(users[0]))
    assert response.status_code == 200
    saved = response.json()
    assert "grading_scale" not in saved
    for q in saved["blocks"][0]["questions"]:
        assert not {"points", "allow_partial_scoring", "correct_text_answers"} & q.keys()
        assert all("is_correct" not in option for option in q["options"])


@pytest.mark.parametrize("field,value", [("time_limit_minutes", 0), ("time_limit_minutes", 1441),
                                         ("max_attempts", 0), ("max_attempts", 1001)])
def test_numeric_settings_limits(client, users, field, value):
    form = create(client, users[0], True)
    data = quiz_draft()
    data[field] = value
    assert client.put(f"/forms/{form['id']}", json=data, headers=headers(users[0])).status_code == 422


@pytest.mark.parametrize("kind", ["wrong-type", "too-long"])
def test_invalid_text_answers(client, users, kind):
    form = create(client, users[0], True)
    data = quiz_draft()
    index = 0 if kind == "wrong-type" else 2
    data["blocks"][0]["questions"][index]["correct_text_answers"] = ["ответ" if index == 0 else "я" * 256]
    response = client.put(f"/forms/{form['id']}", json=data, headers=headers(users[0]))
    assert response.status_code == 422
    assert f"Вопрос {index + 1}" in response.json()["detail"]


def test_normalize_text_answers():
    assert normalize_text_answers([" Москва ", "МОСКВА", "", "  ", "А  Б", "а\tб", "я" * 255], 1) == ["Москва", "А  Б", "я" * 255]


def test_replace_scale_and_answers(client, db_session, users):
    form, url, before = save(client, users)
    old_question = int(before["blocks"][0]["questions"][2]["key"][1:])
    old_answers = db_session.scalars(select(CorrectTextAnswer.id).where(CorrectTextAnswer.question_id == old_question)).all()
    old_grades = db_session.scalars(select(GradingScale.id).where(GradingScale.form_id == form["id"])).all()
    data = quiz_draft()
    data["grading_scale"] = [{"min_percent": 0, "grade": "Зачёт"}]
    data["blocks"][0]["questions"][2]["correct_text_answers"] = ["Другой ответ"]
    response = client.put(url, json=data, headers=headers(users[0]))
    assert response.status_code == 200
    assert db_session.scalars(select(CorrectTextAnswer.id).where(CorrectTextAnswer.id.in_(old_answers))).all() == []
    assert db_session.scalars(select(GradingScale.id).where(GradingScale.id.in_(old_grades))).all() == []
    assert response.json()["blocks"][0]["questions"][2]["correct_text_answers"] == ["Другой ответ"]
    assert len(response.json()["grading_scale"]) == 1


def test_rollback_scale_and_answers(client, db_session, users):
    _, url, before = save(client, users)
    connection = db_session.connection()
    def fail(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO grading_scale"):
            raise RuntimeError("Откат шкалы")
    event.listen(connection, "before_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="Откат шкалы"):
            client.put(url, json=quiz_draft(), headers=headers(users[0]))
    finally:
        event.remove(connection, "before_cursor_execute", fail)
    assert client.get(url, headers=headers(users[0])).json() == before


def test_legacy_test_points_null(client, db_session, users):
    form = create(client, users[0], True)
    block_id = int(form["blocks"][0]["key"][1:])
    type_id = db_session.scalar(select(QuestionType.id).where(QuestionType.type == "single"))
    db_session.add(Question(block_id=block_id, type_id=type_id, text="Старый вопрос", position=1))
    db_session.commit()
    response = client.get(f"/forms/{form['id']}", headers=headers(users[0]))
    assert response.status_code == 200
    assert response.json()["blocks"][0]["questions"][0]["points"] is None
