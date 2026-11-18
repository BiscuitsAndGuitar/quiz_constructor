from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text

from app.database import Base


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    form_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("forms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    attempt_key: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    grading_scale_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("grading_scale.id", ondelete="SET NULL"),
        nullable=True,
    )
    early_finish_rule_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("early_finish_rules.id", ondelete="SET NULL"),
        nullable=True,
    )


class AttemptAnswer(Base):
    __tablename__ = "attempt_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    attempt_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)


class AttemptAnswerChoice(Base):
    __tablename__ = "attempt_answer_choices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    attempt_answer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("attempt_answers.id", ondelete="CASCADE"),
        nullable=False,
    )
    choice_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("question_choices.id", ondelete="CASCADE"),
        nullable=False,
    )
