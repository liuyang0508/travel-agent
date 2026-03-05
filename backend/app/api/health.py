"""
健康检查 API 模块。

职责：
    提供服务健康状态探测端点，供负载均衡器和监控系统使用。

与其他模块的关系：
    - 被 main.py 注册到 FastAPI 应用。
"""

from fastapi import APIRouter
from loguru import logger

router = APIRouter()


@router.get("/health")
async def health_check():
    """服务健康检查端点。

    Returns:
        dict: 包含 status 和 service 的健康状态信息。
    """
    logger.debug("[Health] 健康检查请求")
    return {"status": "ok", "service": "travel-agent"}
