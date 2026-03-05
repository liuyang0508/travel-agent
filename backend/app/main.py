"""
FastAPI 应用入口模块。

职责：
    创建并配置 FastAPI 应用实例，注册中间件和路由。

核心概念：
    - 使用 lifespan 管理应用的启动/关闭生命周期。
    - 通过 CORSMiddleware 开放跨域访问（开发阶段允许所有来源）。
    - 挂载三组路由：健康检查、聊天 API、任务 API。

与其他模块的关系：
    - 依赖 config 模块读取运行环境配置。
    - 依赖 api 子包（health / chat / tasks）提供具体的路由处理。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import get_settings
from app.api import chat, tasks, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 应用生命周期管理器。

    Args:
        app: FastAPI 应用实例。

    Yields:
        None: yield 前执行启动逻辑，yield 后执行关闭逻辑。
    """
    settings = get_settings()
    logger.info(f"[Main] 应用启动, 运行环境={settings.app_env}")
    yield
    logger.info("[Main] 应用关闭")


app = FastAPI(
    title="AI差旅引擎 - TravelAgent",
    description="基于 LangGraph 多智能体协作的 AI 差旅系统",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
