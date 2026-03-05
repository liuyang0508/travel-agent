"""
编排器 (Orchestrator) 模块：基于 LangGraph StateGraph 实现多 Agent 协作。

职责：
    构建并执行多 Agent 协作的状态图，是整个差旅系统的核心调度中枢。

核心路由逻辑：
    用户输入 → 意图识别 → 路由决策 → 子 Agent 执行 → 响应合成

设计思路（参照 Manus / Cursor 的 Supervisor 模式）：
    1. 控制 Agent 执行顺序 (DAG)
    2. 根据意图分发到对应 Agent
    3. 管理对话状态与上下文
    4. 聚合结果并生成最终响应

与其他模块的关系：
    - 依赖所有子 Agent（intent、query_rewriter、travel_apply、itinerary、booking）。
    - 被 api/chat 调用，提供同步 (run_agent_pipeline) 和流式 (stream_agent_pipeline) 两种执行模式。
    - 依赖 models/message.SessionState 管理会话状态。
    - 依赖 model_router.get_chat_llm 为通用对话提供 LLM。
"""

from __future__ import annotations

import time
from typing import Any, AsyncGenerator

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from loguru import logger

from app.agents.state import AgentState
from app.agents.intent_agent import intent_agent
from app.agents.query_rewriter import query_rewrite_agent
from app.agents.travel_apply_agent import travel_apply_agent
from app.agents.itinerary_agent import itinerary_agent
from app.agents.booking_agent import booking_agent
from app.engine.model_router import get_chat_llm
from app.engine.task_planner import TaskPlanner
from app.models.message import SessionState


def _route_by_intent(state: AgentState) -> str:
    """根据意图识别结果路由到对应 Agent 节点。

    Args:
        state: 全局 Agent 状态，使用 intent 和 intent_confidence 字段。

    Returns:
        str: 目标节点名称。置信度低于 0.4 时降级为 general_chat。
    """
    intent = state.intent
    confidence = state.intent_confidence

    # 置信度过低时直接走通用对话，避免误路由
    if confidence < 0.4:
        logger.info(f"[Orchestrator] 置信度过低({confidence:.2f})，降级为通用对话")
        return "general_chat"

    route_map = {
        "travel_apply": "travel_apply",
        "itinerary_query": "query_rewrite",
        "travel_status": "travel_apply",
        "booking": "booking",
        "general_chat": "general_chat",
        "unclear": "general_chat",
    }
    target = route_map.get(intent, "general_chat")
    logger.info(f"[Orchestrator] 路由决策: intent={intent} → {target}")
    return target


async def general_chat_agent(state: AgentState) -> dict:
    """通用对话 Agent：处理非差旅相关的闲聊和兜底回复。

    Args:
        state: 全局 Agent 状态。

    Returns:
        dict: 包含 response 和 current_agent 字段的状态更新。
    """
    logger.info("[Orchestrator] 进入通用对话处理")
    llm = get_chat_llm()

    ctx = state.travel_context
    context_parts = []
    if ctx.destination:
        context_parts.append(f"目的地: {ctx.destination}")
    if ctx.apply_id:
        context_parts.append(f"申请ID: {ctx.apply_id} ({ctx.apply_status})")

    system_msg = (
        "你是「差旅通」，一个智能差旅助手。"
        "如果用户提到出差、旅行、出行相关话题，引导他们使用差旅服务。"
        "保持友好、专业、简洁。使用中文回复。"
    )
    if context_parts:
        system_msg += f"\n\n当前差旅上下文: {', '.join(context_parts)}"

    messages = [{"role": "system", "content": system_msg}]
    for m in state.messages[-8:]:
        if hasattr(m, "type"):
            messages.append({"role": m.type, "content": m.content})

    result = await llm.ainvoke(messages)

    return {
        "response": result.content,
        "current_agent": "general_chat",
    }


def build_graph() -> StateGraph:
    """构建 LangGraph 状态图，定义所有节点和边。

    Returns:
        StateGraph: 未编译的状态图实例。

    图结构：
        intent_recognition → (条件路由) → travel_apply / query_rewrite / booking / general_chat
        query_rewrite → itinerary
        所有叶子节点 → END
    """
    logger.info("[Orchestrator] 构建 LangGraph 状态图")
    graph = StateGraph(AgentState)

    graph.add_node("intent_recognition", intent_agent)
    graph.add_node("query_rewrite", query_rewrite_agent)
    graph.add_node("travel_apply", travel_apply_agent)
    graph.add_node("itinerary", itinerary_agent)
    graph.add_node("booking", booking_agent)
    graph.add_node("general_chat", general_chat_agent)

    graph.set_entry_point("intent_recognition")

    graph.add_conditional_edges(
        "intent_recognition",
        _route_by_intent,
        {
            "travel_apply": "travel_apply",
            "query_rewrite": "query_rewrite",
            "booking": "booking",
            "general_chat": "general_chat",
        },
    )

    graph.add_edge("query_rewrite", "itinerary")

    graph.add_edge("travel_apply", END)
    graph.add_edge("itinerary", END)
    graph.add_edge("booking", END)
    graph.add_edge("general_chat", END)

    return graph


_compiled_graph = None


def get_graph():
    """获取编译后的状态图单例（延迟编译）。

    Returns:
        编译后的 LangGraph 可执行图。
    """
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph().compile()
        logger.info("[Orchestrator] 状态图编译完成")
    return _compiled_graph


