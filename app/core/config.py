
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Central Attendance Management API"
    app_version: str = "0.1.0"
    environment: str = "development"
    company_timezone: str = "Asia/Kolkata"
    jwt_secret_key: SecretStr
    access_token_expire_minutes: int = 15

    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "attendance_db"
    database_user: str = "attendance_app"
    database_password: SecretStr

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: SecretStr | None = None
    redis_cache_ttl_seconds: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
