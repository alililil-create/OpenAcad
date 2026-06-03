from sqlalchemy.ext.asyncio import (
    create_async_engine, async_sessionmaker, AsyncSession
)
from redis import asyncio as aioredis
from redis.asyncio import Redis
import logging
from database.models import Base

logger = logging.getLogger(__name__)

# ===== 全局连接实例 =====
_async_engine = None
_async_session_factory = None
_redis_client: Redis | None = None


# ===== PostgreSQL 连接 =====

async def init_db(database_url: str) -> None:
    """初始化数据库连接并创建表"""
    global _async_engine, _async_session_factory

    logger.info(f"[DB] 连接数据库: {database_url[:50]}...")

    _async_engine = create_async_engine(
        database_url,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

    _async_session_factory = async_sessionmaker(
        _async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    # 自动建表（开发环境）
    async with _async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("[DB] 数据库初始化完成，所有表已创建")


async def close_db() -> None:
    """关闭数据库连接"""
    global _async_engine

    if _async_engine:
        await _async_engine.dispose()
        _async_engine = None
        logger.info("[DB] 数据库连接已关闭")


async def get_db_session() -> AsyncSession:
    """获取数据库会话（依赖注入用）"""
    if _async_session_factory is None:
        raise RuntimeError("[DB] 数据库未初始化，请先调用 init_db()")

    async with _async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


def get_session_factory():
    """获取session工厂（路由层直接使用）"""
    return _async_session_factory


# 直接获取 session 实例（非依赖注入场景）
AsyncSessionLocal = get_db_session


# ===== Redis 连接 =====

async def init_redis(redis_url: str) -> Redis:
    """初始化Redis连接（失败时降级为内存缓存）"""
    global _redis_client

    logger.info(f"[Redis] 连接: {redis_url}")

    try:
        _redis_client = aioredis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
            socket_timeout=5,
            socket_connect_timeout=5,
        )

        # 连接测试
        await _redis_client.ping()
        logger.info("[Redis] 连接成功")
        return _redis_client
    except Exception as e:
        logger.warning(f"[Redis] 连接失败（降级为内存缓存）: {e}")
        _redis_client = None
        return None


async def close_redis() -> None:
    """关闭Redis连接"""
    global _redis_client

    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("[Redis] 连接已关闭")


def get_redis() -> Redis | None:
    """获取Redis客户端"""
    return _redis_client