import base64
import re

import pytest
from sqlalchemy import select
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.main import app
from app.models import Image, AttemptAnswer
from app.services.images import MAX_IMAGE_SIZE
from test_forms import users, headers, create, draft

# Маленькие изображения, без файлов в рабочей папке uploads.
IMAGES = {
    "png": base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="),
    "gif": base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"),
    "webp": base64.b64decode("UklGRiIAAABXRUJQVlA4IBYAAAAwAQCdASoBAAEADsD+JaQAA3AAAAAA"),
    "jpg": base64.b64decode("/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD5/ooooA//2Q=="),
}


@pytest.fixture
def uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOADS_DIR", tmp_path)
    mount = next(route for route in app.routes if getattr(route, "name", None) == "uploads")
    monkeypatch.setattr(mount, "app", StaticFiles(directory=tmp_path))
    return tmp_path


def upload(client, user, kind="png"):
    return client.post("/images", headers=headers(user), files={"file": ("wrong.txt", IMAGES[kind], "text/plain")})


@pytest.mark.parametrize("kind", IMAGES)
def test_upload_real_image(client, db_session, users, uploads, kind):
    response = upload(client, users[0], kind)
    assert response.status_code == 201, response.text
    data = response.json()
    image = db_session.get(Image, data["id"])
    assert re.fullmatch(r"[0-9a-f]{32}\." + kind, image.file_name)
    assert image.owner_id == users[0] and image.size == len(IMAGES[kind])
    assert image.content_type == f"image/{'jpeg' if kind == 'jpg' else kind}"
    assert image.created_at is not None
    assert (uploads / image.file_name).read_bytes() == IMAGES[kind]
    served = client.get(data["url"])
    assert served.status_code == 200 and served.content == IMAGES[kind]


def test_upload_rejections(client, users, uploads):
    assert client.post("/images", files={"file": ("x.png", IMAGES["png"])}).status_code == 401
    assert upload(client, users[2]).status_code == 403
    assert client.post("/images", headers=headers(users[0]), files={"file": ("x.png", b"text", "image/png")}).status_code == 422
    assert client.post("/images", headers=headers(users[0]), files={"file": ("x.png", IMAGES["png"] + bytes(MAX_IMAGE_SIZE), "image/png")}).status_code == 413
    assert list(uploads.iterdir()) == []


def test_upload_database_failure_removes_file(client, db_session, users, uploads, monkeypatch):
    def fail():
        raise RuntimeError("test commit failure")
    monkeypatch.setattr(db_session, "commit", fail)
    with pytest.raises(RuntimeError, match="test commit failure"):
        upload(client, users[0])
    assert list(uploads.iterdir()) == []


@pytest.mark.parametrize("is_test", [False, True])
def test_images_info_roundtrip_copy_publish_and_attempt(client, db_session, users, uploads, is_test):
    # Картинку другого составителя можно использовать при копировании из библиотеки.
    image = upload(client, users[1]).json()
    form = create(client, users[0], is_test)
    url = f"/forms/{form['id']}"
    info = {"key": "info", "text": "Пояснение", "type": "info", "image_id": image["id"]}
    data = {"title": "Форма", "blocks": [{"key": "b", "questions": [info]}]}
    response = client.put(url, headers=headers(users[0]), json=data)
    assert response.status_code == 200, response.text
    assert client.post(url + "/publish", headers=headers(users[0])).json()["problems"] == ["Добавьте хотя бы один вопрос"]
    question = {"key": "q", "text": "Ответ", "type": "text"}
    if is_test:
        question.update(points=1, correct_text_answers=["Да"])
    else:
        info["condition"] = {"match_all": True, "items": [{"question": "q", "operator": "answered"}]}
    data["blocks"][0]["questions"] = [question, info]
    saved = client.put(url, headers=headers(users[0]), json=data)
    assert saved.status_code == 200, saved.text
    saved = saved.json()
    assert saved == client.get(url, headers=headers(users[0])).json()
    assert saved["blocks"][0]["questions"][1]["image"] == image
    assert saved["blocks"][0]["questions"][0]["image"] is None
    copy = client.post(url + "/copy", headers=headers(users[0])).json()
    assert client.get(f"/forms/{copy['id']}", headers=headers(users[0])).json()["blocks"][0]["questions"][1]["image"] == image
    data["blocks"][0]["questions"][1]["image_id"] = 2147483647
    rejected = client.put(url, headers=headers(users[0]), json=data)
    assert rejected.status_code == 422 and rejected.json()["detail"] == "Картинка не найдена"
    assert client.get(url, headers=headers(users[0])).json() == saved
    assert client.post(url + "/publish", headers=headers(users[0])).status_code == 200
    start = client.post(url + "/attempts", headers=headers(users[2]))
    assert start.status_code == 201, start.text
    start = start.json()
    questions = start["form"]["blocks"][0]["questions"]
    assert questions[0]["image"] is None and questions[1]["image"] == image
    attempt_id = start["attempt"]["id"]
    finished = client.post(f"/attempts/{attempt_id}/finish", headers=headers(users[2]), json={"answers": [{"question_id": questions[0]["id"], "text": "Да"}, {"question_id": questions[1]["id"], "text": "ignored"}]})
    assert finished.status_code == 200, finished.text
    result = client.get(f"/attempts/{attempt_id}/result", headers=headers(users[2]))
    assert result.status_code == 200
    if not is_test:
        assert [answer["question_id"] for answer in result.json()["answers"]] == [questions[0]["id"]]
    details = client.get(f"/attempts/{attempt_id}/details", headers=headers(users[0])).json()
    assert [answer["question_id"] for answer in details["answers"]] == [questions[0]["id"]]
    assert list(db_session.scalars(select(AttemptAnswer.question_id).where(AttemptAnswer.attempt_id == attempt_id))) == [questions[0]["id"]]
    stats = client.get(url + "/stats", headers=headers(users[0])).json()
    assert [q["question_id"] for q in stats["questions"]] == [questions[0]["id"]]


@pytest.mark.parametrize("extra", [{"options": [{"key": "o", "text": "Да"}]}, {"points": 1}, {"is_answer_required": True}, {"allow_partial_scoring": True}, {"correct_text_answers": ["Да"]}, {"finish_rules": [{"key": "r", "condition": {"match_all": True, "items": []}}]}])
def test_info_forbidden_fields(client, users, extra):
    form = create(client, users[0], True)
    response = client.put(f"/forms/{form['id']}", headers=headers(users[0]), json={"title": "Тест", "blocks": [{"key": "b", "questions": [{"key": "q", "type": "info", "text": "Текст", **extra}]}]})
    assert response.status_code == 422
    assert '«Текста без вопроса»' in response.json()["detail"]


def test_info_condition_forbidden_in_test(client, users):
    form = create(client, users[0], True)
    response = client.put(f"/forms/{form['id']}", headers=headers(users[0]), json={"title": "Тест", "blocks": [{"key": "b", "questions": [{"key": "q", "type": "info", "text": "Текст", "condition": {"match_all": True, "items": []}}]}]})
    assert response.status_code == 422
    assert "только у опросов" in response.json()["detail"]
