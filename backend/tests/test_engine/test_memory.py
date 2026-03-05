"""Memory 管理器单元测试。"""

import pytest
from app.engine.memory_manager import MemoryManager


@pytest.mark.asyncio
async def test_short_term_memory():
    mm = MemoryManager()
    await mm.save_short_term("s1", "user", "我要去上海出差")
    await mm.save_short_term("s1", "assistant", "好的，请问什么时间？")

    msgs = await mm.get_short_term("s1")
    assert len(msgs) == 2
    assert msgs[0]["content"] == "我要去上海出差"


@pytest.mark.asyncio
async def test_short_term_limit():
    mm = MemoryManager()
    for i in range(60):
        await mm.save_short_term("s1", "user", f"message {i}")

    msgs = await mm.get_short_term("s1", limit=100)
    assert len(msgs) == 50


@pytest.mark.asyncio
async def test_long_term_memory():
    mm = MemoryManager()
    await mm.save_long_term("u1", "preferred_airline", "中国国航")

    val = await mm.get_long_term("u1", "preferred_airline")
    assert val == "中国国航"


@pytest.mark.asyncio
async def test_user_preferences():
    mm = MemoryManager()
    await mm.save_long_term("u1", "preferred_hotel_brand", "亚朵")
    await mm.save_long_term("u1", "budget_level", "中等")

    prefs = await mm.get_user_preferences("u1")
    assert prefs["preferred_hotel_brand"] == "亚朵"
    assert prefs["budget_level"] == "中等"


@pytest.mark.asyncio
async def test_working_memory():
    mm = MemoryManager()
    await mm.update_working_memory("s1", "current_step", "collecting_info")

    working = await mm.get_working_memory("s1")
    assert working["current_step"] == "collecting_info"

    await mm.clear_working_memory("s1")
    working = await mm.get_working_memory("s1")
    assert working == {}


@pytest.mark.asyncio
async def test_context_summary():
    mm = MemoryManager()
    await mm.save_short_term("s1", "user", "我要去上海出差")
    await mm.save_long_term("u1", "preferred_airline", "国航")
    await mm.update_working_memory("s1", "step", "apply")

    summary = await mm.build_context_summary("s1", "u1")
    assert "上海" in summary or "国航" in summary
