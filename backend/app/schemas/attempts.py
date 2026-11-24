from datetime import datetime
from typing import Literal
from pydantic import BaseModel, StrictInt


class SubmittedAnswer(BaseModel):
    question_id: StrictInt
    option_ids: list[StrictInt] | None = None
    text: str | None = None


class AttemptFinish(BaseModel):
    answers: list[SubmittedAnswer]


class PublicForm(BaseModel):
    id: int
    is_test: bool
    title: str
    description: str | None
    requires_login: bool
    time_limit_minutes: int | None
    max_attempts: int | None
    attempts_used: int | None
    attempts_left: int | None


class StartedAttempt(BaseModel):
    id: int
    attempt_key: str
    started_at: datetime
    deadline: datetime | None


class AttemptStart(BaseModel):
    attempt: StartedAttempt
    form: dict


class SurveyResult(BaseModel):
    attempt_id: int
    is_test: Literal[False]
    finished_early: bool
    message: str
    answers: list[dict] | None = None


class TestResult(BaseModel):
    attempt_id: int
    is_test: Literal[True]
    finished_early: Literal[False]
    message: str
    score: int
    max_score: int
    percent: float
    grade: str | None
    better_than_percent: int | None
    block_results: list[dict] | None
    review: list[dict] | None


class HistoryForm(BaseModel):
    id: int
    title: str
    is_test: bool


class HistoryItem(BaseModel):
    attempt_id: int
    form: HistoryForm
    is_finished: bool
    finished_at: datetime | None
    score: int | None
    max_score: int | None
    percent: float | None
    grade: str | None
