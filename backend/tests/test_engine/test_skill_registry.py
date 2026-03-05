"""Skills 注册中心单元测试。"""

import pytest
from app.engine.skill_registry import SkillRegistry, SkillNotFoundError, SkillParamError


def test_singleton():
    r1 = SkillRegistry.get_instance()
    r2 = SkillRegistry.get_instance()
    assert r1 is r2


def test_builtin_skills_registered():
    registry = SkillRegistry.get_instance()
    skills = registry.list_skills()
    assert len(skills) >= 3
    names = [s.name for s in skills]
    assert "full_travel_planning" in names
    assert "smart_hotel_recommend" in names
    assert "optimal_transport" in names


def test_list_by_category():
    registry = SkillRegistry.get_instance()
    travel = registry.list_skills(category="travel")
    assert all(s.category == "travel" for s in travel)


@pytest.mark.asyncio
async def test_execute_missing_skill():
    registry = SkillRegistry.get_instance()
    with pytest.raises(SkillNotFoundError):
        await registry.execute("nonexistent", {})


@pytest.mark.asyncio
async def test_execute_missing_params():
    registry = SkillRegistry.get_instance()
    with pytest.raises(SkillParamError):
        await registry.execute("smart_hotel_recommend", {})


@pytest.mark.asyncio
async def test_execute_smart_hotel():
    registry = SkillRegistry.get_instance()
    result = await registry.execute("smart_hotel_recommend", {
        "city": "上海",
        "check_in": "2026-03-10",
        "check_out": "2026-03-12",
    })
    assert "hotels" in result
    assert result["total_found"] > 0
