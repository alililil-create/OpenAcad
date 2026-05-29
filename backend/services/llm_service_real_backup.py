import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 全局单例
_llm_service = None


async def get_llm_service():
    """
    获取LLM服务（自动根据模式选择）
    
    - MODE=mock: 返回Mock服务（模拟数据）
    - MODE=production: 返回真实API服务
    """
    global _llm_service
    
    if _llm_service is None:
        from config import settings
        
        if settings.MODE == "mock":
            # 使用Mock模式
            from services.mock_llm_service import get_llm_service as get_mock
            _llm_service = await get_mock()
            logger.info("[LLM] 🎭 使用 Mock 模式")
        else:
            # 使用生产模式（真实AI）
            from services.llm_service_real import get_llm_service as get_real
            _llm_service = await get_real()
            logger.info("[LLM] 🤖 使用 Production 模式")
    
    return _llm_service


# 为了向后兼容，保留原来的导入方式
__all__ = ['get_llm_service']
