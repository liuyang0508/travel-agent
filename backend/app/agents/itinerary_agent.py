"""
行程规划 Agent 模块。

职责：
    并行查询酒店/机票/高铁资源，组合成完整行程方案推荐给用户确认。

设计思路：
    - 先校验必要的差旅上下文（目的地、日期），缺失时提示用户补充。
    - 使用 asyncio.gather 并行查询三类资源，提升响应速度。
    - 单个查询失败时降级为空列表，不阻塞整体流程。
    - 从查询结果中挑选最优组合（交通+酒店），生成推荐行程方案。
    - 将完整方案展示给用户，等待用户确认后再进入预订流程。

与其他模块的关系：
    - 由 orchestrator 在 query_rewrite 之后路由至此。
    - 依赖 mcp/client 调用后端酒店/机票/高铁查询服务。
    - 依赖 model_router.get_planning_llm 获取规划模型。
    - 依赖 prompt_engine.TRAVEL_PLANNING_PROMPT 获取提示词模板。
"""

from __future__ import annotations

import asyncio
import time
from datetime import date, timedelta
from loguru import logger

from app.agents.state import AgentState
from app.engine.model_router import get_planning_llm
from app.engine.prompt_engine import TRAVEL_PLANNING_PROMPT


async def itinerary_agent(state: AgentState) -> dict:
    """并行查询交通和住宿资源，组合推荐方案并等待用户确认。

    Args:
        state: 全局 Agent 状态，主要使用 travel_context 中的目的地、日期等。

    Returns:
        dict: 包含 response、tool_results、events 等字段的状态更新。
              缺少必要信息时返回追问提示；方案就绪时等待用户确认。
    """
    logger.info(f"[ItineraryAgent] 开始规划行程, 目的地={state.travel_context.destination}")

    ctx = state.travel_context
    if not ctx.destination:
        logger.info("[ItineraryAgent] 缺少目的地，请求用户补充")
        return {
            "response": "请先告诉我您的目的地，我来帮您规划行程。",
            "needs_user_input": True,
            "current_agent": "itinerary",
        }

    if not ctx.start_date:
        default_date = (date.today() + timedelta(days=7)).isoformat()
        logger.info(f"[ItineraryAgent] 未指定出发日期，使用默认日期: {default_date}")
        ctx = ctx.model_copy(update={"start_date": default_date})
    if not ctx.end_date and ctx.start_date:
        start = date.fromisoformat(ctx.start_date)
        ctx = ctx.model_copy(update={"end_date": (start + timedelta(days=3)).isoformat()})

    from app.mcp.client import MCPClient
    mcp = MCPClient()

    events = list(state.events)
    events.append({
        "type": "agent_event",
        "data": {
            "event_type": "tool_call",
            "agent_role": "itinerary",
            "content": "正在并行查询酒店、机票、高铁信息...",
        },
    })

    t0 = time.time()
    hotels, flights, trains = await asyncio.gather(
        _query_hotels(mcp, ctx),
        _query_flights(mcp, ctx),
        _query_trains(mcp, ctx),
        return_exceptions=True,
    )
    elapsed = time.time() - t0
    logger.info(f"[ItineraryAgent] 并行查询完成, 耗时={elapsed:.2f}s")

    if isinstance(hotels, Exception):
        logger.warning(f"[ItineraryAgent] 酒店查询失败: {hotels}")
        hotels = []
    if isinstance(flights, Exception):
        logger.warning(f"[ItineraryAgent] 机票查询失败: {flights}")
        flights = []
    if isinstance(trains, Exception):
        logger.warning(f"[ItineraryAgent] 高铁查询失败: {trains}")
        trains = []

    logger.info(f"[ItineraryAgent] 查询结果: 酒店={len(hotels)}, 航班={len(flights)}, 高铁={len(trains)}")

    events.append({
        "type": "agent_event",
        "data": {
            "event_type": "tool_result",
            "agent_role": "itinerary",
            "content": f"查询完成: {len(hotels)}家酒店, {len(flights)}个航班, {len(trains)}个车次",
        },
    })

    recommended = _pick_recommended(ctx, hotels, flights, trains)

    if recommended:
        events.append({
            "type": "structured_data",
            "data": {
                "card_type": "itinerary_plan",
                "recommended": recommended,
            },
        })

    if flights:
        events.append({
            "type": "structured_data",
            "data": {"card_type": "flight_list", "items": flights},
        })
    if hotels:
        events.append({
            "type": "structured_data",
            "data": {"card_type": "hotel_list", "items": hotels},
        })
    if trains:
        events.append({
            "type": "structured_data",
            "data": {"card_type": "train_list", "items": trains},
        })

    response = await _generate_plan_summary(ctx, hotels, flights, trains, recommended)

    return {
        "response": response,
        "tool_results": [
            {"type": "hotels", "data": hotels},
            {"type": "flights", "data": flights},
            {"type": "trains", "data": trains},
            {"type": "recommended", "data": recommended},
        ],
        "current_agent": "itinerary",
        "needs_user_input": True,
        "events": events,
    }


