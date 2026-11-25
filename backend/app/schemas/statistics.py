from datetime import datetime, date
from pydantic import BaseModel


class Participant(BaseModel):
    id: int
    name: str


class AttemptFields(BaseModel):
    user: Participant | None
    is_finished: bool
    finished_early: bool
    started_at: datetime
    finished_at: datetime | None
    score: int | None
    max_score: int | None
    percent: float | None
    grade: str | None


class AttemptListItem(AttemptFields):
    attempt_id: int


class DetailedAttempt(AttemptFields):
    id: int


class SelectedOption(BaseModel):
    id: int
    text: str


class DetailedAnswer(BaseModel):
    question_id: int
    block_title: str | None
    text: str
    type: str
    selected_options: list[SelectedOption]
    text_answer: str | None
    max_points: int | None
    score: int | None


class AttemptDetails(BaseModel):
    attempt: DetailedAttempt
    answers: list[DetailedAnswer]


class StatisticsForm(BaseModel):
    id: int
    is_test: bool
    title: str


class Summary(BaseModel):
    started: int
    finished: int
    completion_percent: float
    finished_early: int | None
    median_time_seconds: int | None
    avg_score: float | None
    avg_percent: float | None


class GradeCount(BaseModel):
    grade: str
    count: int


class RuleCount(BaseModel):
    rule_id: int
    question_id: int
    question_text: str
    message: str | None
    count: int


class DailyCount(BaseModel):
    date: date
    count: int


class BlockStatistics(BaseModel):
    block_id: int
    title: str | None
    questions_count: int
    max_points: int
    avg_percent: float


class OptionStatistics(BaseModel):
    option_id: int
    text: str
    count: int
    percent: float
    is_correct: bool | None = None


class TextCount(BaseModel):
    value: str
    count: int


class QuestionStatistics(BaseModel):
    question_id: int
    text: str
    type: str
    shown: int
    skipped: int
    correct_percent: float | None = None
    avg_score_percent: float | None = None
    options: list[OptionStatistics] | None = None
    top_answers: list[TextCount] | None = None


class FormStatistics(BaseModel):
    form: StatisticsForm
    summary: Summary
    grade_distribution: list[GradeCount] | None
    early_finish_rules: list[RuleCount] | None
    daily_finished: list[DailyCount]
    blocks: list[BlockStatistics] | None
    questions: list[QuestionStatistics]
