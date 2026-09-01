"""Application configuration loaded from environment variables.

2026-08-03 深度精简：项目只剩 AIDE + 用户管理，原来五层业务域 / 专家团 /
算力调度 / 数据平台 / 知识库 / Agent Looper 的配置项已全部删除。
"""

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

    # JWT Auth
    SECRET_KEY: str = DEFAULT_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS — 加前端端口时改这里
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:5176",
        "http://127.0.0.1:5176",
        "http://localhost:3000",
    ]

    # === AIDE / opencode ===
    # AIDE 页面 iframe 嵌入 opencode Web UI。
    # opencode ≥ 1.18 的 `serve` 已内置 Web UI，默认复用 4096；
    # 老版本 serve 无 UI 时后端会拉起独立 `opencode web`（4097）兜底。
    OPENCODE_HOST: str = "127.0.0.1"
    OPENCODE_PORT: int = 4096       # serve（优先复用）
    OPENCODE_WEB_PORT: int = 4097   # 独立 web（兜底）

    # === DeepSeek Harness（会话插件，不是 Web UI）===
    # 指向 deepseek-harness 源码检出。空则尝试同级目录 ../deepseek-harness
    DSH_REPO: str = ""

    # === DataOps · Doris 默认数据源（可选种子，勿把密码提交进 git）===
    DORIS_SOURCE_NAME: str = "Doris 数仓"
    DORIS_HOST: str = ""
    DORIS_PORT: int = 9030
    DORIS_USER: str = "root"
    DORIS_PASSWORD: str = ""
    DORIS_DATABASE: str = ""
    DORIS_CHARSET: str = "utf8mb4"

    # === LLM（元数据标注 / 本体生成，OpenAI 兼容端点）===
    LLM_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = ""
    LLM_TIMEOUT: int = 120
    LLM_MAX_CONCURRENCY: int = 4

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        # 忽略 .env 里的历史遗留项（如已删模块的 FERNET_KEY / REDIS_URL /
        # OPENAI_API_KEY / AGENT_CONFIG_PATH 等），避免启动时报 extra_forbidden
        "extra": "ignore",
    }


settings = Settings()


def validate_production_security(config: Settings = settings) -> None:
    """Fail startup when production is using a missing/default SECRET_KEY."""
    if config.ENVIRONMENT.strip().lower() not in {"production", "prod"}:
        return

    if not config.SECRET_KEY or config.SECRET_KEY == DEFAULT_SECRET_KEY:
        raise RuntimeError(
            "生产环境安全配置校验失败: SECRET_KEY 仍为默认值"
            "（用 `openssl rand -hex 32` 生成后写进 .env）"
        )


__all__ = [
    "DEFAULT_SECRET_KEY",
    "Settings",
    "settings",
    "validate_production_security",
]
