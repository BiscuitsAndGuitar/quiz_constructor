from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.dependencies import require_author, require_participant
from app.models import User
from app.services.security import PASSWORD_TOO_LONG, PASSWORD_TOO_SHORT, create_access_token, verify_password


@pytest.fixture
def registration():
    return {"email": f"stage2-{uuid4().hex}@example.com", "password": "пароль123",
            "name": " Анна ", "is_author": True}


@pytest.mark.parametrize("is_author", [True, False])
def test_register(client, db_session, registration, is_author):
    registration["is_author"] = is_author
    registration["email"] = " " + registration["email"].upper() + " "
    response = client.post("/auth/register", json=registration)
    assert response.status_code == 201
    data = response.json()
    assert data == {"id": data["id"], "email": registration["email"].strip().lower(),
                    "name": "Анна", "is_author": is_author}
    user = db_session.get(User, data["id"])
    assert user.password_hash != registration["password"]
    assert verify_password(registration["password"], user.password_hash)


def test_duplicate_email(client, registration):
    assert client.post("/auth/register", json=registration).status_code == 201
    registration["email"] = " " + registration["email"].upper() + " "
    response = client.post("/auth/register", json=registration)
    assert response.status_code == 409
    assert response.json() == {"detail": "Пользователь с таким email уже есть"}


@pytest.mark.parametrize("password, message", [
    ("a" * 7, PASSWORD_TOO_SHORT), ("a" * 73, PASSWORD_TOO_LONG),
    ("я" * 37, PASSWORD_TOO_LONG), ("😀" * 19, PASSWORD_TOO_LONG),
])
def test_registration_password_errors(client, registration, password, message):
    registration["password"] = password
    response = client.post("/auth/register", json=registration)
    assert response.status_code == 422
    assert response.json() == {"detail": message}


@pytest.mark.parametrize("field, value", [("email", "invalid"), ("name", "  "),
                                           ("name", "a" * 101), ("is_author", "true")])
def test_invalid_registration(client, registration, field, value):
    registration[field] = value
    response = client.post("/auth/register", json=registration)
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)


def test_role_required(client, registration):
    del registration["is_author"]
    assert client.post("/auth/register", json=registration).status_code == 422


def test_login_and_me(client, registration):
    registered = client.post("/auth/register", json=registration).json()
    response = client.post("/auth/login", json={"email": " " + registration["email"].upper(),
                                               "password": registration["password"]})
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"access_token", "token_type", "user"}
    assert data["token_type"] == "bearer"
    assert data["user"] == registered
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert response.status_code == 200
    assert response.json() == registered


@pytest.mark.parametrize("password", ["wrong-password", "short", "", "я" * 37, "a" * 73])
def test_wrong_password_returns_401(client, registration, password):
    client.post("/auth/register", json=registration)
    response = client.post("/auth/login", json={"email": registration["email"], "password": password})
    assert response.status_code == 401
    assert response.json() == {"detail": "Неверный email или пароль"}


def test_unknown_email(client, registration):
    response = client.post("/auth/login", json={"email": registration["email"], "password": "password123"})
    assert response.status_code == 401


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid"},
                                     {"Authorization": "Basic abc"}])
def test_me_without_valid_token(client, headers):
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 401
    assert isinstance(response.json()["detail"], str)


def test_me_expired_token(client, registration, monkeypatch):
    from app.config import settings
    user = client.post("/auth/register", json=registration).json()
    monkeypatch.setattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", -1)
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {create_access_token(user['id'])}"})
    assert response.status_code == 401


def test_me_deleted_user(client, db_session, registration):
    user = client.post("/auth/register", json=registration).json()
    token = create_access_token(user["id"])
    db_session.delete(db_session.get(User, user["id"]))
    db_session.commit()
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_role_dependencies():
    author, participant = User(is_author=True), User(is_author=False)
    assert require_author(author) is author
    assert require_participant(participant) is participant
    for function, user in [(require_author, participant), (require_participant, author)]:
        with pytest.raises(HTTPException) as error:
            function(user)
        assert error.value.status_code == 403
