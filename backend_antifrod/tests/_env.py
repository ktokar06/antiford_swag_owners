"""Минимальное окружение для импорта приложения в тестах (БД не нужна)."""
import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test")
os.environ.setdefault("JWT_SECRET", "test-secret-" + "x" * 40)
