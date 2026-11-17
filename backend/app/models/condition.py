from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, true

from app.database import Base


class ConditionGroup(Base):
    __tablename__ = "condition_groups"
    __table_args__ = (
        # Верхняя группа принадлежит блоку или вопросу, вложенная — только группе.
        CheckConstraint(
            "(parent_group_id IS NULL AND "
            "((block_id IS NULL) <> (question_id IS NULL))) OR "
            "(parent_group_id IS NOT NULL AND block_id IS NULL AND question_id IS NULL)",
            name="ck_condition_groups_owner",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    parent_group_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("condition_groups.id", ondelete="CASCADE"),
        nullable=True,
    )
    match_all: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )
    block_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("blocks.id", ondelete="CASCADE"),
        nullable=True,
    )
    question_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=True,
    )


class Condition(Base):
    __tablename__ = "conditions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("condition_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    operator_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("condition_operators.id", ondelete="RESTRICT"),
        nullable=False,
    )
    choice_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("question_choices.id", ondelete="CASCADE"),
        nullable=True,
    )
    text_answer: Mapped[str | None] = mapped_column(String(500), nullable=True)


class ConditionOperator(Base):
    __tablename__ = "condition_operators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    operator: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
