from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, UserResponse
from app.services.auth import EmailAlreadyExistsError, authenticate_user, register_user
from app.services.security import create_access_token

router = APIRouter(prefix="/auth", tags=["Регистрация и вход"])


@router.post("/register", status_code=201, response_model=UserResponse)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    try:
        return register_user(db, **data.model_dump())
    except EmailAlreadyExistsError:
        raise HTTPException(status_code=409, detail="Пользователь с таким email уже есть") from None


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, data.email, data.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    return LoginResponse(access_token=create_access_token(user.id), user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user
