"""
LangGraph 全局状态定义模块。

职责：
    定义所有 Agent 共享的状态数据结构，是整个多 Agent 协作流程的"数据总线"。

设计思路：
    - TravelContext：业务领域模型，封装差旅相关的上下文信息（出发地、目的地、日期等）。
    - AgentState：LangGraph StateGraph 的全局状态，包含消息历史、意图识别结果、
      当前/下一步 Agent 标识、工具调用结果、最终响应等运行时信息。
    - 使用 Pydantic BaseModel 保证类型安全和序列化能力。

与其他模块的关系：
    - 被所有 Agent（intent_agent、query_rewriter、travel_apply_agent、itinerary_agent、
      booking_agent）作为输入/输出的状态载体。
    - 被 orchestrator 用于构建 StateGraph、初始化状态和传递结果。
"""

from __future__ import annotations

from typing import Annotated, Any
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field


class TravelContext(BaseModel):
    """差旅上下文：贯穿整个 Agent 协作流程的业务信息。

    Attributes:
        origin: 出发城市
        destination: 目的城市
        start_date: 出发日期（格式 YYYY-MM-DD）
        end_date: 返回日期（格式 YYYY-MM-DD）
        reason: 出差事由
        apply_id: 出差申请单号（由 MCP 后端生成）
        apply_status: 申请审批状态（pending / approved / rejected）
        budget_limit: 预算上限（元）
        preferences: 用户偏好（如座位类型、酒店星级等）
    """
    origin: str = ""
    destination: str = ""
    start_date: str = ""
    end_date: str = ""
    reason: str = ""
    apply_id: str = ""
    apply_status: str = ""
    budget_limit: float = 0.0
    preferences: dict[str, Any] = Field(default_factory=dict)


class AgentState(BaseModel):
    """LangGraph StateGraph 的全局状态，所有节点共享此结构。

    Attributes:
        messages: 对话消息历史，使用 LangGraph add_messages reducer 自动合并
        user_input: 当前轮次的原始用户输入
        session_id: 会话唯一标识
        user_id: 用户唯一标识

        intent: 识别到的用户意图（如 travel_apply / itinerary_query / booking）
        intent_confidence: 意图置信度 0.0~1.0
        intent_entities: 意图附带的实体信息（目的地、日期等）

        rewritten_query: 经 QueryRewriter 改写后的结构化查询

        travel_context: 差旅业务上下文

        current_agent: 当前正在执行的 Agent 名称
        next_agent: 下一步将执行的 Agent 名称

        task_plan_id: 任务计划 ID（预留）
        pending_tasks: 待执行任务列表（预留）

        tool_results: 工具调用结果集合（酒店/机票/高铁查询结果等）

        response: 最终返回给用户的文本响应
        needs_user_input: 是否需要用户补充信息
        error: 错误信息（为空表示无错误）

        events: 流式事件列表，用于 SSE/WebSocket 推送给前端
    """
    # ── 对话 & 身份 ──
    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)
    user_input: str = ""
    session_id: str = ""
    user_id: str = ""

    # ── 意图识别 ──
    intent: str = ""
    intent_confidence: float = 0.0
    intent_entities: dict[str, Any] = Field(default_factory=dict)

    # ── 查询改写 ──
    rewritten_query: str = ""

    # ── 差旅上下文 ──
    travel_context: TravelContext = Field(default_factory=TravelContext)

    # ── Agent 调度 ──
    current_agent: str = ""
    next_agent: str = ""

    # ── 任务计划（预留） ──
    task_plan_id: str = ""
    pending_tasks: list[dict[str, Any]] = Field(default_factory=list)

    # ── 工具调用结果 ──
    tool_results: list[dict[str, Any]] = Field(default_factory=list)

    # ── 响应 & 控制 ──
    response: str = ""
    needs_user_input: bool = False
    error: str = ""

    # ── 流式事件 ──
    events: list[dict[str, Any]] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True
