from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy import select, func

from app.models import Block, Question, QuestionChoice, CorrectTextAnswer, ConditionGroup, Condition, LibraryBlock, LibraryBlockTag, Tag, Image
from app.services.library import normalize_tags, prepare_library_block
from app.services.form_validation import InvalidFormError
from test_forms import users, headers, create


def condition(question, option=None):
    item = {"question": question, "operator": "chosen" if option else "answered"}
    if option:
        item["option"] = option
    return {"match_all": True, "items": [item]}


def payload(is_test=False):
    first = {"key": "q-first", "type": "single", "text": "Выбор", "options": [{"key": "o-first", "text": "Да"}, {"key": "o-second", "text": "Нет"}]}
    second = {"key": "q-second", "type": "text", "text": "Текст"}
    if is_test:
        first.update(points=2, allow_partial_scoring=False)
        first["options"][0]["is_correct"] = True
        second.update(points=1, correct_text_answers=["Да"])
    else:
        second["condition"] = condition("q-first", "o-first")
    return {"title": "Образец", "is_test": is_test, "tags": [" АлГеБра ", "алгебра", "  Два   слова "],
            "block": {"key": "source", "title": "ignored", "questions": [first, second, {"key": "info", "type": "info", "text": "Пояснение"}]}}


def post(client, user, data=None):
    response = client.post("/library/blocks", headers=headers(user), json=data or payload())
    assert response.status_code == 201, response.text
    return response.json()


def for_editor(block):
    block = deepcopy(block)
    keys = {block["key"]: uuid4().hex}
    for question in block["questions"]:
        keys[question["key"]] = uuid4().hex
        for option in question["options"]:
            keys[option["key"]] = uuid4().hex
    block["key"] = keys[block["key"]]
    for question in block["questions"]:
        question["key"] = keys[question["key"]]
        question["image_id"] = (question.pop("image") or {}).get("id")
        for option in question["options"]:
            option["key"] = keys[option["key"]]
        for item in (question.get("condition") or {}).get("items", []):
            item["question"] = keys[item["question"]]
            if "option" in item:
                item["option"] = keys[item["option"]]
    return block


def test_normalize_tags():
    assert normalize_tags([" А ", "а", "  ДВА\t Слова ", ""]) == ["а", "два слова"]
    assert normalize_tags(["а" * 30]) == ["а" * 30]
    assert len(normalize_tags([str(n) for n in range(10)] * 2)) == 10
    for tags in [["а" * 31], [str(n) for n in range(11)]]:
        with pytest.raises(InvalidFormError):
            normalize_tags(tags)


@pytest.mark.parametrize("reference,option", [("outside", None), ("q-second", None), ("info", None), ("q-first", "wrong-option")])
def test_filter_conditions(reference, option):
    data = payload()["block"]
    data["condition"] = condition("outside")
    data["questions"][1]["condition"] = condition(reference, option)
    data["questions"][0]["finish_rules"] = [{"key": "r", "condition": condition("q-first")}]
    original = deepcopy(data)
    result, warnings = prepare_library_block(data)
    assert data == original
    assert "condition" not in result and "condition" not in result["questions"][1]
    assert "finish_rules" not in result["questions"][0]
    assert len(warnings) == 3 and "(1 шт.)" in warnings[1]


def test_keep_internal_condition():
    data = payload()["block"]
    result, warnings = prepare_library_block(data)
    assert result == data and warnings == []


