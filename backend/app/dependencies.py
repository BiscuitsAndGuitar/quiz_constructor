from fastapi import Depends, HTTPException, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Form, User, Attempt, LibraryBlock
from sqlalchemy import select
import secrets
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


def get_owned_form(id: int, user: User = Depends(require_author), db: Session = Depends(get_db)) -> Form:
    form = db.get(Form, id) if 1 <= id <= 2147483647 else None
    if form is None:
        raise HTTPException(status_code=404, detail="Форма не найдена")
    if form.author_id != user.id:
        raise HTTPException(status_code=403, detail="Нет доступа к чужой форме")
    return form


def optional_user(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
                  db: Session = Depends(get_db)) -> User | None:
    if "authorization" not in request.headers:
        return None
    return get_current_user(credentials, db)


def get_library_block(id: int, user: User = Depends(require_author), db: Session = Depends(get_db)) -> LibraryBlock:
    item = db.get(LibraryBlock, id) if 1 <= id <= 2147483647 else None
    if item is None:
        raise HTTPException(status_code=404, detail="Блок библиотеки не найден")
    return item


def get_visible_library_block(item: LibraryBlock = Depends(get_library_block), user: User = Depends(require_author)) -> LibraryBlock:
    if item.owner_id != user.id and not item.is_public:
        raise HTTPException(status_code=403, detail="Нет доступа к приватному блоку")
    return item


def get_owned_library_block(item: LibraryBlock = Depends(get_library_block), user: User = Depends(require_author)) -> LibraryBlock:
    if item.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Нет доступа к чужому блоку")
    return item


def get_author_attempt(id: int, user: User = Depends(require_author), db: Session = Depends(get_db)) -> Attempt:
    attempt = db.get(Attempt, id) if 1 <= id <= 2147483647 else None
    if attempt is None:
        raise HTTPException(status_code=404, detail="Попытка не найдена")
    get_owned_form(attempt.form_id, user, db)
    return attempt


def attempt_participant(user: User | None = Depends(optional_user)):
    if user is not None and user.is_author:
        raise HTTPException(status_code=403, detail="Составители не могут проходить формы")
    return user


def check_attempt_owner(attempt, user, key):
    if attempt.user_id is not None:
        if user is None:
            raise HTTPException(status_code=403 if key else 401, detail="Для этой попытки нужен токен её владельца")
        if user.id != attempt.user_id:
            raise HTTPException(status_code=403, detail="Нет доступа к чужой попытке")
    else:
        if not key:
            raise HTTPException(status_code=403 if user else 401, detail="Передайте ключ анонимной попытки")
        if not secrets.compare_digest(key.encode(), attempt.attempt_key.encode()):
            raise HTTPException(status_code=403, detail="Неверный ключ попытки")


def owned_attempt(id: int, request: Request, user: User | None = Depends(optional_user),
                  x_attempt_key: str | None = Header(default=None), db: Session = Depends(get_db)):
    statement = select(Attempt).where(Attempt.id == id) if 1 <= id <= 2147483647 else select(Attempt).where(False)
    if request.method == "POST":
        statement = statement.with_for_update()
    attempt = db.scalar(statement.execution_options(populate_existing=True))
    if attempt is None:
        raise HTTPException(status_code=404, detail="Попытка не найдена")
    check_attempt_owner(attempt, user, x_attempt_key)
    return attempt
