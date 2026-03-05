"""
出差申请 Agent 模块。

职责：
    处理出差申请的完整生命周期：信息收集 → 提交申请 → 状态查询。

设计思路：
    - 先检查必填字段（目的地、日期、事由）是否齐全。
    - 缺失字段时，调用 LLM 生成自然语言追问，逐个收集信息。
    - 字段齐全后，通过 MCPClient 调用后端服务提交申请。
    - 已有申请单号时，查询审批状态。
    - 审批通过后引导用户进入行程规划流程。

与其他模块的关系：
    - 由 orchestrator 在意图为 travel_apply / travel_status 时路由至此。
    - 依赖 state.AgentState 和 TravelContext 获取/更新差旅上下文。
    - 依赖 model_router.get_chat_llm 生成自然语言追问。
    - 通过 MCPClient 与后端差旅服务交互（提交申请、查询状态）。
"""

from __future__ import annotations

from loguru import logger

from app.agents.state import AgentState
from app.engine.model_router import get_chat_llm


async def travel_apply_agent(state: AgentState) -> dict:
    """出差申请主流程：根据上下文决定收集信息 / 提交申请 / 查询状态。

    Args:
        state: 全局 Agent 状态，主要使用 travel_context 和 user_id。

    Returns:
        dict: 包含 response、travel_context、needs_user_input 等字段的状态更新。

    核心流程：
        1. 检查必填字段是否齐全
        2. 缺失 → 生成追问提示，等待用户补充
        3. 齐全且无申请单号 → 提交申请
        4. 已有申请单号 → 查询审批状态
    """
    logger.info("[TravelApplyAgent] 开始处理出差申请流程...")

    ctx = state.travel_context

    # 检查必填字段
    missing = _check_required_fields(ctx)

    if missing:
        logger.info(f"[TravelApplyAgent] 缺少必填字段: {missing}")
        prompt = _build_collection_prompt(missing, ctx)
        llm = get_chat_llm()
        result = await llm.ainvoke(prompt)

        return {
            "response": result.content,
            "needs_user_input": True,
            "current_agent": "travel_apply",
            "events": state.events + [{
                "type": "agent_event",
                "data": {
                    "event_type": "message",
                    "agent_role": "travel_apply",
                    "content": f"需要补充信息: {', '.join(missing)}",
                },
            }],
        }

    # 尚未提交申请 → 提交
    if not ctx.apply_id:
        logger.info("[TravelApplyAgent] 必填字段齐全，准备提交申请")
        return await _submit_application(state)

    # 已有申请单号 → 查询状态
    logger.info(f"[TravelApplyAgent] 查询申请状态 apply_id={ctx.apply_id}")
    return await _check_status(state)


def _check_required_fields(ctx) -> list[str]:
    """检查出差申请必填字段是否齐全。

    Args:
        ctx: TravelContext 差旅上下文。

    Returns:
        list[str]: 缺失字段的中文名称列表，为空表示全部齐全。
    """
    missing = []
    if not ctx.destination:
        missing.append("目的地")
    if not ctx.start_date:
        missing.append("出发日期")
    if not ctx.end_date:
        missing.append("返回日期")
    if not ctx.reason:
        missing.append("出差事由")
    return missing


def _build_collection_prompt(missing: list[str], ctx) -> str:
    """构建信息收集的 LLM 提示词，引导模型生成自然语言追问。

    Args:
        missing: 缺失字段中文名称列表。
        ctx: TravelContext 差旅上下文，用于展示已收集信息。

    Returns:
        str: 拼接好的提示词文本。
    """
    known = []
    if ctx.destination:
        known.append(f"目的地: {ctx.destination}")
    if ctx.origin:
        known.append(f"出发地: {ctx.origin}")
    if ctx.start_date:
        known.append(f"出发日期: {ctx.start_date}")
    if ctx.end_date:
        known.append(f"返回日期: {ctx.end_date}")
    if ctx.reason:
        known.append(f"出差事由: {ctx.reason}")

    known_str = "\n".join(known) if known else "暂无"

    return (
        f"用户想要发起出差申请。\n"
        f"已收集的信息:\n{known_str}\n\n"
        f"还需要收集: {', '.join(missing)}\n\n"
        f"请用自然、友好的语气向用户询问缺失信息。每次只问一个问题。"
    )


