"""
Redis 缓存层 - 画像缓存 + 会话管理
禁用时自动降级为空操作，不影响功能
"""

import json
import logging
from redis.asyncio import Redis
from database.connection import get_redis

logger = logging.getLogger(__name__)


class CacheService:
    """Redis 缓存服务"""

    # 缓存 Key 前缀
    PROFILE_PREFIX = "profile:"
    SESSION_PREFIX = "session:"
    RATE_LIMIT_PREFIX = "rate:"

    # 过期时间
    PROFILE_TTL = 3600    # 画像缓存1小时
    SESSION_TTL = 1800    # 会话缓存30分钟
    RATE_TTL = 60         # 限流窗口1分钟

    @staticmethod
    def _get_redis() -> Redis | None:
        return get_redis()

    # ===== 画像缓存 =====

    @staticmethod
    async def cache_profile(user_id: int, profile_data: dict) -> None:
        """缓存学生画像"""
        r = CacheService._get_redis()
        if r is None:
            return
        key = f"{CacheService.PROFILE_PREFIX}{user_id}"
        try:
            await r.setex(key, CacheService.PROFILE_TTL, json.dumps(profile_data, ensure_ascii=False))
            logger.debug(f"[Cache] 画像已缓存 user_id={user_id}")
        except Exception as e:
            logger.warning(f"[Cache] 画像缓存失败: {e}")

    @staticmethod
    async def get_cached_profile(user_id: int) -> dict | None:
        """获取缓存的画像"""
        r = CacheService._get_redis()
        if r is None:
            return None
        key = f"{CacheService.PROFILE_PREFIX}{user_id}"
        try:
            data = await r.get(key)
            if data:
                logger.debug(f"[Cache] 画像命中 user_id={user_id}")
                return json.loads(data)
        except Exception as e:
            logger.warning(f"[Cache] 画像读取失败: {e}")
        return None

    @staticmethod
    async def invalidate_profile(user_id: int) -> None:
        """清除画像缓存"""
        r = CacheService._get_redis()
        if r is None:
            return
        key = f"{CacheService.PROFILE_PREFIX}{user_id}"
        try:
            await r.delete(key)
        except Exception:
            pass

    # ===== 会话上下文缓存 =====

    @staticmethod
    async def cache_session_context(thread_id: str, context: dict) -> None:
        """缓存会话上下文（包含历史消息摘要）"""
        r = CacheService._get_redis()
        if r is None:
            return
        key = f"{CacheService.SESSION_PREFIX}{thread_id}"
        try:
            await r.setex(key, CacheService.SESSION_TTL, json.dumps(context, ensure_ascii=False))
        except Exception as e:
            logger.warning(f"[Cache] 会话缓存失败: {e}")

    @staticmethod
    async def get_session_context(thread_id: str) -> dict | None:
        """获取会话上下文"""
        r = CacheService._get_redis()
        if r is None:
            return None
        key = f"{CacheService.SESSION_PREFIX}{thread_id}"
        try:
            data = await r.get(key)
            if data:
                return json.loads(data)
        except Exception:
            pass
        return None

    # ===== 热点数据缓存 =====

    @staticmethod
    async def cache_json(key: str, data: dict, ttl: int = 300) -> None:
        """通用 JSON 缓存"""
        r = CacheService._get_redis()
        if r is None:
            return
        try:
            await r.setex(key, ttl, json.dumps(data, ensure_ascii=False))
        except Exception:
            pass

    @staticmethod
    async def get_json(key: str) -> dict | None:
        """通用 JSON 读取"""
        r = CacheService._get_redis()
        if r is None:
            return None
        try:
            data = await r.get(key)
            return json.loads(data) if data else None
        except Exception:
            return None