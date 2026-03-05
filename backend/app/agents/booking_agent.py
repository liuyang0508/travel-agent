"""
预订执行 Agent 模块。

职责：
    执行酒店/机票/高铁的实际预订操作。

设计思路：
    - 从意图实体中提取预订类型（hotel/flight/train）和预订 ID。
    - 通过 tool_map 映射到对应的 MCP 工具名称。
    - 缺少必要信息时提示用户补充。
    - 预订失败时返回友好的错误提示。

与其他模块的关系：
    - 由 orchestrator 在意图为 booking 时路由至此。
    - 依赖 mcp/client 调用后端预订服务。
    - 通常在 itinerary_agent 查询出行程方案后，用户选择具体选项后触发。
"""

from __future__ import annotations

from loguru import logger

from app.agents.state import AgentState


async def booking_agent(state: AgentState) -> dict:
    """执行预订操作，支持酒店、机票、高铁三种类型。

    Args:
        state: 全局 Agent 状态，主要使用 intent_entities 中的
               booking_type 和 booking_id。

    Returns:
        dict: 包含 response、events 等字段的状态更新。
              缺少参数时返回追问提示；预订失败时返回错误信息。
    """
    logger.info(f"[BookingAgent] 开始处理预订, entities={state.intent_entities}")

    from app.mcp.client import MCPClient
    mcp = MCPClient()

    booking_type = state.intent_entities.get("booking_type", "")
    booking_id = state.intent_entities.get("booking_id", "")

    if not booking_type or not booking_id:
        logger.info("[BookingAgent] 缺少预订类型或预订ID，请求用户补充")
        return {
            "response": "请告诉我您想预订哪个选项？（请提供具体的航班号/车次/酒店名称）",
            "needs_user_input": True,
            "current_agent": "booking",
        }

    tool_map = {
        "hotel": "book_hotel",
        "flight": "book_flight",
        "train": "book_train",
    }
    tool_name = tool_map.get(booking_type)

    if not tool_name:
        logger.warning(f"[BookingAgent] 不支持的预订类型: {booking_type}")
        return {
            "response": f"不支持的预订类型: {booking_type}",
            "current_agent": "booking",
        }

    try:
        logger.info(f"[BookingAgent] 调用 MCP 工具 {tool_name}, booking_id={booking_id}")
        result = await mcp.call_tool(tool_name, {
            "booking_id": booking_id,
            "user_id": state.user_id,
            "apply_id": state.travel_context.apply_id,
        })

        order_id = result.get("order_id", "N/A")
        logger.info(f"[BookingAgent] 预订成功, order_id={order_id}")
        return {
            "response": f"预订成功！订单号: {order_id}\n\n预订详情已发送到您的钉钉消息。",
            "current_agent": "booking",
            "events": state.events + [{
                "type": "agent_event",
                "data": {
                    "event_type": "tool_result",
                    "agent_role": "booking",
                    "content": f"预订成功，订单号: {order_id}",
                },
            }, {
                "type": "structured_data",
                "data": {
                    "card_type": "booking_result",
                    "items": [result],
                },
            }],
        }
    except Exception as e:
        logger.error(f"[BookingAgent] 预订失败: {e}", exc_info=True)
        return {
            "response": f"预订失败: {e}。请稍后重试或联系管理员。",
            "error": str(e),
        }
