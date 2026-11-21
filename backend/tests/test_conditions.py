import pytest
from sqlalchemy import event, select

from app.models import Condition, ConditionGroup, EarlyFinishRule
from app.services.conditions import validate_conditions
from app.services.form_validation import InvalidFormError
from test_forms import create, draft, headers, users


OPERATORS = {"chosen", "not_chosen", "equals", "contains", "answered", "not_answered"}


def condition(question="question-1", operator="answered", **value):
    return {"match_all": True, "items": [{"question": question, "operator": operator, **value}]}


def survey():
    data = draft()
    questions = data["blocks"][0]["questions"]
    questions.append({"key": "text", "text": "Город", "type": "text", "options": []})
    data["blocks"].append({"key": "second", "title": "Второй", "questions": [
        {"key": "last", "text": "Последний", "type": "single", "options": []},
    ]})
    return data


def put(client, users, form, data):
    return client.put(f"/forms/{form['id']}", headers=headers(users[0]), json=data)


def test_roundtrip_all_conditions_and_replace(client, db_session, users):
    form = create(client, users[0])
    data = survey()
    first, second = data["blocks"]
    first["questions"][1]["condition"] = condition(operator="chosen", option="choice-1")
    second["condition"] = condition("text", "contains", text_answer="Москва")
    second["condition"]["match_all"] = False
    last = second["questions"][0]
    last["condition"] = {"match_all": True, "items": [
        {"question": "question-1", "operator": "not_chosen", "option": "choice-2"},
        {"question": "text", "operator": "equals", "text_answer": "Москва"},
        {"question": "question-2", "operator": "answered"},
        {"question": "text", "operator": "not_answered"},
    ]}
    last["finish_rules"] = [
        {"key": "r-first", "message": "Первое", "condition": condition("last")},
        {"key": "r-second", "condition": condition("text", "not_answered")},
    ]
    response = put(client, users, form, data)
    assert response.status_code == 200, response.text
    saved = response.json()
    assert client.get(f"/forms/{form['id']}", headers=headers(users[0])).json() == saved
    b1, b2 = saved["blocks"]
    q1, q2, text = b1["questions"]
    last = b2["questions"][0]
    assert q2["condition"] == condition(q1["key"], "chosen", option=q1["options"][0]["key"])
    assert b2["condition"]["match_all"] is False
    assert b2["condition"]["items"][0]["question"] == text["key"]
    assert [item["operator"] for item in last["condition"]["items"]] == ["not_chosen", "equals", "answered", "not_answered"]
    rules = last["finish_rules"]
    assert rules[0]["condition"] == condition(last["key"])
    assert rules[1]["message"] is None
    rule_ids = [int(rule["key"][1:]) for rule in rules]
    assert [db_session.get(EarlyFinishRule, rule_id).position for rule_id in rule_ids] == [1, 2]
    old_group_ids = list(db_session.scalars(select(ConditionGroup.id).where(
        ConditionGroup.early_finish_rule_id.in_(rule_ids))))
    old_condition_ids = list(db_session.scalars(select(Condition.id).where(Condition.group_id.in_(old_group_ids))))
    # GET можно отправить назад: все ссылки уже используют новые ключи.
    rules.reverse()
    response = put(client, users, form, saved)
    assert response.status_code == 200, response.text
    assert [rule["message"] for rule in response.json()["blocks"][1]["questions"][0]["finish_rules"]] == [None, "Первое"]
    assert not list(db_session.scalars(select(EarlyFinishRule.id).where(EarlyFinishRule.id.in_(rule_ids))))
    assert not list(db_session.scalars(select(ConditionGroup.id).where(ConditionGroup.id.in_(old_group_ids))))
    assert not list(db_session.scalars(select(Condition.id).where(Condition.id.in_(old_condition_ids))))
    response = put(client, users, form, survey())
    assert response.status_code == 200
    assert response.json()["blocks"][1]["condition"] is None
    assert response.json()["blocks"][1]["questions"][0]["finish_rules"] == []


@pytest.mark.parametrize("kind", ["later", "same-block", "foreign-option", "empty", "operator", "wrong-type",
                                  "missing-text", "long-text", "extra-value", "rule-later", "long-message", "missing-condition"])
