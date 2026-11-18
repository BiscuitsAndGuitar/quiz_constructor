from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings

PASSWORD_TOO_SHORT = "Пароль должен быть не короче 8 символов"
PASSWORD_TOO_LONG = (
    "Пароль слишком длинный. Допустимо примерно до 36 русских букв или 72 латинских символов"
)


def validate_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError(PASSWORD_TOO_SHORT)
    # bcrypt ограничивает размер UTF-8, а не число символов. Не обрезаем пароль.
    if len(password.encode("utf-8")) > 72:
        raise ValueError(PASSWORD_TOO_LONG)
    return password


def hash_password(password: str) -> str:
    validate_password(password)
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        encoded = password.encode("utf-8")
        if len(encoded) > 72:
            return False
        return bcrypt.checkpw(encoded, password_hash.encode("ascii"))
    except (ValueError, UnicodeError):
        return False


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": str(user_id), "iat": now,
         "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_access_token(token: str) -> int:
    payload = jwt.decode(
        token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM],
        options={"require": ["sub", "exp", "iat"]},
    )
    subject = payload["sub"]
    if not isinstance(subject, str) or not subject.isascii() or not subject.isdecimal():
        raise jwt.InvalidTokenError("Некорректный пользователь в токене")
    # В базе id имеет тип integer; не передаём заведомо недопустимое число в SQL.
    if len(subject) > 10 or not 1 <= int(subject) <= 2147483647:
        raise jwt.InvalidTokenError("Некорректный пользователь в токене")
    return int(subject)
