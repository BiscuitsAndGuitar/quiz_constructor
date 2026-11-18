from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=401, detail="Войдите в аккаунт: токен отсутствует или недействителен",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        user_id = decode_access_token(credentials.credentials)
    except InvalidTokenError:
        raise unauthorized from None
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user


def require_author(user: User = Depends(get_current_user)) -> User:
    if not user.is_author:
        raise HTTPException(status_code=403, detail="Доступ только для составителя")
    return user


def require_participant(user: User = Depends(get_current_user)) -> User:
    if user.is_author:
        raise HTTPException(status_code=403, detail="Доступ только для участника")
    return user