async def _submit_application(state: AgentState) -> dict:
    """通过 MCP 提交出差申请。

    Args:
        state: 全局 Agent 状态，需要 user_id 和 travel_context。

    Returns:
        dict: 包含提交结果响应和更新后的 travel_context。
    """
    ctx = state.travel_context

    from app.mcp.client import MCPClient
    mcp = MCPClient()

    try:
        logger.info(f"[TravelApplyAgent] 提交申请: {ctx.origin} → {ctx.destination}, "
                     f"{ctx.start_date} ~ {ctx.end_date}")
        result = await mcp.call_tool("travel_apply", {
            "user_id": state.user_id,
            "destination": ctx.destination,
            "origin": ctx.origin or "未指定",
            "start_date": ctx.start_date,
            "end_date": ctx.end_date,
            "reason": ctx.reason,
        })

        apply_id = result.get("apply_id", "MOCK_ID")
        # 更新上下文：写入申请单号和初始状态
        updated_ctx = ctx.model_copy(update={
            "apply_id": apply_id,
            "apply_status": "pending",
        })

        response = (
            f"出差申请已提交成功！\n\n"
            f"- 申请编号: {apply_id}\n"
            f"- 目的地: {ctx.destination}\n"
            f"- 日期: {ctx.start_date} ~ {ctx.end_date}\n"
            f"- 事由: {ctx.reason}\n\n"
            f"审批通过后我会第一时间通知您，届时可以帮您规划行程。"
        )

        logger.info(f"[TravelApplyAgent] 申请提交成功 apply_id={apply_id}")

        return {
            "response": response,
            "travel_context": updated_ctx,
            "needs_user_input": False,
            "current_agent": "travel_apply",
            "events": state.events + [{
                "type": "agent_event",
                "data": {
                    "event_type": "tool_call",
                    "agent_role": "travel_apply",
                    "content": f"出差申请已提交 (ID: {apply_id})",
                },
            }, {
                "type": "structured_data",
                "data": {
                    "card_type": "approval_status",
                    "items": [result],
                },
            }],
        }
    except Exception as e:
        logger.error(f"[TravelApplyAgent] 提交申请失败: {e}", exc_info=True)
        return {
            "response": f"抱歉，提交出差申请时遇到问题: {e}。请稍后重试。",
            "error": str(e),
        }


async def _check_status(state: AgentState) -> dict:
    """通过 MCP 查询出差申请的审批状态。

    Args:
        state: 全局 Agent 状态，需要 travel_context.apply_id。

    Returns:
        dict: 包含审批状态响应和更新后的 travel_context。
              审批通过时引导用户进入行程规划。
    """
    ctx = state.travel_context
    from app.mcp.client import MCPClient
    mcp = MCPClient()

    try:
        result = await mcp.call_tool("travel_apply_status", {
            "apply_id": ctx.apply_id,
        })
        status = result.get("status", ctx.apply_status)
        updated_ctx = ctx.model_copy(update={"apply_status": status})

        # 状态码转中文
        status_text = {
            "pending": "审批中",
            "approved": "已通过",
            "rejected": "已驳回",
        }.get(status, status)

        logger.info(f"[TravelApplyAgent] 申请 {ctx.apply_id} 状态: {status_text}")

        response = f"出差申请 {ctx.apply_id} 当前状态: **{status_text}**"

        # 审批通过时引导用户进入行程规划
        if status == "approved":
            response += "\n\n审批已通过！需要我帮您规划行程吗？（酒店、机票、高铁等）"

        return {
            "response": response,
            "travel_context": updated_ctx,
            "needs_user_input": status == "approved",
            "current_agent": "travel_apply",
            "events": state.events + [{
                "type": "structured_data",
                "data": {
                    "card_type": "approval_status",
                    "items": [result],
                },
            }],
        }
    except Exception as e:
        logger.error(f"[TravelApplyAgent] 查询审批状态失败: {e}", exc_info=True)
        return {"response": f"查询审批状态失败: {e}", "error": str(e)}
