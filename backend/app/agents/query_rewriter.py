"""
查询改写 Agent 模块。

职责：
    将用户的模糊、口语化查询改写为结构化、明确的查询，
    同时从对话上下文中解析并补全差旅实体（目的地、日期等）。

设计思路：
    - 使用 QUERY_REWRITE_PROMPT 模板引导 LLM 输出改写后的查询和解析出的实体。
    - 截取最近 6 条消息作为上下文（改写不需要太长历史）。
    - 将解析出的实体合并到 TravelContext 中，供下游 Agent 使用。
    - 解析失败时回退使用原始输入，保证流程不中断。

与其他模块的关系：
    - 在 orchestrator 中位于意图识别之后、行程规划之前。
    - 当意图为 itinerary_query 时，由 orchestrator 路由至本模块。
    - 改写后的查询和更新的 travel_context 传递给 itinerary_agent 使用。
    - 依赖 state.AgentState 作为输入/输出载体。
"""

from __future__ import annotations

import json
from loguru import logger

from app.agents.state import AgentState
from app.engine.model_router import get_intent_llm
from app.engine.prompt_engine import QUERY_REWRITE_PROMPT


async def query_rewrite_agent(state: AgentState) -> dict:
    """基于对话上下文改写用户查询，并提取差旅实体。

    Args:
        state: 全局 Agent 状态，主要使用 user_input、messages、travel_context。

    Returns:
        dict: 包含 rewritten_query、travel_context 等字段的状态更新。
              失败时回退使用原始 user_input。

    核心流程：
        1. 调用 LLM 对用户查询进行改写和实体提取
        2. 将提取的实体（目的地、出发地、日期）合并到 TravelContext
        3. 返回改写后的查询和更新的上下文
    """
    logger.info(f"[QueryRewriter] 开始改写查询: {state.user_input[:50]}...")

    llm = get_intent_llm()
    chain = QUERY_REWRITE_PROMPT | llm

    # 改写只需最近 6 条消息，减少 token 消耗
    chat_history = state.messages[-6:] if len(state.messages) > 6 else state.messages

    try:
        result = await chain.ainvoke({
            "input": state.user_input,
            "chat_history": chat_history,
        })

        parsed = _parse_rewrite(result.content)
        rewritten = parsed.get("rewritten_query", state.user_input)

        # 从改写结果中提取差旅实体，合并到上下文
        entities = parsed.get("resolved_entities", {})
        travel_ctx_updates = {}
        if entities.get("destination"):
            travel_ctx_updates["destination"] = entities["destination"]
        if entities.get("origin"):
            travel_ctx_updates["origin"] = entities["origin"]
        if entities.get("start_date"):
            travel_ctx_updates["start_date"] = entities["start_date"]
        if entities.get("end_date"):
            travel_ctx_updates["end_date"] = entities["end_date"]

        # 使用 model_copy 不可变更新，保留原有字段
        updated_context = state.travel_context.model_copy(update=travel_ctx_updates)

        logger.info(f"[QueryRewriter] 改写完成: {rewritten[:80]}")
        if travel_ctx_updates:
            logger.info(f"[QueryRewriter] 提取到实体: {travel_ctx_updates}")

        return {
            "rewritten_query": rewritten,
            "travel_context": updated_context,
            "current_agent": "query_rewriter",
            "events": state.events + [{
                "type": "agent_event",
                "data": {
                    "event_type": "thinking",
                    "agent_role": "query_rewriter",
                    "content": f"查询改写: {rewritten[:60]}",
                },
            }],
        }
    except Exception as e:
        logger.error(f"[QueryRewriter] 查询改写异常: {e}", exc_info=True)
        return {"rewritten_query": state.user_input}


def _parse_rewrite(content: str) -> dict:
    """解析 LLM 返回的查询改写结果 JSON。

    Args:
        content: LLM 原始输出文本，可能包含 markdown 代码块包裹。

    Returns:
        dict: 包含 rewritten_query 和 resolved_entities 字段。
              JSON 解析失败时将原始内容作为改写结果返回。
    """
    content = content.strip()
    # 去除可能的 markdown 代码块包裹
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        logger.warning(f"[QueryRewriter] JSON 解析失败，使用原始内容: {content[:100]}")
        return {"rewritten_query": content}