async def run_agent_pipeline(session: SessionState, user_input: str) -> dict[str, Any]:
    """同步执行 Agent 管道（非流式），返回最终结果。

    Args:
        session: 当前会话状态，包含历史消息和上下文。
        user_input: 用户本轮输入文本。

    Returns:
        dict: 包含 response（回复文本）和 metadata（意图、置信度、Agent 名称）。
    """
    logger.info(f"[Orchestrator] run_agent_pipeline 开始, session={session.session_id}, "
                f"input={user_input[:50]}...")
    t0 = time.time()

    graph = get_graph()

    messages = []
    for msg in session.messages[-10:]:
        if msg.role.value == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role.value == "assistant":
            messages.append(AIMessage(content=msg.content))

    initial_state = AgentState(
        messages=messages,
        user_input=user_input,
        session_id=session.session_id,
        user_id=session.user_id,
        travel_context=session.context.get("travel_context", AgentState().travel_context),
    )

    result = await graph.ainvoke(initial_state)

    if "travel_context" in result:
        session.context["travel_context"] = result["travel_context"]

    elapsed = time.time() - t0
    logger.info(f"[Orchestrator] run_agent_pipeline 完成, 耗时={elapsed:.2f}s, "
                f"intent={result.get('intent')}, agent={result.get('current_agent')}")

    return {
        "response": result.get("response") or "抱歉，我暂时无法处理这个请求。",
        "metadata": {
            "intent": result.get("intent", ""),
            "confidence": result.get("intent_confidence", 0.0),
            "agent": result.get("current_agent", ""),
        },
    }


async def stream_agent_pipeline(
    session: SessionState, user_input: str
) -> AsyncGenerator[dict[str, Any], None]:
    """流式执行 Agent 管道，逐步产出事件供 SSE/WebSocket 推送。

    Args:
        session: 当前会话状态。
        user_input: 用户本轮输入文本。

    Yields:
        dict: 包含 type 和 data 的事件字典，类型包括
              agent_event（思考/工具调用）、token（流式文本）、done（结束标志）。
    """
    logger.info(f"[Orchestrator] stream_agent_pipeline 开始, session={session.session_id}")
    t0 = time.time()

    graph = get_graph()

    messages = []
    for msg in session.messages[-10:]:
        if msg.role.value == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role.value == "assistant":
            messages.append(AIMessage(content=msg.content))

    travel_ctx_data = session.context.get("travel_context")
    if isinstance(travel_ctx_data, dict):
        from app.agents.state import TravelContext
        travel_ctx = TravelContext(**travel_ctx_data)
    elif travel_ctx_data is not None:
        travel_ctx = travel_ctx_data
    else:
        travel_ctx = AgentState().travel_context

    initial_state = AgentState(
        messages=messages,
        user_input=user_input,
        session_id=session.session_id,
        user_id=session.user_id,
        travel_context=travel_ctx,
    )

    yield {
        "type": "agent_event",
        "data": {
            "event_type": "thinking",
            "agent_role": "orchestrator",
            "content": "正在分析您的需求...",
            "session_id": session.session_id,
        },
    }

    task_planner = TaskPlanner()
    plan_yielded = False
    seen_event_count = 0

    final_state = None
    async for event in graph.astream(initial_state, stream_mode="values"):
        final_state = event

        current_events = []
        if isinstance(event, dict) and "events" in event:
            current_events = event["events"]
        elif hasattr(event, "events"):
            current_events = list(event.events)

        new_events = current_events[seen_event_count:]
        seen_event_count = len(current_events)

        current_agent = event.get("current_agent") if isinstance(event, dict) else getattr(event, "current_agent", "")
        intent = event.get("intent", "") if isinstance(event, dict) else getattr(event, "intent", "")

        if intent and not plan_yielded:
            try:
                ctx_data = {}
                travel_ctx = event.get("travel_context") if isinstance(event, dict) else getattr(event, "travel_context", None)
                if travel_ctx is not None:
                    ctx_data = travel_ctx.model_dump() if hasattr(travel_ctx, "model_dump") else travel_ctx
                plan = await task_planner.create_plan(session.session_id, intent, ctx_data)
                if plan:
                    yield {
                        "type": "task_update",
                        "data": {"plan": plan.model_dump() if hasattr(plan, "model_dump") else plan},
                    }
                    plan_yielded = True
            except Exception as e:
                logger.warning(f"[Orchestrator] 创建任务计划失败: {e}")

        for ev in new_events:
            yield ev

    if final_state:
        travel_ctx = final_state.get("travel_context") if isinstance(final_state, dict) else getattr(final_state, "travel_context", None)
        if travel_ctx is not None:
            if hasattr(travel_ctx, "model_dump"):
                session.context["travel_context"] = travel_ctx.model_dump()
            elif isinstance(travel_ctx, dict):
                session.context["travel_context"] = travel_ctx

        response = (final_state.get("response") if isinstance(final_state, dict) else getattr(final_state, "response", None)) or "抱歉，我暂时无法处理这个请求。"

        # 模拟流式输出，每次推送 20 字符
        for i in range(0, len(response), 20):
            yield {
                "type": "token",
                "data": {"token": response[i:i+20]},
            }

    elapsed = time.time() - t0
    logger.info(f"[Orchestrator] stream_agent_pipeline 完成, 耗时={elapsed:.2f}s")

    yield {"type": "done", "data": {}}
