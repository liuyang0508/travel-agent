"""
消息模型模块：定义聊天消息、会话状态和流式推送的数据结构。

职责：
    为 API 层和 Agent 层提供统一的消息与会话数据模型。

核心概念：
    - ChatMessage：单条聊天消息，包含角色、内容、元数据和时间戳。
    - SessionState：会话状态，持有消息历史、任务计划 ID 和差旅上下文。
    - StreamChunk：SSE 流式推送给前端的数据块。

与其他模块的关系：
    - 被 api/chat 用于请求/响应的序列化。
    - 被 orchestrator 用于管理会话内的消息历史和上下文。
    - SessionState 是跨 Agent 调用的持久化载体。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """消息角色枚举。"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ChatMessage(BaseModel):
    """单条聊天消息。

    Attributes:
        message_id: 消息唯一 ID。
        session_id: 所属会话 ID。
        role: 消息角色（user / assistant / system / tool）。
        content: 消息文本内容。
        metadata: 附加元数据（如意图、置信度等）。
        timestamp: 消息创建时间。
    """
    message_id: str = ""
    session_id: str
    role: MessageRole
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class SessionState(BaseModel):
    """会话状态，贯穿整个用户对话生命周期。

    Attributes:
        session_id: 会话唯一 ID。
        user_id: 用户唯一 ID。
        messages: 消息历史列表。
        current_plan_id: 当前关联的任务计划 ID（可选）。
        context: 扩展上下文字典（存放 travel_context 等）。
        created_at: 会话创建时间。
    """
    session_id: str
    user_id: str
    messages: list[ChatMessage] = Field(default_factory=list)
    current_plan_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


class StreamChunk(BaseModel):
    """SSE 流式推送给前端的数据块。

    Attributes:
        chunk_type: 数据块类型（token / agent_event / task_update / done / error）。
        data: 具体数据载荷。
    """
    chunk_type: str
    data: dict[str, Any] = Field(default_factory=dict)
