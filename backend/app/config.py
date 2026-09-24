from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    # Application
    app_name: str = "ThreatLens"
    app_env: str = "development"
    app_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"
    threatlens_version: str = "1.0.0"
    demo_mode: bool = True
    log_level: str = "INFO"
    seed_on_start: bool = True

    # Database / cache / search
    database_url: str = (
        "postgresql+psycopg://threatlens:threatlens@localhost:5432/threatlens"
    )
    redis_url: str = "redis://localhost:6379/0"
    elasticsearch_url: str = "http://localhost:9200"

    # Authentication
    jwt_secret: str = Field(default="")
    jwt_refresh_secret: str = Field(default="")

    jwt_access_minutes: int = 15
    jwt_refresh_days: int = 7

    encryption_key: str = Field(default="")

    cookie_secure: bool = False

    # Email
    email_provider: str = "smtp"
    email_api_key: str = ""
    email_from: str = "ThreatLens <noreply@threatlens.local>"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_tls: bool = False

    # Threat intelligence
    otx_api_key: str = ""
    abuseipdb_api_key: str = ""
    virustotal_api_key: str = ""
    malwarebazaar_api_key: str = ""
    urlhaus_auth_key: str = ""

    # AI triage
    ai_api_key: str = ""
    ai_api_base: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4o-mini"

    # CORS
    cors_origins: str = "http://localhost:3000"

    @field_validator("jwt_secret", "jwt_refresh_secret")
    @classmethod
    def validate_secret_length(cls, value: str) -> str:
        if value and len(value) < 32:
            raise ValueError(
                "JWT secrets must contain at least 32 characters."
            )
        return value

    @model_validator(mode="after")
    def validate_production_security(self):
        """
        Development/demo environments may use generated development
        defaults, but production-like environments must provide real
        secrets and secure cookies.
        """

        production_like = (
            self.app_env.lower() in {"production", "staging"}
            or not self.demo_mode
        )

        if production_like:
            missing = []

            if not self.jwt_secret:
                missing.append("JWT_SECRET")

            if not self.jwt_refresh_secret:
                missing.append("JWT_REFRESH_SECRET")

            if not self.encryption_key:
                missing.append("ENCRYPTION_KEY")

            if missing:
                raise ValueError(
                    "Missing required security secrets for "
                    f"{self.app_env} environment: {', '.join(missing)}"
                )

            if len(self.jwt_secret) < 32:
                raise ValueError("JWT_SECRET must be at least 32 characters.")

            if len(self.jwt_refresh_secret) < 32:
                raise ValueError(
                    "JWT_REFRESH_SECRET must be at least 32 characters."
                )

            if len(self.encryption_key) < 32:
                raise ValueError(
                    "ENCRYPTION_KEY must be at least 32 characters."
                )

            if not self.cookie_secure:
                raise ValueError(
                    "COOKIE_SECURE must be true in production/staging."
                )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()