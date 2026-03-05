"""任务规划器单元测试。"""

import pytest
from app.engine.task_planner import TaskPlanner, _TASK_TEMPLATES
from app.models.agent import TaskStatus


@pytest.mark.asyncio
async def test_create_plan_travel_apply():
    planner = TaskPlanner()
    plan = await planner.create_plan(
        session_id="test-session",
        intent="travel_apply",
        context={"destination": "上海", "start_date": "2026-03-10"},
    )
    assert plan.plan_id.startswith("plan-")
    assert len(plan.tasks) == 3
    assert plan.tasks[0].name == "收集出差信息"


@pytest.mark.asyncio
async def test_create_plan_itinerary():
    planner = TaskPlanner()
    plan = await planner.create_plan(
        session_id="test-session",
        intent="itinerary_query",
        context={"origin": "北京", "destination": "上海"},
    )
    assert len(plan.tasks) == 4
    parallel_tasks = [t for t in plan.tasks if t.name in ("查询交通方案", "查询酒店")]
    assert len(parallel_tasks) == 2


@pytest.mark.asyncio
async def test_get_executable_tasks():
    planner = TaskPlanner()
    plan = await planner.create_plan(
        session_id="test-session",
        intent="travel_apply",
        context={},
    )
    ready = planner.get_executable_tasks(plan.plan_id)
    assert len(ready) == 1
    assert ready[0].name == "收集出差信息"


@pytest.mark.asyncio
async def test_update_task_status():
    planner = TaskPlanner()
    plan = await planner.create_plan(
        session_id="test-session",
        intent="travel_apply",
        context={},
    )
    first_task = plan.tasks[0]
    planner.update_task_status(plan.plan_id, first_task.task_id, TaskStatus.COMPLETED)

    assert first_task.status == TaskStatus.COMPLETED
    assert first_task.completed_at is not None

    ready = planner.get_executable_tasks(plan.plan_id)
    assert any(t.name == "提交出差申请" for t in ready)


def test_task_templates_exist():
    assert "travel_apply" in _TASK_TEMPLATES
    assert "itinerary_query" in _TASK_TEMPLATES
