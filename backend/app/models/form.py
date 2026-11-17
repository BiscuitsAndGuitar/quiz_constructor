from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, false, text

from app.database import Base


class Form(Base):
    __tablename__ = "forms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    author_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    is_test: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_published: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    public_code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    requires_login: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    max_attempts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_limit_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    take_by_blocks: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    allow_free_navigation: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    shuffle_questions: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    shuffle_answer_options: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    show_correct_answers: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    show_results_by_block: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("timezone('utc', now())"),
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Block(Base):
    __tablename__ = "blocks"
    __table_args__ = (
        CheckConstraint("(form_id IS NULL) <> (library_block_id IS NULL)", name="ck_blocks_owner"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    form_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("forms.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    library_block_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("library_blocks.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    block_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("blocks.id", ondelete="CASCADE"),
        nullable=False,
    )
    type_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("question_types.id", ondelete="RESTRICT"),
        nullable=False,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    image_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("images.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_answer_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    allow_partial_scoring: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )


class QuestionType(Base):
    __tablename__ = "question_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)


class QuestionChoice(Base):
    __tablename__ = "question_choices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    question_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    text: Mapped[str] = mapped_column(String(500), nullable=False)
    is_correct: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class CorrectTextAnswer(Base):
    __tablename__ = "correct_text_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    question_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    answer_text: Mapped[str] = mapped_column(String(500), nullable=False)


class Image(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    owner_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    file_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("timezone('utc', now())"),
    )


class GradingScale(Base):
    __tablename__ = "grading_scale"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    form_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("forms.id", ondelete="CASCADE"),
        nullable=False,
    )
    min_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    grade: Mapped[str] = mapped_column(String(20), nullable=False)
