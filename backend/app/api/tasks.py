"""
任务 API 模块：提供任务计划的查询接口。

职责：
    暴露任务计划（TaskPlan）的查询端点，支持按 plan_id 和 session_id 查询。

与其他模块的关系：
    - 被 main.py 注册到 FastAPI 应用（前缀 /api/tasks）。
    - 依赖 models/agent.TaskPlan 数据结构。
    - 任务计划由 engine/task_planner 创建和管理（当前通过内存字典存储）。
"""

from fastapi import APIRouter
from loguru import logger

from app.models.agent import TaskPlan

router = APIRouter()

_task_plans: dict[str, TaskPlan] = {}


@router.get("/{plan_id}", response_model=TaskPlan | None)
async def get_task_plan(plan_id: str):
    """根据 plan_id 查询任务计划。

    Args:
        plan_id: 任务计划 ID。

    Returns:
        TaskPlan | None: 找到的计划，不存在时返回 None。
    """
    logger.info(f"[Tasks] 查询任务计划: plan_id={plan_id}")
    plan = _task_plans.get(plan_id)
    if not plan:
        logger.debug(f"[Tasks] 任务计划未找到: plan_id={plan_id}")
    return plan


@router.get("/session/{session_id}")
async def get_session_tasks(session_id: str):
    """根据 session_id 查询关联的所有任务计划。

    Args:
        session_id: 会话 ID。

    Returns:
        list[TaskPlan]: 该会话下的任务计划列表。
    """
    logger.info(f"[Tasks] 查询会话任务计划: session_id={session_id}")
    plans = [p for p in _task_plans.values() if p.session_id == session_id]
    logger.debug(f"[Tasks] 找到 {len(plans)} 个计划")
    return plans
