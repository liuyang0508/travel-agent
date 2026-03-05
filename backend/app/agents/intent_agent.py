"""
意图识别 Agent 模块。

职责：
    分析用户输入消息，判断差旅相关意图并提取关键实体。

设计思路：
    - 调用轻量级 LLM（通过 model_router 获取）完成意图分类。
    - 使用 INTENT_RECOGNITION_PROMPT 模板引导 LLM 输出结构化 JSON。
    - 截取最近 10 条消息作为上下文，平衡准确率与 token 消耗。
    - 解析失败时降级为 general_chat，保证流程不中断。

与其他模块的关系：
    - 是 orchestrator 状态图的入口节点，所有请求首先经过意图识别。
    - 输出的 intent 字段决定 orchestrator 的路由走向。
    - 依赖 state.AgentState 作为输入/输出载体。
    - 依赖 model_router.get_intent_llm 获取模型实例。
    - 依赖 prompt_engine.INTENT_RECOGNITION_PROMPT 获取提示词模板。
"""

from __future__ import annotations

import json
from langchain_core.messages import HumanMessage, AIMessage
from loguru import logger

from app.agents.state import AgentState
from app.engine.model_router import get_intent_llm
from app.engine.prompt_engine import INTENT_RECOGNITION_PROMPT


async def intent_agent(state: AgentState) -> dict:
    """识别用户意图并提取实体。

    Args:
        state: 全局 Agent 状态，主要使用 user_input 和 messages 字段。

    Returns:
        dict: 包含 intent、intent_confidence、intent_entities 等字段的状态更新。
              解析失败时降级返回 general_chat 意图。

    核心流程：
        1. 获取意图识别专用 LLM
        2. 截取最近对话历史
        3. 调用 LLM 链获取结构化意图结果
        4. 解析 JSON 响应并返回状态更新
    """
    logger.info(f"[IntentAgent] 开始分析用户输入: {state.user_input[:50]}...")

    # 获取意图识别专用的轻量级 LLM
    llm = get_intent_llm()
    chain = INTENT_RECOGNITION_PROMPT | llm

    # 截取最近 10 条消息作为上下文，避免 token 超限
    chat_history = state.messages[-10:] if len(state.messages) > 10 else state.messages

    try:
        # 调用 LLM 进行意图识别
        result = await chain.ainvoke({
            "input": state.user_input,
            "chat_history": chat_history,
        })

        # 解析 LLM 返回的 JSON 结构
        parsed = _parse_intent_result(result.content)

        logger.info(f"[IntentAgent] 识别结果 intent={parsed['intent']}, confidence={parsed['confidence']:.2f}")

        entities = parsed.get("entities", {})
        try:
            updated_ctx = _merge_entities_to_context(state.travel_context, entities)
        except Exception as merge_err:
            logger.warning(f"[IntentAgent] 实体合并失败，跳过: {merge_err}")
            updated_ctx = state.travel_context

        return {
            "intent": parsed["intent"],
            "intent_confidence": parsed["confidence"],
            "intent_entities": entities,
            "travel_context": updated_ctx,
            "current_agent": "intent",
            "events": state.events + [{
                "type": "agent_event",
                "data": {
                    "event_type": "thinking",
                    "agent_role": "intent",
                    "content": f"识别意图: {parsed['intent']} (置信度: {parsed['confidence']:.0%})",
                },
            }],
        }
    except Exception as e:
        logger.error(f"[IntentAgent] 意图识别异常: {e}", exc_info=True)
        # 降级为通用闲聊，保证流程不中断
        return {
            "intent": "general_chat",
            "intent_confidence": 0.5,
            "error": str(e),
        }


def _merge_entities_to_context(ctx, entities):
    """将意图识别提取的实体合并到 travel_context 中。

    只更新非空实体，不覆盖已有的非空字段。
    """
    if not isinstance(entities, dict):
        return ctx

    update_fields = {}
    field_map = {
        "destination": "destination",
        "origin": "origin",
        "start_date": "start_date",
        "end_date": "end_date",
        "reason": "reason",
    }
    for entity_key, ctx_field in field_map.items():
        value = entities.get(entity_key, "")
        if value and isinstance(value, str) and not getattr(ctx, ctx_field, ""):
            update_fields[ctx_field] = value

    if update_fields:
        logger.info(f"[IntentAgent] 合并实体到上下文: {update_fields}")
        return ctx.model_copy(update=update_fields)
    return ctx


def _parse_intent_result(content: str) -> dict:
    """解析 LLM 返回的意图识别结果 JSON。

    Args:
        content: LLM 原始输出文本，可能包含 markdown 代码块包裹。

    Returns:
        dict: 包含 intent、confidence、entities、reasoning 字段。
              JSON 解析失败时返回 general_chat 降级结果。
    """
    # 去除可能的 markdown 代码块包裹
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        logger.warning(f"[IntentAgent] JSON 解析失败，降级为 general_chat，原始内容: {content[:100]}")
        return {
            "intent": "general_chat",
            "confidence": 0.3,
            "entities": {},
            "reasoning": "Failed to parse LLM response",
        }
