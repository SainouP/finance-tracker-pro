import os
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR / 'finance_tracker.db'}",
)

# Render entrega normalmente una URL que empieza con postgresql://.
# Se especifica psycopg para utilizar el driver instalado en requirements.txt.
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1,
    )

connect_args = (
    {"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session