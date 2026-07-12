"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from typing import Optional


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
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # === 感知层加密（T01 新增） ===
    FERNET_KEY: Optional[str] = None  # 逗号分隔 = MultiFernet 轮换

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

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

<<<<<<< HEAD
    # === Agent Resource Platform (T44) ===
=======
    # === Opencode Config Discovery (T46) ===
>>>>>>> blueprint/46-opencode-discovery
    OPENCODE_CONFIG_PATH: str = "~/.config/opencode"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
