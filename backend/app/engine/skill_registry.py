"""
Skills 注册中心模块：管理和执行可复用的差旅技能包。

职责：
    集中注册、发现和执行差旅相关的 Skill（可复用工作流模板）。

设计思路（参照 Claude Code / Cursor 的 Skills 系统）：
    - 每个 Skill 是一个独立的工作流模板，封装了对 MCP 工具的组合调用。
    - 支持动态注册和按名称 / 分类发现。
    - 内置三个核心 Skill：完整差旅规划、智能酒店推荐、最优交通方案。
    - 执行前校验必填参数，缺失时抛出 SkillParamError。

与其他模块的关系：
    - 被 task_planner 在执行任务节点时调用。
    - 各 Skill handler 内部通过 mcp/client 调用后端服务。
    - 单例模式，通过 get_instance() 获取全局实例。
"""

from __future__ import annotations

import time
from typing import Any, Callable, Awaitable
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class Skill:
    """可复用的差旅技能定义。

    Attributes:
        name: 技能唯一名称。
        description: 技能功能描述。
        category: 技能分类（travel / booking / query / utility）。
        handler: 异步执行函数。
        required_params: 必填参数列表。
        optional_params: 可选参数列表。
    """
    name: str
    description: str
    category: str
    handler: Callable[..., Awaitable[dict[str, Any]]]
    required_params: list[str] = field(default_factory=list)
    optional_params: list[str] = field(default_factory=list)


class SkillRegistry:
    """Skill 注册中心，单例模式管理所有可用技能。

    Attributes:
        _instance: 全局单例引用。
        _skills: 以技能名称为键的注册表。
    """
    _instance: SkillRegistry | None = None

    def __init__(self):
        self._skills: dict[str, Skill] = {}

    @classmethod
    def get_instance(cls) -> SkillRegistry:
        """获取 SkillRegistry 全局单例（首次调用时自动注册内置 Skill）。

        Returns:
            SkillRegistry: 全局单例实例。
        """
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._register_builtin_skills()
            logger.info(f"[SkillRegistry] 初始化完成, "
                        f"已注册 {len(cls._instance._skills)} 个内置 Skill")
        return cls._instance

    def register(self, skill: Skill) -> None:
        """注册一个新的 Skill。

        Args:
            skill: 待注册的 Skill 实例。
        """
        logger.info(f"[SkillRegistry] 注册 Skill: {skill.name} ({skill.category})")
        self._skills[skill.name] = skill

    def get(self, name: str) -> Skill | None:
        """按名称获取 Skill。

        Args:
            name: Skill 名称。

        Returns:
            Skill | None: 找到的 Skill，不存在则返回 None。
        """
        return self._skills.get(name)

    def list_skills(self, category: str | None = None) -> list[Skill]:
        """列出所有已注册的 Skill，可按分类过滤。

        Args:
            category: 可选的分类过滤条件。

        Returns:
            list[Skill]: 符合条件的 Skill 列表。
        """
        skills = list(self._skills.values())
        if category:
            skills = [s for s in skills if s.category == category]
        return skills

    async def execute(self, name: str, params: dict[str, Any]) -> dict[str, Any]:
        """执行指定名称的 Skill。

        Args:
            name: Skill 名称。
            params: 执行参数字典。

        Returns:
            dict: Skill 执行结果。

        Raises:
            SkillNotFoundError: 指定名称的 Skill 不存在。
            SkillParamError: 缺少必填参数。
        """
        skill = self._skills.get(name)
        if not skill:
            raise SkillNotFoundError(f"Skill not found: {name}")

        missing = [p for p in skill.required_params if p not in params]
        if missing:
            raise SkillParamError(f"Missing required params: {missing}")

        logger.info(f"[SkillRegistry] 执行 Skill: {name}")
        t0 = time.time()
        result = await skill.handler(**params)
        elapsed = time.time() - t0
        logger.info(f"[SkillRegistry] Skill {name} 执行完毕, 耗时={elapsed:.2f}s")
        return result

    def _register_builtin_skills(self):
        """注册内置的核心 Skill。"""
        self.register(Skill(
            name="full_travel_planning",
            description="完整差旅规划：从申请到行程一条龙服务",
            category="travel",
            handler=_skill_full_travel_planning,
            required_params=["destination", "start_date", "end_date", "reason"],
            optional_params=["origin", "budget_limit", "preferences"],
        ))
        self.register(Skill(
            name="smart_hotel_recommend",
            description="智能酒店推荐：根据偏好和预算推荐最佳酒店",
            category="booking",
            handler=_skill_smart_hotel_recommend,
            required_params=["city", "check_in", "check_out"],
            optional_params=["budget", "preferences"],
        ))
        self.register(Skill(
            name="optimal_transport",
            description="最优交通方案：综合对比飞机和高铁，推荐性价比最高的选项",
            category="booking",
            handler=_skill_optimal_transport,
            required_params=["origin", "destination", "date"],
            optional_params=["prefer_type", "budget"],
        ))


