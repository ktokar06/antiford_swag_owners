from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent
WEAK_JWT_SECRETS = {
    "change-me-please-use-a-long-random-string",
    "change-me",
    "secret",
    "changeme",
}
MIN_JWT_SECRET_LEN = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "SWAG OWNERS Antifraud API"
    app_version: str = "0.2.0"

    database_url: str = Field(..., alias="DATABASE_URL")
    db_echo: bool = False

    jwt_secret: str = Field(..., alias="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM")
    jwt_expire_hours: int = Field(12, alias="JWT_EXPIRE_HOURS", ge=1, le=24 * 30)

    frontend_url: str = Field("http://localhost:5173", alias="FRONTEND_URL")
    reset_token_ttl_minutes: int = Field(60, alias="RESET_TOKEN_TTL_MINUTES")
    cors_origins: str = Field("http://localhost:5173,http://localhost:5174", alias="CORS_ORIGINS")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    cdr_dir: str = Field(str(BASE_DIR.parent / "cdr_out" / "cdr_out"), alias="CDR_DIR")
    cdr_timezone: str = Field("Europe/Moscow", alias="CDR_TIMEZONE")
    cdr_autoload: bool = Field(False, alias="CDR_AUTOLOAD")
    max_upload_mb: int = Field(200, alias="MAX_UPLOAD_MB", ge=1)
    ml_model_dir: str = Field(str(BASE_DIR / "models" / "release"), alias="ML_MODEL_DIR")

    operator_email: str | None = Field(None, alias="OPERATOR_EMAIL")
    operator_password: str | None = Field(None, alias="OPERATOR_PASSWORD")

    smtp_host: str | None = Field(None, alias="SMTP_HOST")
    smtp_port: int = Field(465, alias="SMTP_PORT")
    smtp_user: str | None = Field(None, alias="SMTP_USER")
    smtp_password: str | None = Field(None, alias="SMTP_PASSWORD")
    smtp_from: str | None = Field(None, alias="SMTP_FROM")
    smtp_use_tls: bool = Field(True, alias="SMTP_USE_TLS")

    @field_validator("jwt_secret")
    @classmethod
    def _check_jwt_secret(cls, v: str) -> str:
        v = v.strip()
        if v.lower() in WEAK_JWT_SECRETS or len(v) < MIN_JWT_SECRET_LEN:
            raise ValueError(
                f"JWT_SECRET слишком слабый: нужна случайная строка не короче {MIN_JWT_SECRET_LEN} символов "
                "в единственном корневом .env"
            )
        return v

    @field_validator("jwt_algorithm")
    @classmethod
    def _check_jwt_algorithm(cls, v: str) -> str:
        if v not in {"HS256", "HS384", "HS512"}:
            raise ValueError("JWT_ALGORITHM должен быть HS256, HS384 или HS512")
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
