from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, StrictBool, field_validator
from pydantic_core import PydanticCustomError

from app.services.security import validate_password


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    is_author: StrictBool

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def check_email_length(cls, value):
        if len(value) > 255:
            raise PydanticCustomError("auth", "Email слишком длинный")
        return value.lower()

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        try:
            return validate_password(value)
        except ValueError as error:
            raise PydanticCustomError("auth", str(error)) from error

    @field_validator("name")
    @classmethod
    def check_name(cls, value: str) -> str:
        value = value.strip()
        if not 1 <= len(value) <= 100:
            raise PydanticCustomError("auth", "Имя должно содержать от 1 до 100 символов")
        return value


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    is_author: bool


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserResponse
