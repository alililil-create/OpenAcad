from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    """应用配置 - 从环境变量读取"""

    # 应用基础配置
    APP_NAME: str = "ML Learning Agent System"
    DEBUG: bool = True
    VERSION: str = "1.0.0"

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # 运行模式
    MODE: str = "mock"  # mock 或 production

    # 讯飞星火配置【备用】
    XUNFEI_API_KEY: str = ""
    XUNFEI_APP_ID: str = ""
    XUNFEI_API_SECRET: str = ""
    XUNFEI_API_PASSWORD: str = ""

    # LLM 提供商
    LLM_PROVIDER: str = "spark"  # spark / deepseek / qwen
    LLM_MODEL: str = "spark-x"

    # DeepSeek 配置 (支持火山方舟等第三方平台)
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"

    # 阿里云通义千问配置
    QWEN_API_KEY: str = ""
    QWEN_MODEL: str = "qwen-plus"

    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./ml_learning.db"
    DB_ENGINE: str = "postgresql"  # postgresql 或 sqlite
    PG_HOST: str = "localhost"
    PG_PORT: int = 5432
    PG_USER: str = "ml_learning"
    PG_PASSWORD: str = ""
    PG_DATABASE: str = "ml_learning"

    # Redis 配置
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_ENABLED: bool = False

    # Milvus 向量数据库配置
    MILVUS_URI: str = "http://localhost:19530"
    MILVUS_ENABLED: bool = True

    # MinIO OSS 配置
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    MINIO_ENABLED: bool = True

    # JWT认证配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # CORS配置
    CORS_ORIGINS: list = ["http://localhost:3000", "http://127.0.0.1:5500", "*"]

    class Config:
        _base_dir = Path(__file__).resolve().parent.parent
        env_file = _base_dir / ".env"
        case_sensitive = True


settings = Settings()


def get_settings() -> Settings:
    return settings


# 调试输出
if settings.DEBUG:
    print(f"[Config] OK config loaded")
    print(f"[Config] MODE: {settings.MODE.upper()}")

    if settings.MODE == "mock":
        print(f"[Config] Using MOCK mode (simulated data)")
    else:
        print(f"[Config] Using PRODUCTION mode (real AI)")
        if settings.QWEN_API_KEY:
            print(f"[Config] Qwen Key: {settings.QWEN_API_KEY[:10]}...")
