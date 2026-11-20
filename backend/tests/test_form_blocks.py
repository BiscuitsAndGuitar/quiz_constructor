from copy import deepcopy

import pytest
from sqlalchemy import event, select

from app.models import Block, Question
from test_forms import create, draft, headers, users


def three_blocks():
    data = draft()
    data["blocks"][0]["title"] = "  Первый  "
    data["blocks"].extend([
        {"key": "empty", "title": "  ", "questions": []},
        {"key": "last", "questions": [{"key": "last-question", "text": "Третий", "type": "text"}]},
    ])
    return data


def assert_positions(db, form_id, saved):
    blocks = db.scalars(select(Block).where(Block.form_id == form_id).order_by(Block.position)).all()
    assert [b.position for b in blocks] == [1, 2, 3]
    for block, expected in zip(blocks, saved["blocks"]):
        assert block.id == int(expected["key"][1:])
        assert block.title == expected["title"]
        questions = db.scalars(select(Question).where(Question.block_id == block.id).order_by(Question.position)).all()
        assert [q.position for q in questions] == list(range(1, len(questions) + 1))
        assert [q.text for q in questions] == [q["text"] for q in expected["questions"]]


def test_three_blocks_reorder_and_transfer(client, db_session, users):
    form = create(client, users[0])
    url = f"/forms/{form['id']}"
    response = client.put(url, json=three_blocks(), headers=headers(users[0]))
    assert response.status_code == 200, response.text
    saved = response.json()
    assert [b["title"] for b in saved["blocks"]] == ["Первый", None, None]
    assert_positions(db_session, form["id"], saved)
    assert client.get(url, headers=headers(users[0])).json() == saved
    changed = deepcopy(saved)
    changed["blocks"][1]["questions"].append(changed["blocks"][0]["questions"].pop(0))
    changed["blocks"][2]["questions"].append(changed["blocks"][0]["questions"].pop())
    changed["blocks"][2]["questions"].reverse()
    changed["blocks"].reverse()
    response = client.put(url, json=changed, headers=headers(users[0]))
    assert response.status_code == 200, response.text
    saved = response.json()
    assert [[q["text"] for q in b["questions"]] for b in saved["blocks"]] == [["Второй вопрос", "Третий"], ["Первый вопрос"], []]
    assert_positions(db_session, form["id"], saved)
    assert client.get(url, headers=headers(users[0])).json() == saved


@pytest.mark.parametrize("title,valid", [("я" * 256, False), ("  " + "я" * 255 + "  ", True), ("", True), (None, True)])
def test_block_title(client, users, title, valid):
    form = create(client, users[0])
    url = f"/forms/{form['id']}"
    before = client.get(url, headers=headers(users[0])).json()
    data = three_blocks()
    data["blocks"][0]["title"] = title
    response = client.put(url, json=data, headers=headers(users[0]))
    if valid:
        assert response.status_code == 200
        assert response.json()["blocks"][0]["title"] == (title.strip() or None if title is not None else None)
    else:
        assert response.status_code == 422
        assert response.json()["detail"] == "Название блока должно быть не длиннее 255 символов"
        assert client.get(url, headers=headers(users[0])).json() == before


def test_blocks_rollback_after_partial_insert(client, db_session, users):
    form = create(client, users[0])
    url = f"/forms/{form['id']}"
    before = client.put(url, json=three_blocks(), headers=headers(users[0])).json()
    connection = db_session.connection()
    inserts = 0
    def fail(conn, cursor, statement, parameters, context, executemany):
        nonlocal inserts
        if statement.startswith("INSERT INTO blocks"):
            inserts += 1
            if inserts == 2:
                raise RuntimeError("Ошибка второго блока")
    event.listen(connection, "before_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="Ошибка второго блока"):
            client.put(url, json=three_blocks(), headers=headers(users[0]))
    finally:
        event.remove(connection, "before_cursor_execute", fail)
    assert client.get(url, headers=headers(users[0])).json() == before
    assert_positions(db_session, form["id"], before)
