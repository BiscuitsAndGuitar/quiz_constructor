import os

# Тесты проверяют HTTP и метаданные, подключение к PostgreSQL не открывается.
os.environ["DATABASE_URL"] = "postgresql+psycopg://test:test@localhost:1/test"
os.environ["SECRET_KEY"] = "test-only-key"
