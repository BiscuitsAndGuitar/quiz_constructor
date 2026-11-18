from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config import settings
from app.services.security import (
    PASSWORD_TOO_LONG, PASSWORD_TOO_SHORT, create_access_token,
    decode_access_token, hash_password, validate_password, verify_password,
)


@pytest.mark.parametrize("password", ["abcdefgh", "a" * 72, "я" * 36, "😀" * 18])
def test_password_boundaries_accepted(password):
    assert validate_password(password) == password
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password(password + "a", hashed)


@pytest.mark.parametrize("password, message", [
    ("abcdefg", PASSWORD_TOO_SHORT), ("😀" * 7, PASSWORD_TOO_SHORT),
    ("a" * 73, PASSWORD_TOO_LONG), ("я" * 37, PASSWORD_TOO_LONG),
    ("😀" * 18 + "a", PASSWORD_TOO_LONG), ("😀" * 19, PASSWORD_TOO_LONG),
])
def test_password_boundaries_rejected(password, message):
    for function in (validate_password, hash_password):
        with pytest.raises(ValueError, match=message):
            function(password)


def test_hash_uses_random_salt_and_preserves_spaces():
    password = "  пароль123  "
    hashed = hash_password(password)
    assert hashed != hash_password(password)
    assert verify_password(password, hashed)
    assert not verify_password(password.strip(), hashed)
    assert not verify_password("wrong", hashed)


def test_token_round_trip():
    assert decode_access_token(create_access_token(42)) == 42


def test_expired_token(monkeypatch):
    monkeypatch.setattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", -1)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(create_access_token(42))


def test_wrong_signature():
    token = jwt.encode({"sub": "42", "exp": datetime.now(timezone.utc) + timedelta(minutes=1),
                        "iat": datetime.now(timezone.utc)}, "other-secret" * 4, algorithm="HS256")
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)


@pytest.mark.parametrize("subject", ["wrong", "0", "2147483648", "9" * 5000])
def test_invalid_user_id(subject):
    now = datetime.now(timezone.utc)
    token = jwt.encode({"sub": subject, "iat": now, "exp": now + timedelta(minutes=1)},
                       settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)
