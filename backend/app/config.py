from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ThreatLens"
    app_env: str = "development"
    app_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"
    threatlens_version: str = "1.0.0"
    demo_mode: bool = True
    log_level: str = "INFO"
    seed_on_start: bool = True

    database_url: str = "postgresql+psycopg://threatlens:threatlens@localhost:5432/threatlens"
    redis_url: str = "redis://localhost:6379/0"
    elasticsearch_url: str = "http://localhost:9200"

    jwt_secret: str = "dev-access-secret-change-me-please-32"
    jwt_refresh_secret: str = "dev-refresh-secret-change-me-please"
    jwt_access_minutes: int = 15
    jwt_refresh_days: int = 7
    encryption_key: str = "dev-encryption-key-change-me-32ch"
    cookie_secure: bool = False

    email_provider: str = "smtp"
    email_api_key: str = ""
    email_from: str = "ThreatLens <noreply@threatlens.local>"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_tls: bool = False

    otx_api_key: str = ""
    abuseipdb_api_key: str = ""
    virustotal_api_key: str = ""
    malwarebazaar_api_key: str = ""
    urlhaus_auth_key: str = ""

    ai_api_key: str = ""
    ai_api_base: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4o-mini"

    cors_origins: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
