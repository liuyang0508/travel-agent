"""
Agent 模型模块：定义 Agent 角色、任务状态、任务节点和执行计划的数据结构。

职责：
    为任务规划器和编排器提供核心数据模型。

核心概念：
    - AgentRole：Agent 角色枚举，对应系统中的各个 Agent 节点。
    - TaskStatus：任务生命周期状态枚举。
    - TaskNode：DAG 中的原子任务节点，包含依赖关系和执行数据。
    - TaskPlan：由多个 TaskNode 组成的 DAG 执行计划。
    - AgentEvent：Agent 执行过程中产出的事件，用于前端实时展示。

与其他模块的关系：
    - 被 engine/task_planner 用于构建和管理任务 DAG。
    - 被 api/tasks 用于序列化任务查询响应。
    - AgentEvent 被 orchestrator 在流式输出中产出。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    """Agent 角色枚举，标识系统中的各个 Agent 节点。"""
    ORCHESTRATOR = "orchestrator"
    INTENT = "intent"
    QUERY_REWRITER = "query_rewriter"
    TRAVEL_APPLY = "travel_apply"
    ITINERARY = "itinerary"
    BOOKING = "booking"


class TaskStatus(str, Enum):
    """任务生命周期状态枚举。"""
    PENDING = "pending"
    RUNNING = "running"
    WAITING_USER = "waiting_user"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskNode(BaseModel):
    """DAG 中的一个原子任务节点。

    Attributes:
        task_id: 任务唯一 ID。
        name: 任务名称。
        description: 任务描述。
        agent_role: 负责执行该任务的 Agent 角色。
        status: 当前执行状态。
        dependencies: 前置依赖任务的 task_id 列表。
        input_data: 输入参数字典。
        output_data: 输出结果字典。
        error: 执行失败时的错误信息。
        started_at: 开始执行时间。
        completed_at: 执行完成时间。
    """
    task_id: str
    name: str
    description: str = ""
    agent_role: AgentRole
    status: TaskStatus = TaskStatus.PENDING
    dependencies: list[str] = Field(default_factory=list)
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class TaskPlan(BaseModel):
    """任务执行计划，由多个 TaskNode 组成的 DAG。

    Attributes:
        plan_id: 计划唯一 ID。
        session_id: 所属会话 ID。
        tasks: 任务节点列表。
        created_at: 计划创建时间。
    """
    plan_id: str
    session_id: str
    tasks: list[TaskNode] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def is_complete(self) -> bool:
        """判断计划中所有任务是否已完成或取消。

        Returns:
            bool: 全部完成或取消时返回 True。
        """
        return all(
            t.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED)
            for t in self.tasks
        )

    @property
    def current_tasks(self) -> list[TaskNode]:
        """获取当前可执行的任务（状态为 PENDING 且所有依赖已完成）。

        Returns:
            list[TaskNode]: 可立即执行的任务列表。
        """
        completed_ids = {
            t.task_id for t in self.tasks if t.status == TaskStatus.COMPLETED
        }
        return [
            t for t in self.tasks
            if t.status == TaskStatus.PENDING
            and all(d in completed_ids for d in t.dependencies)
        ]


class AgentEvent(BaseModel):
    """Agent 执行事件，用于 SSE/WebSocket 实时推送给前端。

    Attributes:
        event_type: 事件类型（thinking / tool_call / tool_result / message / error）。
        agent_role: 产出该事件的 Agent 角色。
        task_id: 关联的任务 ID（可选）。
        content: 事件内容文本。
        metadata: 附加元数据。
        timestamp: 事件产生时间。
    """
    event_type: str
    agent_role: AgentRole
    task_id: str | None = None
    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
