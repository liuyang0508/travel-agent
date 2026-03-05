"""
聊天 API 模块：提供同步、SSE 流式和 WebSocket 三种对话接口。

职责：
    接收用户消息，管理会话状态，调用 Agent 管道处理并返回响应。

设计思路：
    - POST /send：同步模式，等待 Agent 管道完成后返回完整响应。
    - POST /stream：SSE 流式模式，逐步推送 Agent 执行事件和回复 token。
    - WS /ws/{session_id}：WebSocket 双向通信模式。
    - 会话状态存储在内存字典 _sessions 中（生产环境需迁移至 Redis）。

与其他模块的关系：
    - 被 main.py 注册到 FastAPI 应用（前缀 /api/chat）。
    - 依赖 agents/orchestrator 的 run_agent_pipeline 和 stream_agent_pipeline。
    - 依赖 models/message 中的 ChatMessage、SessionState 等数据结构。
"""

from __future__ import annotations

import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel

from app.models.message import ChatMessage, MessageRole, StreamChunk, SessionState

router = APIRouter()

_sessions: dict[str, SessionState] = {}


class ChatRequest(BaseModel):
    """聊天请求体。

    Attributes:
        session_id: 会话 ID（可选，为空时自动创建新会话）。
        user_id: 用户 ID。
        message: 用户消息文本。
    """
    session_id: str | None = None
    user_id: str = "default_user"
    message: str


class ChatResponse(BaseModel):
    """聊天响应体。

    Attributes:
        session_id: 会话 ID。
        message_id: 助手回复的消息 ID。
        content: 助手回复文本。
    """
    session_id: str
    message_id: str
    content: str


def _get_or_create_session(session_id: str | None, user_id: str) -> SessionState:
    """获取已有会话或创建新会话。

    Args:
        session_id: 会话 ID（可选）。
        user_id: 用户 ID。

    Returns:
        SessionState: 会话状态实例。
    """
    if session_id and session_id in _sessions:
        return _sessions[session_id]
    sid = session_id or str(uuid.uuid4())
    session = SessionState(session_id=sid, user_id=user_id)
    _sessions[sid] = session
    logger.info(f"[Chat] 创建新会话: session_id={sid}, user_id={user_id}")
    return session


@router.post("/send", response_model=ChatResponse)
async def send_message(req: ChatRequest):
    """同步发送消息并获取完整回复。

    Args:
        req: 聊天请求体。

    Returns:
        ChatResponse: 包含助手回复的响应。
    """
    logger.info(f"[Chat] /send 收到请求, session={req.session_id}, "
                f"message={req.message[:50]}...")

    session = _get_or_create_session(req.session_id, req.user_id)
    user_msg = ChatMessage(
        message_id=str(uuid.uuid4()),
        session_id=session.session_id,
        role=MessageRole.USER,
        content=req.message,
    )
    session.messages.append(user_msg)

    from app.agents.orchestrator import run_agent_pipeline

    result = await run_agent_pipeline(session, req.message)

    assistant_msg = ChatMessage(
        message_id=str(uuid.uuid4()),
        session_id=session.session_id,
        role=MessageRole.ASSISTANT,
        content=result["response"],
        metadata=result.get("metadata", {}),
    )
    session.messages.append(assistant_msg)

    logger.info(f"[Chat] /send 响应完成, session={session.session_id}, "
                f"intent={result.get('metadata', {}).get('intent', 'N/A')}")

    return ChatResponse(
        session_id=session.session_id,
        message_id=assistant_msg.message_id,
        content=assistant_msg.content,
    )


async def _stream_agent(session: SessionState, message: str) -> AsyncGenerator[str, None]:
    """SSE 流式推送 Agent 执行过程。

    Args:
        session: 当前会话状态。
        message: 用户消息文本。

    Yields:
        str: SSE 格式的数据行。
    """
    import json
    from app.agents.orchestrator import stream_agent_pipeline

    async for event in stream_agent_pipeline(session, message):
        chunk = StreamChunk(chunk_type=event["type"], data=event.get("data", {}))
        yield f"data: {json.dumps(chunk.model_dump(), ensure_ascii=False, default=str)}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/stream")
async def stream_message(req: ChatRequest):
    """SSE 流式发送消息，逐步推送 Agent 执行事件和回复。

    Args:
        req: 聊天请求体。

    Returns:
        StreamingResponse: SSE 格式的流式响应。
    """
    logger.info(f"[Chat] /stream 收到请求, session={req.session_id}, "
                f"message={req.message[:50]}...")

    session = _get_or_create_session(req.session_id, req.user_id)
    user_msg = ChatMessage(
        message_id=str(uuid.uuid4()),
        session_id=session.session_id,
        role=MessageRole.USER,
        content=req.message,
    )
    session.messages.append(user_msg)

    return StreamingResponse(
        _stream_agent(session, req.message),
        media_type="text/event-stream",
    )


@router.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """WebSocket 双向通信聊天端点。

    Args:
        websocket: WebSocket 连接实例。
        session_id: 会话 ID。
    """
    await websocket.accept()
    session = _get_or_create_session(session_id, "ws_user")
    logger.info(f"[Chat] WebSocket 连接建立: session={session_id}")

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            logger.info(f"[Chat] WebSocket 收到消息: session={session_id}, "
                        f"message={message[:50]}...")

            user_msg = ChatMessage(
                message_id=str(uuid.uuid4()),
                session_id=session.session_id,
                role=MessageRole.USER,
                content=message,
            )
            session.messages.append(user_msg)

            from app.agents.orchestrator import stream_agent_pipeline

            async for event in stream_agent_pipeline(session, message):
                await websocket.send_json(event)

            await websocket.send_json({"type": "done"})
    except WebSocketDisconnect:
        logger.info(f"[Chat] WebSocket 断开连接: session={session_id}")
