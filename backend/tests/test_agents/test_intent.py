"""意图识别评测集：覆盖差旅场景的典型 query。"""

import pytest

EVAL_DATASET = [
    # (user_input, expected_intent, min_confidence)
    ("我下周一需要去上海出差", "travel_apply", 0.7),
    ("帮我订一张明天去深圳的机票", "booking", 0.7),
    ("查一下北京到杭州的高铁", "itinerary_query", 0.7),
    ("推荐几个广州天河区的酒店", "itinerary_query", 0.6),
    ("我的出差申请审批到哪了", "travel_status", 0.7),
    ("今天天气怎么样", "general_chat", 0.5),
    ("你好", "general_chat", 0.5),
    ("下个月要去客户那边做技术交流", "travel_apply", 0.6),
    ("帮我看看那个酒店有没有空房", "itinerary_query", 0.5),
    ("取消我的出差申请", "travel_apply", 0.5),
]


@pytest.mark.parametrize("user_input,expected_intent,min_confidence", EVAL_DATASET)
def test_intent_eval_dataset_defined(user_input, expected_intent, min_confidence):
    """验证评测数据集的完整性。"""
    assert isinstance(user_input, str)
    assert expected_intent in [
        "travel_apply", "itinerary_query", "travel_status",
        "booking", "general_chat", "unclear",
    ]
    assert 0 <= min_confidence <= 1.0


MULTI_TURN_EVAL = [
    {
        "name": "完整出差申请流程",
        "turns": [
            {"user": "我需要出差", "expected_intent": "travel_apply"},
            {"user": "去上海", "context_update": {"destination": "上海"}},
            {"user": "下周一到周三", "context_update": {"start_date": "2026-03-09", "end_date": "2026-03-11"}},
            {"user": "拜访客户做技术交流", "context_update": {"reason": "拜访客户做技术交流"}},
        ],
    },
    {
        "name": "行程规划流程",
        "turns": [
            {"user": "帮我查查去上海怎么走", "expected_intent": "itinerary_query"},
            {"user": "高铁有哪些", "expected_intent": "itinerary_query"},
            {"user": "帮我订第一个", "expected_intent": "booking"},
        ],
    },
]


@pytest.mark.parametrize("scenario", MULTI_TURN_EVAL, ids=lambda s: s["name"])
def test_multi_turn_eval_defined(scenario):
    """验证多轮评测场景完整性。"""
    assert "name" in scenario
    assert len(scenario["turns"]) >= 2
