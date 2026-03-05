"""Context 治理器单元测试。"""

import pytest
from app.engine.context_manager import ContextManager


def test_estimate_tokens_chinese():
    cm = ContextManager()
    tokens = cm.estimate_tokens("你好世界")
    assert tokens == 6  # 4 chars * 1.5


def test_estimate_tokens_english():
    cm = ContextManager()
    tokens = cm.estimate_tokens("hello world")
    assert tokens > 0


def test_should_compact():
    cm = ContextManager()
    cm._token_usage["s1"] = int(cm.MAX_CONTEXT_TOKENS * 0.9)
    assert cm.should_compact("s1") is True

    cm._token_usage["s2"] = 100
    assert cm.should_compact("s2") is False


@pytest.mark.asyncio
async def test_compact_context():
    cm = ContextManager()
    messages = [
        {"role": "user", "content": f"消息 {i}"} for i in range(20)
    ]
    compacted = await cm.compact_context(messages, keep_recent=4)
    assert len(compacted) == 5  # 1 summary + 4 recent
    assert compacted[0]["role"] == "system"
    assert "[历史摘要]" in compacted[0]["content"]


def test_track_usage():
    cm = ContextManager()
    result = cm.track_usage("s1", "测试文本" * 100)
    assert result["session_tokens"] > 0
    assert result["max_tokens"] == cm.MAX_CONTEXT_TOKENS


def test_select_relevant_context():
    cm = ContextManager()
    candidates = [
        {"content": "北京到上海的机票", "recency_score": 5},
        {"content": "今天天气不错", "recency_score": 1},
        {"content": "上海酒店推荐", "recency_score": 3},
    ]
    result = cm.select_relevant_context("上海", candidates, top_k=2)
    assert len(result) == 2
