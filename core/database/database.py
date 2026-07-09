from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def create_database_engine(database_file: str | Path):
    database_file = Path(database_file)
    database_file.parent.mkdir(parents=True, exist_ok=True)

    return create_engine(
        f"sqlite:///{database_file.as_posix()}",
        echo=False,
        future=True,
    )


def create_session_factory(database_file: str | Path):
    engine = create_database_engine(database_file)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
