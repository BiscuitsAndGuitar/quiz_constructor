import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Подпись тестовых токенов не зависит от секрета рабочего приложения.
os.environ["SECRET_KEY"] = "test-only-secret-key-not-for-production-123456"
os.environ["ALGORITHM"] = "HS256"
if not (Path(__file__).resolve().parents[1] / ".env").exists():
    os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:1/test")

from app.database import engine, get_db
from app.main import app


@pytest.fixture
def db_session():
    # commit() внутри сервиса завершает только SAVEPOINT, а не внешнюю транзакцию.
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            try:
                yield session
            finally:
                session.close()
                transaction.rollback()


@pytest.fixture
def client(db_session):
    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
