"""
任务规划器模块：基于 DAG 的任务分解、依赖管理和执行编排。

职责：
    将复杂差旅需求分解为原子任务节点，构建 DAG 并按拓扑顺序执行。

设计思路（参照 Manus 的 Task Planning 机制）：
    - 优先使用预定义模板（_TASK_TEMPLATES）实例化已知意图的任务。
    - 未知意图时调用 LLM 动态分解任务。
    - 构建有向无环图 (DAG) 表达任务间的依赖关系。
    - 支持并行执行无依赖的任务，实时追踪任务状态。

与其他模块的关系：
    - 被 orchestrator 在需要多步骤任务规划时调用（预留能力）。
    - 依赖 models/agent 中的 TaskNode、TaskPlan 等数据结构。
    - 依赖 model_router.get_planning_llm 获取规划模型。
    - 依赖 skill_registry 执行具体任务对应的 Skill。
"""

from __future__ import annotations

import asyncio
import uuid
import time
from datetime import datetime
from typing import Any
from loguru import logger

from app.models.agent import TaskNode, TaskPlan, TaskStatus, AgentRole
from app.engine.model_router import get_planning_llm


class TaskPlanner:
    """DAG 任务规划器，负责任务分解、依赖管理和编排执行。

    Attributes:
        _plans: 以 plan_id 为键的任务计划缓存。
    """

    def __init__(self):
        self._plans: dict[str, TaskPlan] = {}

    async def create_plan(
        self, session_id: str, intent: str, context: dict[str, Any]
    ) -> TaskPlan:
        """根据意图和上下文创建任务执行计划。

        Args:
            session_id: 会话 ID。
            intent: 识别到的用户意图。
            context: 差旅上下文信息字典。

        Returns:
            TaskPlan: 创建好的任务计划（包含 DAG 节点列表）。
        """
        logger.info(f"[TaskPlanner] 创建任务计划, session={session_id}, intent={intent}")
        tasks = await self._decompose_tasks(intent, context)
        plan = TaskPlan(
            plan_id=f"plan-{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            tasks=tasks,
        )
        self._plans[plan.plan_id] = plan
        logger.info(f"[TaskPlanner] 计划创建完成, plan_id={plan.plan_id}, "
                     f"任务数={len(tasks)}")
        return plan

    async def _decompose_tasks(
        self, intent: str, context: dict[str, Any]
    ) -> list[TaskNode]:
        """基于意图将需求分解为 DAG 任务节点。

        Args:
            intent: 用户意图。
            context: 差旅上下文。

        Returns:
            list[TaskNode]: 任务节点列表。优先使用模板，无模板时走 LLM 动态分解。
        """
        templates = _TASK_TEMPLATES.get(intent)
        if templates:
            logger.debug(f"[TaskPlanner] 使用预定义模板分解, intent={intent}")
            return _instantiate_template(templates, context)

        logger.info(f"[TaskPlanner] 无预定义模板，使用 LLM 动态分解, intent={intent}")
        return await self._llm_decompose(intent, context)

    async def _llm_decompose(
        self, intent: str, context: dict[str, Any]
    ) -> list[TaskNode]:
        """使用 LLM 动态分解未知意图的任务。

        Args:
            intent: 用户意图。
            context: 差旅上下文。

        Returns:
            list[TaskNode]: 包含单个动态任务的列表（LLM 分解结果）。
        """
        logger.info(f"[TaskPlanner] LLM 动态分解开始, intent={intent}")
        try:
            llm = get_planning_llm()
            prompt = (
                f"将以下差旅需求分解为可执行的原子任务列表：\n"
                f"意图: {intent}\n"
                f"上下文: {context}\n\n"
                f"每个任务包含: name, description, agent_role, dependencies\n"
                f"agent_role 取值: orchestrator, intent, query_rewriter, travel_apply, itinerary, booking"
            )
            result = await asyncio.wait_for(llm.ainvoke(prompt), timeout=15)
            logger.debug(f"[TaskPlanner] LLM 分解结果: {result.content[:100]}")
            return [TaskNode(
                task_id=f"task-{uuid.uuid4().hex[:6]}",
                name="动态任务",
                description=result.content[:200],
                agent_role=AgentRole.ORCHESTRATOR,
            )]
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning(f"[TaskPlanner] LLM 动态分解失败或超时: {e}, 使用默认单任务")
            return [TaskNode(
                task_id=f"task-{uuid.uuid4().hex[:6]}",
                name="处理请求",
                description=f"处理 {intent} 类型的用户请求",
                agent_role=AgentRole.ORCHESTRATOR,
            )]

    def get_plan(self, plan_id: str) -> TaskPlan | None:
        """根据 plan_id 获取任务计划。

        Args:
            plan_id: 任务计划 ID。

        Returns:
            TaskPlan | None: 找到的计划，不存在则返回 None。
        """
        return self._plans.get(plan_id)

    def get_executable_tasks(self, plan_id: str) -> list[TaskNode]:
        """获取当前可执行的任务（所有前置依赖已完成）。

        Args:
            plan_id: 任务计划 ID。

        Returns:
            list[TaskNode]: 可立即执行的任务列表。
        """
        plan = self._plans.get(plan_id)
        if not plan:
            return []
        return plan.current_tasks

    def update_task_status(
        self, plan_id: str, task_id: str, status: TaskStatus, output: dict | None = None
    ) -> TaskNode | None:
        """更新指定任务的执行状态。

        Args:
            plan_id: 任务计划 ID。
            task_id: 任务节点 ID。
            status: 新的任务状态。
            output: 任务输出数据（可选）。

        Returns:
            TaskNode | None: 更新后的任务节点，未找到返回 None。
        """
        plan = self._plans.get(plan_id)
        if not plan:
            return None

        for task in plan.tasks:
            if task.task_id == task_id:
                task.status = status
                if status == TaskStatus.RUNNING:
                    task.started_at = datetime.now()
                elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                    task.completed_at = datetime.now()
                if output:
                    task.output_data = output
                logger.debug(f"[TaskPlanner] 任务状态更新: {task_id} → {status.value}")
                return task
        return None

    async def execute_plan(self, plan_id: str) -> TaskPlan:
        """按 DAG 拓扑顺序执行计划中的所有任务。

        Args:
            plan_id: 任务计划 ID。

        Returns:
            TaskPlan: 执行完毕的任务计划。

        Raises:
            ValueError: plan_id 对应的计划不存在。
        """
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")

        logger.info(f"[TaskPlanner] 开始执行计划 {plan_id}")
        t0 = time.time()

        while not plan.is_complete:
            ready = plan.current_tasks
            if not ready:
                logger.warning(f"[TaskPlanner] 无可执行任务但计划未完成, plan_id={plan_id}")
                break

            for task in ready:
                self.update_task_status(plan_id, task.task_id, TaskStatus.RUNNING)
                try:
                    result = await self._execute_task(task)
                    self.update_task_status(
                        plan_id, task.task_id, TaskStatus.COMPLETED, result
                    )
                except Exception as e:
                    logger.error(f"[TaskPlanner] 任务执行失败: task={task.task_id}, "
                                 f"错误={e}", exc_info=True)
                    self.update_task_status(plan_id, task.task_id, TaskStatus.FAILED)
                    task.error = str(e)

        elapsed = time.time() - t0
        logger.info(f"[TaskPlanner] 计划执行完毕, plan_id={plan_id}, 耗时={elapsed:.2f}s")
        return plan

    async def _execute_task(self, task: TaskNode) -> dict:
        """执行单个任务节点，通过 SkillRegistry 查找并调用对应的 Skill。

        Args:
            task: 待执行的任务节点。

        Returns:
            dict: 任务执行结果。
        """
        from app.engine.skill_registry import SkillRegistry
        registry = SkillRegistry.get_instance()

        skill_name = task.input_data.get("skill")
        if skill_name:
            logger.info(f"[TaskPlanner] 执行 Skill: {skill_name}, task={task.task_id}")
            return await registry.execute(skill_name, task.input_data.get("params", {}))

        return {"status": "completed", "message": f"Task {task.name} executed"}


