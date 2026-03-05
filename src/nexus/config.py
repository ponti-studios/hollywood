import os
import secrets
from typing import Annotated, Any, Literal, Optional

from pydantic import (
    AnyUrl,
    BeforeValidator,
    HttpUrl,
    computed_field,
)
from pydantic_settings import BaseSettings

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ENV = os.environ.get("ENV", "dev")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class _Settings(BaseSettings, extra="allow"):
    API_V1_STR: str = "/api/v1"
    CI: bool | None = None
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ADMIN_TOKEN: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 60 minutes * 24 hours * 8 days = 8 days
    DOMAIN: str = "localhost"
    ENVIRONMENT: Literal["local", "staging", "production", "test"] = "local"
    SENTRY_DSN: HttpUrl | None = None

    # APIs
    OPENAI_API_KEY: str
    OPENROUTER_API_KEY: Optional[str] = None

    # Chroma
    CHROMA_AUTH_TOKEN_TRANSPORT_HEADER: str
    CHROMA_SERVER_AUTH_PROVIDER: str
    CHROMA_SERVER_AUTH_CREDENTIALS: str
    CHROMA_SERVER_HOST: str
    CHROMA_SERVER_HTTP_PORT: Optional[int] = None

    # Supabase
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def server_host(self) -> str:
        # Use HTTPS for anything other than local development
        if self.ENVIRONMENT == "local":
            return f"http://{self.DOMAIN}"
        return f"https://{self.DOMAIN}"

    BACKEND_CORS_ORIGINS: Annotated[list[AnyUrl] | str, BeforeValidator(parse_cors)] = []

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: str | None = None
    EMAILS_FROM_NAME: str | None = None

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    class Config:
        env_file = ".env"


settings = _Settings()  # type: ignore