def test_invalid_conditions_rollback(client, users, kind):
    form = create(client, users[0])
    data = survey()
    before = put(client, users, form, data).json()
    first, second = data["blocks"]
    q1, q2, text = first["questions"]
    if kind == "later":
        q1["condition"] = condition("question-2")
    elif kind == "same-block":
        first["condition"] = condition()
    elif kind == "foreign-option":
        q2["condition"] = condition(operator="chosen", option="choice-3")
    elif kind == "empty":
        q2["condition"] = {"match_all": True, "items": []}
    elif kind == "operator":
        q2["condition"] = condition(operator="unknown")
    elif kind == "wrong-type":
        q2["condition"] = condition(operator="equals", text_answer="Да")
    elif kind in {"missing-text", "long-text"}:
        second["condition"] = condition("text", "contains", text_answer=" " if kind == "missing-text" else "x" * 501)
    elif kind == "extra-value":
        q2["condition"] = condition(option="choice-1")
    else:
        q1["finish_rules"] = [{"key": "rule", "condition": condition(), "message": None}]
        rule = q1["finish_rules"][0]
        if kind == "rule-later":
            rule["condition"] = condition("question-2")
        elif kind == "long-message":
            rule["message"] = "я" * 1001
        else:
            del rule["condition"]
    data["title"] = "Не должно сохраниться"
    response = put(client, users, form, data)
    assert response.status_code == 422, response.text
    assert client.get(f"/forms/{form['id']}", headers=headers(users[0])).json() == before


@pytest.mark.parametrize("place", ["block", "question", "rule"])
def test_test_forms_reject_conditions(client, users, place):
    form = create(client, users[0], True)
    data = draft()
    for question in data["blocks"][0]["questions"]:
        question["points"] = 1
    block = data["blocks"][0]
    if place == "block":
        block["condition"] = condition()
    elif place == "question":
        block["questions"][1]["condition"] = condition()
    else:
        block["questions"][0]["finish_rules"] = [{"key": "rule", "condition": condition()}]
    response = put(client, users, form, data)
    assert response.status_code == 422
    assert "только у опросов" in response.json()["detail"]


@pytest.mark.parametrize("own_rule", [False, True])
def test_info_restrictions_directly(own_rule):
    blocks = survey()["blocks"]
    first = blocks[0]["questions"][0]
    first["type"] = "info"
    if own_rule:
        first["finish_rules"] = [{"key": "r", "condition": condition()}]
    else:
        blocks[0]["questions"][1]["condition"] = condition()
    with pytest.raises(InvalidFormError, match="Текст.*вопроса"):
        validate_conditions(blocks, False, OPERATORS)


def test_self_reference_only_for_rule_and_operator_dictionary():
    blocks = survey()["blocks"]
    first = blocks[0]["questions"][0]
    first["finish_rules"] = [{"key": "r", "condition": condition(), "message": "x" * 1000}]
    validate_conditions(blocks, False, OPERATORS)
    with pytest.raises(InvalidFormError, match="неизвестный оператор"):
        validate_conditions(blocks, False, OPERATORS - {"answered"})
    first["condition"] = condition()
    with pytest.raises(InvalidFormError, match="раньше"):
        validate_conditions(blocks, False, OPERATORS)


@pytest.mark.parametrize("place", ["block", "question", "rules"])
def test_even_empty_survey_fields_not_accepted_in_test(client, users, place):
    form = create(client, users[0], True)
    data = {"title": "Тест", "blocks": [{"key": "b", "questions": [
        {"key": "q", "text": "Вопрос", "type": "text", "points": 1}]}]}
    block = data["blocks"][0]
    if place == "block":
        block["condition"] = None
    elif place == "question":
        block["questions"][0]["condition"] = None
    else:
        block["questions"][0]["finish_rules"] = []
    assert put(client, users, form, data).status_code == 422


def test_storage_failure_restores_conditions(client, db_session, users):
    form = create(client, users[0])
    data = survey()
    data["blocks"][1]["condition"] = condition()
    data["blocks"][0]["questions"][0]["finish_rules"] = [{"key": "rule", "condition": condition()}]
    before = put(client, users, form, data).json()
    connection = db_session.connection()

    def fail_insert(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO conditions "):
            raise RuntimeError("Проверка отката условий")

    event.listen(connection, "before_cursor_execute", fail_insert)
    try:
        with pytest.raises(RuntimeError, match="Проверка отката"):
            put(client, users, form, data)
    finally:
        event.remove(connection, "before_cursor_execute", fail_insert)
    assert client.get(f"/forms/{form['id']}", headers=headers(users[0])).json() == before