def _instantiate_template(
    template: list[dict], context: dict[str, Any]
) -> list[TaskNode]:
    """从预定义模板实例化任务节点列表。

    Args:
        template: 任务模板定义列表。
        context: 差旅上下文，注入到每个任务的 input_data 中。

    Returns:
        list[TaskNode]: 实例化后的任务节点列表（已建立依赖关系）。
    """
    nodes = []
    for t in template:
        node = TaskNode(
            task_id=f"task-{uuid.uuid4().hex[:6]}",
            name=t["name"],
            description=t.get("description", ""),
            agent_role=AgentRole(t["agent_role"]),
            dependencies=[],
            input_data={**t.get("input_data", {}), "context": context},
        )
        nodes.append(node)

    # 根据模板中的 depends_on 索引建立节点间的依赖关系
    for i, t in enumerate(template):
        dep_indices = t.get("depends_on", [])
        nodes[i].dependencies = [nodes[d].task_id for d in dep_indices if d < len(nodes)]

    return nodes


_TASK_TEMPLATES: dict[str, list[dict]] = {
    "general_chat": [
        {
            "name": "通用对话",
            "description": "处理用户的通用问题或闲聊",
            "agent_role": "orchestrator",
            "depends_on": [],
        },
    ],
    "unclear": [
        {
            "name": "意图澄清",
            "description": "引导用户明确差旅需求",
            "agent_role": "orchestrator",
            "depends_on": [],
        },
    ],
    "travel_apply": [
        {
            "name": "收集出差信息",
            "description": "收集目的地、日期、事由等必要信息",
            "agent_role": "travel_apply",
            "depends_on": [],
        },
        {
            "name": "提交出差申请",
            "description": "通过钉钉接口提交出差申请",
            "agent_role": "travel_apply",
            "depends_on": [0],
            "input_data": {"skill": "full_travel_planning"},
        },
        {
            "name": "等待审批结果",
            "description": "跟踪审批状态",
            "agent_role": "travel_apply",
            "depends_on": [1],
        },
    ],
    "itinerary_query": [
        {
            "name": "查询改写",
            "description": "优化用户查询，补全缺失信息",
            "agent_role": "query_rewriter",
            "depends_on": [],
        },
        {
            "name": "查询交通方案",
            "description": "并行查询机票和高铁",
            "agent_role": "itinerary",
            "depends_on": [0],
            "input_data": {"skill": "optimal_transport"},
        },
        {
            "name": "查询酒店",
            "description": "查询目的地酒店",
            "agent_role": "itinerary",
            "depends_on": [0],
            "input_data": {"skill": "smart_hotel_recommend"},
        },
        {
            "name": "生成综合方案",
            "description": "汇总交通和住宿信息，生成最优方案",
            "agent_role": "itinerary",
            "depends_on": [1, 2],
        },
    ],
}