def _pick_recommended(ctx, hotels: list, flights: list, trains: list) -> dict:
    """从查询结果中挑选性价比最优的交通+酒店组合。

    选择策略：
      - 交通：优先选经济舱/二等座中价格最低的航班或高铁
      - 酒店：优先选 4 星商务酒店（性价比平衡点）；没有则选评分最高的
    """
    rec = {"travel_info": {
        "origin": ctx.origin or "",
        "destination": ctx.destination,
        "start_date": ctx.start_date,
        "end_date": ctx.end_date,
    }}

    if flights:
        economy = [f for f in flights if f.get("cabin_class") == "经济舱"]
        pick = min(economy or flights, key=lambda x: x.get("price", float("inf")))
        rec["flight"] = pick
        rec["transport_type"] = "flight"
    elif trains:
        second_class = [t for t in trains if t.get("seat_type") == "二等座"]
        pick = min(second_class or trains, key=lambda x: x.get("price", float("inf")))
        rec["train"] = pick
        rec["transport_type"] = "train"

    if hotels:
        business = [h for h in hotels if h.get("stars") == 4]
        if business:
            rec["hotel"] = max(business, key=lambda x: x.get("rating", 0))
        else:
            rec["hotel"] = max(hotels, key=lambda x: x.get("rating", 0))

    if rec.get("flight") or rec.get("train"):
        transport_price = rec.get("flight", rec.get("train", {})).get("price", 0)
        hotel_price = rec.get("hotel", {}).get("price_per_night", 0)
        nights = 1
        if ctx.start_date and ctx.end_date:
            try:
                d1 = date.fromisoformat(ctx.start_date)
                d2 = date.fromisoformat(ctx.end_date)
                nights = max((d2 - d1).days, 1)
            except ValueError:
                pass
        rec["total_estimate"] = transport_price + hotel_price * nights
        rec["nights"] = nights

    return rec


async def _query_hotels(mcp, ctx) -> list[dict]:
    """查询目的地酒店列表。"""
    return await mcp.call_tool("get_hotel_list", {
        "city": ctx.destination,
        "check_in": ctx.start_date,
        "check_out": ctx.end_date,
    })


async def _query_flights(mcp, ctx) -> list[dict]:
    """查询航班列表，出发地未知时返回空列表。"""
    if not ctx.origin:
        return []
    return await mcp.call_tool("get_flights", {
        "origin": ctx.origin,
        "destination": ctx.destination,
        "date": ctx.start_date,
    })


async def _query_trains(mcp, ctx) -> list[dict]:
    """查询高铁车次列表，出发地未知时返回空列表。"""
    if not ctx.origin:
        return []
    return await mcp.call_tool("get_trains", {
        "origin": ctx.origin,
        "destination": ctx.destination,
        "date": ctx.start_date,
    })


async def _generate_plan_summary(ctx, hotels, flights, trains, recommended) -> str:
    """使用规划 LLM 生成完整行程方案摘要，引导用户确认。"""
    logger.info("[ItineraryAgent] 调用 LLM 生成行程方案摘要")
    llm = get_planning_llm()

    tools_info = []
    if flights:
        tools_info.append(f"航班选项({len(flights)}个): {_brief(flights)}")
    if trains:
        tools_info.append(f"高铁选项({len(trains)}个): {_brief(trains)}")
    if hotels:
        tools_info.append(f"酒店选项({len(hotels)}个): {_brief(hotels)}")

    rec_desc = ""
    if recommended.get("flight"):
        f = recommended["flight"]
        rec_desc += f"推荐航班: {f.get('flight_no','')} {f.get('airline','')} {f.get('depart_time','')}→{f.get('arrive_time','')} ¥{f.get('price','')}\n"
    elif recommended.get("train"):
        t = recommended["train"]
        rec_desc += f"推荐高铁: {t.get('train_no','')} {t.get('depart_time','')}→{t.get('arrive_time','')} ¥{t.get('price','')} {t.get('seat_type','')}\n"
    if recommended.get("hotel"):
        h = recommended["hotel"]
        rec_desc += f"推荐酒店: {h.get('name','')} {'⭐'*h.get('stars',0)} ¥{h.get('price_per_night','')}/晚\n"
    if recommended.get("total_estimate"):
        rec_desc += f"预估总费用: ¥{recommended['total_estimate']}（交通+{recommended.get('nights',1)}晚住宿）\n"

    input_text = (
        f"出差信息: {ctx.origin} → {ctx.destination}, "
        f"{ctx.start_date} ~ {ctx.end_date}, 事由: {ctx.reason}\n\n"
        f"查询结果:\n" + "\n".join(tools_info) + "\n\n"
        f"推荐方案:\n{rec_desc}\n"
        f"请生成完整的行程方案摘要，包含推荐的交通和住宿，最后询问用户是否同意此方案。"
        f"如果用户同意，将直接为其预订。"
    )

    chain = TRAVEL_PLANNING_PROMPT | llm
    result = await chain.ainvoke({
        "input": input_text,
        "chat_history": [],
        "available_tools": "酒店查询、机票查询、高铁查询",
    })
    return result.content


def _brief(items: list[dict], limit: int = 3) -> str:
    """截取列表前几项的关键信息用于摘要。"""
    if not items:
        return "暂无数据"
    preview = items[:limit]
    return str(preview)
