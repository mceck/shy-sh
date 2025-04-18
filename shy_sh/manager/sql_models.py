from contextlib import contextmanager
from datetime import datetime
import os
from sqlalchemy import DateTime, Text, create_engine, JSON, ForeignKey
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
    mapped_column,
    relationship,
    Mapped,
)
from enum import Enum

Base = declarative_base()


class Chat(Base):
    __tablename__ = "chat"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    messages: Mapped[list[dict]] = mapped_column(JSON)
    meta: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.utcnow()
    )

    executed_scripts: Mapped[list["ExecutedScript"]] = relationship(
        "ExecutedScript", back_populates="chat", cascade="all, delete-orphan"
    )


class ScriptType(str, Enum):
    SHELL = "shell"
    SHELL_SCRIPT = "shell_script"
    PYTHON = "python"


class ExecutedScript(Base):
    __tablename__ = "executed_script"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[ScriptType]
    script: Mapped[str] = mapped_column(Text)
    result: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.utcnow()
    )

    chat_id: Mapped[int] = mapped_column(ForeignKey("chat.id"))
    chat: Mapped[Chat] = relationship("Chat", back_populates="executed_scripts")


DATABASE_URL = os.path.expanduser("~/.config/shy/shy.db")
if not os.path.exists(os.path.dirname(DATABASE_URL)):
    os.makedirs(os.path.dirname(DATABASE_URL), exist_ok=True)
engine = create_engine(f"sqlite:///{DATABASE_URL}")
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)


@contextmanager
def session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
