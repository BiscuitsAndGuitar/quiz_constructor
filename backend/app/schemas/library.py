from datetime import datetime
from pydantic import Field, StrictBool, field_validator
from pydantic_core import PydanticCustomError
from app.schemas.forms import FormTitle, BlockData
from pydantic import BaseModel


class LibraryMetadata(FormTitle):
    description: str | None = None
    is_public: StrictBool = False
    tags: list[str] = Field(default_factory=list)

    @field_validator("tags")
    @classmethod
    def check_tags(cls, value):
        from app.services.library import normalize_tags
        from app.services.form_validation import InvalidFormError
        try:
            return normalize_tags(value)
        except InvalidFormError as error:
            raise PydanticCustomError("form", str(error)) from None


class LibraryCreate(LibraryMetadata):
    is_test: StrictBool
    block: BlockData

    @field_validator("block", mode="before")
    @classmethod
    def ignore_inner_title(cls, value):
        # Название образца задаётся только полем верхнего уровня.
        return {**value, "title": None} if isinstance(value, dict) else value


class LibraryCreated(BaseModel):
    id: int
    title: str
    is_test: bool
    is_public: bool
    tags: list[str]
    warnings: list[str]


class LibraryItem(BaseModel):
    id: int
    title: str
    description: str | None
    is_test: bool
    is_public: bool
    is_mine: bool
    owner_name: str
    tags: list[str]
    questions_count: int
    created_at: datetime


class LibraryDetails(BaseModel):
    id: int
    title: str
    description: str | None
    is_test: bool
    is_public: bool
    tags: list[str]
    block: BlockData


class LibraryTag(BaseModel):
    name: str
    count: int
