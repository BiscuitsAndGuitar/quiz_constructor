from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User
from app.services.security import hash_password, verify_password


class EmailAlreadyExistsError(Exception):
    pass


def register_user(db: Session, email: str, password: str, name: str, is_author: bool) -> User:
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise EmailAlreadyExistsError
    user = User(email=email, password_hash=hash_password(password), name=name, is_author=is_author)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        # Уникальность защищает и от двух одновременных регистраций одного email.
        if getattr(error.orig, "sqlstate", None) == "23505":
            raise EmailAlreadyExistsError from error
        raise
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user
