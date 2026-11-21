from datetime import datetime

from pydantic import BaseModel, Field, StrictBool, StrictInt, field_validator, model_validator
from pydantic_core import PydanticCustomError


class FormTitle(BaseModel):
    title: str

    @field_validator("title")
    @classmethod
    def check_title(cls, value: str) -> str:
        value = value.strip()
        if not 1 <= len(value) <= 255:
            raise PydanticCustomError("form", "Название должно содержать от 1 до 255 символов")
        return value


class FormCreate(FormTitle):
    is_test: StrictBool


class ChoiceData(BaseModel):
    key: str = Field(min_length=1)
    text: str = Field(max_length=500)
    is_correct: StrictBool | None = None


class ConditionItemData(BaseModel):
    question: str
    operator: str
    option: str | None = None
    text_answer: str | None = None


class ConditionData(BaseModel):
    match_all: StrictBool
    items: list[ConditionItemData]


class FinishRuleData(BaseModel):
    key: str = Field(min_length=1)
    message: str | None = None
    condition: ConditionData


class QuestionData(BaseModel):
    key: str = Field(min_length=1)
    text: str
    type: str
    is_answer_required: StrictBool = False
    options: list[ChoiceData] = Field(default_factory=list)
    points: StrictInt | None = None
    allow_partial_scoring: StrictBool | None = None
    correct_text_answers: list[str] | None = None
    condition: ConditionData | None = None
    finish_rules: list[FinishRuleData] = Field(default_factory=list)

    @field_validator("type")
    @classmethod
    def check_type(cls, value: str) -> str:
        if value == "info":
            raise PydanticCustomError("form", "Тип «Текст без вопроса» пока не поддерживается")
        if value not in {"single", "multiple", "text"}:
            raise PydanticCustomError("form", "Неизвестный тип вопроса")
        return value

    @model_validator(mode="after")
    def check_options(self):
        if self.type == "text" and self.options:
            raise PydanticCustomError("form", "У текстового вопроса не должно быть вариантов ответа")
        return self


class BlockData(BaseModel):
    key: str = Field(min_length=1)
    title: str | None = None
    questions: list[QuestionData] = Field(default_factory=list)
    condition: ConditionData | None = None

    @field_validator("title")
    @classmethod
    def check_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if len(value) > 255:
            raise PydanticCustomError("form", "Название блока должно быть не длиннее 255 символов")
        return value or None


class FormSettings(FormTitle):
    description: str | None = None
    requires_login: StrictBool = False
    max_attempts: int | None = Field(default=None, ge=-2147483648, le=2147483647, strict=True)
    time_limit_minutes: int | None = Field(default=None, ge=-2147483648, le=2147483647, strict=True)
    take_by_blocks: StrictBool = False
    allow_free_navigation: StrictBool = False
    shuffle_questions: StrictBool = False
    shuffle_answer_options: StrictBool = False
    show_correct_answers: StrictBool = False
    show_results_by_block: StrictBool = False
    completion_message: str | None = Field(default=None, max_length=1000)


class GradeData(BaseModel):
    min_percent: StrictInt
    grade: str
    message: str | None = None


class FormSave(FormSettings):
    # Неизвестные поля Pydantic игнорирует, в том числе поля будущих этапов.
    blocks: list[BlockData] = Field(min_length=1)
    grading_scale: list[GradeData] | None = None

    @model_validator(mode="after")
    def check_settings_and_keys(self):
        if self.max_attempts is not None and not self.requires_login:
            raise PydanticCustomError("form", "Максимум попыток можно задать только при обязательном входе")
        keys = []
        for block in self.blocks:
            keys.append(block.key)
            for question in block.questions:
                keys.append(question.key)
                keys.extend(option.key for option in question.options)
                keys.extend(rule.key for rule in question.finish_rules)
        if len(keys) != len(set(keys)):
            raise PydanticCustomError("form", "Ключи блоков, вопросов, вариантов и правил должны быть уникальными")
        return self


class FormCreated(BaseModel):
    id: int
    is_test: bool
    title: str
    is_published: bool
    requires_login: bool
    public_code: str
    blocks: list[BlockData]


class FormResponse(FormSettings):
    id: int
    is_test: bool
    is_published: bool
    public_code: str
    blocks: list[BlockData]
    grading_scale: list[GradeData] | None = None


class FormListItem(BaseModel):
    id: int
    is_test: bool
    title: str
    is_published: bool
    requires_login: bool
    public_code: str
    attempts_count: int
    created_at: datetime
    published_at: datetime | None