async def _skill_full_travel_planning(**kwargs) -> dict[str, Any]:
    """完整差旅规划 Skill：提交出差申请。

    Args:
        **kwargs: 包含 destination、start_date、end_date、reason 等参数。

    Returns:
        dict: 包含申请结果和下一步指引。
    """
    logger.info(f"[Skill:full_travel_planning] 开始执行, 目的地={kwargs.get('destination')}")
    from app.mcp.client import MCPClient
    mcp = MCPClient()

    apply_result = await mcp.call_tool("travel_apply", {
        "user_id": kwargs.get("user_id", "default"),
        "destination": kwargs["destination"],
        "origin": kwargs.get("origin", ""),
        "start_date": kwargs["start_date"],
        "end_date": kwargs["end_date"],
        "reason": kwargs["reason"],
    })

    logger.info(f"[Skill:full_travel_planning] 申请提交完成")
    return {
        "apply": apply_result,
        "next_step": "等待审批通过后自动规划行程",
        "status": "申请已提交",
    }


async def _skill_smart_hotel_recommend(**kwargs) -> dict[str, Any]:
    """智能酒店推荐 Skill：查询并按评分排序，支持预算过滤。

    Args:
        **kwargs: 包含 city、check_in、check_out、budget（可选）等参数。

    Returns:
        dict: 包含排序后的酒店列表和统计信息。
    """
    logger.info(f"[Skill:smart_hotel_recommend] 查询酒店, 城市={kwargs.get('city')}")
    from app.mcp.client import MCPClient
    mcp = MCPClient()

    hotels = await mcp.call_tool("get_hotel_list", {
        "city": kwargs["city"],
        "check_in": kwargs["check_in"],
        "check_out": kwargs["check_out"],
    })

    budget = kwargs.get("budget", float("inf"))
    filtered = [h for h in hotels if h.get("price_per_night", 0) <= budget]
    sorted_hotels = sorted(filtered, key=lambda h: -h.get("rating", 0))

    logger.info(f"[Skill:smart_hotel_recommend] 查询到 {len(hotels)} 家, "
                f"预算内 {len(filtered)} 家")
    return {
        "hotels": sorted_hotels,
        "total_found": len(hotels),
        "within_budget": len(filtered),
    }


async def _skill_optimal_transport(**kwargs) -> dict[str, Any]:
    """最优交通方案 Skill：并行查询机票和高铁，按价格排序推荐。

    Args:
        **kwargs: 包含 origin、destination、date 等参数。

    Returns:
        dict: 包含推荐方案和全部选项。
    """
    import asyncio
    logger.info(f"[Skill:optimal_transport] 查询交通方案, "
                f"{kwargs.get('origin')} → {kwargs.get('destination')}")
    from app.mcp.client import MCPClient
    mcp = MCPClient()

    flights, trains = await asyncio.gather(
        mcp.call_tool("get_flights", kwargs),
        mcp.call_tool("get_trains", kwargs),
    )

    all_options = []
    for f in (flights or []):
        all_options.append({**f, "type": "flight"})
    for t in (trains or []):
        all_options.append({**t, "type": "train"})

    sorted_options = sorted(all_options, key=lambda x: x.get("price", float("inf")))

    logger.info(f"[Skill:optimal_transport] 航班={len(flights or [])}, "
                f"高铁={len(trains or [])}, 推荐={'有' if sorted_options else '无'}")
    return {
        "recommended": sorted_options[0] if sorted_options else None,
        "all_flights": flights,
        "all_trains": trains,
    }


class SkillNotFoundError(Exception):
    """指定名称的 Skill 不存在时抛出。"""
    pass


class SkillParamError(Exception):
    """Skill 执行缺少必填参数时抛出。"""
    pass
