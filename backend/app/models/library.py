from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, false, text

from app.database import Base


class LibraryBlock(Base):
    __tablename__ = "library_blocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    owner_id: Mapped[int] = mapped_column(
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
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(
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


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)


class LibraryBlockTag(Base):
    __tablename__ = "library_block_tags"

    library_block_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("library_blocks.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    tag_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
