"""Application configuration loaded from environment variables."""

from cryptography.fernet import Fernet
from pydantic_settings import BaseSettings
from typing import Optional


DEFAULT_SECRET_KEY = "change-me-in-production-use-openssl-rand-hex-32"


class Settings(BaseSettings):
    """Central configuration for the OntoMind backend."""

    # App
    APP_NAME: str = "OntoMind"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database (MySQL)
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "ontomind"
    DB_PASSWORD: str = "ontomind_secret"
    DB_NAME: str = "ontomind"
    DATABASE_URL: Optional[str] = None

    @property
    def db_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT Auth
    SECRET_KEY: str = DEFAULT_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # === 感知层加密（T01 新增） ===
    FERNET_KEY: Optional[str] = None  # 逗号分隔 = MultiFernet 轮换

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    # AI / LLM
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = None
    LLM_MODEL: str = "gpt-4o"

    # File Upload
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # === Agent Looper (T34/T35/T36) ===
    AGENT_CONFIG_PATH: str = "~/.config/opencode/agents"
    AGENT_LOOPER_TEST_RUNS_TTL_DAYS: int = 30

    # === Agent Resource Platform (T44) / Opencode Config Discovery (T46) ===
    OPENCODE_CONFIG_PATH: str = "~/.config/opencode"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()


def validate_production_security(config: Settings = settings) -> None:
    """Fail startup when production is using missing/default security keys."""
    if config.ENVIRONMENT.strip().lower() not in {"production", "prod"}:
        return

    errors: list[str] = []
    if not config.SECRET_KEY or config.SECRET_KEY == DEFAULT_SECRET_KEY:
        errors.append("SECRET_KEY 仍为默认值")

    raw_fernet = (config.FERNET_KEY or "").strip()
    if not raw_fernet:
        errors.append("FERNET_KEY 未配置")
    else:
        try:
            keys = [part.strip() for part in raw_fernet.split(",") if part.strip()]
            if not keys:
                raise ValueError("no Fernet keys")
            for key in keys:
                Fernet(key.encode("ascii"))
        except (ValueError, TypeError):
            errors.append("FERNET_KEY 格式无效")

    if errors:
        raise RuntimeError("生产环境安全配置校验失败: " + "；".join(errors))


__all__ = [
    "DEFAULT_SECRET_KEY",
    "Settings",
    "settings",
    "validate_production_security",
]