@pytest.mark.parametrize("is_test", [False, True])
def test_roundtrip_insert_independence_and_cascade(client, db_session, users, is_test):
    image = Image(owner_id=users[1], file_name=f"{uuid4().hex}.png", content_type="image/png", size=10)
    db_session.add(image)
    db_session.commit()
    image_id = image.id
    data = payload(is_test)
    data["block"]["questions"][0]["image_id"] = image_id
    if not is_test:
        data["block"]["condition"] = condition("outside")
        data["block"]["questions"][2]["condition"] = condition("outside")
        data["block"]["questions"][0]["finish_rules"] = [{"key": "r", "condition": condition("q-first")}]
    created = post(client, users[0], data)
    assert created["tags"] == ["алгебра", "два слова"]
    assert len(created["warnings"]) == (0 if is_test else 3)
    url = f"/library/blocks/{created['id']}"
    details = client.get(url, headers=headers(users[0])).json()
    assert details["title"] == details["block"]["title"] == "Образец"
    block = details["block"]
    assert block["key"] == "b1"
    assert [q["key"] for q in block["questions"]] == ["q1", "q2", "q3"]
    if is_test:
        assert block["questions"][0]["points"] == 2
        assert block["questions"][0]["options"][0]["is_correct"] is True
        assert block["questions"][1]["correct_text_answers"] == ["Да"]
    else:
        assert block["condition"] is None
        assert block["questions"][1]["condition"] == condition("q1", "o1")
        assert block["questions"][2]["condition"] is None
        assert all(q["finish_rules"] == [] for q in block["questions"])
    sample = db_session.scalar(select(Block).where(Block.library_block_id == created["id"]))
    sample_id = sample.id
    assert sample.form_id is None and sample.position == 1
    qids = list(db_session.scalars(select(Question.id).where(Question.block_id == sample_id)))
    choice_ids = list(db_session.scalars(select(QuestionChoice.id).where(QuestionChoice.question_id.in_(qids))))
    group_ids = list(db_session.scalars(select(ConditionGroup.id).where(ConditionGroup.question_id.in_(qids))))
    form = create(client, users[0], is_test)
    form_url = f"/forms/{form['id']}"
    response = client.put(form_url, headers=headers(users[0]), json={"title": "Вставка", "blocks": [for_editor(block)]})
    assert response.status_code == 200, response.text
    saved = client.get(form_url, headers=headers(users[0])).json()
    assert saved["blocks"][0]["questions"][0]["image"] == {"id": image_id, "url": f"/uploads/{image.file_name}"}
    if not is_test:
        questions = saved["blocks"][0]["questions"]
        assert questions[1]["condition"] == condition(questions[0]["key"], questions[0]["options"][0]["key"])
    assert client.post(form_url + "/publish", headers=headers(users[0])).status_code == 200
    copied = client.post(form_url + "/copy", headers=headers(users[0])).json()
    assert len(client.get(f"/forms/{copied['id']}", headers=headers(users[0])).json()["blocks"]) == 1
    stats = client.get(form_url + "/stats", headers=headers(users[0])).json()
    assert len(stats["questions"]) == 2
    assert len(client.get("/my/forms", headers=headers(users[0])).json()) == 2
    assert client.delete(form_url, headers=headers(users[0])).status_code == 204
    assert client.get(url, headers=headers(users[0])).json() == details
    assert client.delete(url, headers=headers(users[0])).status_code == 204
    db_session.expire_all()
    for model, clause in [(Block, Block.id == sample_id), (Question, Question.id.in_(qids)),
                          (QuestionChoice, QuestionChoice.id.in_(choice_ids)), (CorrectTextAnswer, CorrectTextAnswer.question_id.in_(qids)),
                          (ConditionGroup, ConditionGroup.id.in_(group_ids)), (Condition, Condition.group_id.in_(group_ids)),
                          (LibraryBlockTag, LibraryBlockTag.library_block_id == created["id"])]:
        assert db_session.scalar(select(func.count()).select_from(model).where(clause)) == 0
    assert db_session.scalar(select(Tag).where(Tag.name == "алгебра")) is not None
    copied_after = client.get(f"/forms/{copied['id']}", headers=headers(users[0]))
    assert copied_after.status_code == 200 and len(copied_after.json()["blocks"][0]["questions"]) == 3


def test_list_filters_metadata_and_tags(client, users):
    marker = uuid4().hex[:8]
    def add(user, title, public=False, is_test=False, description=None, tags=None):
        data = payload(is_test)
        data.update(title=title, is_public=public, description=description, tags=tags or [marker])
        return post(client, user, data)["id"]
    own = add(users[0], "АлГЕБРА " + marker)
    other = add(users[1], "Чужой", True, True, "Описание " + marker.upper())
    own_public = add(users[0], "Публичный", True, tags=[marker, "тег " + marker])
    private = add(users[1], "Секрет", tags=[marker, "скрытый " + marker])
    def listed(**params):
        response = client.get("/library/blocks", headers=headers(users[0]), params={"query": marker, **params})
        assert response.status_code == 200, response.text
        return response.json()
    assert [r["id"] for r in listed()] == [own_public, other, own]
    assert [r["id"] for r in listed(scope="mine")] == [own_public, own]
    assert [r["id"] for r in listed(scope="public")] == [other]
    assert [r["id"] for r in listed(is_test=True)] == [other]
    assert [r["id"] for r in listed(query="АЛГЕБРА " + marker)] == [own]
    assert [r["id"] for r in listed(query="ОПИСАНИЕ " + marker)] == [other]
    assert [r["id"] for r in listed(query="ТЕГ " + marker)] == [own_public]
    assert [r["id"] for r in listed(tag="ТЕГ " + marker)] == [own_public]
    assert [r["id"] for r in listed(limit=1, offset=1)] == [other]
    assert all(r["questions_count"] == 2 for r in listed())
    assert [r["is_mine"] for r in listed()] == [True, False, True]
    assert all(r["owner_name"] for r in listed())
    tags = client.get("/library/tags", params={"query": marker.upper()}, headers=headers(users[0])).json()
    assert tags == [{"name": marker, "count": 3}]
    assert client.get("/library/tags", params={"query": "скрытый " + marker}, headers=headers(users[0])).json() == []
    url = f"/library/blocks/{own}"
    before = client.get(url, headers=headers(users[0])).json()["block"]
    update = {"title": " Новое ", "description": "Другое", "is_public": True, "tags": [" Новый ", "новый"]}
    result = client.put(url, json=update, headers=headers(users[0]))
    assert result.status_code == 200 and result.json()["tags"] == ["новый"]
    assert result.json()["title"] == "Новое" and result.json()["is_public"] is True
    after = client.get(url, headers=headers(users[0])).json()["block"]
    assert before["questions"] == after["questions"]
    assert client.get(f"/library/blocks/{private}", headers=headers(users[0])).status_code == 403
    assert client.get(f"/library/blocks/{other}", headers=headers(users[0])).status_code == 200


def test_access(client, users):
    item = post(client, users[0])
    url = f"/library/blocks/{item['id']}"
    for method, path, body in [("get", "/library/blocks", None), ("get", "/library/tags", None), ("get", url, None),
                               ("post", "/library/blocks", payload()), ("put", url, {"title": "Новое"}), ("delete", url, None)]:
        for auth, expected in [({}, 401), (headers(users[2]), 403)]:
            response = client.request(method, path, headers=auth, json=body)
            assert response.status_code == expected
    for method in ["get", "put", "delete"]:
        body = {"title": "Чужое"} if method == "put" else None
        assert client.request(method, url, json=body, headers=headers(users[1])).status_code == 403
        assert client.request(method, "/library/blocks/2147483647", json=body, headers=headers(users[0])).status_code == 404


@pytest.mark.parametrize("change", ["empty", "missing-type", "title", "tags-count", "tag-length", "image", "points", "info-points", "survey-points", "duplicate"])
def test_invalid_create_rolls_back(client, db_session, users, change):
    data = payload(change == "points")
    if change == "empty": data["block"]["questions"] = []
    elif change == "missing-type": data.pop("is_test")
    elif change == "title": data["title"] = " "
    elif change == "tags-count": data["tags"] = [str(n) for n in range(11)]
    elif change == "tag-length": data["tags"] = ["x" * 31]
    elif change == "image": data["block"]["questions"][0]["image_id"] = 2147483647
    elif change == "points": data["block"]["questions"][0]["points"] = 0
    elif change == "info-points": data["block"]["questions"][-1]["points"] = 1
    elif change == "survey-points": data["block"]["questions"][0]["points"] = 1
    elif change == "duplicate": data["block"]["questions"][0]["key"] = data["block"]["key"]
    before = db_session.scalar(select(func.count()).select_from(LibraryBlock))
    response = client.post("/library/blocks", headers=headers(users[0]), json=data)
    assert response.status_code == 422, response.text
    assert db_session.scalar(select(func.count()).select_from(LibraryBlock)) == before


def test_info_only_inner_title_and_invalid_filters(client, users):
    data = payload()
    data["block"]["title"] = "x" * 300
    data["block"]["questions"] = [{"key": "info", "type": "info", "text": "Пояснение"}]
    item = post(client, users[0], data)
    assert item["title"] == "Образец"
    for params in [{"scope": "wrong"}, {"limit": 0}, {"limit": 101}, {"offset": -1}]:
        assert client.get("/library/blocks", params=params, headers=headers(users[0])).status_code == 422
    for fields in [{"title": " "}, {"title": "Новое", "tags": ["a" * 31]}, {"title": "Новое", "tags": [str(n) for n in range(11)]}]:
        assert client.put(f"/library/blocks/{item['id']}", headers=headers(users[0]), json=fields).status_code == 422


def test_source_form_changes_and_delete_do_not_change_sample(client, users):
    form = create(client, users[0])
    url = f"/forms/{form['id']}"
    saved = client.put(url, headers=headers(users[0]), json={"title": "Источник", "blocks": [payload()["block"]]}).json()
    data = payload()
    data["block"] = for_editor(saved["blocks"][0])
    item = post(client, users[0], data)
    library_url = f"/library/blocks/{item['id']}"
    before = client.get(library_url, headers=headers(users[0])).json()
    assert client.put(url, headers=headers(users[0]), json={"title": "Пустая", "blocks": [{"key": "empty", "questions": []}]}).status_code == 200
    assert client.delete(url, headers=headers(users[0])).status_code == 204
    assert client.get(library_url, headers=headers(users[0])).json() == before


def test_create_failure_rolls_back_all_rows(client, db_session, users, monkeypatch):
    from app.services import library
    before = {model: db_session.scalar(select(func.count()).select_from(model)) for model in [LibraryBlock, Block, Question, Tag]}
    original = library.save_tags
    def fail(db, id, names):
        original(db, id, names)
        db.flush()
        raise RuntimeError("test rollback")
    monkeypatch.setattr(library, "save_tags", fail)
    with pytest.raises(RuntimeError, match="test rollback"):
        post(client, users[0])
    for model, count in before.items():
        assert db_session.scalar(select(func.count()).select_from(model)) == count
